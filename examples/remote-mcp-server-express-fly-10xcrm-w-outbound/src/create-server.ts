import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { google } from "googleapis";

const USER_AGENT = "10x-crm/1.0";
const API_BASE_10xCRM = "https://www.10x-crm.app/api";
const DESCOPE_API_BASE =
  "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest";

// Get environment variables
const PROJECT_ID = process.env.DESCOPE_PROJECT_ID;
const MANAGEMENT_KEY = process.env.DESCOPE_MANAGEMENT_KEY;

if (!PROJECT_ID || !MANAGEMENT_KEY) {
  throw new Error(
    "Missing required environment variables: DESCOPE_PROJECT_ID and/or DESCOPE_MANAGEMENT_KEY"
  );
}

// Custom error class for authentication and authorization errors
class AuthenticationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthenticationError";
  }
}

class AuthorizationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthorizationError";
  }
}

// Function to extract user ID from JWT token
function extractUserIdFromToken(token: string): string | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      throw new Error("Invalid token format");
    }

    const payload = JSON.parse(atob(parts[1]));

    // Extract the sub claim
    if (payload && typeof payload === "object" && "sub" in payload) {
      return payload.sub as string;
    }
    return null;
  } catch (error) {
    console.error("Error decoding token:", error);
    return null;
  }
}

