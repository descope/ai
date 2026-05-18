import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import * as readline from "readline";
import { authenticateUser, fetchUserEmail } from "./auth.js";
import express from "express";
import { CallToolResultSchema } from "@modelcontextprotocol/sdk/types.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! });
const DESCOPE_PROJECT_ID = process.env.DESCOPE_PROJECT_ID!;
const MCP_SERVER_ID = process.env.MCP_SERVER_ID!;

interface PendingEmail {
  to: string;
  subject: string;
  body: string;
  userId: string;
  userToken: string;
  pendingRef: string;
}

const pendingEmails = new Map<string, PendingEmail>();

let userToken: string;
let userId: string;
let userEmail: string;
let refreshToken: string;

async function main() {
  console.log("\nGmail AI Agent");
  console.log("=".repeat(50));

  const app = express();

  // ── Gmail OAuth connection-complete callback ───────────────────────────────
  // Called after user grants Gmail access via the authorization_url
  app.get("/connection-complete", (req: any, res: any) => {
    const error = req.query.err as string;

    if (error) {
      console.error("\n❌ Gmail OAuth error:", decodeURIComponent(error));
      res.send(`
        <html><body style="font-family:Arial;padding:40px;text-align:center">
          <h1 style="color:red">OAuth Error</h1>
          <p>${decodeURIComponent(error)}</p>
        </body></html>`);
      return;
    }

    console.log("\n✅ Gmail connected — token stored in Descope!");
    res.send(`
      <html><body style="font-family:Arial;padding:40px;text-align:center">
        <h1>Permission Granted!</h1>
        <p>You can close this window and return to the terminal.</p>
      </body></html>`);
  });

  // ── Email approval callback ───────────────────────────────────────────────
  app.get("/approve", async (req: any, res: any) => {
    const token = req.query.t as string;
    const pendingId = req.query.id as string;

    if (!token || !pendingId) {
      res.status(400).send("Missing approval token or ID");
      return;
    }

    const { verifyApproval } = await import("./approval.js");
    const verified = await verifyApproval(token);

    if (!verified) {
      res.status(400).send("Invalid approval token");
      return;
    }

    const emailDetails = pendingEmails.get(pendingId);
    if (!emailDetails) {
      res.status(404).send("Pending email not found");
      return;
    }

    try {
      const { to, subject, body } = emailDetails;

      // Fetch Gmail token via mgmt API
      const tokenResp = await fetch(
        "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${DESCOPE_PROJECT_ID}:${userToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ appId: "gmail", loginId: userId }),
        }
      );

      if (!tokenResp.ok) {
        const err = await tokenResp.text();
        res.status(500).send(`Failed to get Gmail token: ${err}`);
        return;
      }

      const tokenData = await tokenResp.json();
      const gmailToken = tokenData.token?.accessToken ?? tokenData.accessToken;

      const raw = Buffer.from(`To: ${to}\r\nSubject: ${subject}\r\n\r\n${body}`)
        .toString("base64")
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");

      const sendResp = await fetch(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${gmailToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ raw }),
        }
      );

      if (sendResp.ok) {
        console.log(`\n✅ Email sent to ${to}!`);
        pendingEmails.delete(pendingId);
        res.send(`
          <html><body style="font-family:Arial;padding:40px;text-align:center">
            <h1>Email Sent!</h1>
            <p>Your email to ${to} has been sent successfully.</p>
          </body></html>`);
      } else {
        const err = await sendResp.text();
        res.status(500).send(`Failed to send email: ${err}`);
      }
    } catch (err: any) {
      res.status(500).send(`Error: ${err.message}`);
    }
  });

  // ── Descope OAuth callback (step 1 auth) ──────────────────────────────────
  let authResolve: any;
  let authReject: any;

  app.get("/callback", async (req: any, res: any) => {
    const code = req.query.code as string;

    if (!code) {
      res.send("Error: No code received");
      if (authReject) authReject(new Error("No authorization code"));
      return;
    }

    try {
      const tokenResponse = await fetch(
        `https://api.descope.com/oauth2/v1/apps/agentic/${DESCOPE_PROJECT_ID}/${MCP_SERVER_ID}/token`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            grant_type: "authorization_code",
            code,
            redirect_uri: "http://localhost:3000/callback",
            client_id: process.env.DESCOPE_CLIENT_ID!,
            client_secret: process.env.DESCOPE_CLIENT_SECRET!,
          }),
        }
      );

      const tokenData = await tokenResponse.json();
      if (!tokenData.access_token) {
        throw new Error(`No access token: ${JSON.stringify(tokenData)}`);
      }

      const payload = JSON.parse(
        Buffer.from(tokenData.access_token.split(".")[1], "base64").toString()
      );
      const uid = payload.sub ?? "";

      let email = "";
      try {
        email = await fetchUserEmail(uid, tokenData.access_token);
      } catch (e) {
        console.error("Failed to fetch user email:", e);
      }

      res.send(`
        <html><body style="font-family:Arial;padding:40px;text-align:center">
          <h1>Authentication Successful!</h1>
          <p>You can close this window and return to the terminal.</p>
        </body></html>`);

      if (authResolve) {
        authResolve({
          accessToken: tokenData.access_token,
          refreshToken: tokenData.refresh_token,
          userId: uid,
          email,
        });
      }
    } catch (error: any) {
      res.send(`Error: ${error.message}`);
      if (authReject) authReject(error);
    }
  });

  app.listen(3000);
  console.log("Server started on port 3000\n");

  // ── Step 1: Authenticate with Descope ─────────────────────────────────────
  console.log("Step 1: Authenticate with Descope...");
  const auth = await new Promise<{
    accessToken: string;
    refreshToken: string;
    userId: string;
    email: string;
  }>((resolve, reject) => {
    authResolve = resolve;
    authReject = reject;
    authenticateUser();
  });

  userToken = auth.accessToken;
  userId = auth.userId;
  userEmail = auth.email;
  refreshToken = auth.refreshToken;

  console.log("Authenticated!");
  console.log(`Email: ${userEmail}`);

  // ── Step 2: Connect to remote MCP server ──────────────────────────────────
  console.log("\nStep 2: Connecting to remote MCP server...");

  const transport = new StreamableHTTPClientTransport(
    new URL("https://mcp-with-next-js-and-descope-beryl.vercel.app/api/mcp"),
    {
      requestInit: {
        headers: { Authorization: `Bearer ${userToken}` },
      },
    }
  );

  const mcpClient = new Client(
    { name: "cli-agent", version: "1.0.0" },
    { capabilities: {} }
  );

  await mcpClient.connect(transport);
  console.log("Connected to remote MCP server!\n");

  // ── Chat loop ─────────────────────────────────────────────────────────────
  console.log("Chat with your AI agent:");
  console.log("Commands: 'read emails', 'send email to <address>', 'exit'\n");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const prompt = (q: string): Promise<string> =>
    new Promise((resolve) => rl.question(q, resolve));

  while (true) {
    const userInput = await prompt("You: ");

    if (userInput.toLowerCase().trim() === "exit") {
      console.log("\nGoodbye!\n");
      process.exit(0);
    }

    if (!userInput.trim()) continue;

    try {
      const response = await runAgent(userInput, mcpClient);
      console.log(`\nAgent: ${response}\n`);
    } catch (error: any) {
      console.error(`\nError: ${error.message}\n`);
    }
  }
}

