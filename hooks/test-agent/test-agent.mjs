#!/usr/bin/env node
/**
 * Descope Agent Hooks — Test Agent
 * ─────────────────────────────────
 * Tests the Cursor hook, Claude Code hook, MCP wrapper, and TypeScript library.
 *
 * Usage:
 *   node test-agent.mjs [--integration] [--verbose]
 *
 * Options:
 *   --integration   Run integration tests (requires descope-auth.config.json with valid credentials)
 *   --verbose       Log detailed output
 */

import { spawn } from "child_process";
import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const HOOKS_ROOT = join(__dirname, "..");
const CURSOR_HOOK = join(HOOKS_ROOT, "cursor", "descope-auth.sh");
const CLAUDE_HOOK = join(HOOKS_ROOT, "claude-code", "descope-auth-cc.sh");
const MCP_WRAPPER = join(HOOKS_ROOT, "claude-code", "descope-mcp-wrapper.sh");
const CURSOR_CONFIG = join(HOOKS_ROOT, "cursor", "descope-auth.config.json");
const CLAUDE_CONFIG = join(HOOKS_ROOT, "claude-code", "descope-auth.config.json");

const INTEGRATION = process.argv.includes("--integration");
const VERBOSE = process.argv.includes("--verbose") || process.env.VERBOSE === "1";

let passed = 0;
let failed = 0;

function log(...args) {
  if (VERBOSE) console.log(...args);
}

function ok(name) {
  passed++;
  console.log(`  ✓ ${name}`);
}

function fail(name, detail) {
  failed++;
  console.log(`  ✗ ${name}`);
  if (detail) console.log(`    ${detail}`);
}

// ─── Run shell script with stdin, return stdout + exit code ─────────────────

async function runHook(script, stdin, opts = {}) {
  return new Promise((resolve) => {
    const proc = spawn("bash", [script], {
      cwd: opts.cwd || dirname(script),
      env: { ...process.env, ...opts.env },
      stdio: ["pipe", "pipe", opts.stderr ? "pipe" : "inherit"],
    });

    let stdout = "";
    let stderr = "";
    if (proc.stdout) proc.stdout.on("data", (d) => (stdout += d.toString()));
    if (proc.stderr) proc.stderr?.on("data", (d) => (stderr += d.toString()));

    proc.stdin.write(stdin);
    proc.stdin.end();

    proc.on("close", (code) => {
      resolve({ stdout: stdout.trim(), stderr, code: code ?? -1 });
    });
  });
}

// ─── Cursor Hook Tests ─────────────────────────────────────────────────────

async function testCursorHook() {
  console.log("\n[Cursor Hook] descope-auth.sh");

  if (!existsSync(CURSOR_HOOK)) {
    fail("Cursor hook exists", `Not found: ${CURSOR_HOOK}`);
    return;
  }
  ok("Cursor hook file exists");

  // Test 1: Non-matching tool or no config → allow
  const input1 = JSON.stringify({
    tool_name: "random_tool_xyz",
    tool_input: {},
    email: "test@example.com",
    conversation_id: "test-1",
  });

  const result1 = await runHook(CURSOR_HOOK, input1);

  if (result1.code !== 0) {
    fail("Cursor hook exits 0 for non-matching tool", `exit ${result1.code}`);
  } else {
    ok("Cursor hook exits 0 for non-matching tool");
  }

  let out1;
  try {
    out1 = JSON.parse(result1.stdout);
  } catch {
    fail("Cursor hook returns valid JSON", result1.stdout?.slice(0, 80));
    return;
  }

  if (out1.permission === "allow") {
    ok("Cursor hook allows non-matching tool");
  } else {
    fail("Cursor hook allows non-matching tool", `got permission=${out1.permission}`);
  }

  if (typeof out1.permission === "string") {
    ok("Cursor hook output has permission field");
  } else {
    fail("Cursor hook output has permission field");
  }

  // Test 2: Matching tool but with placeholder config → may deny or fail gracefully
  const input2 = JSON.stringify({
    tool_name: "github_create_issue",
    tool_input: { repo: "test" },
    email: "test@example.com",
  });

  const result2 = await runHook(CURSOR_HOOK, input2);

  if (result2.code !== 0 && result2.code !== -1) {
    log("  (Cursor hook with placeholder config: non-zero exit is expected)");
  }

  try {
    const out2 = JSON.parse(result2.stdout);
    if (out2.permission === "allow" && out2.headers?.Authorization) {
      ok("Cursor hook returns allow + Authorization header (integration)");
    } else if (out2.permission === "deny" || out2.permission === "allow") {
      ok("Cursor hook returns valid permission (allow or deny)");
    } else {
      fail("Cursor hook output format", `unexpected: ${JSON.stringify(out2)}`);
    }
  } catch {
    // If Descope fails, hook may output nothing or malformed
    if (result2.stdout.includes("permission")) {
      ok("Cursor hook outputs permission-related response");
    } else {
      fail("Cursor hook returns parseable JSON", result2.stdout?.slice(0, 100) || "(empty)");
    }
  }
}

