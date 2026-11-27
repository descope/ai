"""Meridian MCP Server — a fictional B2B corporate travel & expense platform.

Meridian is a stand-in for a real B2B SaaS company (think Navan, Ramp, Brex, or
Box): a multi-tenant product where every customer is an *organization*, every
user belongs to a tenant, and what a user can do is governed by their role.
This server exposes Meridian's capabilities as MCP tools and shows how Descope
secures a B2B MCP server on two axes at once:

  1. Multi-tenant isolation (authentication + tenant claim).
     Every request to the MCP endpoint must carry a valid Descope-issued JWT.
     The token identifies the caller's organization (tenant), and every tool
     reads and writes only that tenant's data. Acme's agent can never see
     Globex's expenses, even though both hit the same server.

  2. Role-based authorization (tool-level OAuth scopes).
     Each tool declares the scope(s) it needs via `@mcp.tool(auth=...)`. A caller
     whose token lacks a scope won't even see the tool in `tools/list`, and a
     direct call returns "not found". Roles map to scope bundles:

        Employee       expenses:read expenses:write trips:read trips:book
        Manager        + expenses:approve reports:read
        Finance Admin  + admin  (org directory, budgets, travel policy)

This is a self-contained, in-memory demo — swap the store for a real database
and the tenant/role model stays identical. The scopes used here must be defined
on your Descope MCP Server and requested by the client during the OAuth flow.
"""

import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.descope import DescopeProvider
from fastmcp.server.dependencies import get_access_token
from starlette.requests import Request
from starlette.responses import FileResponse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Descope configuration (from environment) ---------------------------------
# The public URL where this server is reachable. Used as the OAuth "resource"
# identifier and to build the discovery (.well-known) endpoints.
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
# The .well-known URL of your Descope MCP Server. Copy it from the Descope
# Console under Agentic Identity Hub -> MCP Servers.
DESCOPE_CONFIG_URL = os.getenv("DESCOPE_CONFIG_URL")

if not DESCOPE_CONFIG_URL:
    raise ValueError(
        "Set DESCOPE_CONFIG_URL to your Descope MCP Server's .well-known URL "
        "so the server can discover Descope's endpoints and validate tokens."
    )

# The DescopeProvider discovers Descope's endpoints from the MCP Server's
# .well-known URL and configures JWT validation plus the OAuth 2.1 discovery
# routes — no project ID or client credentials needed.
auth_provider = DescopeProvider(
    config_url=DESCOPE_CONFIG_URL,  # Your MCP Server .well-known URL
    base_url=SERVER_URL,  # Your server's public URL
)

mcp = FastMCP(name="Meridian Travel & Expense MCP Server", auth=auth_provider)


# --- In-memory, tenant-partitioned data store ---------------------------------
# Keyed by tenant id. Two demo organizations are seeded so you can prove tenant
# isolation: authenticate as Acme and you only ever touch Acme's data. Swap this
# for a real per-tenant datastore in production.
DEFAULT_TENANT = "acme-robotics"

_ORGS: dict[str, dict] = {
    "acme-robotics": {
        "name": "Acme Robotics",
        "monthly_travel_budget_usd": 50_000,
        "travel_policy": {
            "max_flight_usd": 1_200,
            "max_hotel_nightly_usd": 350,
            "cabin": "economy",
            "requires_approval_over_usd": 1_000,
        },
        "employees": {
            "e-101": {"id": "e-101", "name": "Dana Okafor", "role": "Employee", "email": "dana@acme.example"},
            "e-102": {"id": "e-102", "name": "Miguel Santos", "role": "Manager", "email": "miguel@acme.example"},
            "e-103": {"id": "e-103", "name": "Priya Nair", "role": "Finance Admin", "email": "priya@acme.example"},
        },
        "expenses": {
            1: {"id": 1, "employee_id": "e-101", "merchant": "United Airlines", "category": "Airfare",
                "amount_usd": 640.00, "date": "2026-06-14", "status": "approved"},
            2: {"id": 2, "employee_id": "e-101", "merchant": "Marriott SFO", "category": "Lodging",
                "amount_usd": 1_180.00, "date": "2026-06-15", "status": "pending"},
            3: {"id": 3, "employee_id": "e-102", "merchant": "Uber", "category": "Ground Transport",
                "amount_usd": 74.50, "date": "2026-06-16", "status": "pending"},
        },
        "trips": {
            "t-9001": {"id": "t-9001", "employee_id": "e-101", "origin": "SFO", "destination": "JFK",
                       "depart": "2026-07-10", "return": "2026-07-14", "status": "booked", "total_usd": 820.00},
        },
    },
    "globex": {
        "name": "Globex Corporation",
        "monthly_travel_budget_usd": 20_000,
        "travel_policy": {
            "max_flight_usd": 800,
            "max_hotel_nightly_usd": 250,
            "cabin": "economy",
            "requires_approval_over_usd": 500,
        },
        "employees": {
            "g-201": {"id": "g-201", "name": "Lena Fischer", "role": "Employee", "email": "lena@globex.example"},
            "g-202": {"id": "g-202", "name": "Tom Reyes", "role": "Finance Admin", "email": "tom@globex.example"},
        },
        "expenses": {
            1: {"id": 1, "employee_id": "g-201", "merchant": "Delta", "category": "Airfare",
                "amount_usd": 410.00, "date": "2026-06-20", "status": "approved"},
        },
        "trips": {},
    },
}

