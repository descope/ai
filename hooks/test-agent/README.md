# Descope Agent Hooks — Test Agent

Automated tests for the Cursor hook, Claude Code hook, MCP wrapper, and TypeScript library.

## Requirements

- Node.js 18+
- `jq` and `curl` (required by the hooks themselves)

## Usage

From the `hooks` directory:

```bash
node test-agent/test-agent.mjs
```

Or from the test-agent directory:

```bash
node test-agent.mjs
```

### Options

| Option        | Description                                                           |
|---------------|-----------------------------------------------------------------------|
| `--integration` | Run integration tests (requires `descope-auth.config.json` with valid credentials) |
| `--verbose`    | Log detailed output                                                    |

### Environment

| Variable   | Description           |
|------------|-----------------------|
| `VERBOSE=1` | Same as `--verbose`   |

## What It Tests

### Cursor Hook (`cursor/descope-auth.sh`)

- Hook exists and is executable
- Returns `{"permission": "allow"}` for non-matching tools or when no config exists
- Output is valid JSON with a `permission` field
- With matching config: returns allow+headers or deny+reason

### Claude Code Hook (`claude-code/descope-auth-cc.sh`)

- Hook exists and is executable
- Exits 0 for non-MCP tools (tool names not starting with `mcp__`)
- Exits 0 for unknown MCP servers (no config)
- Handles Descope failures gracefully (exit 0 with block reason, or success with cached token)

### MCP Wrapper (`claude-code/descope-mcp-wrapper.sh`)

- Wrapper exists and is executable
- Requires `DESCOPE_SERVER_KEY` environment variable

### TypeScript Library (`typescript/src/descope-auth-hooks.ts`)

- Library file exists
- Exports `clientCredentialsTokenExchange`, `userTokenExchange`, `preToolUseHook`, etc.

### Config

- Validates `descope-auth.config.json` structure when present
- Checks for example configs as fallback

## Integration Tests

To run with real Descope credentials:

1. Copy the example config and fill in your credentials:

   ```bash
   cp hooks/claude-code/descope-auth.config.example.json hooks/claude-code/descope-auth.config.json
   # Edit with your projectId, clientId, clientSecret, etc.
   ```

2. Run with `--integration`:

   ```bash
   node test-agent/test-agent.mjs --integration
   ```

## Adding to package.json

If the hooks repo has a root `package.json`, add:

```json
{
  "scripts": {
    "test:hooks": "node test-agent/test-agent.mjs"
  }
}
```
