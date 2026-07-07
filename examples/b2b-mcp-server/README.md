# Meridian — a B2B Travel & Expense MCP Server (Python)

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

**Meridian** is a fictional B2B SaaS company — a corporate **travel & expense**
platform in the spirit of Navan, Ramp, Brex, or Box. This example wraps
Meridian's product surface in a [FastMCP 3](https://gofastmcp.com/) server and
secures it with [Descope](https://www.descope.com/), so an AI agent can book
travel, file expenses, approve reports, and pull spend analytics on a user's
behalf.

It's built to be a **demo of Descope's B2B capabilities for MCP auth**. Unlike a
consumer (B2C) app, a B2B product is organized around *organizations* (tenants)
and *roles*. This server shows both:

1. **Multi-tenant isolation.** Descope provides the **auth layer**, not your data
   layer — it doesn't store or return your tenants' records. What it does is
   authenticate the request and stamp the caller's **organization** into the
   token via the **`dct` claim** (the "current tenant"). Your MCP server reads
   `dct` off the validated token and is responsible for scoping every query to
   that tenant. In this example, `_current_tenant()` reads the claim and each
   tool only touches that org's in-memory data — so Acme Robotics' agent never
   sees Globex Corporation's expenses, even though both connect to the same
   server. Two demo tenants are seeded so you can prove it. Swap the in-memory
   store for your real database and you'd apply the same `dct`-based filter (a
   `WHERE tenant_id = …`, a per-tenant schema, etc.).
2. **Role-based authorization (tool-level scopes).** Each tool declares the OAuth
   scope(s) it needs. A caller whose token lacks a scope won't even see the tool
   in `tools/list`, and a direct call returns _not found_. Roles map to scope
   bundles, so an Employee, a Manager, and a Finance Admin each see a different
   toolset.

The store is in-memory, so it runs with no external dependencies. Swap it for a
real per-tenant database and the identity model is unchanged.

## The B2B model: roles → scopes → tools

Meridian defines these OAuth scopes (configure them on your Descope MCP Server):

| Scope              | Grants                                            |
| ------------------ | ------------------------------------------------- |
| `expenses:read`    | View expense reports                              |
| `expenses:write`   | Submit expense reports                            |
| `expenses:approve` | Approve / reject expenses (Manager)               |
| `trips:read`       | Search flights, list trips                        |
| `trips:book`       | Book travel                                       |
| `reports:read`     | Spend analytics (Manager)                         |
| `admin`            | Org directory, budgets, travel policy (Finance)   |

A typical B2B role → scope mapping:

| Role              | Scopes                                                                                     |
| ----------------- | ------------------------------------------------------------------------------------------ |
| **Employee**      | `expenses:read` `expenses:write` `trips:read` `trips:book`                                 |
| **Manager**       | Employee + `expenses:approve` `reports:read`                                               |
| **Finance Admin** | Manager + `admin`                                                                          |

### Tools and the scopes they require

| Tool                | Required scope     | Description                                     |
| ------------------- | ------------------ | ----------------------------------------------- |
| `whoami`            | _(any authed)_     | Show caller identity, organization, and scopes  |
| `list_expenses`     | `expenses:read`    | List your org's expenses (optional status filter) |
| `get_expense`       | `expenses:read`    | Fetch one expense by id                         |
| `submit_expense`    | `expenses:write`   | File a new expense (policy sets auto-approval)  |
| `approve_expense`   | `expenses:approve` | Approve a pending expense                       |
| `reject_expense`    | `expenses:approve` | Reject a pending expense with a reason          |
| `search_flights`    | `trips:read`       | Search in-policy flights                        |
| `list_trips`        | `trips:read`       | List booked trips                               |
| `book_trip`         | `trips:book`       | Book a trip (enforced against policy)           |
| `expense_summary`   | `reports:read`     | Org spend analytics + budget utilization        |
| `list_employees`    | `admin`            | Organization directory                          |
| `set_travel_policy` | `admin`            | Update the org's travel/expense policy          |

## How the two layers work

**Authentication (server-wide).** The `DescopeProvider` points at your Descope
**MCP Server**'s `.well-known` URL. It discovers Descope's endpoints, validates
every request's JWT against Descope's JWKS, and serves the OAuth 2.1 discovery
routes. In FastMCP 3, configuring an auth provider rejects unauthenticated
requests at the transport layer automatically.

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.descope import DescopeProvider

