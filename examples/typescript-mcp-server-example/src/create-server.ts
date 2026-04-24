import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

export const createServer = () => {
  const server = new McpServer({
    name: "vanilla-typescript-mcp-server",
    version: "1.0.0",
  });

  server.tool(
    "echo",
    "Echoes the message back to the caller",
    {
      message: z.string().describe("Message to echo"),
    },
    async ({ message }) => {
      return {
        content: [{ type: "text", text: `Echo: ${message}` }],
      };
    },
  );

  return { server };
};
