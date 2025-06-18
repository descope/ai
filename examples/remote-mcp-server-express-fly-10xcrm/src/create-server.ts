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

interface ContactSearchResponse {
    contacts: ContactFeatures[];
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
        "get-contacts-search",
        "Search contacts with optional filters and pagination",
        {
            query: z.string().describe("The name or email of the contact to retrieve.").optional(),
            company: z.string().describe("The company of the contact to retrieve.").optional(),
            status: z.string().describe("The status of the contact to retrieve.").optional(),
        },
        async ( {query, company, status} ) => {
            const params = new URLSearchParams();
            if (query != undefined && query != "undefined") params.append("query", query);
            if (company != undefined && company != "undefined") params.append("company", company);
            if (status != undefined && status != "undefined") params.append("status", status);
            const contactsUrl = `${API_BASE_10xCRM}/contacts/search?${params.toString()}`;
            const contactsData = await make10xCRMRequest<ContactSearchResponse>(contactsUrl, authToken);
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

            const features = contactsData.contacts || [];
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
        },
        async ({ id }) => {
            const contactsUrl = `${API_BASE_10xCRM}/contacts/${id}`;
            const contactsData = await make10xCRMRequest<ContactFeatures>(contactsUrl, authToken);
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
            search: z.string().describe("Customer name or deal name of the deals to retrieve").optional(),
            page: z.string().describe("Page from which to retrieve deals").optional(),
            limit: z.string().describe("Limit from which to retrieve deals").optional(),
            stage: z.string().describe("Stage of the deals to retrieve").optional(),

        },
        async ({ search, page, limit, stage }) => {
            const params = new URLSearchParams();
            if (search != undefined && search != "undefined") params.append("search", search);
            if (page != undefined && page != "undefined") params.append("page", page);
            if (limit != undefined && limit != "undefined") params.append("limit", limit);
            if (stage != undefined && stage != "undefined") params.append("stage", stage);
            let dealsUrl = `${API_BASE_10xCRM}/deals?${params.toString()}`;
            if (params == null) {
                dealsUrl = `${API_BASE_10xCRM}/deals`;
            }
            
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
        "list-contacts",
        "List all contacts",
        {
        },
        async ({}) => {
            const contactsUrl = `${API_BASE_10xCRM}/contacts`;
            const contactsData = await make10xCRMRequest<ContactResponse>(contactsUrl, authToken);

            if (!contactsData) {
                return {
                    content: [
                        {
                            type: "text",
                            text: "Failed to retrieve contacts data",
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
                            text: `No contacts found`,
                        },
                    ],
                };
            }

            const formattedContacts = features.map(formatContact);
            const contactsText = `Active contacts:\n\n${formattedContacts.join("\n")}`;

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


    return { server };
}
