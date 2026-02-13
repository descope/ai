import Anthropic from "@anthropic-ai/sdk";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import * as readline from "readline";
import { authenticateUser, fetchUserEmail } from "./auth.js";
import express from "express";
import {
  CallToolResultSchema,
} from "@modelcontextprotocol/sdk/types.js";

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

async function main() {
  console.log("\nGmail AI Agent");
  console.log("=".repeat(50));

  const app = express();
  
  app.get("/connection-complete", (req: any, res: any) => {
    const error = req.query.err as string;

    if (error) {
      console.error("\n❌ OAuth ERROR from Descope:");
      console.error(`Error code: ${error}`);
      console.error(`Full URL: ${req.url}`);

      res.send(`
        <html>
          <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h1 style="color: red;">OAuth Error</h1>
            <p>Error: ${decodeURIComponent(error)}</p>
            <p>Please check the terminal for details.</p>
          </body>
        </html>
      `);
      return;
    }

    console.error("\n✅ OAuth completed successfully");
    res.send(`
      <html>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
          <h1>Permission Granted!</h1>
          <p>You can close this window and return to the agent.</p>
        </body>
      </html>
    `);
  });

  app.get("/approve", async (req: any, res: any) => {
    const token = req.query.t as string;
    const pendingId = req.query.id as string;
    
    if (!token || !pendingId) {
      res.status(400).send("Missing approval token or ID");
      return;
    }

    const { verifyApproval } = await import("./approval.js");
    const verified = await verifyApproval(token);

    if (verified) {
      const emailDetails = pendingEmails.get(pendingId);
      
      if (!emailDetails) {
        console.error("Pending email not found:", pendingId);
        res.status(404).send("Pending email not found");
        return;
      }

      try {
        const { to, subject, body, userId: uid, userToken: uToken } = emailDetails;
        
        console.log(`Sending email to ${to}...`);
        const tokenResp = await fetch(
          "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest",
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${process.env.DESCOPE_PROJECT_ID}:${uToken}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ appId: "gmail", loginId: uid }),
          }
        );
        
        if (!tokenResp.ok) {
          const errorText = await tokenResp.text();
          console.error("Failed to get Gmail token:", errorText);
          res.status(500).send(`Failed to get Gmail token: ${errorText}`);
          return;
        }
        
        const tokenData = await tokenResp.json();
        const gmailToken = tokenData.token.accessToken;
        
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
          console.log(`Email sent to ${to}!`);
          pendingEmails.delete(pendingId);
          res.send(`
            <html>
              <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h1>Email Approved and Sent!</h1>
                <p>Your email to ${to} has been sent successfully.</p>
              </body>
            </html>
          `);
        } else {
          const errorText = await sendResp.text();
          
          try {
            const errorData = JSON.parse(errorText);
            
            if (errorData.error?.code === 403 && 
                errorData.error?.details?.some((d: any) => d.reason === "ACCESS_TOKEN_SCOPE_INSUFFICIENT")) {
              
              console.error("Insufficient scopes, requesting additional permission...");
              
              const connectResp = await fetch(
                "https://api.descope.com/v1/mgmt/outbound/app/connect",
                {
                  method: "POST",
                  headers: {
                    Authorization: `Bearer ${process.env.DESCOPE_PROJECT_ID}:${uToken}`,
                    "Content-Type": "application/json",
                  },
                  body: JSON.stringify({
                    appId: "gmail",
                    options: {
                      redirectUrl: "http://localhost:3000/connection-complete",
                      scopes: ["https://www.googleapis.com/auth/gmail.send"],
                    },
                  }),
                }
              );

              const connectData = await connectResp.json();

              if (!connectData.url) {
                console.error("No URL in connect response");
                res.status(500).send(`Failed to get connection URL: ${JSON.stringify(connectData)}`);
                return;
              }

              const { exec } = await import("child_process");

              res.send(`
                <html>
                  <body style="font-family: Arial; padding: 40px; text-align: center;">
                    <h1>Additional Permission Required</h1>
                    <p>Gmail send permission is needed.</p>
                    <p><a href="${connectData.url}" target="_blank">Click here to grant permission</a></p>
                    <p>After granting permission, approve the email again.</p>
                  </body>
                </html>
              `);

              exec(`open "${connectData.url}"`);
              return;
            }
          } catch (parseError) {
            console.error("Could not parse error response");
          }
          
          console.error(`Gmail API error:`, errorText);
          res.status(500).send(`Failed to send email: ${errorText}`);
        }
      } catch (error: any) {
        console.error(`Exception:`, error);
        res.status(500).send(`Error: ${error.message}`);
      }
    } else {
      res.status(400).send("Invalid approval token");
    }
  });

  const server = app.listen(3000);
  console.log("Server started on port 3000\n");

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
            code: code,
            redirect_uri: "http://localhost:3000/callback",
            client_id: "UDJ0N0NvdjFJTERhYkN1QnJhRmhWbEZzUmwyUDpUUEEzOGZiQXNJVDdrMW5jODRTdkViMnFPaXluNGc=",
            client_secret: process.env.DESCOPE_CLIENT_SECRET!,
          }),
        }
      );

      const tokenData = await tokenResponse.json();

      if (!tokenData.access_token) {
        throw new Error(`No access token: ${JSON.stringify(tokenData)}`);
      }

      const tokenParts = tokenData.access_token.split('.');
      const payload = JSON.parse(Buffer.from(tokenParts[1], 'base64').toString());
      const userId = payload.sub || "";

      // Fetch email from Gmail profile
      let email = "";
      try {
        email = await fetchUserEmail(userId, tokenData.access_token);
      } catch (e) {
        console.error("Failed to fetch user email:", e);
      }

      res.send(`
        <html>
          <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h1>Authentication Successful!</h1>
            <p>You can close this window and return to the terminal.</p>
          </body>
        </html>
      `);

      if (authResolve) {
        authResolve({ 
          accessToken: tokenData.access_token, 
          userId,
          email
        });
      }
    } catch (error: any) {
      res.send(`Error: ${error.message}`);
      if (authReject) authReject(error);
    }
  });

  console.log("Step 1: Authenticate with Descope...");
  const auth = await new Promise<{accessToken: string, userId: string, email: string}>((resolve, reject) => {
    authResolve = resolve;
    authReject = reject;
    authenticateUser();
  });
  userToken = auth.accessToken;
  userId = auth.userId;
  userEmail = auth.email;
  console.log("Authenticated!");
  console.log(`Email: ${userEmail}`);

  console.log("\nStep 2: Starting MCP server...");
  const transport = new StdioClientTransport({
    command: "npx",
    args: ["tsx", "src/mcp-stdio.ts"],
  });

  const mcpClient = new Client(
    { name: "cli-agent", version: "1.0.0" },
    { capabilities: {} }
  );

  await mcpClient.connect(transport);
  console.log("MCP server connected!");

  console.log("\nChat with your AI agent:");
  console.log("Commands: 'read emails', 'send email to <address>', 'exit'\n");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const prompt = (question: string): Promise<string> =>
    new Promise((resolve) => rl.question(question, resolve));

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