auth_provider = DescopeProvider(
    config_url="https://.../.well-known/openid-configuration",  # Your MCP Server .well-known URL
    base_url=SERVER_URL,                                        # Your server's public URL
)
mcp = FastMCP(name="Meridian Travel & Expense MCP Server", auth=auth_provider)
```

**Tenant isolation (your responsibility, using Descope's claim).** Descope puts
the caller's tenant in the token's **`dct` claim**; the server reads it and scopes
its own data access. Descope never sees or returns your business data — it just
tells you *which tenant* the request belongs to:

```python
from fastmcp.server.dependencies import get_access_token

def _current_tenant() -> str:
    claims = get_access_token().claims or {}
    # Descope stamps the caller's tenant into the token as `dct` ("current
    # tenant"); multi-tenant tokens also carry a `tenants` map. Your code reads
    # this and does the data scoping — Descope doesn't touch your data.
    return claims.get("dct") or next(iter(claims.get("tenants", {})), DEFAULT_TENANT)

# ...then every tool filters on it, e.g. rows WHERE tenant_id == _current_tenant().
```

**Authorization (per tool).** Each tool declares its scope:

```python
from fastmcp.server.auth import require_scopes

@mcp.tool(auth=require_scopes("expenses:approve"))
async def approve_expense(expense_id: int) -> str:
    ...
