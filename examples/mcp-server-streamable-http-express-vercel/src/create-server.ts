import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";


export const createServer = () => {
    // Create server instance
    const server = new McpServer({
        name: "demo",
        version: "1.0.0",
    });

    server.tool("add", { a: z.number(), b: z.number() }, async ({ a, b }) => ({
        content: [{ type: "text", text: String(a + b) }],
    }));

    return { server };
}
