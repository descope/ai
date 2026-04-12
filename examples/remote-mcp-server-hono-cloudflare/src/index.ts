import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { Hono } from "hono";
import { layout, homeContent } from "./home";
import { descopeMcpBearerAuth } from "./lib/bearer-auth";
import { cors } from "hono/cors";
import { getDescopeOAuthEndpointUrl } from "./lib/utils";
import { AuthInfo } from "./lib/schemas";

type Bindings = {
	DESCOPE_PROJECT_ID: string;
	DESCOPE_MANAGEMENT_KEY: string;
	DESCOPE_BASE_URL?: string;
	SERVER_URL: string;
};

type Props = {
	auth: AuthInfo;
};

type State = null;
export class MyMCP extends McpAgent<Bindings, State, Props> {
	server = new McpServer({
		name: "Demo",
		version: "1.0.0",
	});

	async init() {
		this.server.tool("add", { a: z.number(), b: z.number() }, async ({ a, b }) => ({
			content: [{ type: "text", text: String(a + b) }],
		}));

		this.server.tool("getToken", {}, async () => ({
			content: [{ type: "text", text: String(`User's token: ${this.props.auth.token}`) }],
		}));
	}
}

const app = new Hono<{ Bindings: Bindings }>();

app.use(cors({
	origin: "*",
	allowHeaders: ["Content-Type", "Authorization", "mcp-protocol-version"],
	maxAge: 86400,
}));

app.get("/", async (c) => {
	const content = await homeContent(c.req.raw);
	return c.html(layout(content, "MCP Remote Auth Demo - Home"));
});

app.get("/.well-known/oauth-authorization-server", async (c) => {
	const baseURL = c.env.DESCOPE_BASE_URL || "https://api.descope.com";
	return c.json({
		issuer: `${baseURL}/v1/apps/${c.env.DESCOPE_PROJECT_ID}`,
		registration_endpoint: `${baseURL}/${c.env.DESCOPE_PROJECT_ID}/oauth2/v1/apps/register`,

		authorization_endpoint: getDescopeOAuthEndpointUrl(baseURL, "authorize"),
		token_endpoint: getDescopeOAuthEndpointUrl(baseURL, "token"),
		revocation_endpoint: getDescopeOAuthEndpointUrl(baseURL, "revoke"),
		userinfo_endpoint: getDescopeOAuthEndpointUrl(baseURL, "userinfo"),

		scopes_supported: ["openid", "email", "profile"],
		response_types_supported: ["code"],
		code_challenge_methods_supported: ["S256"],
		token_endpoint_auth_methods_supported: ["client_secret_post"],
		grant_types_supported: ["authorization_code", "refresh_token"],
	});
});

// Protected MCP routes
app.use("/sse/*", descopeMcpBearerAuth());
app.route("/sse", new Hono().mount("/", (req, env, ctx) => {
	ctx.props = {
		auth: ctx.props.auth,
	};
	return MyMCP.mount("/sse").fetch(req, env, ctx);
}));

export default app;

