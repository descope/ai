import { createMcpHandler, withMcpAuth } from "mcp-handler";
import { z } from "zod";
import DescopeClient from "@descope/node-sdk";

const DESCOPE_PROJECT_ID = process.env.DESCOPE_PROJECT_ID!;
const DESCOPE_BASE_URL =
  process.env.NEXT_PUBLIC_DESCOPE_BASE_URL || "https://api.descope.com";
const SKYFLOW_VAULT_URL_IDENTIFIER = process.env.SKYFLOW_VAULT_URL_IDENTIFIER!;
const SKYFLOW_VAULT_ID = process.env.SKYFLOW_VAULT_ID!;
const SKYFLOW_STS_URL =
  process.env.SKYFLOW_STS_URL || "https://manage.skyflowapis.com/v1/auth/sts/token";
const SKYFLOW_SERVICE_ACCOUNT_ID = process.env.SKYFLOW_SERVICE_ACCOUNT_ID!;

if (!DESCOPE_PROJECT_ID) {
  throw new Error("DESCOPE_PROJECT_ID environment variable is required");
}

// Skyflow environment variables are optional at startup, but required when using the tool

const descopeClient = DescopeClient({
  projectId: DESCOPE_PROJECT_ID,
  baseUrl: DESCOPE_BASE_URL,
});

const exchangeDescopeTokenForSkyflowToken = async (
  descopeToken: string
): Promise<string> => {
  const body = new URLSearchParams();
  body.set("grant_type", "urn:ietf:params:oauth:grant-type:token-exchange");
  body.set("subject_token", descopeToken);
  body.set("subject_token_type", "urn:ietf:params:oauth:token-type:jwt");
  body.set("service_account_id", SKYFLOW_SERVICE_ACCOUNT_ID);

  const response = await fetch(SKYFLOW_STS_URL, {
    method: "POST",
    headers: {
      Accept: "application/x-www-form-urlencoded",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `STS token exchange failed: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  const contentType = response.headers.get("content-type") || "";
  let token: string | null = null;

  if (contentType.includes("application/json")) {
    const data: any = await response.json();
    token = data.accessToken || data.access_token || data.token || null;
  } else {
    const text = await response.text();
    const params = new URLSearchParams(text);
    token =
      params.get("accessToken") ||
      params.get("access_token") ||
      params.get("token");
  }

  if (!token) {
    throw new Error("STS token exchange succeeded but no access token found");
  }

  return token;
};

const handler = createMcpHandler(
  (server: any) => {
   server.tool(
      "get_skyflow_records",
      "Get record(s) from a Skyflow vault table. Fetches sensitive data from Skyflow using the authenticated user's token from Descope.",
      {
        tableName: z
          .string()
          .describe("Name of the table that contains the records"),
        skyflow_ids: z
          .array(z.string())
          .optional()
          .describe(
            "skyflow_id values of the records to return. If not specified, returns the first 25 records in the table."
          ),
        redaction: z
          .enum(["DEFAULT", "MASKED", "PLAIN_TEXT", "REDACTED"])
          .optional()
          .describe(
            "Redaction level to enforce for the returned records. Defaults to DEFAULT."
          ),
        tokenization: z
          .boolean()
          .optional()
          .describe(
            "If true, this operation returns tokens for fields with tokenization enabled. Only applicable if skyflow_id values are specified."
          ),
        returnFileMetadata: z
          .boolean()
          .optional()
          .describe("If true, returns file metadata."),
        fields: z
          .array(z.string())
          .optional()
          .describe(
            "Fields to return for the record. If not specified, returns all fields."
          ),
        offset: z
          .string()
          .optional()
          .describe(
            "Record position at which to start receiving data. Defaults to 0."
          ),
        limit: z
          .string()
          .optional()
          .describe("Number of records to return. Maximum 25. Defaults to 25."),
        downloadURL: z
          .boolean()
          .optional()
          .describe(
            "If true, returns download URLs for fields with a file data type. URLs are valid for 15 minutes."
          ),
        column_name: z
          .string()
          .optional()
          .describe(
            "Name of the column. It must be configured as unique in the schema. Cannot be used with skyflow_ids."
          ),
        column_values: z
          .array(z.string())
          .optional()
          .describe(
            "Column values of the records to return. column_name is mandatory when providing column_values. Cannot be used with skyflow_ids."
          ),
        order_by: z
          .enum(["ASCENDING", "DESCENDING", "NONE"])
          .optional()
          .describe(
            "Order to return records, based on skyflow_id values. Defaults to ASCENDING."
          ),
      },
      async (args: any, context: any) => {
        try {

          if (!SKYFLOW_VAULT_URL_IDENTIFIER) {
            throw new Error(
              "SKYFLOW_VAULT_URL_IDENTIFIER environment variable is required"
            );
          }

          const skyflowToken = context?.authInfo?.extra
            ?.skyflowToken as string | undefined;

          if (!skyflowToken) {
            throw new Error(
              "Skyflow token not found in authentication context (token exchange may have failed)"
            );
          }

          // Build the Skyflow API URL (fixed vault ID)
          const baseUrl = `https://${SKYFLOW_VAULT_URL_IDENTIFIER}.vault.skyflowapis.com/v1/vaults/${SKYFLOW_VAULT_ID}/${args.tableName}`;
          const url = new URL(baseUrl);

          console.log("BASE URL:", baseUrl);

          // Add query parameters
          if (args.skyflow_ids && args.skyflow_ids.length > 0) {
            args.skyflow_ids.forEach((id: string) => {
              url.searchParams.append("skyflow_ids", id);
            });
          }

          if (args.redaction) {
            url.searchParams.append("redaction", args.redaction);
          }

          if (args.tokenization !== undefined) {
            url.searchParams.append("tokenization", String(args.tokenization));
          }

          if (args.returnFileMetadata !== undefined) {
            url.searchParams.append(
              "returnFileMetadata",
              String(args.returnFileMetadata)
            );
          }

          if (args.fields && args.fields.length > 0) {
            args.fields.forEach((field: string) => {
              url.searchParams.append("fields", field);
            });
          }

          if (args.offset) {
            url.searchParams.append("offset", args.offset);
          }

          if (args.limit) {
            url.searchParams.append("limit", args.limit);
          }

          if (args.downloadURL !== undefined) {
            url.searchParams.append("downloadURL", String(args.downloadURL));
          }

          if (args.column_name) {
            url.searchParams.append("column_name", args.column_name);
          }

          if (args.column_values && args.column_values.length > 0) {
            args.column_values.forEach((value: string) => {
              url.searchParams.append("column_values", value);
            });
          }

          if (args.order_by) {
            url.searchParams.append("order_by", args.order_by);
          }

          // Make the request to Skyflow API
          const response = await fetch(url.toString(), {
            method: "GET",
            headers: {
              Authorization: `Bearer ${skyflowToken}`,
              "Content-Type": "application/json",
              "X-SKYFLOW-ACCOUNT-NAME":"area52"
            },
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(
              `Skyflow API error: ${response.status} ${response.statusText} - ${errorText}`
            );
          }

          const data = await response.json();

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(data, null, 2),
              },
            ],
          };
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "Unknown error occurred";
          return {
            content: [
              {
                type: "text",
                text: `Error fetching Skyflow records: ${errorMessage}`,
              },
            ],
            isError: true,
          };
        }
      }
    );

  },
  undefined,
  {
    // basePath is the path to the MCP server. Incorrectly setting this will affect tool discovery by the client.
    basePath: "/api",
    verboseLogs: true,
    maxDuration: 800,
    disableSse: false,
  }
);

