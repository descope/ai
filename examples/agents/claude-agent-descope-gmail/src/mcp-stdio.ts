import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import DescopeClient from "@descope/node-sdk";
import "dotenv/config";

const DESCOPE_PROJECT_ID = process.env.DESCOPE_PROJECT_ID!;
const GMAIL_CONNECTION_ID = "gmail";

function createDescopeClient(userToken: string) {
  return DescopeClient({
    projectId: DESCOPE_PROJECT_ID,
    hooks: {
      beforeRequest: (requestConfig: any) => {
        requestConfig.headers = {
          ...requestConfig.headers,
          Authorization: `Bearer ${DESCOPE_PROJECT_ID}:${userToken}`,
        };
        return requestConfig;
      },
    },
  });
}

const server = new Server(
  { name: "gmail-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "read_gmail_inbox",
      description: "Read the latest 5 emails from Gmail inbox",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    {
      name: "send_gmail_email",
      description: "Send an email via Gmail",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string" },
          subject: { type: "string" },
          body: { type: "string" },
        },
        required: ["to", "subject", "body"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  const userToken = (request.params as any)._meta?.userToken;
  const userId = (request.params as any)._meta?.userId;
  const userEmail = (request.params as any)._meta?.userEmail;

  if (!userToken || !userId) {
    return {
      content: [{ type: "text", text: "Missing authentication" }],
      isError: true,
    };
  }
  
  if (name === "read_gmail_inbox") {
    return await handleReadEmails(userId, userToken);
  } else if (name === "send_gmail_email") {
    const { to, subject, body } = args as any;
    return await handleSendEmail(userId, userToken, to, subject, body, userEmail || userId);
  }

  return { content: [{ type: "text", text: "Unknown tool" }], isError: true };
});

async function handleReadEmails(userId: string, userToken: string) {
  try {
    const descopeClient = createDescopeClient(userToken);
    const READ_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"];

    const tokenResult = await descopeClient.management.outboundApplication.fetchTokenByScopes(
      GMAIL_CONNECTION_ID,
      userId,
      READ_SCOPES
    );

    if (!tokenResult.ok) {
      const connectResponse = await fetch(
        "https://api.descope.com/v1/mgmt/outbound/app/connect",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${DESCOPE_PROJECT_ID}:${userToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            appId: GMAIL_CONNECTION_ID,
            options: {
              redirectUrl: "http://localhost:3000/connection-complete",
              scopes: READ_SCOPES,
            },
          }),
        }
      );

      const connectData = await connectResponse.json();
      return {
        content: [{
          type: "text",
          text: `NEEDS_CONNECTION:${connectData.url}`
        }],
        isError: true,
      };
    }

    const gmailToken = tokenResult.data?.accessToken;

    const listRes = await fetch(
      "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=5",
      { headers: { Authorization: `Bearer ${gmailToken}` } }
    );

    const listData = await listRes.json();

    const emails = [];

    for (const msg of (listData.messages || []).slice(0, 5)) {
      const msgRes = await fetch(
        `https://gmail.googleapis.com/gmail/v1/users/me/messages/${msg.id}`,
        { headers: { Authorization: `Bearer ${gmailToken}` } }
      );
      const msgData = await msgRes.json();
      const headers = msgData.payload?.headers || [];

      emails.push({
        from: headers.find((h: any) => h.name === "From")?.value || "Unknown",
        subject: headers.find((h: any) => h.name === "Subject")?.value || "(No Subject)",
        preview: msgData.snippet,
      });
    }

    return {
      content: [{ type: "text", text: JSON.stringify({ emails }, null, 2) }],
    };
  } catch (error: any) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
}

async function handleSendEmail(
  userId: string, 
  userToken: string, 
  to: string, 
  subject: string, 
  body: string,
  userEmail: string
) {
  try {
    const descopeClient = createDescopeClient(userToken);
    const SEND_SCOPES = [
      "https://www.googleapis.com/auth/gmail.send",
      "https://www.googleapis.com/auth/gmail.readonly",
    ];

    const tokenResult = await descopeClient.management.outboundApplication.fetchTokenByScopes(
      GMAIL_CONNECTION_ID,
      userId,
      SEND_SCOPES
    );

    if (!tokenResult.ok) {
      const connectResponse = await fetch(
        "https://api.descope.com/v1/mgmt/outbound/app/connect",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${DESCOPE_PROJECT_ID}:${userToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            appId: GMAIL_CONNECTION_ID,
            options: {
              redirectUrl: "http://localhost:3000/connection-complete",
              scopes: SEND_SCOPES,
            },
          }),
        }
      );

      const connectData = await connectResponse.json();
      return {
        content: [{
          type: "text",
          text: `NEEDS_CONNECTION:${connectData.url}`
        }],
        isError: true,
      };
    }

    const gmailToken = tokenResult.data?.accessToken;

    // NOW proceed with approval since we have the scope
    // Fetch the actual email address from Gmail
    let actualEmail = userEmail;
    if (!actualEmail || actualEmail === userId) {
      try {
        const profileResponse = await fetch(
          "https://gmail.googleapis.com/gmail/v1/users/me/profile",
          { headers: { Authorization: `Bearer ${gmailToken}` } }
        );
        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          actualEmail = profileData.emailAddress || userId;
        }
      } catch (e) {
        console.error("Failed to fetch email from Gmail:", e);
      }
    }

    const pendingId = `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const { requestApproval } = await import("./approval.js");
    
    const actionDescription = `Send email to ${to} with subject "${subject}"`;
    const { pendingRef, linkId } = await requestApproval(actualEmail, actionDescription, pendingId);


    return {
      content: [{
        type: "text",
        text: `NEEDS_APPROVAL:${pendingRef}:${linkId}:${pendingId}|||${to}|||${subject}|||${body}`
      }],
    };
  } catch (error: any) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
}

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MCP server ready");
}

main().catch(console.error);