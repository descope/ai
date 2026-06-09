import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from descope_mcp import DescopeMCP, require_scopes, validate_token
from fastmcp import FastMCP
from fastmcp.server.auth.providers.descope import DescopeProvider
from starlette.requests import Request
from starlette.responses import JSONResponse

_BASE_URL = (
    os.environ.get("RENDER_EXTERNAL_URL")
    or os.environ.get("SERVER_URL")
    or "http://localhost:8000"
)

auth = DescopeProvider(
    config_url=os.environ["DESCOPE_CONFIG_URL"],
    base_url=_BASE_URL,
    scopes_supported=["mcp:bigquery.read", "mcp:bigquery.write"],
)

DescopeMCP(
    well_known_url=os.environ["DESCOPE_CONFIG_URL"],
    management_key=os.environ.get("DESCOPE_MANAGEMENT_KEY"),
    mcp_server_url=_BASE_URL,
)

mcp = FastMCP("descope-bigquery-mcp", auth=auth)


def _project_id_from_config_url(config_url: str) -> str | None:
    path_parts = [part for part in urlparse(config_url).path.split("/") if part]
    if "agentic" in path_parts:
        index = path_parts.index("agentic")
        if index + 1 < len(path_parts):
            return path_parts[index + 1]
    return None


def _descope_project_id() -> str:
    project_id = os.environ.get("DESCOPE_PROJECT_ID")
    if project_id:
        return project_id
    project_id = _project_id_from_config_url(os.environ["DESCOPE_CONFIG_URL"])
    if project_id:
        return project_id
    raise ValueError(
        "Could not determine Descope project ID. Set DESCOPE_PROJECT_ID or use DESCOPE_CONFIG_URL."
    )


def _require_descope_scope(mcp_access_token: str | None, scope: str) -> dict[str, Any]:
    claims = validate_token(mcp_access_token)
    require_scopes(claims, [scope])
    return claims


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _descope_mgmt_request(
    url: str,
    payload: dict[str, Any],
    *,
    mcp_access_token: str | None,
) -> dict[str, Any]:
    mgmt_bearer = os.environ.get("DESCOPE_MGMT_API_KEY")
    if mcp_access_token:
        auth_value = f"{_descope_project_id()}:{mcp_access_token}"
    elif mgmt_bearer:
        auth_value = mgmt_bearer
    else:
        raise ValueError(
            "Missing credentials for Descope management API. "
            "Provide an MCP access token or DESCOPE_MGMT_API_KEY."
        )

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_value}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Descope management API failed ({exc.code}): {detail}") from exc


def _extract_service_account_json(body: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        body.get("serviceAccount"),
        body.get("service_account"),
        body.get("credentials"),
        body.get("token"),
        body.get("appData"),
        body.get("data"),
    ]
    for candidate in candidates:
        if (
            isinstance(candidate, dict)
            and "private_key" in candidate
            and "client_email" in candidate
        ):
            return candidate
        if isinstance(candidate, str):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(parsed, dict)
                and "private_key" in parsed
                and "client_email" in parsed
            ):
                return parsed

    raise RuntimeError(
        "Descope response did not include a valid Google service account JSON payload"
    )


def _fetch_bigquery_service_account_json(
    user_id: str,
    outbound_app_id: str,
    mcp_access_token: str | None,
) -> dict[str, Any]:
    """
    Fetch a Google service account JSON payload stored in Descope Connections.

    Uses the caller's MCP access token by default (recommended). DESCOPE_MGMT_API_KEY
    can be used as a fallback for local development.
    """
    base_url = os.environ.get("DESCOPE_MGMT_API_BASE_URL", "https://api.descope.com").rstrip(
        "/"
    )
    url = f"{base_url}/v1/mgmt/outbound/app/user/token"
    payload = {
        "appId": outbound_app_id,
        "userId": user_id,
        "options": {
            "withRefreshToken": False,
            "forceRefresh": False,
        },
    }
    response = _descope_mgmt_request(url, payload, mcp_access_token=mcp_access_token)
    return _extract_service_account_json(response)