// Function to get outbound app token
async function getOutboundAppToken(
  userId: string,
  appId: string
): Promise<string> {
  try {
    const response = await fetch(DESCOPE_API_BASE, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${PROJECT_ID}:${MANAGEMENT_KEY}`,
      },
      body: JSON.stringify({
        appId: appId,
        userId: userId,
        options: {
          withRefreshToken: false,
          forceRefresh: false,
        },
      }),
    });

    if (response.status === 401) {
      throw new AuthenticationError("Unauthorized: Invalid credentials");
    }

    if (response.status === 403) {
      throw new AuthorizationError(
        "Forbidden: Insufficient scopes for outbound app"
      );
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = (await response.json()) as { token?: string };
    if (!data.token) {
      throw new AuthorizationError("No outbound app token available");
    }

    return data.token;
  } catch (error) {
    if (
      error instanceof AuthenticationError ||
      error instanceof AuthorizationError
    ) {
      throw error;
    }
    console.error("Error getting outbound app token:", error);
    throw new Error("Failed to get outbound app token");
  }
}

// Format contact data
function formatContact(feature: ContactFeatures): string {
  const props = feature;
  return [
    `ID: ${props.id || "Unknown"}`,
    `Name: ${props.name || "Unknown"}`,
    `Email: ${props.email || "Unknown"}`,
    `Company: ${props.company || "Unknown"}`,
    `Tenant ID: ${props.tenant_id || "Unknown"}`,
    `Created At: ${props.created_at || "Unknown"}`,
    `Last Contact: ${props.last_contact || "Unknown"}`,
    "---",
  ].join("\n");
}

// Format deal data
function formatDeal(feature: DealFeatures): string {
  const props = feature;
  return [
    `ID: ${props.id || "Unknown"}`,
    `Name: ${props.name || "Unknown"}`,
    `Value: ${props.value || "Unknown"}`,
    `Stage: ${props.stage || "Unknown"}`,
    `Customer ID: ${props.customerId || "Unknown"}`,
    `Expected Close Date: ${props.expectedCloseDate || "Unknown"}`,
    `Probability: ${props.probability || "Unknown"}`,
    `Created At: ${props.created_at || "Unknown"}`,
    "---",
  ].join("\n");
}

async function make10xCRMRequest<T>(url: string, userId: string): Promise<T> {
  try {
    // Get outbound app token for 10x CRM
    const outboundToken = await getOutboundAppToken(userId, "custom");

    const headers = {
      "User-Agent": USER_AGENT,
      Accept: "application/json",
      Authorization: `Bearer ${outboundToken}`,
    };

    console.log("Outbound Token:", outboundToken);
    console.log("URL:", url);
    console.log("User Agent:", USER_AGENT);

    const response = await fetch(url, { headers });

    if (response.status === 401) {
      throw new AuthenticationError(
        "Unauthorized: Invalid 10x CRM credentials"
      );
    }

    if (response.status === 403) {
      throw new AuthorizationError(
        "Forbidden: Insufficient permissions for 10x CRM"
      );
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (
      error instanceof AuthenticationError ||
      error instanceof AuthorizationError
    ) {
      throw error;
    }
    console.error("Error making 10xCRM request:", error);
    throw new Error("Failed to make 10x CRM request");
  }
}

interface ContactFeatures {
  id?: string;
  name?: string;
  email?: string;
  company?: string;
  tenant_id?: string;
  created_at?: string;
  last_contact?: string;
}

interface DealFeatures {
  id?: string;
  name?: string;
  value?: number;
  stage?: string;
  customerId?: string;
  expectedCloseDate?: string;
  probability?: number;
  created_at?: string;
}

interface ContactResponse {
  data: ContactFeatures[];
  pagination: [];
}

interface DealResponse {
  data: DealFeatures[];
  pagination: [];
}

// Define available scopes
const SCOPES = {
  CRM: {
    READ_CONTACTS: "contacts:read",
    WRITE_CONTACTS: "contacts:write",
    READ_DEALS: "deals:read",
    WRITE_DEALS: "deals:write",
  },
  CALENDAR: {
    WRITE_EVENTS: "calendar",
  },
} as const;

// Function to check if token has required scopes
function checkScopes(token: string, requiredScopes: string[]): void {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      throw new AuthenticationError("Invalid token format");
    }

    const payload = JSON.parse(atob(parts[1]));
    const tokenScopes = (payload.scope as string[]) || [];

    // Bypass scope check if full_access or profile is present
    if (
      tokenScopes.includes("full_access") ||
      tokenScopes.includes("profile")
    ) {
      return;
    }

    const missingScopes = requiredScopes.filter(
      (scope) => !tokenScopes.includes(scope)
    );
    if (missingScopes.length > 0) {
      throw new AuthorizationError(
        `Missing required scopes: ${missingScopes.join(", ")}`
      );
    }
  } catch (error) {
    if (
      error instanceof AuthenticationError ||
      error instanceof AuthorizationError
    ) {
      throw error;
    }
    throw new AuthenticationError("Failed to verify token scopes");
  }
}

export const createServer = ({ authToken }: { authToken: string }) => {
  // Extract user ID from auth token once
  const userId = extractUserIdFromToken(authToken);
  if (!userId) {
    throw new Error("Failed to extract user ID from token");
  }

  // Create server instance
  const server = new McpServer({
    name: "10x-crm",
    version: "1.0.0",
  });

  server.tool(
    "list-contacts",
    "Get a paginated list of contacts with optional search",
    {
      // TODO: optional search?
    },
    async () => {
      try {
        // Check required scopes
        checkScopes(authToken, [SCOPES.CRM.READ_CONTACTS]);

        const contactsUrl = `${API_BASE_10xCRM}/contacts`;
        const contactsData = await make10xCRMRequest<ContactResponse>(
          contactsUrl,
          userId
        );

        const features = contactsData.data || [];
        if (features.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No contacts found`,
              },
            ],
          };
        }

        const formattedContacts = features.map(formatContact);
        const contactsText = `Contacts:\n\n${formattedContacts.join("\n")}`;

        return {
          content: [
            {
              type: "text",
              text: contactsText,
            },
          ],
        };
      } catch (error) {
        if (error instanceof AuthenticationError) {
          return {
            content: [
              {
                type: "text",
                text: "Authentication error: Please ensure you have valid credentials.",
              },
            ],
          };
        }
        if (error instanceof AuthorizationError) {
          return {
            content: [
              {
                type: "text",
                text: `Authorization error: ${error.message}`,
              },
            ],
          };
        }
        return {
          content: [
            {
              type: "text",
              text: "Failed to retrieve contact data. Please try again later.",
            },
          ],
        };
      }
    }
  );

  server.tool(
    "get-contact",
    "Get a contact by ID or email",
    {
      id: z.string().describe("The ID or email of the contact to retrieve."),
      // email: z.string().describe("The email of the contact to retrieve.")
    },
    async ({ id }) => {
      try {
        // Check required scopes
        checkScopes(authToken, [SCOPES.CRM.READ_CONTACTS]);

        const contactsUrl = `${API_BASE_10xCRM}/contacts/${id}`;
        const contactsData = await make10xCRMRequest<ContactFeatures>(
          contactsUrl,
          userId
        );
        console.log(contactsData);
        if (!contactsData) {
          return {
            content: [
              {
                type: "text",
                text: "Failed to retrieve contact information",
              },
            ],
          };
        }
        const features = contactsData || [];
        console.log(" features " + features);
        if (features === null) {
          return {
            content: [
              {
                type: "text",
                text: `No contacts with ${id}`,
              },
            ],
          };
        }

        const formattedContacts = formatContact(features);
        console.log(formattedContacts);
        const contactsText = `Contact for ${id}:\n\n${formattedContacts}`;

        return {
          content: [
            {
              type: "text",
              text: contactsText,
            },
          ],
        };
      } catch (error) {
        if (error instanceof AuthenticationError) {
          return {
            content: [
              {
                type: "text",
                text: "Authentication error: Please ensure you have valid credentials.",
              },
            ],
          };
        }
        if (error instanceof AuthorizationError) {
          return {
            content: [
              {
                type: "text",
                text: `Authorization error: ${error.message}`,
              },
            ],
          };
        }
        return {
          content: [
            {
              type: "text",
              text: "Failed to retrieve contact information. Please try again later.",
            },
          ],
        };
      }
    }
  );

  server.tool(
    "get-deals",
    "Get a paginated list of deals with optional search and stage filters",
    {
      dealInfo: z.string().describe(""),
    },
    async ({ dealInfo }) => {
      try {
        // Check required scopes
        checkScopes(authToken, [SCOPES.CRM.READ_DEALS]);

        const dealsUrl = `${API_BASE_10xCRM}/deals`;
        const dealsData = await make10xCRMRequest<DealResponse>(
          dealsUrl,
          userId
        );

        const features = dealsData.data || [];
        if (features === null) {
          return {
            content: [
              {
                type: "text",
                text: `No deals found`,
              },
            ],
          };
        }

        const formattedDeals = features.map(formatDeal);
        const dealsText = `Deals:\n\n${formattedDeals.join("\n")}`;

        return {
          content: [
            {
              type: "text",
              text: dealsText,
            },
          ],
        };
      } catch (error) {
        if (error instanceof AuthenticationError) {
          return {
            content: [
              {
                type: "text",
                text: "Authentication error: Please ensure you have valid credentials.",
              },
            ],
          };
        }
        if (error instanceof AuthorizationError) {
          return {
            content: [
              {
                type: "text",
                text: `Authorization error: ${error.message}`,
              },
            ],
          };
        }
        return {
          content: [
            {
              type: "text",
              text: "Failed to retrieve deals data. Please try again later.",
            },
          ],
        };
      }
    }
  );

  server.tool(
    "get-deal",
    "Get deals by deal ID",
    {
      id: z.string().describe("Deal ID of the deal to retrieve."),
    },
    async ({ id }) => {
      const dealsUrl = `${API_BASE_10xCRM}/deals/${id}`;
      const dealsData = await make10xCRMRequest<DealFeatures>(dealsUrl, userId);

      if (!dealsData) {
        return {
          content: [
            {
              type: "text",
              text: "Failed to retrieve deals data",
            },
          ],
        };
      }

      const features = dealsData || [];
      if (features === null) {
        return {
          content: [
            {
              type: "text",
              text: `No active alerts for ${id}`,
            },
          ],
        };
      }

      const formattedDeal = formatDeal(features);
      const dealsText = `Active deal for ${id}:\n\n${formattedDeal}`;

      return {
        content: [
          {
            type: "text",
            text: dealsText,
          },
        ],
      };
    }
  );

  server.tool(
    "get-contacts-search",
    "Search contacts with optional filters and pagination",
    {
      query: z
        .string()
        .describe("Search contacts with optional filters and pagination"),
    },
    async ({ query }) => {
      const alertsUrl = `${API_BASE_10xCRM}/contacts?contacts=${query}`;
      const alertsData = await make10xCRMRequest<ContactResponse>(
        alertsUrl,
        userId
      );

      if (!alertsData) {
        return {
          content: [
            {
              type: "text",
              text: "Failed to retrieve alerts data",
            },
          ],
        };
      }

      const features = alertsData.data || [];
      if (features.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: `No active alerts for ${query}`,
            },
          ],
        };
      }

      const formattedAlerts = features;
      const alertsText = `Active alerts for ${query}:\n\n${formattedAlerts.join(
        "\n"
      )}`;

      return {
        content: [
          {
            type: "text",
            text: alertsText,
          },
        ],
      };
    }
  );

  // Add Google Calendar tool
  server.tool(
    "create-calendar-event",
    "Create a new calendar event in Google Calendar",
    {
      title: z.string().describe("Title of the calendar event"),
      description: z.string().optional().describe("Description of the event"),
      startTime: z.string().describe("Start time of the event in ISO format"),
      endTime: z.string().describe("End time of the event in ISO format"),
      timeZone: z
        .string()
        .optional()
        .describe("Time zone for the event (defaults to UTC)"),
      location: z.string().optional().describe("Location of the event"),
      attendees: z
        .array(z.string())
        .optional()
        .describe("List of attendee email addresses"),
    },
    async (data) => {
      try {
        // Check required scopes
        checkScopes(authToken, [SCOPES.CALENDAR.WRITE_EVENTS]);

        // Get Google Calendar token
        const token = await getOutboundAppToken(userId, "google-calendar");
        if (!token) {
          throw new Error("Failed to get Google Calendar token");
        }

        // Set up Google Calendar API client
        const oauth2Client = new google.auth.OAuth2();
        oauth2Client.setCredentials({
          access_token: token,
        });
        const calendar = google.calendar({ version: "v3", auth: oauth2Client });

        // Prepare event data
        const event = {
          summary: data.title,
          description: data.description,
          start: {
            dateTime: data.startTime,
            timeZone: data.timeZone || "UTC",
          },
          end: {
            dateTime: data.endTime,
            timeZone: data.timeZone || "UTC",
          },
          location: data.location,
          attendees: data.attendees?.map((email) => ({ email })),
        };

        // Create the calendar event
        console.log("Sending calendar event creation request to Google API");
        const response = await calendar.events.insert({
          calendarId: "primary",
          requestBody: event,
          conferenceDataVersion: 1,
        });

        // Log the successful response
        console.log("Calendar event created successfully:", {
          eventId: response.data.id,
          eventLink: response.data.htmlLink,
          summary: response.data.summary,
          status: response.status,
        });

        return {
          content: [
            {
              type: "text",
              text: `Calendar event created successfully!\nEvent ID: ${response.data.id}\nEvent Link: ${response.data.htmlLink}\nSummary: ${response.data.summary}`,
            },
          ],
        };
      } catch (error) {
        if (error instanceof AuthenticationError) {
          return {
            content: [
              {
                type: "text",
                text: "Authentication error: Please ensure you have valid credentials.",
              },
            ],
          };
        }
        if (error instanceof AuthorizationError) {
          return {
            content: [
              {
                type: "text",
                text: `Authorization error: ${error.message}`,
              },
            ],
          };
        }
        return {
          content: [
            {
              type: "text",
              text: "Failed to create calendar event. Please try again later.",
            },
          ],
        };
      }
    }
  );

  return { server };
};