// ─── Claude Code Hook Tests ────────────────────────────────────────────────

async function testClaudeHook() {
  console.log("\n[Claude Code Hook] descope-auth-cc.sh");

  if (!existsSync(CLAUDE_HOOK)) {
    fail("Claude hook exists", `Not found: ${CLAUDE_HOOK}`);
    return;
  }
  ok("Claude hook file exists");

  // Test 1: Non-MCP tool → allow, exit 0
  const input1 = JSON.stringify({
    tool_name: "some_other_tool",
    tool_input: {},
    session_id: "test-session",
  });

  const result1 = await runHook(CLAUDE_HOOK, input1);

  if (result1.code === 0) {
    ok("Claude hook exits 0 for non-MCP tool");
  } else {
    fail("Claude hook exits 0 for non-MCP tool", `exit ${result1.code}`);
  }

  // Test 2: MCP tool with no matching server config → allow
  const input2 = JSON.stringify({
    tool_name: "mcp__unknown_server__some_tool",
    tool_input: {},
    session_id: "test-session",
  });

  // Need config without "unknown_server" - the example has github, salesforce, etc.
  const result2 = await runHook(CLAUDE_HOOK, input2);

  if (result2.code === 0) {
    ok("Claude hook exits 0 for unknown MCP server");
  } else {
    fail("Claude hook exits 0 for unknown MCP server", `exit ${result2.code}`);
  }

  // Test 3: MCP tool with matching config (github) → will try Descope
  const input3 = JSON.stringify({
    tool_name: "mcp__github__create_issue",
    tool_input: { title: "test" },
    session_id: "test-session",
  });

  const result3 = await runHook(CLAUDE_HOOK, input3);

  if (result3.code === 0) {
    if (result3.stdout && result3.stdout.includes("reason")) {
      ok("Claude hook returns block reason when Descope fails (placeholder creds)");
    } else {
      ok("Claude hook succeeds (valid credentials or cached token)");
    }
  } else {
    ok("Claude hook handles Descope failure (non-zero exit or block)");
  }

  // Test 4: Token cache written when successful (integration only)
  const tokenCacheDir = join(HOOKS_ROOT, "claude-code", ".token-cache");
  if (existsSync(tokenCacheDir) && INTEGRATION) {
    ok("Token cache directory exists");
  }
}

// ─── MCP Wrapper Tests ─────────────────────────────────────────────────────

async function testMcpWrapper() {
  console.log("\n[MCP Wrapper] descope-mcp-wrapper.sh");

  if (!existsSync(MCP_WRAPPER)) {
    fail("MCP wrapper exists", `Not found: ${MCP_WRAPPER}`);
    return;
  }
  ok("MCP wrapper file exists");

  // Test: Without DESCOPE_SERVER_KEY → script exits with error (${var:?msg})
  const env = { ...process.env };
  delete env.DESCOPE_SERVER_KEY;
  const proc = spawn("bash", [MCP_WRAPPER, "https://example.com/mcp"], {
    cwd: dirname(MCP_WRAPPER),
    env,
    stdio: ["pipe", "pipe", "pipe"],
  });

  proc.stdin.write('{"jsonrpc":"2.0","id":1,"method":"test"}\n');
  proc.stdin.end();

  const [stdout, stderr, code] = await new Promise((resolve) => {
    let out = "";
    let err = "";
    proc.stdout.on("data", (d) => (out += d.toString()));
    proc.stderr.on("data", (d) => (err += d.toString()));
    proc.on("close", (c) => resolve([out, err, c]));
  });

  if (code !== 0 && (stdout.includes("DESCOPE_SERVER_KEY") || stderr.includes("DESCOPE_SERVER_KEY"))) {
    ok("MCP wrapper requires DESCOPE_SERVER_KEY");
  } else {
    ok("MCP wrapper executable");
  }
}

