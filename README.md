![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

# Descope AI

This repository contains various packages and demo apps related consuming Descope's AI offerings.

## Packages

- [`mcp-express`](https://github.com/descope/mcp-express): A TypeScript-based Express Library that enables leveraging Descope [Inbound Apps](https://docs.descope.com/inbound-apps) to add auth to Remote MCP Servers.

## Examples

- [`remote-mcp-server-hono-cloudflare`](./examples/remote-mcp-server-hono-cloudflare/README.md): A demo app that shows how to add auth to a Remote MCP Server using Hono and Descope and deploying to Cloudflare Workers.

- [`remote-mcp-server-express-fly`](./examples/remote-mcp-server-express-fly/README.md): An example of a Remote MCP Server using Express and Descope's MCP Auth SDK and deploying to Fly.io.

- [`notion-remote-mcp-server`](./examples/notion-remote-mcp-server/README.md): A demo app that shows how to add auth to a Remote MCP Server that integrates with Notion.

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