# Per-tenant counters for newly created records.
_NEXT_EXPENSE_ID: dict[str, int] = {"acme-robotics": 4, "globex": 2}
_NEXT_TRIP_SEQ: dict[str, int] = {"acme-robotics": 9002, "globex": 3001}


# --- Identity & tenant helpers ------------------------------------------------
def _claims() -> dict:
    """Return the validated claims from the caller's Descope access token."""
    token = get_access_token()
    return getattr(token, "claims", {}) or {}


def _current_tenant() -> str:
    """Resolve the caller's tenant (organization) from their token.

    Descope multi-tenant tokens carry a `tenants` claim mapping tenant id ->
    roles/permissions, and often a `dct` ("default/selected tenant") claim. We
    honor those, then fall back to a custom `tenant` claim, then to the demo
    default so the example still runs with a single-tenant project.
    """
    claims = _claims()

    selected = claims.get("dct")
    if isinstance(selected, str) and selected in _ORGS:
        return selected

    tenants = claims.get("tenants")
    if isinstance(tenants, dict) and tenants:
        for tid in tenants:
            if tid in _ORGS:
                return tid
        # Token names a tenant we don't have seeded — surface it anyway.
        return next(iter(tenants))

    tenant = claims.get("tenant")
    if isinstance(tenant, str) and tenant:
        return tenant

    return DEFAULT_TENANT


def _org() -> dict:
    """The current caller's organization record (auto-created if unseeded)."""
    tid = _current_tenant()
    return _ORGS.setdefault(
        tid,
        {
            "name": tid,
            "monthly_travel_budget_usd": 0,
            "travel_policy": {},
            "employees": {},
            "expenses": {},
            "trips": {},
        },
    )


def _fmt_expense(e: dict, org: dict) -> str:
    who = org["employees"].get(e["employee_id"], {}).get("name", e["employee_id"])
    return (
        f"[{e['id']}] {e['date']}  ${e['amount_usd']:,.2f}  {e['category']:<18} "
        f"{e['merchant']:<18} {who:<16} — {e['status']}"
    )


# --- Tools: Expenses ----------------------------------------------------------
# The DescopeProvider authenticates every request before these run; the tenant
# helper scopes the data; `require_scopes` authorizes the action.


@mcp.tool(auth=require_scopes("expenses:read"))
async def list_expenses(status: str | None = None) -> str:
    """List expense reports for your organization. Requires `expenses:read`.

    Args:
        status: Optional filter — one of `pending`, `approved`, `rejected`.
    """
    org = _org()
    rows = sorted(org["expenses"].values(), key=lambda e: e["id"])
    if status:
        rows = [e for e in rows if e["status"] == status.lower()]
    if not rows:
        return f"No expenses for {org['name']}" + (f" with status '{status}'." if status else ".")
    header = f"Expenses for {org['name']}:"
    return header + "\n" + "\n".join(_fmt_expense(e, org) for e in rows)


@mcp.tool(auth=require_scopes("expenses:read"))
async def get_expense(expense_id: int) -> str:
    """Fetch a single expense by id. Requires `expenses:read`.

    Args:
        expense_id: The id of the expense within your organization.
    """
    org = _org()
    e = org["expenses"].get(expense_id)
    if e is None:
        return f"Expense {expense_id} not found in {org['name']}."
    return _fmt_expense(e, org)


@mcp.tool(auth=require_scopes("expenses:write"))
async def submit_expense(merchant: str, category: str, amount_usd: float, date: str | None = None) -> str:
    """Submit a new expense report. Requires `expenses:write`.

    Anything over the org's approval threshold is created as `pending`; smaller
    items are auto-approved — mirroring a real T&E policy engine.

    Args:
        merchant: Where the money was spent (e.g. "Delta", "Hilton").
        category: Expense category (e.g. Airfare, Lodging, Meals).
        amount_usd: Amount in US dollars.
        date: ISO date (YYYY-MM-DD); defaults to today.
    """
    org = _org()
    tid = _current_tenant()
    threshold = org.get("travel_policy", {}).get("requires_approval_over_usd", 0)
    new_id = _NEXT_EXPENSE_ID.get(tid, 1)
    _NEXT_EXPENSE_ID[tid] = new_id + 1
    expense = {
        "id": new_id,
        "employee_id": (_claims().get("sub") or "self"),
        "merchant": merchant,
        "category": category,
        "amount_usd": round(float(amount_usd), 2),
        "date": date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "status": "pending" if amount_usd > threshold else "approved",
    }
    org["expenses"][new_id] = expense
    note = "" if expense["status"] == "approved" else f" (over ${threshold:,.0f} — needs manager approval)"
    return f"Submitted expense:\n{_fmt_expense(expense, org)}{note}"


