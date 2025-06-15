import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const USER_AGENT = "10x-crm/1.0";

const API_BASE_10xCRM = "https://www.10x-crm.app/api";


// // Format alert data
// function formatAlert(feature: AlertFeature): string {
//   const props = feature.properties;
//   return [
//     `Event: ${props.event || "Unknown"}`,
//     `Area: ${props.areaDesc || "Unknown"}`,
//     `Severity: ${props.severity || "Unknown"}`,
//     `Status: ${props.status || "Unknown"}`,
//     `Headline: ${props.headline || "No headline"}`,
//     "---",
//   ].join("\n");
// }

interface ForecastPeriod {
  name?: string;
  temperature?: number;
  temperatureUnit?: string;
  windSpeed?: string;
  windDirection?: string;
  shortForecast?: string;
}



async function make10xCRMRequest<T>(url: string, authToken: string): Promise<T | null> {
  const headers = {
    "User-Agent": USER_AGENT,
    Accept: "application/json",
    Authorization: `Bearer ${authToken}`,
  };

  console.log("authToken " + authToken);
  console.log("url " + url);
  console.log("user agent " + USER_AGENT);

  try {
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error("Error making 10xCRM request:", error);
    return null;
  }
}

interface ContactFeatures {
  properties: {
    id?: string;
    name?: string;
    email?: string;
    company?: string;
    tenant_id?: string;
    created_at?: string;
    last_contact?: string;
  };
}

interface DealFeatures {
    properties: {
        id?: string;
        name?: string;
        value?: number;
        stage?: string;
        customerId?: string;
        expectedCloseDate?: string;
        probability?: number;
        created_at?: string;
    };
}

interface ContactResponse {
    properties: {
        data: ContactFeatures[];
        pagination: [];
    }
}

interface DealResponse {
    properties: {
        data: DealFeatures[];
        pagination: [];
    }
}

export const createServer = ({ authToken }: { authToken: string }) => {
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
            const contactsUrl = `${API_BASE_10xCRM}/contacts`;
            const contactsData = await make10xCRMRequest<ContactResponse>(contactsUrl, authToken);

            if (!contactsData) {
                return {
                    content: [
                        {
                            type: "text",
                            text: "Failed to retrieve contact data",
                        },
                    ],
                };
            }

            const features = contactsData.properties.data || [];
            if (features.length === 0) {
                return {
                    content: [
                        {
                            type: "text",
                            text: `No contacts`,
                        },
                    ],
                };
            }
            // TODO: format return text
            const formattedAlerts = features;
            const contactsText = `Contacts:\n\n${formattedAlerts.join("\n")}`;

            return {
                content: [
                    {
                        type: "text",
                        text: contactsText,
                    },
                ],
            };
        },
    );

    server.tool(
        "get-contact",
        "Get a contact by ID or email",
        {
            id: z.string().describe("The ID or email of the contact to retrieve."),
        },
        async ({ id }) => {
            const contactsUrl = `${API_BASE_10xCRM}/contacts/${id}`;
            const contactsData = await make10xCRMRequest<ContactResponse>(contactsUrl, authToken);
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

            const features = contactsData.properties.data || [];
            if (features.length === 0) {
                return {
                    content: [
                        {
                            type: "text",
                            text: `No contacts with ${id}`,
                        },
                    ],
                };
            }

            const formattedContacts = features;
            const contactsText = `Contact for ${id}:\n\n${formattedContacts.join("\n")}`;

            return {
                content: [
                    {
                        type: "text",
                        text: contactsText,
                    },
                ],
            };
        },
    );

    server.tool(
        "get-deals",
        "Get a paginated list of deals with optional search and stage filters",
        {
            dealInfo: z.string().describe(""),
        },
        async ({ dealInfo }) => {
            const stateCode = dealInfo.toUpperCase();
            const alertsUrl = `${API_BASE_10xCRM}/alerts?deals=${stateCode}`;
            const alertsData = await make10xCRMRequest<DealResponse>(alertsUrl, authToken);

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

            const features = alertsData.properties.data || [];
            if (features.length === 0) {
                return {
                    content: [
                        {
                            type: "text",
                            text: `No active alerts for ${stateCode}`,
                        },
                    ],
                };
            }

            const formattedAlerts = features;
            const alertsText = `Active alerts for ${stateCode}:\n\n${formattedAlerts.join("\n")}`;

            return {
                content: [
                    {
                        type: "text",
                        text: alertsText,
                    },
                ],
            };
        },
    );

    server.tool(
        "get-deal",
        "Get deals by customer ID or email",
        {
            id: z.string().describe("Customer ID or email"),
        },
        async ({ id }) => {
            const alertsUrl = `${API_BASE_10xCRM}/deals?id=${id}`;
            const alertsData = await make10xCRMRequest<DealResponse>(alertsUrl, authToken);

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

            const features = alertsData.properties.data || [];
            if (features.length === 0) {
                return {
                    content: [
                        {
                            type: "text",
                            text: `No active alerts for ${id}`,
                        },
                    ],
                };
            }

            const formattedAlerts = features;
            const alertsText = `Active alerts for ${id}:\n\n${formattedAlerts.join("\n")}`;

            return {
                content: [
                    {
                        type: "text",
                        text: alertsText,
                    },
                ],
            };
        },
    );

    server.tool(
        "get-contacts-search",
        "Search contacts with optional filters and pagination",
        {
            query: z.string().describe("Search contacts with optional filters and pagination"),
        },
        async ({ query }) => {
            const alertsUrl = `${API_BASE_10xCRM}/contacts?contacts=${query}`;
            const alertsData = await make10xCRMRequest<ContactResponse>(alertsUrl, authToken);

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

            const features = alertsData.properties.data || [];
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
            const alertsText = `Active alerts for ${query}:\n\n${formattedAlerts.join("\n")}`;

            return {
                content: [
                    {
                        type: "text",
                        text: alertsText,
                    },
                ],
            };
        },
    );
    

    return { server };
}
