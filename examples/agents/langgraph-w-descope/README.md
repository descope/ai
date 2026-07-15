# LangGraph Agent with Descope MCP Server

This example demonstrates how to connect a LangGraph agent to a remote Descope MCP server using the `MultiServerMCPClient` from `langchain-mcp-adapters` with bearer token authentication. This approach supports both streamable HTTP and SSE transports with runtime headers for authentication.

## Features

- **MultiServerMCPClient**: Connect to multiple MCP servers simultaneously
- **Streamable HTTP & SSE**: Support for both transport protocols
- **Bearer token authentication**: Secure authentication with runtime headers
- **Scope-based requests**: Request specific scopes from MCP servers
- **Interactive session support**: Chat interface with the agent
- **StateGraph integration**: Advanced LangGraph StateGraph implementation
- **Tool discovery and usage**: Automatic tool loading and integration

## Setup

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file with the following variables:

   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

   **Note**: For OAuth discovery agents (recommended), you don't need to set `DESCOPE_BEARER_TOKEN` - it will be obtained automatically through the OAuth flow!

## 🚀 Quick Start with Web UI

The easiest way to get started is with the Streamlit web interface:

```bash
# Run the web UI
python3 run_ui.py
```

Then open your browser to `http://localhost:8501` and follow these steps:

1. **🔍 Discover OAuth Endpoints** - Automatically discovers Descope OAuth configuration
2. **🔐 Start OAuth Authentication** - Opens browser for login and obtains bearer token
3. **🔗 Test MCP Connection** - Connects to Descope MCP server with authentication
4. **💬 Chat with Agent** - Interact with the agent using natural language

### UI Features

- **Step-by-step OAuth flow** with visual progress indicators
- **Real-time status updates** showing connection and authentication status
- **Interactive chat interface** for natural language interaction with the agent
- **Quick action buttons** for common tasks like scheduling meetings and searching contacts
- **Tool validation** that automatically filters out tools with schema issues
- **Session management** with the ability to clear and restart authentication

3. **Get Descope Bearer Token** (Only for manual token agents)

   To authenticate with the Descope MCP server manually, you need a valid bearer token. Here are the steps:

   a. **Using Descope Outbound Apps** (Recommended):

   - Set up an Outbound App in your Descope project
   - Configure it to access the MCP server
   - Use Descope's authentication flow to get a bearer token

   b. **Using Descope SDK**:

   ```python
   from descope import DescopeClient

   descope = DescopeClient(project_id="your_project_id")

   # Authenticate user and get session token
   auth_response = descope.otp.sign_in.email("user@example.com", "123456")
   session_token = auth_response["sessionToken"]

   # Get bearer token for MCP server access
   bearer_token = auth_response["sessionToken"]  # or use refresh token
   ```

   c. **Manual Token**:

   - If you have a valid Descope session token, you can use it as the bearer token
   - Ensure the token has the necessary scopes for MCP server access

## Usage

### 1. OAuth Discovery Agent (Automatic Authentication)

```bash
python3 descope_oauth_agent.py
```

This will:

1. **Automatically discover** Descope OAuth endpoints
2. **Open your browser** for OAuth authentication
3. **Automatically obtain** the bearer token
4. **Connect to MCP server** with the discovered token
5. **Test the connection** and list available tools
6. **Start interactive session** if desired

**No manual token setup required!** 🎉

### 2. Full OAuth Discovery Agent (Advanced)

```bash
python3 oauth_discovery_agent.py
```

This provides:

1. **Comprehensive OAuth discovery** for any MCP server
2. **Multiple OAuth flow support** (authorization code, implicit)
3. **Well-known endpoint discovery**
4. **Fallback endpoint inference**
5. **Full OAuth 2.0/OpenID Connect support**

### 3. MultiServerMCPClient Agent (Manual Token)

```bash
python3 multi_client_agent.py
```

This requires manual token setup and will:

1. Test connection to the Descope MCP server using MultiServerMCPClient
2. Test multiple servers simultaneously
3. List available tools from all servers
4. Optionally start an interactive session

### 4. StateGraph Agent (Advanced)

```bash
python3 state_graph_agent.py
```

This demonstrates:

1. Scope-based requests with custom headers
2. StateGraph implementation for complex workflows
3. Advanced tool integration
4. Interactive StateGraph session

### 5. Simple Agent (Basic)

```bash
python3 simple_agent.py
```

Basic implementation using direct MCP client (legacy approach).

### 6. Original Agent with uAgents Integration

```bash
python3 agent.py
```

Note: The original agent requires additional uagents dependencies that may need to be resolved.

## Server URLs

