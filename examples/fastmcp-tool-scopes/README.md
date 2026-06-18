# FastMCP 3 Server with Descope Auth & Tool-Level Scopes (Python)

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction

This example shows how to secure a [FastMCP **3**](https://gofastmcp.com/) server
with [Descope](https://www.descope.com/) and enforce **tool-level OAuth scopes** —
authorizing each tool individually instead of gating the whole server behind a
single permission.

Two layers work together:

1. **Authentication (server-wide):** the `DescopeProvider` is pointed at your
   Descope **MCP Server**'s `.well-known` URL. It discovers Descope's endpoints
   from there, validates every incoming request's JWT against Descope's JWKS,
   and exposes the OAuth 2.1 discovery endpoints. In FastMCP 3, configuring an
   auth provider rejects unauthenticated requests at the transport layer
   automatically — there is no separate `require_auth` flag anymore.
2. **Authorization (per tool):** each tool declares the scope(s) it needs with
   `require_scopes(...)`. A caller whose token lacks a tool's scope won't even
   see that tool in `tools/list`, and a direct call returns _not found_. Clients
   only ever get the access their granted scopes allow.

The server is a self-contained, in-memory **Task Manager**, so it runs without
any external API.

## How tool-level scopes work

Import the built-in check and attach it to a tool via the `auth` parameter:

```python
from fastmcp.server.auth import require_scopes

@mcp.tool(auth=require_scopes("tasks:read"))
async def list_tasks() -> str:
    ...
```

- **Single scope:** `require_scopes("tasks:read")`
- **Multiple scopes (AND):** `require_scopes("tasks:write", "tasks:admin")` — the
  token must contain _all_ listed scopes.
- **Combine checks (AND):** pass a list, e.g.
  `auth=[require_scopes("tasks:write"), require_scopes("tasks:admin")]`.
- **No scope:** omit `auth` for a tool that any authenticated caller can use.

This example maps tools to scopes as follows:

| Tool              | Required scope(s)                   | Description                |
| ----------------- | ----------------------------------- | -------------------------- |
| `list_tasks`      | `tasks:read`                        | List all tasks             |
| `get_task`        | `tasks:read`                        | Fetch a single task by id  |
| `create_task`     | `tasks:write`                       | Create a new task          |
| `complete_task`   | `tasks:write`                       | Mark a task as done        |
| `delete_task`     | `tasks:admin`                       | Delete a task (privileged) |
| `purge_completed` | `tasks:write` **and** `tasks:admin` | Delete all completed tasks |

## Requirements

- Python 3.12+
- FastMCP 3.4+
- An [MCP Server](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)
  configured in Descope (with the scopes below) and its `.well-known` URL

## Descope setup

1. In the [Descope Console](https://app.descope.com), go to **Agentic Identity
   Hub → [MCP Servers](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)**
   and create an MCP Server.
2. Add the **scopes** this server understands:
   - `tasks:read`
   - `tasks:write`
   - `tasks:admin`
3. Copy the MCP Server's **`.well-known` (OpenID configuration) URL** — this is
   the only value the server needs.

That `.well-known` URL is all `DescopeProvider` needs; it discovers everything
else from there:

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.descope import DescopeProvider

auth_provider = DescopeProvider(
    config_url="https://.../.well-known/openid-configuration",  # Your MCP Server .well-known URL
    base_url=SERVER_URL,                                        # Your server's public URL
)

mcp = FastMCP(name="Task Manager MCP Server", auth=auth_provider)
```

Descope handles Dynamic Client Registration (DCR), so MCP clients can register
and request scopes automatically — no manual client credentials needed. When a
client connects, the scopes it requests (and the user consents to) are embedded
in the issued token and checked by `require_scopes` per tool.

> **Tip:** define one scope per tool or tool group. That way a client only ever
> asks for the access it actually needs.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/descope/ai.git
cd ai/examples/fastmcp-tool-scopes
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

Visit [http://localhost:8000](http://localhost:8000) for the tool/scope reference
and connection config.

## Connecting a client

Point any MCP client at the server URL and let it complete the OAuth flow:

```json
{
  "mcpServers": {
    "tasks": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

During authorization the client requests scopes; the tools you see afterward
depend on which scopes your token was granted.

## Seeing scopes in action

- Connect with **only `tasks:read`** → you see `list_tasks` and `get_task`. The
  write/admin tools are hidden.
- Add **`tasks:write`** → `create_task` and `complete_task` appear.
- Add **`tasks:admin`** → `delete_task` appears, and `purge_completed` becomes
  callable once you hold both `tasks:write` and `tasks:admin`.

## API Endpoints

- `GET /` — Landing page and documentation
- `POST /mcp` — Main MCP endpoint (requires a Bearer token)
- `GET /.well-known/oauth-protected-resource/mcp` — Resource metadata for the `/mcp` endpoint
- `GET /.well-known/oauth-authorization-server` — OAuth 2.1 server metadata (discovered from Descope)

## Troubleshooting

- **A tool is missing.** That's by design when your token lacks its scope.
  Confirm the scope exists on your Descope MCP Server and was requested by the
  client (decode your access token to see the scopes it was granted).
- **Authentication errors.** Clear cached auth state: `rm -rf ~/.mcp-auth`. Also
  double-check `DESCOPE_CONFIG_URL` points at your MCP Server's `.well-known` URL.
- **Token has no scopes.** Make sure the MCP Server defines the scopes and the
  client requested them during the OAuth flow.

## Learn more

- [FastMCP Authorization docs](https://gofastmcp.com/servers/authorization)
- [FastMCP Descope integration](https://gofastmcp.com/integrations/descope)
- [Descope MCP Authorization](https://docs.descope.com/mcp)
- [Descope MCP Servers](https://docs.descope.com/agentic-identity-hub/mcp-servers/settings)