@mcp.tool(auth=require_scopes("expenses:approve"))
async def approve_expense(expense_id: int) -> str:
    """Approve a pending expense. Requires `expenses:approve` (Manager).

    Args:
        expense_id: The id of the pending expense.
    """
    org = _org()
    e = org["expenses"].get(expense_id)
    if e is None:
        return f"Expense {expense_id} not found in {org['name']}."
    if e["status"] == "approved":
        return f"Expense {expense_id} is already approved."
    e["status"] = "approved"
    return f"Approved expense:\n{_fmt_expense(e, org)}"


@mcp.tool(auth=require_scopes("expenses:approve"))
async def reject_expense(expense_id: int, reason: str) -> str:
    """Reject a pending expense with a reason. Requires `expenses:approve`.

    Args:
        expense_id: The id of the pending expense.
        reason: Why the expense is being rejected.
    """
    org = _org()
    e = org["expenses"].get(expense_id)
    if e is None:
        return f"Expense {expense_id} not found in {org['name']}."
    e["status"] = "rejected"
    return f"Rejected expense {expense_id}: {reason}\n{_fmt_expense(e, org)}"


# --- Tools: Travel ------------------------------------------------------------


@mcp.tool(auth=require_scopes("trips:read"))
async def search_flights(origin: str, destination: str, depart: str) -> str:
    """Search bookable flights that fit your org's travel policy.

    Requires `trips:read`. Results are filtered to the org's per-flight price
    cap and cabin class, so the agent only ever offers in-policy options.

    Args:
        origin: Origin airport code (e.g. SFO).
        destination: Destination airport code (e.g. JFK).
        depart: Departure date (YYYY-MM-DD).
    """
    org = _org()
    policy = org.get("travel_policy", {})
    cap = policy.get("max_flight_usd", 10_000)
    cabin = policy.get("cabin", "economy")
    # Toy fare catalog; a real integration would call a GDS/booking API.
    catalog = [
        {"carrier": "United", "price_usd": 640, "stops": 0},
        {"carrier": "Delta", "price_usd": 410, "stops": 1},
        {"carrier": "JetBlue", "price_usd": 980, "stops": 0},
        {"carrier": "Emirates", "price_usd": 3_200, "stops": 0},
    ]
    in_policy = [f for f in catalog if f["price_usd"] <= cap]
    lines = [
        f"{f['carrier']:<10} {origin}->{destination} {depart}  "
        f"${f['price_usd']:,} {cabin}  {'nonstop' if f['stops'] == 0 else str(f['stops']) + ' stop(s)'}"
        for f in in_policy
    ]
    hidden = len(catalog) - len(in_policy)
    footer = f"\n({hidden} option(s) hidden — above {org['name']}'s ${cap:,} in-policy cap.)" if hidden else ""
    return f"In-policy flights for {org['name']}:\n" + "\n".join(lines) + footer


@mcp.tool(auth=require_scopes("trips:read"))
async def list_trips() -> str:
    """List booked trips for your organization. Requires `trips:read`."""
    org = _org()
    if not org["trips"]:
        return f"No trips booked for {org['name']}."
    lines = []
    for t in org["trips"].values():
        who = org["employees"].get(t["employee_id"], {}).get("name", t["employee_id"])
        lines.append(
            f"[{t['id']}] {t['origin']}->{t['destination']}  {t['depart']} to {t['return']}  "
            f"${t['total_usd']:,.2f}  {who} — {t['status']}"
        )
    return f"Trips for {org['name']}:\n" + "\n".join(lines)


