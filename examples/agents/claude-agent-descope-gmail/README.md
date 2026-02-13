# Claude MCP Gmail Agent with Human-in-the-Loop Approval

A secure AI agent that integrates Gmail using Claude's Agents SDK, Model Context Protocol (MCP), and Descope for authentication, authorization, and progressive OAuth scoping with human approval for sensitive actions.

## Features

- 📧 Read emails from Gmail inbox
- ✉️ Send emails with approval workflow
- 🔐 Progressive OAuth scoping (permissions requested on-demand)
- 🎫 Human-in-the-loop approval via Descope Enchanted Links
- 🔒 Agent never directly handles Gmail tokens (Agent → MCP → Descope → Gmail)

## Prerequisites

- Node.js 18+
- Descope account and project
- Anthropic API key
- Google Cloud project with Gmail API enabled

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Descope

**Create Inbound App:**
1. Go to Descope Console → Applications → Inbound Apps
2. Create new application
3. Add scopes: `google-read`, `google-send`
4. Note your Project ID, MCP Server ID, Client ID, and Client Secret

**Create Connection:**
1. Go to Applications → Connections → Add Connection
2. Select Gmail
3. App ID: `gmail`
4. OAuth Scopes: `gmail.readonly`, `gmail.send`
5. Redirect URL: `http://localhost:3000/connection-complete`

**Enable Enchanted Link:**
1. Go to Authentication Methods → Enchanted Link
2. Enable and configure

### 3. Set Environment Variables

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DESCOPE_PROJECT_ID=your_descope_project_id_here
DESCOPE_CLIENT_ID=your_descope_client_id_here
DESCOPE_CLIENT_SECRET=your_descope_client_secret_here
MCP_SERVER_ID=your_mcp_server_id_here
```

### 4. Run the Agent

```bash
npm start
```

## Usage

**Read emails:**
```
You: Read my latest emails
```

**Send email:**
```
You: Send an email to test@example.com with subject "Hello" and body "Test message"
```

The agent will request Gmail permissions only when needed and require approval before sending any email.

## Architecture

```
User → Agent (Claude) → MCP Server → Descope → Gmail API
```

The agent never directly handles Gmail OAuth tokens. The MCP server requests them from Descope, creating an extra security boundary.

## Security

- **Authentication**: OAuth 2.0 via Descope Inbound Apps
- **Authorization**: Tool-level scopes
- **Progressive Scoping**: Gmail permissions requested on-demand
- **Human Approval**: Enchanted Links for sensitive actions
- **Token Isolation**: Agent never touches Gmail tokens

## Project Structure

```
src/
├── cli-agent.ts       # Main agent
├── mcp-stdio.ts       # MCP server with Gmail tools
├── auth.ts            # Descope authentication
└── approval.ts        # Enchanted Link approval
```

## Learn More

- [Claude Agents SDK](https://github.com/anthropics/anthropic-sdk-typescript)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Descope Documentation](https://docs.descope.com/)

## License

MIT