const verifyToken = async (req: Request, bearerToken?: string) => {
  if (!bearerToken) return undefined;
  try {
    // Validate the JWT token with Descope
    const authInfo = await descopeClient.validateSession(bearerToken);
    console.log("DESCOPE BEARER: ", bearerToken)
    let skyflowToken: string | undefined;
    try {
      skyflowToken = await exchangeDescopeTokenForSkyflowToken(bearerToken);
      console.log("SKYFLOW TOKEN:", skyflowToken);
    } catch (stsError) {
      console.error("Skyflow STS token exchange failed during verifyToken:", stsError);
    }

    const scopeString = authInfo.token.scope as string;
    const scopes = scopeString ? scopeString.split(" ") : [];
    const clientId = authInfo.token.azp as string;
    const tenantId = authInfo.token.tenant_id as string | undefined;

    return {
      token: bearerToken,
      scopes: scopes,
      clientId: clientId,
      extra: {
        // Optional extra information
        userId: authInfo.token.sub,
        tenantId: tenantId,
        skyflowToken: skyflowToken,
      },
    };
  } catch (error) {
    console.error("Token validation failed:", error);
    return undefined;
  }
};

const authHandler = withMcpAuth(handler, verifyToken, {
  required: true,
  resourceMetadataPath: "/.well-known/oauth-protected-resource",
});

export { authHandler as GET, authHandler as POST };
