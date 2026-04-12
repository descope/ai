![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

# Descope AI

This repository contains various packages and demo apps related consuming Descope's AI offerings.

## Packages

- [`mcp-express`](https://github.com/descope/mcp-express): A TypeScript-based Express Library that enables leveraging Descope [Inbound Apps](https://docs.descope.com/inbound-apps) to add auth to Remote MCP Servers.

## Rules for AI IDEs

The `/rules` folder contains comprehensive documentation files (`.mdc`) for various Descope SDKs. These files are organized into the following categories:

- `backend-sdks/`: Documentation for backend SDKs (Node.js, Python, Go)
- `client-sdks/`: Documentation for client SDKs
- `mcp/`: Documentation for MCP (Model Context Protocol)

These documentation files are in Markdown format and can be viewed in any Markdown-compatible editor or viewer. These can be easily imported into Cursor or Windsurf projects, to enhance the developer experience and AI response accuracy.

## Examples

- [`remote-mcp-server-hono-cloudflare`](./examples/remote-mcp-server-hono-cloudflare/README.md): A demo app that shows how to add auth to a Remote MCP Server using Hono and Descope and deploying to Cloudflare Workers.

- [`remote-mcp-server-express-fly`](./examples/remote-mcp-server-express-fly/README.md): An example of a Remote MCP Server using Express and Descope's MCP Auth SDK and deploying to Fly.io.

- [`mcp-server-cloudrun`](./examples/mcp-server-cloudrun/README.md): An example of a remote MCP server with authentication using Descope's MCP Auth SDK deployed to Google Cloud Run.

## Contributing

In order to use the repo locally:

1. Fork / Clone this repository
2. Navigate to the pertinent example directory
3. Run `pnpm i`
4. Use the available scripts in the root level `package.json`. e.g. `pnpm run <test/lint/build>`

You can find README and examples in each package.

## Contact Us

If you need help you can email [Descope Support](mailto:support@descope.com)

## License

This project is licensed under the [MIT License](./LICENSE).
