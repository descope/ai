# Claude Gmail Agent with Descope

A Claude-powered AI agent that integrates with Gmail through the Model Context Protocol (MCP), using Descope's Agentic Identity Hub for authentication, progressive OAuth scoping, and human-in-the-loop email approval.

Read the full tutorial: [Build a Claude Gmail Agent with Descope](#) <!-- add blog link once published -->

## What This Does

- Authenticates users via Descope's OAuth 2.0 consent flow
- Connects to a remote MCP server deployed on Vercel
- Reads Gmail inbox using progressive OAuth scoping (`gmail.readonly`)
- Sends emails with human-in-the-loop approval via Descope Enchanted Link (`gmail.send`)
- Verifies MCP access token and enforces required scopes at connection time

## Architecture

```
CLI Agent → Descope (auth) → Remote MCP Server (Vercel) → Gmail API
```

The MCP server handles all on-behalf-of token management. The agent never directly touches Gmail OAuth credentials — it calls tools, the MCP server fetches the right token from Descope, makes the API call, and returns the result.

The MCP server is based on Descope's [Next.js MCP template](https://github.com/descope/mcp-with-next-js-and-descope). Deploy your own instance and point the agent at it.

## Prerequisites

- Node.js 18+
- [Anthropic API key](https://console.anthropic.com)
- [Descope account](https://www.descope.com) with:
  - A Gmail Connection configured in Agentic Identity Hub
  - An MCP Server configured with `google-read` and `google-send` scopes
- Google Cloud Console project with OAuth credentials (client ID and secret)
- A deployed instance of the [Descope Next.js MCP template](https://github.com/descope/mcp-with-next-js-and-descope)

## Setup

**1. Install dependencies**

```bash
npm install
```

**2. Configure environment variables**

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=your_anthropic_api_key

DESCOPE_PROJECT_ID=your_descope_project_id
DESCOPE_CLIENT_ID=your_mcp_server_client_id
DESCOPE_CLIENT_SECRET=your_mcp_server_client_secret
MCP_SERVER_ID=your_mcp_server_id

MCP_SERVER_URL=https://your-vercel-app.vercel.app/api/mcp
```

You can find `DESCOPE_PROJECT_ID`, `DESCOPE_CLIENT_ID`, `DESCOPE_CLIENT_SECRET`, and `MCP_SERVER_ID` in your Descope Console under **Agentic Identity Hub → MCP Servers → your server → Usage Samples**.

**3. Run the agent**

```bash
npx tsx src/cli-agent.ts
```

## How It Works

**Authentication**

On startup, the agent opens a browser for you to authenticate with Descope. After you authorize the `google-read` and `google-send` MCP scopes, you're redirected back and the agent receives an MCP access token.

**Connection-time scope verification**

When the agent connects to the remote MCP server, the server validates the token and checks for the `google-read` scope before allowing any tools to be called. Connections without the required scope are rejected immediately.

**Reading emails**

Type `read emails` in the chat. If you haven't connected Gmail yet, the agent opens a browser for you to grant `gmail.readonly` access. Once granted, the MCP server fetches your Gmail token from Descope on your behalf and returns your latest emails.

**Sending emails**

Type `send email to <address>` in the chat. The agent first checks for `gmail.send` permission (requesting it if needed), then triggers a human approval step. You'll receive an Enchanted Link in your email — click it to approve, and the email sends.

**Exiting**

Type `exit` to quit.

## Project Structure

```
src/
  cli-agent.ts   # Main agent: OAuth callbacks, MCP connection, chat loop
  auth.ts        # Descope authentication helper
  approval.ts    # Enchanted Link approval polling
```

## Environment Variables Reference

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `DESCOPE_PROJECT_ID` | Your Descope project ID |
| `DESCOPE_CLIENT_ID` | MCP server OAuth client ID |
| `DESCOPE_CLIENT_SECRET` | MCP server OAuth client secret |
| `MCP_SERVER_ID` | Your Descope MCP server ID |
| `MCP_SERVER_URL` | URL of your deployed MCP server |

## Related

- [Descope Agentic Identity Hub docs](https://docs.descope.com/agentic-identity-hub)
- [MCP specification](https://spec.modelcontextprotocol.io)
- [Descope Next.js MCP template](https://github.com/descope/mcp-with-next-js-and-descope)
- [Anthropic Claude SDK](https://github.com/anthropic-ai/sdk-python)