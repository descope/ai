import * as dotenv from "dotenv";
import express, { Request, Response } from "express";
import cors from "cors";
import path from 'path';
import serverless from "serverless-http";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { descopeMcpBearerAuth } from "@descope/mcp-express";
import { createServer } from "./create-server.js";
import DescopeClient from '@descope/node-sdk';
import { decodeJwt } from "jose";

const descopeClient = DescopeClient({
    projectId: String(process.env.DESCOPE_PROJECT_ID),
    managementKey: String(process.env.DESCOPE_MANAGEMENT_KEY),
  });

// Type declarations
declare global {
    namespace Express {
        interface Request {
            auth?: AuthInfo;
        }
    }
}

// Environment setup
dotenv.config();

// Environment validation
const requiredEnvVars = ['STRIPE_SECRET_KEY', 'DESCOPE_PROJECT_ID'];
const missingEnvVars = requiredEnvVars.filter(envVar => !process.env[envVar]);

if (missingEnvVars.length > 0) {
    console.error('Missing required environment variables:', missingEnvVars.join(', '));
    console.error('Please check your .env file and ensure all required variables are set.');
    process.exit(1);
}

// Initialize Express app
const app = express();

// Middleware setup
app.use(express.json());
app.use(express.static(path.join(process.cwd(), 'public')));
app.use(cors({
  origin: true,
  methods: '*',
  allowedHeaders: 'Authorization, Origin, Content-Type, Accept, *',
}));
app.options("*", cors());

// Auth middleware for session validation
app.use(["/mcp"], descopeMcpBearerAuth());

// Initialize transport
const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined, // set to undefined for stateless servers
});

// Create server with error handling
let server: any;
let serverConnected = false;

const getOrCreateServer = async (userEmail?: string) => {
    if (!server) {
        try {
            console.log('Creating MCP server with user email:', userEmail);
            const serverResult = await createServer(userEmail);
            server = serverResult.server;
            console.log('MCP server created successfully with capabilities:', server.capabilities);
        } catch (error) {
            console.error('Failed to create server:', error);
            throw error;
        }
    }
    return server;
};

// Connect server to transport
const connectServer = async (userEmail?: string) => {
    if (!serverConnected) {
        try {
            console.log('Connecting server to transport...');
            const currentServer = await getOrCreateServer(userEmail);
            await currentServer.connect(transport);
            serverConnected = true;
            console.log('Server connected successfully');
        } catch (error) {
            console.error('Failed to connect server:', error);
            throw error;
        }
    }
};

// MCP endpoint
app.post('/mcp', async (req: Request, res: Response) => {
    console.log('Received MCP request:', req.body);
    try {
        // Extract user email from Descope auth
        const decodedJwt = decodeJwt(req.auth.token);
        const userEmailFromJwt = decodedJwt.email || 'Email not found';
        await connectServer(String(userEmailFromJwt));

        console.log("user email: " + userEmailFromJwt);
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

// Method not allowed handlers
const methodNotAllowed = (req: Request, res: Response) => {
    console.log(`Received ${req.method} MCP request`);
    res.status(405).json({
        jsonrpc: "2.0",
        error: {
            code: -32000,
            message: "Method not allowed."
        },
        id: null
    });
};

app.get('/mcp', methodNotAllowed);
app.delete('/mcp', methodNotAllowed);

// Health check endpoint
app.get('/', (req: Request, res: Response) => {
    res.json({ 
        status: 'Stripe MCP Server is running',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    });
});

// OAuth Protected Resource Metadata endpoint
app.get('/.well-known/oauth-protected-resource', (req: Request, res: Response) => {
    const baseUrl = process.env.SERVER_URL || `${req.protocol}://${req.get('host')}`;
    
    const metadata = {
        resource: `${baseUrl}/mcp`,
        authorization_servers: [baseUrl],
        bearer_methods_supported: ["header"],
        resource_documentation: `${baseUrl}/docs`
    };

    res.set({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, MCP-Protocol-Version'
    });

    res.json(metadata);
});

// OPTIONS handler for OAuth Protected Resource Metadata
app.options('/.well-known/oauth-protected-resource', (req: Request, res: Response) => {
    res.set({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, MCP-Protocol-Version'
    });
    res.status(200).send('OK');
});

// OAuth Authorization Server Metadata endpoint
app.get('/.well-known/oauth-authorization-server', (req: Request, res: Response) => {
    const baseUrl = process.env.DESCOPE_BASE_URL || "https://api.descope.com";
    const projectId = process.env.DESCOPE_PROJECT_ID;

    if (!projectId) {
        res.status(500).json({
            error: 'DESCOPE_PROJECT_ID environment variable is not set'
        });
        return;
    }

    const metadata = {
        issuer: `${baseUrl}/v1/apps/${projectId}`,
        jwks_uri: `${baseUrl}/${projectId}/.well-known/jwks.json`,
        authorization_endpoint: `${baseUrl}/oauth2/v1/apps/authorize`,
        response_types_supported: ["code"],
        subject_types_supported: ["public"],
        id_token_signing_alg_values_supported: ["RS256"],
        code_challenge_methods_supported: ["S256"],
        token_endpoint: `${baseUrl}/oauth2/v1/apps/token`,
        userinfo_endpoint: `${baseUrl}/oauth2/v1/apps/userinfo`,
        scopes_supported: ["openid"],
        claims_supported: [
            "iss",
            "aud",
            "iat",
            "exp",
            "sub",
            "name",
            "email",
            "email_verified",
            "phone_number",
            "phone_number_verified",
            "picture",
            "family_name",
            "given_name",
        ],
        revocation_endpoint: `${baseUrl}/oauth2/v1/apps/revoke`,
        registration_endpoint: `${baseUrl}/v1/mgmt/inboundapp/app/${projectId}/register`,
    };

    res.set({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, MCP-Protocol-Version'
    });

    res.json(metadata);
});

// OPTIONS handler for OAuth Authorization Server Metadata
app.options('/.well-known/oauth-authorization-server', (req: Request, res: Response) => {
    res.set({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, MCP-Protocol-Version'
    });
    res.status(200).send('OK');
});

// Start server if not in serverless environment
const PORT = process.env.PORT || 3000;
if (process.env.NODE_ENV !== 'production' && !process.env.LAMBDA_TASK_ROOT) {
    app.listen(PORT, () => {
        console.log(`Stripe MCP Server listening on port ${PORT}`);
        console.log(`Health check: http://localhost:${PORT}/`);
        console.log(`MCP endpoint: http://localhost:${PORT}/mcp`);
    });
}

// Export the serverless handler
export const handler = serverless(app);