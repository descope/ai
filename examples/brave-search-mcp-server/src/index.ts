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
	BRAVE_SEARCH_API_KEY: string;
};

type Props = {
	bearerToken: string;
};

type State = null;

interface BraveWeb {
	web?: {
		results?: Array<{
			title: string;
			description: string;
			url: string;
			language?: string;
			published?: string;
			rank?: number;
		}>;
	};
	locations?: {
		results?: Array<{
			id: string;
			title?: string;
		}>;
	};
}

interface BraveLocation {
	id: string;
	name: string;
	address: {
		streetAddress?: string;
		addressLocality?: string;
		addressRegion?: string;
		postalCode?: string;
	};
	coordinates?: {
		latitude: number;
		longitude: number;
	};
	phone?: string;
	rating?: {
		ratingValue?: number;
		ratingCount?: number;
	};
	openingHours?: string[];
	priceRange?: string;
}

interface BravePoiResponse {
	results: BraveLocation[];
}

interface BraveDescription {
	descriptions: { [id: string]: string };
}

export class MyMCP extends McpAgent<Bindings, State, Props> {
	server = new McpServer({
		name: "Brave Search MCP",
		version: "1.0.0",
	});

	async init() {
		const braveApiKey = (this.env as Bindings).BRAVE_SEARCH_API_KEY;

		// Check for API key
		if (!braveApiKey) {
			throw new Error("BRAVE_SEARCH_API_KEY environment variable is required");
		}

		const RATE_LIMIT = {
			perSecond: 1,
			perMonth: 15000
		};

		let requestCount = {
			second: 0,
			month: 0,
			lastReset: Date.now()
		};

		const checkRateLimit = () => {
			const now = Date.now();
			if (now - requestCount.lastReset > 1000) {
				requestCount.second = 0;
				requestCount.lastReset = now;
			}
			if (requestCount.second >= RATE_LIMIT.perSecond ||
				requestCount.month >= RATE_LIMIT.perMonth) {
				throw new Error('Rate limit exceeded');
			}
			requestCount.second++;
			requestCount.month++;
		};

		const performWebSearch = async (query: string, count: number = 10, offset: number = 0) => {
			checkRateLimit();
			const url = new URL('https://api.search.brave.com/res/v1/web/search');
			url.searchParams.set('q', query);
			url.searchParams.set('count', Math.min(count, 20).toString());
			url.searchParams.set('offset', offset.toString());

			const response = await fetch(url, {
				headers: {
					'Accept': 'application/json',
					'Accept-Encoding': 'gzip',
					'X-Subscription-Token': braveApiKey
				}
			});

			if (!response.ok) {
				throw new Error(`Brave API error: ${response.status} ${response.statusText}\n${await response.text()}`);
			}

			const data = await response.json() as BraveWeb;
			const results = (data.web?.results || []).map(result => ({
				title: result.title || '',
				description: result.description || '',
				url: result.url || ''
			}));

			return results.map(r =>
				`Title: ${r.title}\nDescription: ${r.description}\nURL: ${r.url}`
			).join('\n\n');
		};

		const performLocalSearch = async (query: string, count: number = 5) => {
			checkRateLimit();
			const webUrl = new URL('https://api.search.brave.com/res/v1/web/search');
			webUrl.searchParams.set('q', query);
			webUrl.searchParams.set('search_lang', 'en');
			webUrl.searchParams.set('result_filter', 'locations');
			webUrl.searchParams.set('count', Math.min(count, 20).toString());

			const webResponse = await fetch(webUrl, {
				headers: {
					'Accept': 'application/json',
					'Accept-Encoding': 'gzip',
					'X-Subscription-Token': braveApiKey
				}
			});

			if (!webResponse.ok) {
				throw new Error(`Brave API error: ${webResponse.status} ${webResponse.statusText}\n${await webResponse.text()}`);
			}

			const webData = await webResponse.json() as BraveWeb;
			const locationIds = webData.locations?.results?.filter((r): r is { id: string; title?: string } => r.id != null).map(r => r.id) || [];

			if (locationIds.length === 0) {
				return performWebSearch(query, count);
			}

			const [poisData, descriptionsData] = await Promise.all([
				getPoisData(locationIds),
				getDescriptionsData(locationIds)
			]);

			return formatLocalResults(poisData, descriptionsData);
		};

		const getPoisData = async (ids: string[]): Promise<BravePoiResponse> => {
			checkRateLimit();
			const url = new URL('https://api.search.brave.com/res/v1/local/pois');
			ids.filter(Boolean).forEach(id => url.searchParams.append('ids', id));
			const response = await fetch(url, {
				headers: {
					'Accept': 'application/json',
					'Accept-Encoding': 'gzip',
					'X-Subscription-Token': braveApiKey
				}
			});

			if (!response.ok) {
				throw new Error(`Brave API error: ${response.status} ${response.statusText}\n${await response.text()}`);
			}

			return await response.json() as BravePoiResponse;
		};

		const getDescriptionsData = async (ids: string[]): Promise<BraveDescription> => {
			checkRateLimit();
			const url = new URL('https://api.search.brave.com/res/v1/local/descriptions');
			ids.filter(Boolean).forEach(id => url.searchParams.append('ids', id));
			const response = await fetch(url, {
				headers: {
					'Accept': 'application/json',
					'Accept-Encoding': 'gzip',
					'X-Subscription-Token': braveApiKey
				}
			});

			if (!response.ok) {
				throw new Error(`Brave API error: ${response.status} ${response.statusText}\n${await response.text()}`);
			}

			return await response.json() as BraveDescription;
		};

		const formatLocalResults = (poisData: BravePoiResponse, descData: BraveDescription): string => {
			return (poisData.results || []).map(poi => {
				const address = [
					poi.address?.streetAddress ?? '',
					poi.address?.addressLocality ?? '',
					poi.address?.addressRegion ?? '',
					poi.address?.postalCode ?? ''
				].filter(part => part !== '').join(', ') || 'N/A';

				return `Name: ${poi.name}
Address: ${address}
Phone: ${poi.phone || 'N/A'}
Rating: ${poi.rating?.ratingValue ?? 'N/A'} (${poi.rating?.ratingCount ?? 0} reviews)
Price Range: ${poi.priceRange || 'N/A'}
Hours: ${(poi.openingHours || []).join(', ') || 'N/A'}
Description: ${descData.descriptions[poi.id] || 'No description available'}
`;
			}).join('\n---\n') || 'No local results found';
		};

		// Register web search tool
		this.server.tool("brave_web_search", {
			query: z.string().max(400),
			count: z.number().min(1).max(20).default(10),
			offset: z.number().min(0).max(9).default(0)
		}, async ({ query, count, offset }) => ({
			content: [{ type: "text", text: await performWebSearch(query, count, offset) }],
		}));

		// Register local search tool
		this.server.tool("brave_local_search", {
			query: z.string(),
			count: z.number().min(1).max(20).default(5)
		}, async ({ query, count }) => ({
			content: [{ type: "text", text: await performLocalSearch(query, count) }],
		}));
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