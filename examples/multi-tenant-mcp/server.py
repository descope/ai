import asyncio
import os
import ssl
import certifi
import aiohttp
from descope import DescopeClient
from descope.exceptions import AuthException
from fastmcp import FastMCP
from fastmcp.server.auth.providers.descope import DescopeProvider
from fastmcp.server.context import Context
from fastmcp.server.dependencies import get_access_token
from dotenv import load_dotenv
import logging
from starlette.responses import FileResponse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Descope & server config ---

CONFIG_URL = os.getenv("DESCOPE_CONFIG_URL")
DESCOPE_PROJECT_ID = os.getenv("DESCOPE_PROJECT_ID")
DESCOPE_BASE_URL = os.getenv("DESCOPE_BASE_URL", "https://api.descope.com")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:3000")
DESCOPE_MANAGEMENT_KEY = os.getenv("DESCOPE_MANAGEMENT_KEY")

# Demo tool tags — example tools scoped to these tenant ids when currentTenant matches
TENANT_A = "tenant-a"
TENANT_B = "tenant-b"

if not DESCOPE_PROJECT_ID:
    raise ValueError("DESCOPE_PROJECT_ID environment variable must be set")

if CONFIG_URL:
    auth_provider = DescopeProvider(config_url=CONFIG_URL, base_url=SERVER_URL)
else:
    auth_provider = DescopeProvider(
        base_url=SERVER_URL,
        project_id=DESCOPE_PROJECT_ID,
        descope_base_url=DESCOPE_BASE_URL,
    )

mcp = FastMCP(name="Multi-tenant MCP Server (Descope)", auth=auth_provider)
app = mcp.http_app(path="/mcp")

# Management client (used by switch_tenant). Requires DESCOPE_MANAGEMENT_KEY.
_descope_mgmt: DescopeClient | None = None
if DESCOPE_MANAGEMENT_KEY:
    _descope_mgmt = DescopeClient(
        project_id=DESCOPE_PROJECT_ID,
        management_key=DESCOPE_MANAGEMENT_KEY,
        base_url=DESCOPE_BASE_URL,
    )


@app.route("/", methods=["GET"])
async def serve_index(request):
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))


USERINFO_URL = f"{DESCOPE_BASE_URL.rstrip('/')}/oauth2/v1/userinfo"


def _ssl_connector() -> aiohttp.TCPConnector:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return aiohttp.TCPConnector(ssl=ssl_context)