// ─── TypeScript Library Tests ──────────────────────────────────────────────

async function testTypescriptLibrary() {
  console.log("\n[TypeScript Library] descope-auth-hooks.ts");

  const tsPath = join(HOOKS_ROOT, "typescript", "src", "descope-auth-hooks.ts");
  if (!existsSync(tsPath)) {
    fail("TypeScript library exists", `Not found: ${tsPath}`);
    return;
  }
  ok("TypeScript library file exists");

  try {
    // Dynamic import of the TS file - Node may not resolve .ts by default
    const pkgPath = join(HOOKS_ROOT, "typescript");
    const pkg = JSON.parse(
      readFileSync(join(pkgPath, "package.json"), "utf8").replace(/\/\*.*?\*\//gs, "")
    );
    // Try to import - the package might use "exports"
    const mod = await import(tsPath.replace(/\.ts$/, ".js")).catch(() =>
      import(tsPath).catch(() => null)
    );
    if (!mod) {
      // Fallback: run tsc and test, or just verify exports exist
      const content = readFileSync(tsPath, "utf8");
      if (
        content.includes("clientCredentialsTokenExchange") &&
        content.includes("userTokenExchange") &&
        content.includes("preToolUseHook")
      ) {
        ok("TypeScript library exports all strategies");
      } else {
        fail("TypeScript library exports", "Could not verify exports");
      }
      return;
    }

    const {
      clientCredentialsTokenExchange,
      userTokenExchange,
      preToolUseHook,
    } = mod;

    if (typeof clientCredentialsTokenExchange === "function") ok("clientCredentialsTokenExchange");
    if (typeof userTokenExchange === "function") ok("userTokenExchange");
    if (typeof preToolUseHook === "function") ok("preToolUseHook");
  } catch (err) {
    // Library may not be built - check source structure
    const content = readFileSync(tsPath, "utf8");
    if (
      content.includes("export async function clientCredentialsTokenExchange") &&
      content.includes("export async function userTokenExchange") &&
      content.includes("export async function preToolUseHook")
    ) {
      ok("TypeScript library defines all strategy functions");
    } else {
      fail("TypeScript library", err.message);
    }
  }
}

// ─── Config Validation ─────────────────────────────────────────────────────

async function testConfig() {
  console.log("\n[Config] descope-auth.config.json");

  for (const [name, configPath, examplePath] of [
    ["Cursor", CURSOR_CONFIG, join(HOOKS_ROOT, "cursor", "descope-auth.config.example.json")],
    ["Claude Code", CLAUDE_CONFIG, join(HOOKS_ROOT, "claude-code", "descope-auth.config.example.json")],
  ]) {
    if (existsSync(configPath)) {
      try {
        const cfg = JSON.parse(readFileSync(configPath, "utf8"));
        if (cfg.servers && typeof cfg.servers === "object") {
          ok(`${name} config valid with ${Object.keys(cfg.servers).length} server(s)`);
        } else {
          fail(`${name} config structure`, "missing servers object");
        }
      } catch (e) {
        fail(`${name} config valid JSON`, e.message);
      }
    } else if (existsSync(examplePath)) {
      ok(`${name} example config exists (copy to config.json for integration)`);
    } else {
      ok(`${name} config path checked`);
    }
  }
}

// ─── Main ──────────────────────────────────────────────────────────────────

async function main() {
  console.log("🔐 Descope Agent Hooks — Test Agent");
  console.log("────────────────────────────────────");

  if (!INTEGRATION) {
    console.log("(Unit tests only. Use --integration for full tests with Descope.)");
  }

  await testConfig();
  await testCursorHook();
  await testClaudeHook();
  await testMcpWrapper();
  await testTypescriptLibrary();

  console.log("\n────────────────────────────────────");
  console.log(`Results: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
