import dotenv from "dotenv";
import express, { Request, Response } from "express";
import cors from "cors";
import path from 'path';
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { descopeMcpAuthRouter, DescopeMcpProvider } from "@descope/mcp-express";
import serverless from "serverless-http";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { createWeatherServer } from "./tools";

declare global {
    namespace Express {
        interface Request {
            auth?: AuthInfo;
        }
    }
}

dotenv.config();
const PORT = process.env.PORT || 3000;

const app = express();

// Middleware setup
app.use(express.json());
app.use(express.static(path.join(process.cwd(), "public")));
app.use(
  cors({
    origin: true,
    methods: "*",
    allowedHeaders: "Authorization, Origin, Content-Type, Accept, *",
  })
);
app.options("*", cors());

// Initialize Descope MCP Provider
const provider = new DescopeMcpProvider({
  authorizationServerOptions: {
    isDisabled: false,
    enableDynamicClientRegistration: true,
  },
});

// Initialize transport
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined, // set to undefined for stateless servers
});

// Initialize weather server
let weatherServer: ReturnType<typeof createWeatherServer> | null = null;
let serverConnected = false;

const initializeServer = async () => {
  if (!weatherServer) {
    weatherServer = createWeatherServer();
  }
  
  if (!serverConnected) {
    try {
      await weatherServer.server.connect(transport);
      serverConnected = true;
      console.log("Weather server connected successfully");
    } catch (error) {
      console.error("Failed to connect weather server:", error);
      throw error;
    }
  }
};

// MCP endpoint
app.post('/mcp', async (req: Request, res: Response) => {
  console.log('Received MCP request:', req.body);
  try {
    const authToken = req.headers?.authorization;
    const token = authToken?.split(" ")[1];

    // Require authentication for all requests, including initialize
    if (!token) {
      console.log("No authentication token provided");
      res.status(401).json({
        jsonrpc: "2.0",
        error: {
          code: -32001,
          message: "Authentication required",
        },
        id: req.body?.id || null,
      });
      res.set({
        'WWW-Authenticate': `Bearer error="invalid_token", error_description="Missing Authorization header", resource_metadata="${process.env.SERVER_URL}/.well-known/oauth-protected-resource"`
      });
      return;
    }

    // Initialize and connect the weather server
    await initializeServer();
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
app.get("/", (req: Request, res: Response) => {
  res.json({ status: "MCP Server is running" });
});

// OAuth Protected Resource Metadata endpoint
app.get(
  "/.well-known/oauth-protected-resource",
  (req: Request, res: Response) => {
    const baseUrl =
      process.env.SERVER_URL || `${req.protocol}://${req.get("host")}`;

    const metadata = {
      resource: `${baseUrl}/mcp`,
      authorization_servers: [baseUrl],
      bearer_methods_supported: ["header"],
      resource_documentation: `${baseUrl}/docs`,
    };

    res.set({
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers":
        "Content-Type, Authorization, MCP-Protocol-Version",
    });

    res.json(metadata);
  }
);

// OPTIONS handler for OAuth Protected Resource Metadata
app.options(
  "/.well-known/oauth-protected-resource",
  (req: Request, res: Response) => {
    res.set({
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers":
        "Content-Type, Authorization, MCP-Protocol-Version",
    });
    res.status(200).send("OK");
  }
);

// OAuth Authorization Server Metadata endpoint
app.get(
  "/.well-known/oauth-authorization-server",
  (req: Request, res: Response) => {
    const baseUrl = process.env.DESCOPE_BASE_URL || "https://api.descope.com";
    const projectId = process.env.DESCOPE_PROJECT_ID;

    const redirectUrl = `${baseUrl}/v1/apps/${projectId}/.well-known/openid-configuration`;

    res.redirect(302, redirectUrl);
  }
);

// OPTIONS handler for OAuth Authorization Server Metadata
app.options(
  "/.well-known/oauth-authorization-server",
  (req: Request, res: Response) => {
    res.set({
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers":
        "Content-Type, Authorization, MCP-Protocol-Version",
    });
    res.status(200).send("OK");
  }
);

// Descope MCP Auth router (must be added after other routes)
app.use(descopeMcpAuthRouter(undefined, provider));

// Start server only in development mode
if (process.env.NODE_ENV !== 'production' && process.env.AWS_LAMBDA_FUNCTION_NAME === undefined) {
  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
}

// Export the serverless handler
export const handler = serverless(app);
