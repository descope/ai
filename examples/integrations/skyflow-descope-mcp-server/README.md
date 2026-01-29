# Skyflow + Descope MCP Server

An MCP (Model Context Protocol) server that provides secure access to Skyflow vault data through authenticated API calls. This server integrates Descope for user authentication and Skyflow for sensitive data management.

## What This MCP Server Does

This MCP server enables AI assistants and other MCP clients to securely query and retrieve sensitive data stored in Skyflow vaults. It provides a `get_skyflow_records` tool that allows fetching records from Skyflow vault tables with support for filtering, pagination, redaction, and tokenization.

## How It Integrates with Skyflow

The server implements a secure token exchange flow to access Skyflow vaults:

1. **Authentication with Descope**: Users authenticate using Descope and receive a JWT token
2. **Token Validation**: The server validates the Descope JWT token using Descope's Node SDK
3. **Token Exchange**: The validated Descope token is exchanged for a Skyflow access token using Skyflow's Security Token Service (STS) via OAuth 2.0 token exchange
4. **Skyflow API Calls**: The Skyflow token is used to make authenticated API calls to the Skyflow vault to retrieve sensitive data

This integration ensures that:
- Only authenticated users can access Skyflow data
- Tokens are securely exchanged without exposing credentials
- Each request uses the appropriate Skyflow token for the authenticated user

## Key Components

- **Vercel's [mcp-handler](https://github.com/vercel/mcp-handler)**: Handles the MCP protocol communication and serverless function deployment
- **Descope Node SDK**: Validates user sessions and provides authentication context
- **Skyflow STS Integration**: Exchanges Descope tokens for Skyflow access tokens
- **Skyflow Vault API**: Retrieves sensitive data from Skyflow vaults

## Requirements

Before proceeding, make sure you have the following:

- [Node.js](https://nodejs.org/) (version 20 or later)
- A valid Descope [Project ID](https://app.descope.com/settings/project)
- A Skyflow account with:
  - Vault URL identifier
  - Vault ID
  - Service Account ID
  - STS (Security Token Service) URL (optional, defaults to `https://api.skyflowapis.com/v1/auth/sts/token`)

## Running the Server

First, add the environment variables in a `.env` file at the root:

```bash
# Descope Configuration
NEXT_PUBLIC_DESCOPE_PROJECT_ID=     # Your Descope project ID
NEXT_PUBLIC_DESCOPE_BASE_URL=       # Your Descope base URL (optional, defaults to https://api.descope.com)
DESCOPE_MCP_ISSUER_URL=             # Your MCP server issuer URL from the Descope Console (MCP server config)

# Skyflow Configuration
SKYFLOW_VAULT_URL_IDENTIFIER=       # Your Skyflow vault URL identifier (e.g., "manage-blitz")
SKYFLOW_VAULT_ID=                   # Your Skyflow vault ID
SKYFLOW_SERVICE_ACCOUNT_ID=         # Your Skyflow service account ID
SKYFLOW_STS_URL=                    # Skyflow STS URL (optional, defaults to https://api.skyflowapis.com/v1/auth/sts/token)
```

> **Note**: The `DESCOPE_MCP_ISSUER_URL` can be found in your Descope Console under your [MCP server configuration](https://app.descope.com/agentic-hub/mcp-servers) settings.

Then, install dependencies:

```bash
npm install
```

Finally, run the server:

```bash
npm run dev
```

The server will start on port 3000 (or the port specified in your environment variables).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/[transport]` | Handles incoming MCP protocol messages (supports SSE and HTTP transports) |
| `GET` | `/.well-known/oauth-protected-resource` | Provides OAuth protected resource metadata for MCP clients |

## Authentication Flow

The server implements a secure authentication and token exchange flow:

1. **Client Authentication**: MCP clients must provide a valid Descope bearer token in the `Authorization` header
2. **Token Validation**: The server validates the Descope token using `descopeClient.validateSession()`
3. **Token Exchange**: The validated Descope token is exchanged for a Skyflow token via Skyflow's STS endpoint using OAuth 2.0 token exchange (RFC 8693)
4. **Context Injection**: Both the Descope token and Skyflow token are made available to MCP tools in the authentication context

All MCP endpoints require a valid bearer token. The Skyflow token is automatically exchanged and included in the tool execution context.

## Available Tools

### `get_skyflow_records`

Fetches record(s) from a Skyflow vault table. This tool retrieves sensitive data from Skyflow using the authenticated user's token obtained through the Descope-to-Skyflow token exchange.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tableName` | string | Yes | Name of the table that contains the records |
| `skyflow_ids` | string[] | No | Array of skyflow_id values of the records to return. If not specified, returns the first 25 records in the table |
| `redaction` | string | No | Redaction level to enforce (`DEFAULT`, `MASKED`, `PLAIN_TEXT`, `REDACTED`). Defaults to `DEFAULT` |
| `tokenization` | boolean | No | If true, returns tokens for fields with tokenization enabled. Only applicable if skyflow_id values are specified |
| `returnFileMetadata` | boolean | No | If true, returns file metadata |
| `fields` | string[] | No | Array of field names to return. If not specified, returns all fields |
| `offset` | number | No | Record position at which to start receiving data. Defaults to 0 |
| `limit` | number | No | Number of records to return. Maximum 25. Defaults to 25 |
| `downloadURL` | boolean | No | If true, returns download URLs for fields with a file data type. URLs are valid for 15 minutes |
| `column_name` | string | No | Name of a unique column to filter by. Cannot be used with `skyflow_ids` |
| `column_values` | string[] | No | Array of column values to filter by. Requires `column_name`. Cannot be used with `skyflow_ids` |
| `order_by` | string | No | Order to return records (`ASCENDING`, `DESCENDING`, `NONE`). Defaults to `ASCENDING` |

**Example Usage:**
```json
{
  "tableName": "users",
  "skyflow_ids": ["id1", "id2"],
  "redaction": "PLAIN_TEXT",
  "fields": ["email", "name"]
}
```

## Connecting to the Server

You can connect to the server using the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) or any other MCP client. Be sure to:

1. Include the `/api` path in the connection URL (e.g., `http://localhost:3000/api/mcp`)
2. Provide a valid Descope bearer token in the `Authorization` header
3. Ensure your Descope token is configured for token exchange with Skyflow STS

## License

This project is licensed under the MIT License.