// ─── Agent loop ──────────────────────────────────────────────────────────────

async function runAgent(userMessage: string, mcpClient: Client): Promise<string> {
  const messages: Anthropic.MessageParam[] = [
    { role: "user", content: userMessage },
  ];

  const toolsResponse = await mcpClient.listTools().catch((e) => {
    console.error("Error getting tools:", e);
    throw e;
  });

  const mcpTools = toolsResponse.tools ?? [];
  const anthropicTools: Anthropic.Tool[] = mcpTools.map((tool: any) => ({
    name: tool.name,
    description: tool.description,
    input_schema: tool.inputSchema,
  }));

  while (true) {
    const response = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 4096,
      tools: anthropicTools,
      messages,
    });

    messages.push({ role: "assistant", content: response.content });

    const toolUse = response.content.find(
      (b): b is Anthropic.ToolUseBlock => b.type === "tool_use"
    );

    if (!toolUse) {
      const text = response.content.find(
        (b): b is Anthropic.TextBlock => b.type === "text"
      );
      return text?.text ?? "Done.";
    }

    console.log(`\nCalling tool: ${toolUse.name}...`);

    try {
      const toolResult: any = await (mcpClient.request as any)(
        {
          method: "tools/call",
          params: {
            name: toolUse.name,
            arguments: toolUse.input,
            _meta: { userToken, refreshToken, userId, userEmail },
          },
        },
        CallToolResultSchema
      );

      const resultContent = toolResult.content[0].text;

      // ── Approval flow (send email) ─────────────────────────────────────
      if (resultContent.startsWith("NEEDS_APPROVAL:")) {
        const [header, ...emailParts] = resultContent.split("|||");
        const parts = header.replace("NEEDS_APPROVAL:", "").split(":");
        const pendingRef = parts[0];
        const linkId = parts[1];
        const pendingId = parts[2];

        pendingEmails.set(pendingId, {
          to: emailParts[0],
          subject: emailParts[1],
          body: emailParts[2],
          userId,
          userToken,
          pendingRef,
        });

        console.log(`\nApproval required!`);
        console.log(`Check your email (${userEmail}) for the approval link`);
        console.log(`Link ID: ${linkId}\nWaiting for approval...\n`);

        const { waitForApproval } = await import("./approval.js");
        const approved = await waitForApproval(pendingRef);

        messages.push({
          role: "user",
          content: [{
            type: "tool_result",
            tool_use_id: toolUse.id,
            content: approved
              ? "Approval received. Email sent successfully."
              : "Approval timeout or denied.",
            ...(approved ? {} : { is_error: true }),
          }],
        });
        continue;
      }

      // ── Gmail OAuth required (no token yet, or insufficient scope) ─────
      if (resultContent.includes("insufficient_scope")) {
        let authUrl = "";
        try {
          const errorData = JSON.parse(resultContent);
          authUrl = errorData.authorization_url ?? "";
        } catch { /* not JSON */ }

        if (authUrl) {
          console.log(`\n🔐 Gmail permission required. Opening browser...`);
          const { exec } = await import("child_process");
          exec(`open "${authUrl}"`);

          console.log("Please grant permission in your browser.");
          console.log("⏳ Waiting for you to complete the OAuth flow...\n");

          // Give the user time to complete OAuth in browser
          await new Promise((r) => setTimeout(r, 15_000));
          console.log("Retrying...\n");

          messages.push({
            role: "user",
            content: [{
              type: "tool_result",
              tool_use_id: toolUse.id,
              content: "Permission granted. Please retry.",
            }],
          });
          continue;
        }
      }

      // ── Normal result ──────────────────────────────────────────────────
      messages.push({
        role: "user",
        content: [{
          type: "tool_result",
          tool_use_id: toolUse.id,
          content: resultContent,
        }],
      });
    } catch (error: any) {
      console.error("Tool error:", error);
      messages.push({
        role: "user",
        content: [{
          type: "tool_result",
          tool_use_id: toolUse.id,
          content: `Error: ${error.message}`,
          is_error: true,
        }],
      });
    }
  }
}

main().catch(console.error);