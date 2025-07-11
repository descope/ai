import {
  createMcpHandler,
  experimental_withMcpAuth,
} from "@vercel/mcp-adapter";
import DescopeClient from "@descope/node-sdk";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { getAlerts, getForecast } from "./tools/weather";

/**
 * For later reference - this function verifies the token and returns the auth info
 * @param req
 * @param token
 * @returns
 */
async function verifyToken(
  req: Request,
  token?: string
): Promise<AuthInfo | undefined> {
  if (!token) {
    return undefined;
  }

  const descope = DescopeClient({
    projectId: process.env.DESCOPE_PROJECT_ID!,
    baseUrl: process.env.DESCOPE_BASE_URL!,
  });

  const authInfo = await descope.validateSession(token).catch((e) => {
    return undefined;
  });

  if (!authInfo) {
    return undefined;
  }

  const scope = authInfo.token.scope as string | undefined;
  const scopes = scope ? scope.split(" ").filter(Boolean) : [];

  const clientId = authInfo.token.azp as string;

  return {
    token: authInfo.jwt,
    clientId,
    scopes,
    expiresAt: authInfo.token.exp,
  };
}

const mcpHandler = async (req: Request) => {
  return createMcpHandler(
    (server: any) => {
      // Weather tools
      getAlerts(server);
      getForecast(server);
    },
    {
      capabilities: {
        tools: {
          getAlerts: {
            description: "Get weather alerts for a state",
          },
          getForecast: {
            description: "Get weather forecast for a location",
          },
        },
      },
    },
    {
      redisUrl: process.env.REDIS_URL,
      basePath: "",
      verboseLogs: true,
      maxDuration: 60,
    }
  )(req);
};

const handler = experimental_withMcpAuth(mcpHandler, verifyToken, {
  required: true,
});

export { handler as GET, handler as POST, handler as DELETE };
