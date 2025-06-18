import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const USER_AGENT = "10x-crm/1.0";

const API_BASE_10xCRM = "https://www.10x-crm.app/api";


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
            console.log(contactsData);
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

            const features = contactsData.data || [];
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
        },
    );

    server.tool(
        "get-contact",
        "Get a contact by ID or email",
        {
            id: z.string().describe("The ID or email of the contact to retrieve."),
            // email: z.string().describe("The email of the contact to retrieve.")
        },
        async ({ id }) => {
            const contactsUrl = `${API_BASE_10xCRM}/contacts/${id}`;
            const contactsData = await make10xCRMRequest<ContactFeatures>(contactsUrl, authToken);
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
        },
    );

    server.tool(
        "get-deals",
        "Get a paginated list of deals with optional search and stage filters",
        {
            dealInfo: z.string().describe(""),
        },
        async ({ dealInfo }) => {
            const dealsUrl = `${API_BASE_10xCRM}/deals`;
            const dealsData = await make10xCRMRequest<DealResponse>(dealsUrl, authToken);

            if (!dealsData) {
                return {
                    content: [
                        {
                            type: "text",
                            text: "Failed to retrieve alerts data",
                        },
                    ],
                };
            }

            const features = dealsData.data || [];
            if (features === null) {
                return {
                    content: [
                        {
                            type: "text",
                            text: `No active alerts for ${dealsData}`,
                        },
                    ],
                };
            }

            const formattedDeals = features.map(formatDeal);
            const dealsText = `Active alerts for ${dealsData}:\n\n${formattedDeals.join("\n")}`;

            return {
                content: [
                    {
                        type: "text",
                        text: dealsText,
                    },
                ],
            };
        },
    );

    server.tool(
        "get-deal",
        "Get deals by deal ID",
        {
            id: z.string().describe("Deal ID of the deal to retrieve."),
        },
        async ({ id }) => {
            const dealsUrl = `${API_BASE_10xCRM}/deals/${id}`;
            const dealsData = await make10xCRMRequest<DealFeatures>(dealsUrl, authToken);

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
