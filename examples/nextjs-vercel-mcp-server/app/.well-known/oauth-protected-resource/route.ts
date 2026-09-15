import {
  protectedResourceHandler,
  metadataCorsOptionsRequestHandler,
} from "mcp-handler";

const DESCOPE_MCP_ISSUER_URL = process.env.DESCOPE_MCP_ISSUER_URL;

if (!DESCOPE_MCP_ISSUER_URL) {
  throw new Error("DESCOPE_MCP_ISSUER_URL environment variable is required");
}

const handler = protectedResourceHandler({
  authServerUrls: [`${DESCOPE_MCP_ISSUER_URL}`],
});

const optionsHandler = metadataCorsOptionsRequestHandler();

export const GET = handler;
export const OPTIONS = metadataCorsOptionsRequestHandler();
