import {
  McpServer,
  ToolCallback,
} from "@modelcontextprotocol/sdk/server/mcp.js";
import { ZodRawShape } from "zod";
import { RequestHandlerExtra } from "@modelcontextprotocol/sdk/shared/protocol.js";
import {
  ServerNotification,
  ServerRequest,
} from "@modelcontextprotocol/sdk/types.js";

type ToolFn = (args: {
  args: Record<string, unknown>;
  extra: RequestHandlerExtra<ServerRequest, ServerNotification>;
}) => Promise<Record<string, unknown>>;

type DefineToolWithDescopeParams<Args extends ZodRawShape> = {
  name: string;
  description: string;
  paramsSchema: Args;
  execute: ToolFn;
};

export default function defineToolWithDescope<Args extends ZodRawShape>({
  name,
  description,
  paramsSchema,
  execute,
}: DefineToolWithDescopeParams<Args>) {
  return (server: McpServer) =>
    server.tool(name, description, paramsSchema, (async (args, extra) => {
      const result = await execute({ args, extra });

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }) as ToolCallback<Args>);
}
