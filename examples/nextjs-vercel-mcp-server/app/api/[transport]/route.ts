import { createMcpHandler, withMcpAuth } from "mcp-handler";
import { z } from "zod";
import DescopeClient from "@descope/node-sdk";

const DESCOPE_PROJECT_ID = process.env.NEXT_PUBLIC_DESCOPE_PROJECT_ID;
const DESCOPE_BASE_URL = process.env.NEXT_PUBLIC_DESCOPE_BASE_URL;

if (!DESCOPE_PROJECT_ID) {
  throw new Error("DESCOPE_PROJECT_ID environment variable is required");
}

const descopeClient = DescopeClient({
  projectId: DESCOPE_PROJECT_ID,
  baseUrl: DESCOPE_BASE_URL
});

const handler = createMcpHandler(
  (server) => {
    server.tool("echo", "Echo a message", {}, async () => {
      return {
        content: [
          {
            type: "text",
            text: "Hello, world!",
          },
        ],
      };
    });
  },
  undefined,
  {
    // basePath is the path to the MCP server. Incorrectly setting this will affect tool discovery by the client.
    basePath: "/api",
    verboseLogs: true,
    maxDuration: 800,
    disableSse: false,
  }
);

const verifyToken = async (req: Request, bearerToken?: string) => {
  if (!bearerToken) return undefined;

  try {
    // Validate the JWT token with Descope
    const authInfo = await descopeClient.validateSession(bearerToken);

    const scopeString = authInfo.token.scope as string;
    const scopes = scopeString ? scopeString.split(" ") : [];
    const clientId = authInfo.token.azp as string;

    return {
      token: bearerToken,
      scopes: scopes,
      clientId: clientId,
      extra: {
        // Optional extra information
        userId: authInfo.token.sub,
      },
    };
  } catch (error) {
    console.error("Token validation failed:", error);
    return undefined;
  }
};

const authHandler = withMcpAuth(handler, verifyToken, {
  required: true,
  resourceMetadataPath: "/.well-known/oauth-protected-resource",
});

export { authHandler as GET, authHandler as POST };