```

- **Single scope:** `require_scopes("expenses:read")`
- **Multiple scopes (AND):** `require_scopes("expenses:write", "expenses:approve")`
- **No scope:** omit `auth` for a tool any authenticated caller can use (`whoami`).

Descope handles Dynamic Client Registration (DCR), so MCP clients register and
request scopes automatically. The scopes the user consents to are embedded in the
issued token and checked per tool.

## Enterprise-managed access with ID-JAG (Cross-App Access)

The flow above is the standard interactive OAuth path: a user connects a client,
gets redirected to consent, and a token is minted. That's great for self-serve
adoption — but inside a large enterprise, IT wants to *centrally* govern which AI
apps may reach which internal MCP servers, without every employee doing a
per-app OAuth dance.

Descope supports exactly that for Meridian's MCP server through **ID-JAG**
(Identity Assertion Authorization Grant), the token type behind
**Cross-App Access (XAA)** and the MCP spec's
[Enterprise-Managed Authorization extension](https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization)
(SEP-990, MCP 2025-11-25). This is the path used when **Claude is deployed
internally with a workforce IdP**: an admin authorizes the client (Claude,
Claude Code, Cowork) once, at the IdP, and users get Meridian already connected
on first login — no separate consent screen.

**How it works.** ID-JAG lets your enterprise identity provider (Okta, Entra ID,
etc.) issue a short-lived, signed assertion that a given client may act for a
given user at a specific resource — here, Meridian's MCP server. The full
exchange:

1. The user signs in to the client through the workforce IdP via SSO (OIDC),
   receiving an ID token.
2. The client exchanges that ID token for an **ID-JAG** at the IdP's token
   endpoint using OAuth token exchange
   ([RFC 8693](https://www.rfc-editor.org/rfc/rfc8693)). The IdP applies company
   policy — is this app allowed to call Meridian, with these scopes?
3. The client presents the ID-JAG to **Descope** (Meridian's authorization
   server) using the JWT-bearer grant
   ([RFC 7523](https://www.rfc-editor.org/rfc/rfc7523)):
   `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`.
4. Descope validates the assertion against the **trusted IdP** configured on your
   tenant and mints a short-lived Meridian access token — the same kind of Descope
   token this server already validates, carrying the tenant and scopes. Your tool
   code (`_current_tenant()`, `require_scopes(...)`) does not change at all.
5. The client calls Meridian's `/mcp` endpoint with that access token until it
   expires.

**Enabling it in your tenant.** ID-JAG exchange is enabled per **tenant** in
Descope — the same tenant construct this server already uses for isolation. In
the [Descope Console](https://app.descope.com), under **Agentic Identity Hub →
MCP Servers**, turn on ID-JAG / Cross-App Access for Meridian's MCP server and
register the enterprise **IdP you trust to issue assertions** for that tenant
(e.g. the customer's Okta or Entra tenant). Once trusted, ID-JAG tokens minted by
that IdP can be exchanged for access tokens to this MCP server; ID-JAG from any
untrusted issuer is rejected. Because trust is scoped to the tenant, Acme can
authorize its own IdP without granting Globex's IdP any access.

> This complements — it doesn't replace — the interactive OAuth + DCR flow. The
> same MCP server can serve self-serve users (interactive consent) and enterprise
> workforce users (IdP-governed, zero-touch via ID-JAG) at once.

See the [Descope MCP Authorization docs](https://docs.descope.com/mcp) for the
current console steps.

## Requirements

- Python 3.12+
- FastMCP 3.4+
- An [MCP Server](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)
  configured in Descope (with the scopes above) and its `.well-known` URL
- For the multi-tenant demo: at least one **tenant** (and, ideally, roles) set up
  in your Descope project
- For the enterprise / workforce demo (Claude internal): ID-JAG / Cross-App Access
  enabled on the tenant, with a trusted enterprise IdP (see below)

## Descope setup

1. In the [Descope Console](https://app.descope.com), go to **Agentic Identity
   Hub → [MCP Servers](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)**
   and create an MCP Server.
2. Add the **scopes** listed above (`expenses:read`, `expenses:write`, … `admin`).
3. (For the tenant demo) Create **tenants** — e.g. one named `acme-robotics` and
   one named `globex` — and assign your test users to them. The seeded data in
   this server uses those tenant ids; a token for any other tenant still works,
   it just starts with an empty (auto-created) org.
4. Copy the MCP Server's **`.well-known` (OpenID configuration) URL**.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/descope/ai.git
cd ai/examples/b2b-mcp-server
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Then edit `.env`:

```env
# Your Descope MCP Server's .well-known URL (Console -> Agentic Identity Hub -> MCP Servers)
DESCOPE_CONFIG_URL=https://api.descope.com/v1/apps/agentic/<project-id>/<mcp-server-id>/.well-known/openid-configuration
# The public URL where this server is reachable
SERVER_URL=http://localhost:8000
# Port to listen on (optional)
PORT=8000
```

### 3. Install dependencies

```bash
uv sync
```

(Or with pip: `pip install -r requirements.txt`.)

### 4. Run the server

```bash
uv run python server.py
```

### 5. Open the landing page

Visit [http://localhost:8000](http://localhost:8000) for the company overview,
tool/scope reference, and connection config.

## Connecting a client

Point any MCP client at the server URL and let it complete the OAuth flow:

```json
{
  "mcpServers": {
    "meridian": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Seeing it in action (demo script)

1. **Show identity.** Ask the agent to call `whoami` → it reports the subject,
   the **organization** the token belongs to, and the granted scopes.
2. **Role scoping.** Connect as an **Employee** → you can `submit_expense`,
   `search_flights`, and `book_trip`, but `approve_expense`, `expense_summary`,
   and `list_employees` are hidden. Re-connect as a **Manager** → approvals and
   reporting appear. As a **Finance Admin** → the `admin` tools appear.
3. **Tenant isolation.** Connect with an **Acme** token and `list_expenses` — you
   see Acme's data. Connect with a **Globex** token and you see only Globex's.
   The same server, the same tools, strictly separated data.
4. **Policy in the loop.** `set_travel_policy` (admin) lowers the flight cap, then
   `search_flights` and `book_trip` immediately enforce the new limit.

## API Endpoints

- `GET /` — Landing page and documentation
- `POST /mcp` — Main MCP endpoint (requires a Bearer token)
- `GET /.well-known/oauth-protected-resource/mcp` — Resource metadata for the `/mcp` endpoint
- `GET /.well-known/oauth-authorization-server` — OAuth 2.1 server metadata (discovered from Descope)

## Troubleshooting

- **A tool is missing.** By design when your token lacks its scope. Confirm the
  scope exists on your Descope MCP Server and was requested by the client (decode
  your access token to inspect its scopes).
- **`whoami` shows the wrong / default org.** Your token isn't carrying a tenant
  claim. Assign the user to a tenant in Descope and ensure the token includes it
  (`dct` or the `tenants` map).
- **Authentication errors.** Clear cached auth state: `rm -rf ~/.mcp-auth`, and
  verify `DESCOPE_CONFIG_URL` points at your MCP Server's `.well-known` URL.

## Learn more

- [FastMCP Authorization docs](https://gofastmcp.com/servers/authorization)
- [FastMCP Descope integration](https://gofastmcp.com/integrations/descope)
- [Descope MCP Authorization](https://docs.descope.com/mcp)
- [Descope MCP Servers](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)
