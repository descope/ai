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

// app.use(descopeMcpAuthRouter());

// app.use(["/mcp"], descopeMcpBearerAuth());


const transport: StreamableHTTPServerTransport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined, // set to undefined for stateless servers
});

const setupServer = async () => {
    const { server } = createServer();
    await server.connect(transport);
};


app.post('/mcp', async (req, res) => {
    console.log('Received MCP request:', req.body);
    try {
        await transport.handleRequest(req, res, req.body);
    } catch (error) {
        console.error('Error handling MCP request:', error);
        if (!res.headersSent) {
            res.status(500).json({
                jsonrpc: '2.0',
                error: {
                    code: -32603,
                    message: 'Internal server error',
                },
                id: null,
            });
        }
    }
});

app.get('/mcp', async (req, res) => {
    console.log('Received GET MCP request');
    res.writeHead(405).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
            code: -32000,
            message: "Method not allowed."
        },
        id: null
    }));
});

app.delete('/mcp', async (req, res) => {
    console.log('Received DELETE MCP request');
    res.writeHead(405).end(JSON.stringify({
        jsonrpc: "2.0",
        error: {
            code: -32000,
            message: "Method not allowed."
        },
        id: null
    }));
});

const PORT = process.env.PORT || 3000;
setupServer().then(() => {
    app.listen(PORT, () => {
        console.log(`MCP Streamable HTTP Server listening on port ${PORT}`);
    });
}).catch(error => {
    console.error('Failed to set up the server:', error);
    process.exit(1);
});