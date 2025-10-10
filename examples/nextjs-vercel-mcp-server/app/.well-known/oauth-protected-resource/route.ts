import {
  protectedResourceHandler,
  metadataCorsOptionsRequestHandler,
} from "mcp-handler";

const DESCOPE_BASE_URL =
  process.env.DESCOPE_BASE_URL || "https://api.descope.com";
const DESCOPE_PROJECT_ID = process.env.NEXT_PUBLIC_DESCOPE_PROJECT_ID;

const handler = protectedResourceHandler({
  authServerUrls: [`${DESCOPE_BASE_URL}/v1/apps/${DESCOPE_PROJECT_ID}`],
});

const optionsHandler = metadataCorsOptionsRequestHandler();

export const GET = handler;
export const OPTIONS = metadataCorsOptionsRequestHandler();