def _create_google_service_account_jwt_assertion(
    *,
    client_email: str,
    private_key_pem: str,
    scope: str,
    token_uri: str,
) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": client_email,
        "scope": scope,
        "aud": token_uri,
        "iat": now,
        "exp": now + 3600,
    }

    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    encoded_claims = _base64url_encode(
        json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_claims}".encode("utf-8")

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{encoded_header}.{encoded_claims}.{_base64url_encode(signature)}"


def _exchange_service_account_json_for_bigquery_token(service_account: dict[str, Any]) -> str:
    private_key = service_account.get("private_key")
    client_email = service_account.get("client_email")
    token_uri = service_account.get("token_uri", "https://oauth2.googleapis.com/token")
    if not private_key or not client_email:
        raise RuntimeError("Service account JSON is missing private_key or client_email")

    assertion = _create_google_service_account_jwt_assertion(
        client_email=client_email,
        private_key_pem=private_key,
        scope="https://www.googleapis.com/auth/bigquery",
        token_uri=token_uri,
    )
    form_data = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        token_uri,
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google OAuth token exchange failed ({exc.code}): {detail}") from exc

    access_token = body.get("access_token")
    if not access_token:
        raise RuntimeError("Google OAuth response did not include access_token")
    return access_token


def _bigquery_request(
    *,
    method: str,
    url: str,
    access_token: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=(json.dumps(body).encode("utf-8") if body is not None else None),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BigQuery API call failed ({exc.code}): {detail}") from exc


@mcp.tool()
def bigquery_read(
    project_id: str,
    dataset_id: str,
    table_id: str,
    limit: int = 100,
    mcp_access_token: str = None,
) -> dict[str, Any]:
    """Read rows from a BigQuery table — requires mcp:bigquery.read."""
    claims = _require_descope_scope(mcp_access_token, "mcp:bigquery.read")
    user_id = claims.get("sub") or claims.get("userId")
    if not user_id:
        raise RuntimeError("Validated MCP token did not include caller identity (sub)")

    outbound_app_id = os.environ.get("BIGQUERY_READ_OUTBOUND_APP_ID", "bigquery-read-cert")
    service_account = _fetch_bigquery_service_account_json(
        user_id,
        outbound_app_id,
        mcp_access_token,
    )
    google_access_token = _exchange_service_account_json_for_bigquery_token(service_account)

    query = urllib.parse.urlencode(
        {"maxResults": max(1, min(limit, 10000))},
        doseq=True,
    )
    url = (
        "https://bigquery.googleapis.com/bigquery/v2/projects/"
        f"{project_id}/datasets/{dataset_id}/tables/{table_id}/data?{query}"
    )

    return _bigquery_request(
        method="GET",
        url=url,
        access_token=google_access_token,
    )


@mcp.tool()
def bigquery_write(
    project_id: str,
    dataset_id: str,
    table_id: str,
    rows: list[dict[str, Any]],
    skip_invalid_rows: bool = True,
    ignore_unknown_values: bool = False,
    mcp_access_token: str = None,
) -> dict[str, Any]:
    """Write rows to BigQuery using insertAll — requires mcp:bigquery.write."""
    claims = _require_descope_scope(mcp_access_token, "mcp:bigquery.write")
    user_id = claims.get("sub") or claims.get("userId")
    if not user_id:
        raise RuntimeError("Validated MCP token did not include caller identity (sub)")

    outbound_app_id = os.environ.get(
        "BIGQUERY_WRITE_OUTBOUND_APP_ID",
        "bigquery-readwrite-cert",
    )
    service_account = _fetch_bigquery_service_account_json(
        user_id,
        outbound_app_id,
        mcp_access_token,
    )
    google_access_token = _exchange_service_account_json_for_bigquery_token(service_account)

    url = (
        "https://bigquery.googleapis.com/bigquery/v2/projects/"
        f"{project_id}/datasets/{dataset_id}/tables/{table_id}/insertAll"
    )
    payload = {
        "skipInvalidRows": skip_invalid_rows,
        "ignoreUnknownValues": ignore_unknown_values,
        "rows": [{"json": row} for row in rows],
    }
    return _bigquery_request(
        method="POST",
        url=url,
        access_token=google_access_token,
        body=payload,
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(transport="http")
