![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

# Descope AI

This repository contains various packages and demo apps related consuming Descope's AI offerings. It is a monorepo powered by Nx and Changesets.

## Packages

- [`mcp-express`](./packages/mcp-express/README.md): A TypeScript-based Express Library that enables leveraging Descope Inbound Apps to add auth to Remote MCP Servers.

## Examples

- [`remote-mcp-server-hono-cloudflare`](./examples/remote-mcp-server-hono-cloudflare/README.md): A demo app that shows how to add auth to a Remote MCP Server using Hono and Descope and deploying to Cloudflare Workers.

- [`remote-mcp-server-express-cloudflare`](./examples/remote-mcp-server-express-cloudflare/README.md): An example of a Remote MCP Server using Express and Descope's MCP Auth SDK and deploying to Fly.io.

## Contributing

This monorepo is built and managed using [NX](https://nx.dev/). In order to use the repo locally.

1. Fork / Clone this repository
2. Run `pnpm i`
3. Use the available scripts in the root level `package.json`. e.g. `pnpm run <test/lint/build>`

You can find README and examples in each package.

## Contact Us

If you need help you can email [Descope Support](mailto:support@descope.com)

## License

This project is licensed under the [MIT License](./LICENSE).