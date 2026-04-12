import {
  protectedResourceHandler,
  metadataCorsOptionsRequestHandler,
} from "mcp-handler";

const AUTH_SERVER_URL = process.env.DESCOPE_MCP_ISSUER_URL;

if (!AUTH_SERVER_URL) {
  throw new Error("AUTH_SERVER_URL environment variable is required");
}

const handler = protectedResourceHandler({
  authServerUrls: [AUTH_SERVER_URL],
});

export const GET = handler;
export const OPTIONS = metadataCorsOptionsRequestHandler();
