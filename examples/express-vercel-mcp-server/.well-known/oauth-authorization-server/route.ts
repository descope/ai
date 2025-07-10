export async function GET() {
  const baseUrl = process.env.DESCOPE_BASE_URL || "https://api.descope.com";

  return Response.json(
    {
      issuer: `${baseUrl}/v1/apps/${process.env.DESCOPE_PROJECT_ID}`,
      jwks_uri: `${baseUrl}/${process.env.DESCOPE_PROJECT_ID}/.well-known/jwks.json`,
      authorization_endpoint: `${baseUrl}/oauth2/v1/apps/authorize`,
      response_types_supported: ["code"],
      subject_types_supported: ["public"],
      id_token_signing_alg_values_supported: ["RS256"],
      code_challenge_methods_supported: ["S256"],
      token_endpoint: `${baseUrl}/oauth2/v1/apps/token`,
      userinfo_endpoint: `${baseUrl}/oauth2/v1/apps/userinfo`,
      scopes_supported: ["openid"],
      claims_supported: [
        "iss",
        "aud",
        "iat",
        "exp",
        "sub",
        "name",
        "email",
        "email_verified",
        "phone_number",
        "phone_number_verified",
        "picture",
        "family_name",
        "given_name",
      ],
      revocation_endpoint: `${baseUrl}/oauth2/v1/apps/revoke`,
      registration_endpoint: `${baseUrl}/v1/mgmt/inboundapp/app/${process.env.DESCOPE_PROJECT_ID}/register`,
    },
    {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, mcp-protocol-version",
      },
    }
  );
}

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, mcp-protocol-version",
      "Content-Type": "application/json",
    },
  });
}
