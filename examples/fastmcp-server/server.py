import os
import aiohttp
from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import logging
import jwt
import json
from typing import Optional
from contextvars import ContextVar

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

# Get Descope configuration from environment variables
DESCOPE_PROJECT_ID = os.getenv("DESCOPE_PROJECT_ID")
DESCOPE_BASE_URL = os.getenv("DESCOPE_BASE_URL", "https://api.descope.com")

if not DESCOPE_PROJECT_ID:
    raise ValueError("DESCOPE_PROJECT_ID environment variable must be set")

# Context variable to store the current token
current_token: ContextVar[Optional[str]] = ContextVar('current_token', default=None)

class TokenAwareBearerAuthProvider(BearerAuthProvider):
    """Custom auth provider that stores the token for access in tools."""
    
    async def authenticate(self, request: Request) -> bool:
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            # Store token in context for tools to access
            current_token.set(token)
        
        # Call parent authentication
        return await super().authenticate(request)

auth = TokenAwareBearerAuthProvider(
    jwks_uri=f"{DESCOPE_BASE_URL}/{DESCOPE_PROJECT_ID}/.well-known/jwks.json",
    issuer=f"{DESCOPE_BASE_URL}/v1/apps/{DESCOPE_PROJECT_ID}",
    algorithm="RS256",
)

# FastMCP server for tools with built-in auth
mcp = FastMCP(name="Weather MCP Server", auth=auth)
mcp_app = mcp.http_app(path='/mcp')

# Helper function to decode JWT token (for informational purposes only)
def decode_token_info(token: str) -> dict:
    """Decode JWT token to get payload information (without verification)."""
    try:
        # Decode without verification to get payload
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        return {"error": f"Failed to decode token: {str(e)}"}

# Helper function to get current token
def get_current_token() -> Optional[str]:
    """Get the current access token from the request context."""
    return current_token.get()

