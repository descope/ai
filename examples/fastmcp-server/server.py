import os
import aiohttp
from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import logging

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

auth = BearerAuthProvider(
    jwks_uri=f"{DESCOPE_BASE_URL}/{DESCOPE_PROJECT_ID}/.well-known/jwks.json",
    issuer=f"{DESCOPE_BASE_URL}/v1/apps/{DESCOPE_PROJECT_ID}",
    algorithm="RS256",
)

# FastMCP server for tools with built-in auth
mcp = FastMCP(name="Weather MCP Server", auth=auth)
mcp_app = mcp.http_app(path='/mcp')

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)