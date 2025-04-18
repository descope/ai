import dotenv from "dotenv";
import express from "express";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { createServer } from "./create-server.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { descopeMcpAuthRouter, descopeMcpBearerAuth, DescopeMcpProvider, DescopeMcpProviderOptions } from "@descope/mcp-express";
import cors from "cors";
import path from 'path';
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
declare global {
    namespace Express {
        interface Request {
            auth?: AuthInfo;
        }
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

app.use(descopeMcpAuthRouter());

app.use(["/mcp"], descopeMcpBearerAuth());

const { server } = createServer();

app.all('/mcp', async (req, res) => {
    // Disable session tracking by setting sessionIdGenerator to undefined  
    const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined
    });

    // Connect to server and handle the request
    await server.connect(transport);
    await transport.handleRequest(req, res);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Weather MCP Server is running on port ${PORT}`);
})