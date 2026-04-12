import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { Context, Hono } from "hono";
import { DescopeMcpProvider } from "./descope-hono/provider";
import { descopeMcpAuthRouter } from "./descope-hono/router";
import { descopeMcpBearerAuth } from "./descope-hono/middleware/bearerAuth";
import { cors } from "hono/cors";

type Bindings = {
	DESCOPE_PROJECT_ID: string;
	DESCOPE_MANAGEMENT_KEY: string;
	DESCOPE_BASE_URL?: string;
	SERVER_URL: string;
};

type Props = {
	bearerToken: string;
};

type State = null;

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

export class MyMCP extends McpAgent<Bindings, State, Props> {
	server = new McpServer({
		name: "Weather MCP",
		version: "1.0.0",
	});

	async init() {
		// Register weather tools
		this.server.tool(
			"get-alerts",
			"Get weather alerts for a state",
			{
				state: z.string().length(2).describe("Two-letter state code (e.g. CA, NY)"),
			},
			async ({ state }) => {
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
				const alertsText = `Active alerts for ${stateCode}:\n\n${formattedAlerts.join("\n")}`;

				return {
					content: [
						{
							type: "text",
							text: alertsText,
						},
					],
				};
			},
		);

		this.server.tool(
			"get-forecast",
			"Get weather forecast for a location",
			{
				latitude: z.number().min(-90).max(90).describe("Latitude of the location"),
				longitude: z.number().min(-180).max(180).describe("Longitude of the location"),
			},
			async ({ latitude, longitude }) => {
				// Get grid point data
				const pointsUrl = `${NWS_API_BASE}/points/${latitude.toFixed(4)},${longitude.toFixed(4)}`;
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
						`Temperature: ${period.temperature || "Unknown"}°${period.temperatureUnit || "F"}`,
						`Wind: ${period.windSpeed || "Unknown"} ${period.windDirection || ""}`,
						`${period.shortForecast || "No forecast available"}`,
						"---",
					].join("\n"),
				);

				const forecastText = `Forecast for ${latitude}, ${longitude}:\n\n${formattedForecast.join("\n")}`;

				return {
					content: [
						{
							type: "text",
							text: forecastText,
						},
					],
				};
			},
		);
	}
}

// Create the main Hono app
const app = new Hono<{ Bindings: Bindings }>();

// Apply CORS middleware
app.use(cors({
	origin: "*",
	allowHeaders: ["Content-Type", "Authorization", "mcp-protocol-version"],
	maxAge: 86400,
}));

// OAuth routes handler
const handleOAuthRoute = async (c: Context) => {
	const provider = new DescopeMcpProvider({}, { env: c.env })
	const router = descopeMcpAuthRouter(provider);
	return router.fetch(c.req.raw, c.env, c.executionCtx);
};

// OAuth routes
app.use("/.well-known/oauth-authorization-server", handleOAuthRoute);
app.all("/authorize", handleOAuthRoute);
app.use("/register", handleOAuthRoute);

// Protected MCP routes
app.use("/sse/*", descopeMcpBearerAuth());
app.route("/sse", new Hono().mount("/", (req, env, ctx) => {
	const authHeader = req.headers.get("authorization");
	ctx.props = {
		bearerToken: authHeader,
	};
	return MyMCP.mount("/sse").fetch(req, env, ctx);
}));

export default app;