import dotenv from "dotenv";
import express, { Request, Response } from "express";
import cors from "cors";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";
import { descopeMcpAuthRouter, descopeMcpBearerAuth } from "@descope/mcp-express";
import { createServer } from "./create-server.js";

declare global {
  namespace Express {
    interface Request {
      auth?: AuthInfo;
    }
  }
}

dotenv.config();

const app = express();
const port = Number(process.env.PORT || 3000);
const serverUrl = process.env.SERVER_URL || `http://localhost:${port}`;
const descopeMcpServerIssuer = process.env.DESCOPE_MCP_SERVER_ISSUER;

if (!descopeMcpServerIssuer) {
  throw new Error("Missing required environment variable: DESCOPE_MCP_SERVER_ISSUER");
}

app.use(express.json());
app.use(
  cors({
    origin: true,
    methods: "*",
    allowedHeaders: "Authorization, Origin, Content-Type, Accept, *",
  }),
);
app.options("*", cors());

app.get("/.well-known/oauth-protected-resource", (_req: Request, res: Response) => {
  res.json({
    resource: `${serverUrl}/mcp`,
    authorization_servers: [descopeMcpServerIssuer],
  });
});

app.use(descopeMcpAuthRouter());
app.use(["/mcp"], descopeMcpBearerAuth());

const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
});

app.post("/mcp", async (req: Request, res: Response) => {
  try {
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error("Error handling MCP request:", error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: "2.0",
        error: {
          code: -32603,
          message: "Internal server error",
        },
        id: null,
      });
    }
  }
});

const methodNotAllowed = (_req: Request, res: Response) => {
  res.status(405).json({
    jsonrpc: "2.0",
    error: {
      code: -32000,
      message: "Method not allowed.",
    },
    id: null,
  });
};

app.get("/mcp", methodNotAllowed);
app.delete("/mcp", methodNotAllowed);

const { server } = createServer();

const start = async () => {
  await server.connect(transport);
  app.listen(port, () => {
    console.log(`MCP server listening on port ${port}`);
  });
};

start().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});
