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

// declare module "express-serve-static-core" {
//     interface Request {
//         /**
//          * Information about the validated access token, if the `descopeMcpBearerAuth` middleware was used.
//          * Contains user information and token details after successful authentication.
//          */
//         auth?: AuthInfo;
//     }
// }

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
    console.log("mcp request", req.body);
    // Disable session tracking by setting sessionIdGenerator to undefined  
    const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined
    });
    console.log("transport", transport);

    // Connect to server and handle the request
    await server.connect(transport);
    console.log("transport connected to server");
    await transport.handleRequest(req, res);
    console.log("transport handled request");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Weather MCP Server is running on port ${PORT}`);
})