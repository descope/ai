from fastapi import FastAPI, Depends, Security, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import urllib.request
import httpx

from app.auth.auth import TokenVerifier
from app.auth.auth_config import get_settings

from fastapi_mcp import FastApiMCP, AuthConfig

# Descope imports
from descope import DescopeClient

# We use PyJWKClient, which internally uses Python's built-in urllib.request, which sends requests
# without a standard User-Agent header (e.g., it sends "Python-urllib/3.x").
# Some CDNs or API gateways (like the one serving Descope's JWKS) may block such requests as they resemble bot traffic or security scanners.
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (DescopeFastAPISampleApp)')]
urllib.request.install_opener(opener)

app = FastAPI()
auth = TokenVerifier()
config = get_settings()

# Initialize Descope client
descope_client = DescopeClient(project_id=config.descope_project_id)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class CalendarEventRequest(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: Optional[List[str]] = None

class CalendarReadRequest(BaseModel):
    time_min: Optional[datetime] = None
    time_max: Optional[datetime] = None
    max_results: Optional[int] = 10

def get_outbound_app_token(inbound_token: str, user_id: str) -> str:
    """
    Get the outbound app token from Descope using the inbound app token and user ID.
    """
    try:
        latest_user_token = descope_client.mgmt.outbound_application_by_token.fetch_token(
            inbound_token,
            config.google_outbound_app_id,
            user_id,
        )
        return latest_user_token
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get outbound app token: {str(e)}")

async def make_google_calendar_request(outbound_token: str, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
    """
    Make a direct HTTP request to Google Calendar API using the outbound token.
    """
    base_url = "https://www.googleapis.com/calendar/v3"
    headers = {
        "Authorization": f"Bearer {outbound_token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            response = await client.get(f"{base_url}{endpoint}", headers=headers)
        elif method.upper() == "POST":
            response = await client.post(f"{base_url}{endpoint}", headers=headers, json=data)
        elif method.upper() == "PUT":
            response = await client.put(f"{base_url}{endpoint}", headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = await client.delete(f"{base_url}{endpoint}", headers=headers)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported HTTP method: {method}")
        
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=f"Google Calendar API error: {response.text}")
        
        return response.json()

@app.post("/calendar/events", operation_id="create-calendar-event")
async def create_calendar_event(
    request: CalendarEventRequest, 
    auth_result: Dict[str, Any] = Security(auth)
):
    """
    Create a new calendar event using Google Calendar API.
    
    Parameters
    ----------
    request : CalendarEventRequest
        A Pydantic model containing event details.
    auth_result : Dict[str, Any]
        The authenticated user's token payload.
    
    Returns
    -------
    JSONResponse
        A JSON object containing the created event details.
    """
    try:
        # Extract user ID from auth result
        user_id = auth_result.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in token")
        
        # Get the inbound token from the request context
        # Note: You'll need to modify the auth dependency to return the raw token
        inbound_token = auth_result.get("raw_token")  # This needs to be implemented
        
        # Get outbound app token
        outbound_token = get_outbound_app_token(inbound_token, user_id)
        
        # Prepare event data
        event_data = {
            'summary': request.summary,
            'description': request.description,
            'start': {
                'dateTime': request.start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': request.end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }
        
        if request.location:
            event_data['location'] = request.location
            
        if request.attendees:
            event_data['attendees'] = [{'email': email} for email in request.attendees]
        
        # Create the event using direct HTTP request
        event_result = await make_google_calendar_request(
            outbound_token, 
            "POST", 
            "/calendars/primary/events", 
            event_data
        )
        
        return JSONResponse(content={
            "success": True,
            "event": {
                "id": event_result['id'],
                "summary": event_result['summary'],
                "start": event_result['start'],
                "end": event_result['end'],
                "htmlLink": event_result['htmlLink']
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create calendar event: {str(e)}")

@app.get("/calendar/events", operation_id="list-calendar-events")
async def list_calendar_events(
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: Optional[int] = 10,
    auth_result: Dict[str, Any] = Security(auth)
):
    """
    List calendar events from Google Calendar API.
    
    Parameters
    ----------
    time_min : Optional[datetime]
        Start time for the query (defaults to now).
    time_max : Optional[datetime]
        End time for the query (defaults to 7 days from now).
    max_results : Optional[int]
        Maximum number of events to return (default 10).
    auth_result : Dict[str, Any]
        The authenticated user's token payload.
    
    Returns
    -------
    JSONResponse
        A JSON object containing the list of events.
    """
    try:
        # Extract user ID from auth result
        user_id = auth_result.get("sub")
        print(f"User ID: {user_id}")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found in token")
        
        # Get the inbound token from the request context
        inbound_token = auth_result.get("raw_token")  # This needs to be implemented
        
        # Get outbound app token
        outbound_token = get_outbound_app_token(inbound_token, user_id)
        
        # Set default time range if not provided
        if not time_min:
            time_min = datetime.utcnow()
        if not time_max:
            time_max = time_min + timedelta(days=7)
        
        # Build query parameters
        params = {
            'timeMin': time_min.isoformat() + 'Z',
            'timeMax': time_max.isoformat() + 'Z',
            'maxResults': max_results,
            'singleEvents': 'true',
            'orderBy': 'startTime'
        }
        
        # Convert params to query string
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        
        # Get events using direct HTTP request
        events_result = await make_google_calendar_request(
            outbound_token, 
            "GET", 
            f"/calendars/primary/events?{query_string}"
        )
        
        events = events_result.get('items', [])
        
        # Format events for response
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start': start,
                'end': end,
                'location': event.get('location', ''),
                'htmlLink': event.get('htmlLink', '')
            })
        
        return JSONResponse(content={
            "success": True,
            "events": formatted_events,
            "count": len(formatted_events)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list calendar events: {str(e)}")

mcp = FastApiMCP(
    app,
    name="Google Calendar MCP Server",
    description="MCP Server for Google Calendar operations including creating and reading events.",
    auth_config=AuthConfig(
        custom_oauth_metadata={
            "issuer": HttpUrl(f"{config.descope_api_base_url}/v1/apps/{config.descope_project_id}"),
            "jwks_uri": HttpUrl(f"{config.descope_api_base_url}/{config.descope_project_id}/.well-known/jwks.json"),
            "authorization_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/authorize"),
            "response_types_supported": ["code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/token"),
            "userinfo_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/userinfo"),
            "scopes_supported": ["openid"],
            "claims_supported": [
                "iss", "aud", "iat", "exp", "sub", "name", "email",
                "email_verified", "phone_number", "phone_number_verified",
                "picture", "family_name", "given_name"
            ],
            "revocation_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/revoke"),
            "registration_endpoint": HttpUrl(f"{config.descope_api_base_url}/v1/mgmt/inboundapp/app/{config.descope_project_id}/register"),
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_post"],
            "end_session_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/logout")
        },
        dependencies=[Depends(auth)],
    ),
)

mcp.setup_server()
mcp.mount()