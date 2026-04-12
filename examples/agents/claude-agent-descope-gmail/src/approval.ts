import DescopeClient from "@descope/node-sdk";
import "dotenv/config";

const descopeClient = DescopeClient({ projectId: process.env.DESCOPE_PROJECT_ID! });

interface ApprovalRequest {
  pendingRef: string;
  linkId: string;
}

export async function requestApproval(
  userEmail: string,
  actionDescription: string,
  pendingId: string
): Promise<ApprovalRequest> {
  // Generate enchanted link for approval
  const response = await descopeClient.enchantedLink.signIn(
    userEmail,
    `http://localhost:3000/approve?id=${pendingId}`,
    {
      customClaims: {
        action: actionDescription,
      },
    }
  );

  if (!response.ok || !response.data) {
    throw new Error(`Failed to create approval link: ${response.error?.errorMessage || "Unknown error"}`);
  }

  console.log(`\n✉️  Approval link sent to ${userEmail}`);
  console.log(`📋 Link ID to approve: ${response.data.linkId}\n`);

  return {
    pendingRef: response.data.pendingRef,
    linkId: response.data.linkId,
  };
}

export async function waitForApproval(pendingRef: string): Promise<boolean> {
  try {
    const response = await descopeClient.enchantedLink.waitForSession(pendingRef);
    
    if (!response.ok) {
      return false;
    }

    console.log("✅ Approval received!\n");
    return true;
  } catch (error) {
    return false;
  }
}

export async function verifyApproval(token: string): Promise<boolean> {
  try {
    const response = await descopeClient.enchantedLink.verify(token);
    return response.ok;
  } catch (error) {
    return false;
  }
}