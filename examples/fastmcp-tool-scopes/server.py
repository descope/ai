"""FastMCP 3 server demonstrating Descope auth with tool-level scopes.

Authentication is enforced at the transport layer by the DescopeProvider:
every request to the MCP endpoint must carry a valid Descope-issued JWT.

Authorization is enforced per tool with `require_scopes(...)`. Each tool
declares the OAuth scope(s) it needs via `@mcp.tool(auth=...)`. A caller whose
token is missing the required scope simply won't see the tool in `tools/list`,
and a direct call returns "not found" — so clients only ever get the access
their granted scopes allow.

This is a self-contained, in-memory "Task Manager" so the example runs without
any external API. The scopes used here (`tasks:read`, `tasks:write`,
`tasks:admin`) must be defined on your Descope MCP Server and requested by the
client during the OAuth flow.
"""

import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.descope import DescopeProvider
from starlette.requests import Request
from starlette.responses import FileResponse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Descope configuration (from environment) ---------------------------------
# The public URL where this server is reachable. It is used as the OAuth
# "resource" identifier and to build the discovery (.well-known) endpoints.
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

mcp = FastMCP(name="Task Manager MCP Server", auth=auth_provider)


# --- In-memory data store -----------------------------------------------------
# A toy store so the example is fully runnable; swap this for a real database
# in production.
_TASKS: dict[int, dict] = {
    1: {"id": 1, "title": "Set up Descope MCP Server", "done": True},
    2: {"id": 2, "title": "Wire tool-level scopes", "done": False},
}
_NEXT_ID = 3


def _serialize(task: dict) -> str:
    status = "✓" if task["done"] else "○"
    return f"{status} [{task['id']}] {task['title']}"


# --- Tools --------------------------------------------------------------------
# Each tool declares the scope(s) it requires. The DescopeProvider has already
# authenticated the request before any of these run; `require_scopes` then
# authorizes it against the token's granted scopes.


@mcp.tool(auth=require_scopes("tasks:read"))
async def list_tasks() -> str:
    """List all tasks. Requires the `tasks:read` scope."""
    if not _TASKS:
        return "No tasks yet."
    return "\n".join(_serialize(t) for t in sorted(_TASKS.values(), key=lambda t: t["id"]))


@mcp.tool(auth=require_scopes("tasks:read"))
async def get_task(task_id: int) -> str:
    """Get a single task by id. Requires the `tasks:read` scope.

    Args:
        task_id: The id of the task to fetch.
    """
    task = _TASKS.get(task_id)
    if task is None:
        return f"Task {task_id} not found."
    return _serialize(task)


@mcp.tool(auth=require_scopes("tasks:write"))
async def create_task(title: str) -> str:
    """Create a new task. Requires the `tasks:write` scope.

    Args:
        title: A short description of the task.
    """
    global _NEXT_ID
    task = {"id": _NEXT_ID, "title": title, "done": False}
    _TASKS[_NEXT_ID] = task
    _NEXT_ID += 1
    return f"Created task:\n{_serialize(task)}"


@mcp.tool(auth=require_scopes("tasks:write"))
async def complete_task(task_id: int) -> str:
    """Mark a task as done. Requires the `tasks:write` scope.

    Args:
        task_id: The id of the task to complete.
    """
    task = _TASKS.get(task_id)
    if task is None:
        return f"Task {task_id} not found."
    task["done"] = True
    return f"Completed task:\n{_serialize(task)}"


@mcp.tool(auth=require_scopes("tasks:admin"))
async def delete_task(task_id: int) -> str:
    """Delete a task. Requires the privileged `tasks:admin` scope.

    Args:
        task_id: The id of the task to delete.
    """
    task = _TASKS.pop(task_id, None)
    if task is None:
        return f"Task {task_id} not found."
    return f"Deleted task [{task['id']}] {task['title']}."


@mcp.tool(auth=[require_scopes("tasks:write"), require_scopes("tasks:admin")])
async def purge_completed() -> str:
    """Delete every completed task.

    Requires BOTH `tasks:write` AND `tasks:admin`. Passing a list of checks to
    `auth` requires all of them to pass (AND logic), which is useful for
    destructive bulk operations.
    """
    completed = [tid for tid, t in _TASKS.items() if t["done"]]
    for tid in completed:
        _TASKS.pop(tid, None)
    return f"Purged {len(completed)} completed task(s)."


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
