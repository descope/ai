
export function getDescopeOAuthEndpointUrl(baseUrl: string, endpoint: string): string {
	return `${baseUrl}/oauth2/v1/apps/${endpoint}`;
}