async function runAgent(userMessage: string, mcpClient: Client): Promise<string> {
  const messages: Anthropic.MessageParam[] = [
    { role: "user", content: userMessage },
  ];

  let toolsResponse;
  try {
    toolsResponse = await mcpClient.listTools();
  } catch (error) {
    console.error("Error getting tools:", error);
    throw error;
  }

  const mcpTools = toolsResponse.tools || [];

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
      (block): block is Anthropic.ToolUseBlock => block.type === "tool_use"
    );

    if (!toolUse) {
      const textBlock = response.content.find(
        (block): block is Anthropic.TextBlock => block.type === "text"
      );
      return textBlock?.text || "Done.";
    }

    console.log(`\nCalling tool: ${toolUse.name}...`);

    try {
      const toolResult: any = await (mcpClient.request as any)({
        method: "tools/call",
        params: {
          name: toolUse.name,
          arguments: toolUse.input,
          _meta: { userToken, userId, userEmail },
        },
      }, CallToolResultSchema);

      const resultContent = toolResult.content[0].text;

      if (resultContent.startsWith("NEEDS_APPROVAL:")) {
        const [header, ...emailParts] = resultContent.split("|||");
        const parts = header.replace("NEEDS_APPROVAL:", "").split(":");
        const pendingRef = parts[0];
        const linkId = parts[1];
        const pendingId = parts[2];
        const to = emailParts[0];
        const subject = emailParts[1];
        const body = emailParts[2];
        
        pendingEmails.set(pendingId, {
          to,
          subject,
          body,
          userId,
          userToken,
          pendingRef,
        });
        console.log(`\nApproval required!`);
        console.log(`Check your email (${userEmail}) for the approval link`);
        console.log(`Link ID: ${linkId}`);
        console.log(`Waiting for approval...\n`);

        const { waitForApproval } = await import("./approval.js");
        const approved = await waitForApproval(pendingRef);

        if (approved) {
          messages.push({
            role: "user",
            content: [{
              type: "tool_result",
              tool_use_id: toolUse.id,
              content: `Approval received. Please check if the email was sent or if additional permissions are needed.`,
            }],
          });
        } else {
          messages.push({
            role: "user",
            content: [{
              type: "tool_result",
              tool_use_id: toolUse.id,
              content: `Approval timeout or denied.`,
              is_error: true,
            }],
          });
        }
        continue;
      }

      if (resultContent.startsWith("NEEDS_CONNECTION:")) {
        const url = resultContent.replace("NEEDS_CONNECTION:", "");
        console.log(`\n🔐 Gmail permission required. Opening browser...`);

        const { exec } = await import("child_process");
        exec(`open "${url}"`);

        console.log(`\nPlease grant permission in your browser.`);
        console.log(`⏳ Waiting for you to click Allow...`);

        // Poll for token (max 60 seconds)
        let tokenAvailable = false;
        let attempts = 0;
        const maxAttempts = 20;

        while (attempts < maxAttempts && !tokenAvailable) {
          await new Promise(resolve => setTimeout(resolve, 3000));
          attempts++;
          process.stdout.write(".");

          try {
            const checkResponse = await fetch(
              "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest",
              {
                method: "POST",
                headers: {
                  Authorization: `Bearer ${DESCOPE_PROJECT_ID}:${userToken}`,
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({ appId: "gmail", userId }),
              }
            );

            if (checkResponse.ok) {
              console.log(`\n\n✅ Permission granted! Continuing...\n`);
              tokenAvailable = true;
            }
          } catch (error) {
            // Keep polling
          }
        }

        if (!tokenAvailable) {
          console.log(`\n\n❌ Timeout. Please try again.\n`);
          messages.push({
            role: "user",
            content: [{
              type: "tool_result",
              tool_use_id: toolUse.id,
              content: `Timeout waiting for permission.`,
              is_error: true,
            }],
          });
        } else if (toolUse.name === "send_gmail_email") {
          messages.push({
            role: "user",
            content: [{
              type: "tool_result",
              tool_use_id: toolUse.id,
              content: `Gmail send permission granted. Let the user know they can now ask you to send the email again.`,
            }],
          });
        } else {
          messages.push({
            role: "user",
            content: [{
              type: "tool_result",
              tool_use_id: toolUse.id,
              content: `Permission granted. Retrying...`,
            }],
          });
        }
        continue;
      }

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