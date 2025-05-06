import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { AuthInfo } from "@modelcontextprotocol/sdk/server/auth/types.js";

export interface McpContext {
    auth?: AuthInfo;
    [key: string]: any;
}

export class MCPWrapper {
    private server: McpServer;
    private context: McpContext = {};

    constructor(server: McpServer) {
        this.server = server;
    }

    setContext(context: Partial<McpContext>) {
        this.context = { ...this.context, ...context };
    }

    getContext(): McpContext {
        return this.context;
    }

    tool(
        name: string,
        description: string,
        parameters: any,
        handler: (params: any) => Promise<any>
    ) {
        // Wrap the handler to include context
        const wrappedHandler = async (params: any) => {
            // Pass both params and context to the handler
            return handler({ ...params, context: this.context });
        };

        return this.server.tool(name, description, parameters, wrappedHandler);
    }

    // Forward other McpServer methods
    connect(transport: any) {
        return this.server.connect(transport);
    }

    close() {
        return this.server.close();
    }
} 