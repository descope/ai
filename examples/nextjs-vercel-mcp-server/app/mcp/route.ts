import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import {
  createMcpHandler,
  experimental_withMcpAuth,
} from "@vercel/mcp-adapter";
import DescopeClient from "@descope/node-sdk";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { z } from "zod";

const NWS_API_BASE = "https://api.weather.gov";
const USER_AGENT = "weather-app/1.0";

// Helper function for making NWS API requests
async function makeNWSRequest<T>(url: string): Promise<T | null> {
  const headers = {
    "User-Agent": USER_AGENT,
    Accept: "application/geo+json",
  };

  try {
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error("Error making NWS request:", error);
    return null;
  }
}

interface AlertFeature {
  properties: {
    event?: string;
    areaDesc?: string;
    severity?: string;
    status?: string;
    headline?: string;
  };
}

// Format alert data
function formatAlert(feature: AlertFeature): string {
  const props = feature.properties;
  return [
    `Event: ${props.event || "Unknown"}`,
    `Area: ${props.areaDesc || "Unknown"}`,
    `Severity: ${props.severity || "Unknown"}`,
    `Status: ${props.status || "Unknown"}`,
    `Headline: ${props.headline || "No headline"}`,
    "---",
  ].join("\n");
}

interface ForecastPeriod {
  name?: string;
  temperature?: number;
  temperatureUnit?: string;
  windSpeed?: string;
  windDirection?: string;
  shortForecast?: string;
}

interface AlertsResponse {
  features: AlertFeature[];
}

interface PointsResponse {
  properties: {
    forecast?: string;
  };
}

interface ForecastResponse {
  properties: {
    periods: ForecastPeriod[];
  };
}

// Weather tool functions
function getAlerts(server: any) {
  server.tool(
    "get-alerts",
    "Get weather alerts for a state",
    {
      state: z
        .string()
        .length(2)
        .describe("Two-letter state code (e.g. CA, NY)"),
    },
    async ({ state }: { state: string }) => {
      const stateCode = state.toUpperCase();
      const alertsUrl = `${NWS_API_BASE}/alerts?area=${stateCode}`;
      const alertsData = await makeNWSRequest<AlertsResponse>(alertsUrl);

      if (!alertsData) {
        return {
          content: [
            {
              type: "text",
              text: "Failed to retrieve alerts data",
            },
          ],
        };
      }

      const features = alertsData.features || [];
      if (features.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: `No active alerts for ${stateCode}`,
            },
          ],
        };
      }

      const formattedAlerts = features.map(formatAlert);
      const alertsText = `Active alerts for ${stateCode}:\n\n${formattedAlerts.join(
        "\n"
      )}`;

      return {
        content: [
          {
            type: "text",
            text: alertsText,
          },
        ],
      };
    }
  );
}

function getForecast(server: any) {
  server.tool(
    "get-forecast",
    "Get weather forecast for a location",
    {
      latitude: z
        .number()
        .min(-90)
        .max(90)
        .describe("Latitude of the location"),
      longitude: z
        .number()
        .min(-180)
        .max(180)
        .describe("Longitude of the location"),
    },
    async ({
      latitude,
      longitude,
    }: {
      latitude: number;
      longitude: number;
    }) => {
      // Get grid point data
      const pointsUrl = `${NWS_API_BASE}/points/${latitude.toFixed(
        4
      )},${longitude.toFixed(4)}`;
      const pointsData = await makeNWSRequest<PointsResponse>(pointsUrl);

      if (!pointsData) {
        return {
          content: [
            {
              type: "text",
              text: `Failed to retrieve grid point data for coordinates: ${latitude}, ${longitude}. This location may not be supported by the NWS API (only US locations are supported).`,
            },
          ],
        };
      }

      const forecastUrl = pointsData.properties?.forecast;
      if (!forecastUrl) {
        return {
          content: [
            {
              type: "text",
              text: "Failed to get forecast URL from grid point data",
            },
          ],
        };
      }

      // Get forecast data
      const forecastData = await makeNWSRequest<ForecastResponse>(forecastUrl);
      if (!forecastData) {
        return {
          content: [
            {
              type: "text",
              text: "Failed to retrieve forecast data",
            },
          ],
        };
      }

      const periods = forecastData.properties?.periods || [];
      if (periods.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: "No forecast periods available",
            },
          ],
        };
      }

      // Format forecast periods
      const formattedForecast = periods.map((period: ForecastPeriod) =>
        [
          `${period.name || "Unknown"}:`,
          `Temperature: ${period.temperature || "Unknown"}°${
            period.temperatureUnit || "F"
          }`,
          `Wind: ${period.windSpeed || "Unknown"} ${
            period.windDirection || ""
          }`,
          `${period.shortForecast || "No forecast available"}`,
          "---",
        ].join("\n")
      );

      const forecastText = `Forecast for ${latitude}, ${longitude}:\n\n${formattedForecast.join(
        "\n"
      )}`;

      return {
        content: [
          {
            type: "text",
            text: forecastText,
          },
        ],
      };
    }
  );
}

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

// Add CORS headers for cross-origin requests
const corsHandler = async (req: Request) => {
  // Handle preflight requests
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers":
          "Content-Type, Authorization, mcp-protocol-version",
        "Access-Control-Max-Age": "86400",
      },
    });
  }

  // Handle actual requests
  const response = await handler(req);

  // Add CORS headers to the response
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
  headers.set(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, mcp-protocol-version"
  );

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
};

export { corsHandler as GET, corsHandler as POST, corsHandler as DELETE };