async def fetch_descope_userinfo(bearer_token: str) -> dict | None:
    """GET Descope OIDC UserInfo (`/oauth2/v1/userinfo`) using the caller's access token."""
    headers = {"Authorization": f"Bearer {bearer_token}", "Accept": "application/json"}
    async with aiohttp.ClientSession(connector=_ssl_connector()) as session:
        try:
            async with session.get(USERINFO_URL, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.warning(
                        "userinfo failed: %s %s", response.status, text[:500]
                    )
                    return None
                return await response.json()
        except Exception as e:
            logger.exception("userinfo request error: %s", e)
            return None


def extract_current_tenant(userinfo: dict) -> str | None:
    """Resolve `currentTenant` from UserInfo payload (handles common Descope shapes)."""
    if not userinfo:
        return None
    direct = userinfo.get("currentTenant")
    if direct is not None:
        return str(direct)

    ca = (
        userinfo.get("customAttributes")
        or userinfo.get("custom_attributes")
        or {}
    )
    if isinstance(ca, dict):
        v = ca.get("currentTenant")
        if v is not None:
            return str(v)

    nsec = userinfo.get("nsec")
    if isinstance(nsec, dict):
        v = nsec.get("currentTenant")
        if v is not None:
            return str(v)

    return None


def login_id_from_access_token_claims(claims: dict) -> str | None:
    """Pick a Descope login id for Management API updates."""
    email = claims.get("email")
    if email:
        return str(email)
    lids = claims.get("loginIds")
    if isinstance(lids, list) and lids:
        return str(lids[0])
    pn = claims.get("preferred_username")
    if pn:
        return str(pn)
    sub = claims.get("sub")
    if sub:
        return str(sub)
    return None


async def load_userinfo_and_tenant() -> tuple[dict | None, str | None, str | None]:
    """Returns (userinfo, current_tenant, error_message)."""
    access = get_access_token()
    if not access:
        return None, None, "Authentication required: no bearer token on this request."
    userinfo = await fetch_descope_userinfo(access.token)
    if userinfo is None:
        return None, None, "Could not retrieve user profile from Descope UserInfo endpoint."
    tenant = extract_current_tenant(userinfo)
    return userinfo, tenant, None


def tenant_guard_error(expected: str, actual: str | None) -> str:
    return (
        f"This tool belongs to tenant {expected!r}, but UserInfo reports "
        f"currentTenant={actual!r}. "
        f"Call switch_tenant with tenant_id={expected!r} first."
    )


def _truthy(val: object) -> bool:
    if val is True:
        return True
    if val is False or val is None:
        return False
    return str(val).strip().lower() in ("true", "1", "yes")


def tenant_requires_sso_block(load: dict, settings: dict) -> tuple[bool, str]:
    """Returns (blocked, human-readable reason). SSO / federated tenants skip MCP-side switch."""

    reasons: list[str] = []

    if _truthy(load.get("enforceSSO")):
        reasons.append("enforceSSO is enabled on the tenant")
    if _truthy(settings.get("enforceSSO")):
        reasons.append("enforceSSO is enabled in tenant session settings")

    auth_type = str(settings.get("authType") or "").strip().lower()
    if auth_type in ("saml", "oidc"):
        reasons.append(
            f"tenant authentication type is {auth_type.upper()} (federated SSO)"
        )

    suite = settings.get("ssoSetupSuiteSettings")
    if isinstance(suite, dict) and _truthy(suite.get("enabled")):
        reasons.append("SSO Setup Suite is enabled for this tenant")

    federated = load.get("federatedAppIds") or []
    if isinstance(federated, list) and len(federated) > 0:
        reasons.append("tenant has federated SSO application IDs configured")

    if reasons:
        return True, "; ".join(reasons)
    return False, ""


async def resolve_tenant_for_switch(
    raw_tenant_id: str,
) -> tuple[str | None, str | None]:
    """Validate tenant exists via Management API and is eligible for MCP switch.

    Returns (canonical_tenant_id, error_message).
    """

    tenant_key = raw_tenant_id.strip()
    if not tenant_key:
        return None, "tenant_id must be a non-empty string."

    if _descope_mgmt is None:
        return (
            None,
            "Management API is not configured. Set DESCOPE_MANAGEMENT_KEY so "
            "tenant lookup and switching can run.",
        )

    def _load():
        return _descope_mgmt.mgmt.tenant.load(tenant_key)

    try:
        tenant_row = await asyncio.to_thread(_load)
    except AuthException as e:
        code = getattr(e, "status_code", None)
        msg = (
            getattr(e, "error_message", None)
            or getattr(e, "error_description", None)
            or str(e)
        ).lower()
        if code == 404 or "not found" in msg or "could not find" in msg:
            return None, (
                f"No Descope tenant exists with id {tenant_key!r}. "
                "Create the tenant in the Descope Console or correct the tenant id."
            )
        logger.warning("mgmt.tenant.load failed: %s", e)
        return None, f"Descope Management API error while loading tenant: {e}"

    canonical_id = str(tenant_row.get("id") or tenant_key)

    if _truthy(tenant_row.get("disabled")):
        return (
            None,
            f"Tenant {canonical_id!r} is disabled in Descope; switching is not allowed.",
        )

    def _load_settings():
        return _descope_mgmt.mgmt.tenant.load_settings(canonical_id)

    try:
        settings_row = await asyncio.to_thread(_load_settings)
    except AuthException as e:
        logger.warning("mgmt.tenant.load_settings failed: %s", e)
        settings_row = {}

    blocked, detail = tenant_requires_sso_block(tenant_row, settings_row)
    if blocked:
        return (
            None,
            "This tenant uses or enforces SSO in Descope; switching active tenant "
            "from this MCP session is not supported—sign in through your IdP / SSO "
            f"flow instead. Details: {detail}",
        )

    return canonical_id, None


async def sync_session_tenant_visibility(ctx: Context, current: str | None) -> None:
    """Per-session FastMCP visibility: only tools tagged for the active tenant are listed.

    Tenant-tagged tools are disabled globally; session rules re-enable the matching tag.
    """
    if current == TENANT_A:
        await ctx.enable_components(tags={TENANT_A}, components={"tool"})
        await ctx.disable_components(tags={TENANT_B}, components={"tool"})
    elif current == TENANT_B:
        await ctx.enable_components(tags={TENANT_B}, components={"tool"})
        await ctx.disable_components(tags={TENANT_A}, components={"tool"})
    else:
        await ctx.disable_components(
            tags={TENANT_A, TENANT_B}, components={"tool"}
        )


@mcp.tool
async def switch_tenant(tenant_id: str, ctx: Context) -> str:
    """Switch which tenant context is active for your user.

    Stores the selection in Descope as the user custom attribute `currentTenant`
    via the Management API (`mgmt.user.patch`). MCP clients read the active
    tenant through the UserInfo endpoint on each subsequent tool call.

    Args:
        tenant_id: Descope tenant id — must exist (`mgmt.tenant.load`). Tenants that
            enforce SSO or use SAML/OIDC federated login cannot be switched here.
    """
    _ui, current_before, err = await load_userinfo_and_tenant()
    if err:
        return err
    await sync_session_tenant_visibility(ctx, current_before)

    canonical_id, tenant_err = await resolve_tenant_for_switch(tenant_id)
    if tenant_err:
        return tenant_err
    assert canonical_id is not None
    assert _descope_mgmt is not None

    access = get_access_token()
    assert access is not None
    login_id = login_id_from_access_token_claims(access.claims or {})
    if not login_id:
        return (
            "Cannot resolve a Descope login id from token claims "
            "(expected email or loginIds). Cannot update user."
        )

    def _patch():
        # patch() merges fields; update() overwrites unspecified fields — avoid for partial custom_attributes
        _descope_mgmt.mgmt.user.patch(
            login_id=login_id,
            custom_attributes={"currentTenant": canonical_id},
        )

    try:
        await asyncio.to_thread(_patch)
    except AuthException as e:
        logger.warning("mgmt.user.patch failed: %s", e)
        return f"Descope Management API error while updating user: {e}"

    confirmed = await fetch_descope_userinfo(access.token)
    after = extract_current_tenant(confirmed or {})
    await sync_session_tenant_visibility(ctx, after)
    return (
        f"Switched active tenant to {canonical_id!r} for login_id={login_id!r}. "
        f"UserInfo currentTenant is now {after!r}."
    )


@mcp.tool(tags={TENANT_A})
async def tenant_a_inventory_snapshot(ctx: Context) -> str:
    """Tenant A demo tool: pretend inventory snapshot (only when current tenant is tenant-a)."""
    _userinfo, current, err = await load_userinfo_and_tenant()
    if err:
        return err
    await sync_session_tenant_visibility(ctx, current)
    if current != TENANT_A:
        return tenant_guard_error(TENANT_A, current)

    sku = (_userinfo or {}).get("email") or (_userinfo or {}).get("sub") or "user"
    return (
        f"[Tenant A — inventory_snapshot] Snapshot OK for identifier {sku!r}. "
        "This tool is exclusive to tenant-a."
    )


@mcp.tool(tags={TENANT_B})
async def tenant_b_metrics_ping(ctx: Context) -> str:
    """Tenant B demo tool #1: lightweight metrics ping (tenant-b only)."""
    _userinfo, current, err = await load_userinfo_and_tenant()
    if err:
        return err
    await sync_session_tenant_visibility(ctx, current)
    if current != TENANT_B:
        return tenant_guard_error(TENANT_B, current)

    return "[Tenant B — metrics_ping] pong (dummy metrics channel)."


@mcp.tool(tags={TENANT_B})
async def tenant_b_notes_echo(note: str, ctx: Context) -> str:
    """Tenant B demo tool #2: echoes a note (tenant-b only)."""
    _userinfo, current, err = await load_userinfo_and_tenant()
    if err:
        return err
    await sync_session_tenant_visibility(ctx, current)
    if current != TENANT_B:
        return tenant_guard_error(TENANT_B, current)

    snippet = note.strip()[:200]
    return f"[Tenant B — notes_echo] Received: {snippet!r}"


# Hide tenant-scoped tools by default; each session re-enables the tools for UserInfo currentTenant.
mcp.disable(tags={TENANT_A, TENANT_B}, components={"tool"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=3000)
