import "dotenv/config";
import { exec } from "child_process";

const DESCOPE_PROJECT_ID = process.env.DESCOPE_PROJECT_ID!;
const MCP_SERVER_ID = process.env.MCP_SERVER_ID!;
const DESCOPE_CLIENT_ID = process.env.DESCOPE_CLIENT_ID!;

export function authenticateUser() {
  const authUrl = `https://api.descope.com/oauth2/v1/apps/agentic/${DESCOPE_PROJECT_ID}/${MCP_SERVER_ID}/authorize?response_type=code&client_id=${DESCOPE_CLIENT_ID}&redirect_uri=http://localhost:3000/callback&scope=google-read+google-send&flow=inbound-apps-user-consent`;
  
  console.log("\nOpening browser for authentication...");
  console.log(`\nIf browser doesn't open, visit:\n${authUrl}\n`);
  
  exec(`open "${authUrl}"`, (error) => {
    if (error) {
      console.log("Could not open browser automatically");
    }
  });
}

export async function fetchUserEmail(userId: string, userToken: string): Promise<string> {
  try {
    const tokenResponse = await fetch(
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

    if (!tokenResponse.ok) {
      return "";
    }

    const tokenData = await tokenResponse.json();
    const gmailToken = tokenData.token.accessToken;

    const profileResponse = await fetch(
      "https://gmail.googleapis.com/gmail/v1/users/me/profile",
      { headers: { Authorization: `Bearer ${gmailToken}` } }
    );

    if (!profileResponse.ok) {
      return "";
    }

    const profileData = await profileResponse.json();
    return profileData.emailAddress || "";
  } catch (error) {
    console.error("Failed to fetch user email:", error);
    return "";
  }
}