@mcp.tool(auth=require_scopes("trips:book"))
async def book_trip(origin: str, destination: str, depart: str, ret: str, total_usd: float) -> str:
    """Book a trip for the caller. Requires `trips:book`.

    Args:
        origin: Origin airport code.
        destination: Destination airport code.
        depart: Departure date (YYYY-MM-DD).
        ret: Return date (YYYY-MM-DD).
        total_usd: Total trip cost in US dollars.
    """
    org = _org()
    tid = _current_tenant()
    cap = org.get("travel_policy", {}).get("max_flight_usd", 10_000)
    if total_usd > cap * 2:  # round-trip sanity check against policy
        return (
            f"Cannot book: ${total_usd:,.2f} exceeds {org['name']}'s travel policy. "
            f"Per-flight cap is ${cap:,}."
        )
    seq = _NEXT_TRIP_SEQ.get(tid, 1)
    _NEXT_TRIP_SEQ[tid] = seq + 1
    trip_id = f"t-{seq}"
    trip = {
        "id": trip_id,
        "employee_id": (_claims().get("sub") or "self"),
        "origin": origin,
        "destination": destination,
        "depart": depart,
        "return": ret,
        "status": "booked",
        "total_usd": round(float(total_usd), 2),
    }
    org["trips"][trip_id] = trip
    return f"Booked trip {trip_id}: {origin}->{destination} {depart} to {ret} for ${total_usd:,.2f}."


# --- Tools: Reporting (Manager) ----------------------------------------------


@mcp.tool(auth=require_scopes("reports:read"))
async def expense_summary() -> str:
    """Spend analytics for your organization. Requires `reports:read` (Manager).

    Summarizes total and per-category spend and shows budget utilization.
    """
    org = _org()
    expenses = list(org["expenses"].values())
    total = sum(e["amount_usd"] for e in expenses)
    by_cat: dict[str, float] = {}
    for e in expenses:
        by_cat[e["category"]] = by_cat.get(e["category"], 0.0) + e["amount_usd"]
    budget = org.get("monthly_travel_budget_usd", 0)
    pending = sum(1 for e in expenses if e["status"] == "pending")
    lines = [f"Spend summary — {org['name']}"]
    lines.append(f"  Total logged:   ${total:,.2f}")
    if budget:
        lines.append(f"  Monthly budget: ${budget:,.2f}  ({total / budget:.0%} used)")
    lines.append(f"  Pending approvals: {pending}")
    lines.append("  By category:")
    for cat, amt in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        lines.append(f"    {cat:<18} ${amt:,.2f}")
    return "\n".join(lines)


# --- Tools: Administration (Finance Admin) -----------------------------------


@mcp.tool(auth=require_scopes("admin"))
async def list_employees() -> str:
    """List everyone in your organization. Requires `admin` (Finance Admin)."""
    org = _org()
    lines = [f"Employees — {org['name']}:"]
    for emp in org["employees"].values():
        lines.append(f"  {emp['id']}  {emp['name']:<16} {emp['role']:<14} {emp['email']}")
    return "\n".join(lines)


@mcp.tool(auth=require_scopes("admin"))
async def set_travel_policy(
    max_flight_usd: float | None = None,
    max_hotel_nightly_usd: float | None = None,
    requires_approval_over_usd: float | None = None,
) -> str:
    """Update your organization's travel policy. Requires `admin`.

    Only the fields you pass are changed. These caps immediately govern
    `search_flights`, `book_trip`, and `submit_expense`.

    Args:
        max_flight_usd: New per-flight price cap.
        max_hotel_nightly_usd: New nightly hotel cap.
        requires_approval_over_usd: New auto-approval threshold for expenses.
    """
    org = _org()
    policy = org.setdefault("travel_policy", {})
    if max_flight_usd is not None:
        policy["max_flight_usd"] = round(float(max_flight_usd), 2)
    if max_hotel_nightly_usd is not None:
        policy["max_hotel_nightly_usd"] = round(float(max_hotel_nightly_usd), 2)
    if requires_approval_over_usd is not None:
        policy["requires_approval_over_usd"] = round(float(requires_approval_over_usd), 2)
    return f"Updated travel policy for {org['name']}: {policy}"


# --- Tool: Identity (any authenticated caller) --------------------------------


@mcp.tool
async def whoami() -> str:
    """Show the caller's identity, organization, and granted scopes.

    Requires only a valid token (no specific scope). Handy for demos: it makes
    the B2B model visible — which organization the token belongs to and exactly
    what the caller is authorized to do.
    """
    token = get_access_token()
    claims = _claims()
    tid = _current_tenant()
    org = _ORGS.get(tid, {})
    scopes = getattr(token, "scopes", None) or []
    lines = [
        "You are authenticated with Descope.",
        f"  Subject:      {claims.get('sub', 'unknown')}",
        f"  Organization: {org.get('name', tid)}  (tenant: {tid})",
        f"  Scopes:       {', '.join(scopes) if scopes else '(none)'}",
    ]
    return "\n".join(lines)


# --- Landing page -------------------------------------------------------------
@mcp.custom_route("/", methods=["GET"])
async def serve_index(request: Request) -> FileResponse:
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))


# The Streamable HTTP app exposes the MCP endpoint plus the OAuth discovery
# routes (`/.well-known/oauth-authorization-server`, `oauth-protected-resource`).
app = mcp.http_app(path="/mcp")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