The agent is configured to connect to:

- **HubSpot CRM MCP Server**: `https://hubspot-crm.preview.descope.org/mcp`

You can modify the URL in the code to connect to other Descope MCP servers:

- **Weather MCP Server**: `https://weather-mcp-server.descope-cx.workers.dev/sse`
- **Brave Search MCP Server**: `https://brave-search-mcp-server.descope-cx.workers.dev/sse`

## Authentication Flow

1. The agent reads the `DESCOPE_BEARER_TOKEN` from environment variables
2. It includes the token in the `Authorization` header as `Bearer {token}`
3. The Descope MCP server validates the token and grants access
4. The agent can then discover and use available tools

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check that your bearer token is valid and not expired
2. **403 Forbidden**: Ensure your token has the necessary scopes for the MCP server
3. **404 Not Found**: Verify the MCP server URL is correct
4. **Connection Timeout**: Check network connectivity and server availability

### Getting a Valid Token

If you don't have a Descope bearer token:

1. **Sign up for Descope**: Go to [app.descope.com](https://app.descope.com)
2. **Create a Project**: Set up a new project in Descope
3. **Configure Authentication**: Set up your authentication method (email, social, etc.)
4. **Get Session Token**: Use Descope's SDK or REST API to authenticate and get a session token
5. **Use as Bearer Token**: The session token can typically be used as a bearer token for MCP servers

## OAuth Discovery Process

The OAuth discovery agents automatically handle the complete authentication flow:

### 🔍 **Discovery Phase**

1. **Endpoint Detection**: Scans for OAuth discovery endpoints (`.well-known/oauth-authorization-server`)
2. **Fallback Inference**: Uses common Descope OAuth endpoint patterns if discovery fails
3. **Endpoint Validation**: Verifies that discovered endpoints are accessible

### 🔐 **Authentication Phase**

1. **Browser Launch**: Automatically opens your default browser
2. **OAuth Flow**: Handles the complete OAuth 2.0 authorization code flow
3. **Token Exchange**: Exchanges authorization code for access token
4. **Token Storage**: Securely handles the bearer token

### 🔗 **Connection Phase**

1. **MCP Connection**: Uses the obtained token to connect to the MCP server
2. **Tool Discovery**: Automatically loads available tools from the server
3. **Agent Creation**: Creates a LangGraph agent with the discovered tools

### 🌐 **Interactive Phase**

1. **Chat Interface**: Provides an interactive chat interface
2. **Tool Execution**: Executes MCP tools based on user requests
3. **Response Handling**: Returns formatted responses from the agent

## Key Features Explained

### MultiServerMCPClient Benefits

The `MultiServerMCPClient` approach provides several advantages:

1. **Multiple Server Support**: Connect to multiple MCP servers simultaneously
2. **Runtime Headers**: Pass authentication and custom headers with every request
3. **Transport Flexibility**: Support for both `streamable_http` and `sse` transports
4. **Scope Management**: Request specific scopes through headers
5. **Tool Aggregation**: Automatically combine tools from multiple servers

### Scope-Based Requests

You can request specific scopes from MCP servers using custom headers:

```python
client = MultiServerMCPClient({
    "descope_crm": {
        "transport": "streamable_http",
        "url": "https://hubspot-crm.preview.descope.org/mcp",
        "headers": {
            "Authorization": f"Bearer {token}",
            "X-Requested-Scopes": "read:contacts,write:contacts",
            "X-Client-ID": "langgraph-agent",
        },
    }
})
```

### StateGraph Integration

The StateGraph approach provides more control over the agent workflow:

```python
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

builder = StateGraph(MessagesState)
builder.add_node("call_model", call_model)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", tools_condition)
builder.add_edge("tools", "call_model")
graph = builder.compile()
```

## Architecture

```
┌─────────────────┐    MultiServerMCPClient     ┌──────────────────┐
│   LangGraph     │ ──────────────────────────► │  Descope MCP     │
│     Agent       │                             │     Server       │
│                 │ ◄────────────────────────── │                  │
└─────────────────┘    Bearer Token + Headers  └──────────────────┘
       │
       ▼
┌─────────────────┐    MultiServerMCPClient     ┌──────────────────┐
│   Multiple      │ ──────────────────────────► │   Weather MCP    │
│   Servers       │                             │     Server       │
│   Support       │ ◄────────────────────────── │                  │
└─────────────────┘    Bearer Token + Headers  └──────────────────┘
```

The agent uses the MCP (Model Context Protocol) with `MultiServerMCPClient` to communicate with multiple remote Descope servers, enabling secure, authenticated access to various tools and services with scope-based permissions.
