export async function GET(req: Request) {
  const origin = new URL(req.url).origin;

  return Response.json(
    {
      resource: `${origin}`,
      authorization_servers: [`${origin}`],
      // scopes_supported: [],
      resource_name: "Descope MCP Server",
      // resource_documentation: `${origin}/docs`
    },
    {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, mcp-protocol-version",
      },
    }
  );
}

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, mcp-protocol-version",
      "Content-Type": "application/json",
    },
  });
}
