# Multi-tenant MCP Server (FastMCP + Descope)

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example demonstrates **tenant-scoped MCP tools** with Descope:

- The **`switch_tenant`** tool validates the tenant with **`mgmt.tenant.load`** (and session settings for SSO), then persists the active tenant id in the user’s **`currentTenant`** custom attribute using **`mgmt.user.patch`**.
- **Tenant-specific tools** are tagged for `tenant-a` vs `tenant-b`; on **every tool execution** the server calls Descope **`GET …/oauth2/v1/userinfo`** with the caller’s bearer token and verifies that `currentTenant` matches the tool’s tenant before running business logic.

## Prerequisites (Descope Console)

1. Create an **[MCP Server](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)** in Descope and note **Well-Known URL** (`DESCOPE_CONFIG_URL`) — or use legacy `DESCOPE_PROJECT_ID` + `DESCOPE_BASE_URL` for local dev.
2. Define a **custom attribute** named **`currentTenant`** on users (same key used in Management API patches).
3. Generate a **[Management Key](https://docs.descope.com/settings/project-management)** with permission to update users (`DESCOPE_MANAGEMENT_KEY`). Required only for **`switch_tenant`**.
4. Ensure MCP clients request scopes that include **`descope.custom_claims`** (and related OIDC scopes) so **UserInfo** returns custom attributes.

## Requirements

- Python 3.12+
- Dependencies in `pyproject.toml` (`uv sync`)

## Quick Start

### 1. Clone and enter this example

```bash
git clone https://github.com/descope/ai.git
cd ai/examples/multi-tenant-mcp
```

### 2. Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
|----------|---------|
| `DESCOPE_PROJECT_ID` | Descope project id |
| `DESCOPE_CONFIG_URL` | MCP server Well-Known URL (recommended) |
| `DESCOPE_BASE_URL` | Legacy; used only if `DESCOPE_CONFIG_URL` is unset |
| `SERVER_URL` | Public base URL of this MCP server |
| `DESCOPE_MANAGEMENT_KEY` | Enables **`switch_tenant`** (updates `currentTenant`) |

### 3. Install and run

```bash
uv sync
uv run python server.py
```

Visit [http://localhost:3000](http://localhost:3000) for the landing page.

## Tools

| Tool | Tenant | Description |
|------|--------|-------------|
| `switch_tenant` | *(any)* | Looks up tenant via Management API, rejects unknown tenants / SSO tenants, then sets `currentTenant` |
| `tenant_a_inventory_snapshot` | `tenant-a` | Dummy “inventory” tool |
| `tenant_b_metrics_ping` | `tenant-b` | Dummy metrics ping |
| `tenant_b_notes_echo` | `tenant-b` | Echoes a note string |

If UserInfo **`currentTenant`** does not match the tool’s tenant, the handler returns an error explaining to call **`switch_tenant`** first.

**`switch_tenant`** requires the tenant id to exist in Descope (`mgmt.tenant.load`). If **`enforceSSO`** is set, **`authType`** is SAML/OIDC, **SSO Setup Suite** is enabled, or **federated SSO app IDs** are configured, the tool returns an error instructing the user to sign in via SSO instead of switching from MCP.

## Implementation notes

- **UserInfo URL:** `{DESCOPE_BASE_URL}/oauth2/v1/userinfo` with `Authorization: Bearer <access_token>`.
- **Login id for Management API:** Resolved from JWT claims (`email`, `loginIds`, etc.).
- Demo tenant ids are **`tenant-a`** and **`tenant-b`** (`ALLOWED_TENANTS` in `server.py`). Align these with real tenant ids if you attach users to Descope tenants.

### FastMCP component visibility

Tools for **tenant-a** and **tenant-b** are tagged and **disabled globally** via `mcp.disable(...)`. Each MCP session **re-enables only the tools for the user’s current tenant** using `ctx.enable_components` / `ctx.disable_components` after reading UserInfo (`sync_session_tenant_visibility`), so clients typically **do not see** the other tenant’s tools. Call **`switch_tenant`** once after connecting so an existing Descope `currentTenant` is applied to the session’s tool list.