# Create FastAPI app with FastMCP lifespan
app = FastAPI(lifespan=mcp_app.lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the MCP app at /mcp-server
app.mount("/mcp-server", mcp_app)

# Add the metadata route for OAuth server discovery
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    return {
        "issuer": f"{DESCOPE_BASE_URL}/v1/apps/{DESCOPE_PROJECT_ID}",
        "jwks_uri": f"{DESCOPE_BASE_URL}/{DESCOPE_PROJECT_ID}/.well-known/jwks.json",
        "authorization_endpoint": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/authorize",
        "response_types_supported": ["code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/token",
        "userinfo_endpoint": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/userinfo",
        "scopes_supported": ["openid"],
        "claims_supported": [
            "iss", "aud", "iat", "exp", "sub", "name", "email",
            "email_verified", "phone_number", "phone_number_verified",
            "picture", "family_name", "given_name"
        ],
        "revocation_endpoint": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/revoke",
        "registration_endpoint": f"{DESCOPE_BASE_URL}/v1/mgmt/inboundapp/app/{DESCOPE_PROJECT_ID}/register",
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "end_session_endpoint": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/logout"
    }

# Have to add this manually, since MCPAuth doesn't support this yet
@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "resource_name": "Weather MCP Server",
    }

@app.get("/")
async def read_index():
    return FileResponse("index.html")

# Helper function for making NWS API requests
async def make_nws_request(url: str) -> dict:
    """Make a request to the NWS API."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if not response.ok:
                    raise Exception(f"HTTP error! status: {response.status}")
                return await response.json()
        except Exception as e:
            print(f"Error making NWS request: {e}")
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature.get("properties", {})
    return "\n".join([
        f"Event: {props.get('event', 'Unknown')}",
        f"Area: {props.get('areaDesc', 'Unknown')}",
        f"Severity: {props.get('severity', 'Unknown')}",
        f"Status: {props.get('status', 'Unknown')}",
        f"Headline: {props.get('headline', 'No headline')}",
        "---"
    ])

@mcp.tool
async def get_alerts(state: str) -> str:
    """Get weather alerts for a state.
    Args:
        state: Two-letter state code (e.g. CA, NY)
    """
    state_code = state.upper()
    alerts_url = f"{NWS_API_BASE}/alerts?area={state_code}"
    alerts_data = await make_nws_request(alerts_url)

    if not alerts_data:
        return "Failed to retrieve alerts data"

    features = alerts_data.get("features", [])
    if not features:
        return f"No active alerts for {state_code}"

    formatted_alerts = [format_alert(feature) for feature in features]
    return f"Active alerts for {state_code}:\n\n{''.join(formatted_alerts)}"

@mcp.tool
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.
    Args:
        latitude: Latitude of the location (-90 to 90)
        longitude: Longitude of the location (-180 to 180)
    """
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return "Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180."

    # Get grid point data
    points_url = f"{NWS_API_BASE}/points/{latitude:.4f},{longitude:.4f}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return f"Failed to retrieve grid point data for coordinates: {latitude}, {longitude}. This location may not be supported by the NWS API (only US locations are supported)."

    forecast_url = points_data.get("properties", {}).get("forecast")
    if not forecast_url:
        return "Failed to get forecast URL from grid point data"

    # Get forecast data
    forecast_data = await make_nws_request(forecast_url)
    if not forecast_data:
        return "Failed to retrieve forecast data"

    periods = forecast_data.get("properties", {}).get("periods", [])
    if not periods:
        return "No forecast periods available"

    # Format forecast periods
    formatted_forecast = []
    for period in periods:
        period_text = "\n".join([
            f"{period.get('name', 'Unknown')}:",
            f"Temperature: {period.get('temperature', 'Unknown')}°{period.get('temperatureUnit', 'F')}",
            f"Wind: {period.get('windSpeed', 'Unknown')} {period.get('windDirection', '')}",
            f"{period.get('shortForecast', 'No forecast available')}",
            "---"
        ])
        formatted_forecast.append(period_text)

    return f"Forecast for {latitude}, {longitude}:\n\n{''.join(formatted_forecast)}"

@mcp.tool
async def get_token_info() -> str:
    """Get information about the current access token being used for authentication.
    This tool demonstrates how to access token information in your MCP tools.
    """
    # Note: In a real implementation, you would get the token from the request context
    # This is a demonstration of what token information looks like
    
    result = "Token Information:\n\n"
    result += "This tool shows what information is available in the access token.\n"
    result += "In a real implementation, you would extract the token from the request context.\n\n"
    
    result += "Typical JWT token payload includes:\n"
    result += "- iss (issuer): The token issuer (Descope)\n"
    result += "- aud (audience): The intended audience\n"
    result += "- exp (expiration): Token expiration time\n"
    result += "- iat (issued at): Token issuance time\n"
    result += "- sub (subject): User identifier\n"
    result += "- name: User's display name\n"
    result += "- email: User's email address\n"
    result += "- scopes: Granted permissions\n\n"
    
    result += "To access the actual token in your tools, you would need to:\n"
    result += "1. Extract the Authorization header from the request\n"
    result += "2. Parse the Bearer token\n"
    result += "3. Decode the JWT payload (for informational purposes)\n"
    result += "4. Use the token information as needed\n\n"
    
    result += "Example token structure:\n"
    example_token = {
        "iss": f"{DESCOPE_BASE_URL}/v1/apps/{DESCOPE_PROJECT_ID}",
        "aud": "your_application",
        "exp": 1234567890,
        "iat": 1234567890,
        "sub": "user_123",
        "name": "John Doe",
        "email": "john@example.com",
        "scopes": ["openid", "profile", "email"]
    }
    result += json.dumps(example_token, indent=2)
    
    return result

@mcp.tool
async def get_user_info() -> str:
    """Get information about the current user using the access token.
    This demonstrates how to use the access token with Descope APIs.
    """
    token = get_current_token()
    if not token:
        return "Error: No access token available"
    
    try:
        # Decode token to get user information
        token_info = decode_token_info(token)
        
        result = "Current User Information:\n\n"
        result += f"User ID: {token_info.get('sub', 'N/A')}\n"
        result += f"Name: {token_info.get('name', 'N/A')}\n"
        result += f"Email: {token_info.get('email', 'N/A')}\n"
        result += f"Token Issuer: {token_info.get('iss', 'N/A')}\n"
        result += f"Token Expires: {token_info.get('exp', 'N/A')}\n"
        result += f"Scopes: {', '.join(token_info.get('scope', '').split()) if token_info.get('scope') else 'N/A'}\n\n"
        
        result += "Token Payload (decoded):\n"
        result += json.dumps(token_info, indent=2)
        
        return result
    except Exception as e:
        return f"Error getting user info: {str(e)}"

@mcp.tool
async def validate_token_with_descope() -> str:
    """Validate the current access token with Descope's userinfo endpoint.
    This demonstrates making authenticated requests to Descope APIs.
    """
    token = get_current_token()
    if not token:
        return "Error: No access token available"
    
    try:
        # Make request to Descope's userinfo endpoint
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        userinfo_url = f"{DESCOPE_BASE_URL}/oauth2/v1/apps/userinfo"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(userinfo_url, headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    
                    result = "Token Validation with Descope: SUCCESS\n\n"
                    result += "User Information from Descope API:\n"
                    result += f"User ID: {user_data.get('sub', 'N/A')}\n"
                    result += f"Name: {user_data.get('name', 'N/A')}\n"
                    result += f"Email: {user_data.get('email', 'N/A')}\n"
                    result += f"Email Verified: {user_data.get('email_verified', 'N/A')}\n"
                    result += f"Picture: {user_data.get('picture', 'N/A')}\n\n"
                    
                    result += "Full Response:\n"
                    result += json.dumps(user_data, indent=2)
                    
                    return result
                else:
                    error_text = await response.text()
                    return f"Token validation failed. Status: {response.status}, Error: {error_text}"
                    
    except Exception as e:
        return f"Error validating token with Descope: {str(e)}"

@mcp.tool
async def call_descope_api_with_token(api_endpoint: str = "userinfo") -> str:
    """Make a custom API call to Descope using the current access token.
    Args:
        api_endpoint: The Descope API endpoint to call (default: userinfo)
    """
    token = get_current_token()
    if not token:
        return "Error: No access token available"
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Map common endpoints
        endpoint_map = {
            "userinfo": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/userinfo",
            "introspect": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/introspect",
            "revoke": f"{DESCOPE_BASE_URL}/oauth2/v1/apps/revoke"
        }
        
        url = endpoint_map.get(api_endpoint.lower(), api_endpoint)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                result = f"API Call to: {url}\n"
                result += f"Status: {response.status}\n\n"
                
                if response.status == 200:
                    data = await response.json()
                    result += "Response:\n"
                    result += json.dumps(data, indent=2)
                else:
                    error_text = await response.text()
                    result += f"Error: {error_text}"
                
                return result
                    
    except Exception as e:
        return f"Error calling Descope API: {str(e)}"

@mcp.tool
async def exchange_token_for_descope_user() -> str:
    """Exchange the access token for Descope user information using Descope SDK.
    This demonstrates using the token with Descope's Python SDK.
    """
    token = get_current_token()
    if not token:
        return "Error: No access token available"
    
    try:
        # Note: This would require the Descope SDK to be installed
        # For now, we'll show the concept and make a direct API call
        
        result = "Token Exchange for Descope User:\n\n"
        result += "Current Access Token (first 50 chars):\n"
        result += f"{token[:50]}...\n\n"
        
        result += "To use this token with Descope SDK:\n"
        result += "1. Initialize DescopeClient with your project ID\n"
        result += "2. Use the token for authenticated requests\n"
        result += "3. Access user information and permissions\n\n"
        
        # Decode token to show what information is available
        token_info = decode_token_info(token)
        result += "Available Token Information:\n"
        result += json.dumps(token_info, indent=2)
        
        return result
        
    except Exception as e:
        return f"Error exchanging token: {str(e)}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)