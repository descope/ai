import dotenv from "dotenv";
import express from "express";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { createServer } from "./create-server.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { descopeMcpAuthRouter, descopeMcpBearerAuth, DescopeMcpProvider, DescopeMcpProviderOptions } from "@descope/mcp-express";
import cors from "cors";
import path from 'path';

declare module "express-serve-static-core" {
    interface Request {
        /**
         * Information about the validated access token, if the `descopeMcpBearerAuth` middleware was used.
         * Contains user information and token details after successful authentication.
         */
        auth?: AuthInfo;
    }
}

dotenv.config();

const app = express();

// Serve static files from the public directory
app.use(express.static(path.join(process.cwd(), 'public')));

app.use(
    cors({
        origin: true,
        methods: '*',
        allowedHeaders: 'Authorization, Origin, Content-Type, Accept, *',
    })
);

app.options("*", cors());

const provider = new DescopeMcpProvider();

app.use(descopeMcpAuthRouter(provider));

app.use(["/sse", "/message"], descopeMcpBearerAuth());

let servers: McpServer[] = [];
const MAX_CONNECTIONS = 100; // Adjust based on your shared instance limits

app.get("/sse", async (req, res) => {
    if (servers.length >= MAX_CONNECTIONS) {
        res.status(429).send("Too many connections");
        return;
    }

    const transport = new SSEServerTransport("/message", res);
    const { server } = createServer();

    servers.push(server);
    server.server.onclose = () => {
        console.log("SSE connection closed");
        servers = servers.filter((s) => s !== server);
    };

    // Add timeout for inactive connections (30 minutes)
    const timeout = setTimeout(() => {
        server.server.close();
    }, 30 * 60 * 1000);

    server.server.onclose = () => {
        clearTimeout(timeout);
        console.log("SSE connection closed");
        servers = servers.filter((s) => s !== server);
    };

    console.log("Received connection");
    await server.connect(transport);
})

app.post("/message", async (req, res) => {
    const sessionId = req.query.sessionId as string;
    const transport = servers.map(s => s.server.transport as SSEServerTransport).find(t => t.sessionId === sessionId);
    if (!transport) {
        res.status(404).send("Session not found");
        return;
    }
    console.log("Received message");
    await transport.handlePostMessage(req, res);
})

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Weather MCP Server is running on port ${PORT}`);
})