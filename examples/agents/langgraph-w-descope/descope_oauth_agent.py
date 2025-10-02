import os
import asyncio
import webbrowser
import json
import urllib.parse
import base64
import hashlib
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Load environment variables
load_dotenv()

class TokenManager:
    """Manages OAuth tokens with automatic refresh capability"""
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.scopes = []
        self.client_id = None
        self.token_endpoint = None
    
    def set_token_info(self, access_token, refresh_token=None, expires_in=None, scopes=None, client_id=None, token_endpoint=None):
        """Set token information and calculate expiration"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.token_endpoint = token_endpoint
        self.scopes = scopes or []
        
        if expires_in:
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        else:
            # Default to 1 hour if no expiration provided
            self.token_expires_at = datetime.now() + timedelta(hours=1)
        
        print(f"🔑 Token set, expires at: {self.token_expires_at}")
    
    def is_token_expired(self, buffer_seconds=300):
        """Check if token is expired or will expire soon (with buffer)"""
        if not self.token_expires_at:
            return True
        
        # Consider token expired if it expires within buffer_seconds (default 5 minutes)
        return datetime.now() + timedelta(seconds=buffer_seconds) >= self.token_expires_at
    
    def get_valid_token(self):
        """Get a valid token, refresh if needed"""
        if not self.access_token or self.is_token_expired():
            print("🔄 Token expired or missing, refresh needed")
            return None
        
        time_left = (self.token_expires_at - datetime.now()).total_seconds()
        print(f"✅ Token valid, expires in {time_left:.0f} seconds")
        return self.access_token
    
    async def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        print(f"🔄 Attempting token refresh...")
        print(f"   Refresh token: {'✅ Present' if self.refresh_token else '❌ Missing'}")
        print(f"   Token endpoint: {'✅ Present' if self.token_endpoint else '❌ Missing'}")
        print(f"   Client ID: {'✅ Present' if self.client_id else '❌ Missing'}")
        
        if not self.refresh_token:
            print("❌ Cannot refresh token - no refresh token available")
            return False
        
        if not self.token_endpoint:
            print("❌ Cannot refresh token - no token endpoint available")
            return False
            
        if not self.client_id:
            print("❌ Cannot refresh token - no client ID available")
            return False
        
        try:
            print("🔄 Refreshing access token...")
            
            async with httpx.AsyncClient() as client:
                token_data = {
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': self.client_id
                }
                
                response = await client.post(
                    self.token_endpoint,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    token_response = response.json()
                    
                    # Update token info
                    new_access_token = token_response.get('access_token')
                    new_refresh_token = token_response.get('refresh_token', self.refresh_token)
                    expires_in = token_response.get('expires_in', 3600)
                    
                    self.set_token_info(
                        new_access_token,
                        new_refresh_token,
                        expires_in,
                        self.scopes,
                        self.client_id,
                        self.token_endpoint
                    )
                    
                    print(f"✅ Token refreshed successfully, expires in {expires_in} seconds")
                    return True
                else:
                    print(f"❌ Token refresh failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error refreshing token: {e}")
            return False

# Global token manager instance
token_manager = TokenManager()

# Set your API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize the model
model = ChatOpenAI(model="gpt-4o")

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to receive OAuth callback"""
    
    def do_GET(self):
        """Handle OAuth callback"""
        if self.path.startswith('/callback'):
            # Parse the callback URL
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Extract authorization code or token
            if 'code' in query_params:
                auth_code = query_params['code'][0]
                print(f"✅ Received authorization code: {auth_code}")
                
                # Store the code for the main process to use
                OAuthCallbackHandler.auth_code = auth_code
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html_content = """
                <html>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <script>setTimeout(() => window.close(), 3000);</script>
                </body>
                </html>
                """
                self.wfile.write(html_content.encode('utf-8'))
            elif 'access_token' in query_params:
                access_token = query_params['access_token'][0]
                print(f"✅ Received access token: {access_token[:20]}...")
                
                # Store the token
                OAuthCallbackHandler.access_token = access_token
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html_content = """
                <html>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <script>setTimeout(() => window.close(), 3000);</script>
                </body>
                </html>
                """
                self.wfile.write(html_content.encode('utf-8'))
            else:
                # Handle error
                error = query_params.get('error', ['Unknown error'])[0]
                print(f"❌ OAuth error: {error}")
                
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_html = f"""
                <html>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Error: {error}</p>
                    <p>Please check the terminal for more details.</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

async def discover_descope_endpoints(mcp_server_url):
    """Discover Descope OAuth endpoints for the MCP server"""
    print(f"🔍 Discovering Descope OAuth endpoints for: {mcp_server_url}")
    
    # Common Descope OAuth endpoints
    base_url = mcp_server_url.replace('/mcp', '').rstrip('/')
    
    descope_endpoints = {
        'authorization_endpoint': f"{base_url}/oauth/authorize",
        'token_endpoint': f"{base_url}/oauth/token",
        'registration_endpoint': f"{base_url}/register",
        'well_known': f"{base_url}/.well-known/oauth-authorization-server",
        'scopes_supported': ['outbound.token.fetch'],  # Always include this as default
        'default_scope': 'outbound.token.fetch'  # Always use this as the primary scope
    }
    
    # Try to discover the actual endpoints
    try:
        async with httpx.AsyncClient() as client:
            # Try the well-known endpoint first
            try:
                response = await client.get(descope_endpoints['well_known'], timeout=5.0)
                if response.status_code == 200:
                    discovery_data = response.json()
                    print(f"✅ Found OAuth discovery endpoint")
                    print(f"📋 Discovery data: {json.dumps(discovery_data, indent=2)}")
                    
                    # Update endpoints with discovered values
                    if 'authorization_endpoint' in discovery_data:
                        descope_endpoints['authorization_endpoint'] = discovery_data['authorization_endpoint']
                    if 'token_endpoint' in discovery_data:
                        descope_endpoints['token_endpoint'] = discovery_data['token_endpoint']
                    if 'registration_endpoint' in discovery_data:
                        descope_endpoints['registration_endpoint'] = discovery_data['registration_endpoint']
                    if 'scopes_supported' in discovery_data:
                        # Always ensure outbound.token.fetch is included in supported scopes
                        discovered_scopes = discovery_data['scopes_supported']
                        if 'outbound.token.fetch' not in discovered_scopes:
                            discovered_scopes.insert(0, 'outbound.token.fetch')
                        descope_endpoints['scopes_supported'] = discovered_scopes
                        print(f"✅ Discovered scopes: {discovered_scopes}")
                        print(f"🎯 Default scope: outbound.token.fetch")
                    
                    # Check if server supports refresh tokens
                    if 'grant_types_supported' in discovery_data:
                        grant_types = discovery_data['grant_types_supported']
                        supports_refresh = 'refresh_token' in grant_types
                        descope_endpoints['supports_refresh_token'] = supports_refresh
                        print(f"🔄 Refresh token support: {'✅ Yes' if supports_refresh else '❌ No'}")
                        if not supports_refresh:
                            print("⚠️ OAuth server does not support refresh tokens - will need re-authentication on expiration")
                    else:
                        descope_endpoints['supports_refresh_token'] = True  # Assume yes if not specified
                        print("🔄 Refresh token support: ✅ Assumed (not specified)")
                        
            except (httpx.RequestError, httpx.TimeoutException):
                print("⚠️ Well-known endpoint not available, using default Descope endpoints")
            
            # Verify endpoints are accessible
            for name, url in descope_endpoints.items():
                if name not in ['well_known', 'scopes_supported']:
                    try:
                        # Just check if endpoint exists (HEAD request)
                        response = await client.head(url, timeout=5.0)
                        if response.status_code in [200, 405, 400]:  # 405 = Method Not Allowed (but endpoint exists)
                            print(f"✅ {name}: {url}")
                        else:
                            print(f"⚠️ {name}: {url} (status: {response.status_code})")
                    except (httpx.RequestError, httpx.TimeoutException):
                        print(f"❌ {name}: {url} (not accessible)")
    
    except Exception as e:
        print(f"❌ Error during endpoint discovery: {e}")
    
    return descope_endpoints

async def get_valid_bearer_token(oauth_endpoints, callback_url):
    """Get a valid bearer token, refreshing if necessary"""
    # Check if we have a valid token
    valid_token = token_manager.get_valid_token()
    
    if valid_token:
        return valid_token
    
    # Try to refresh the token
    if token_manager.refresh_token:
        refresh_success = await token_manager.refresh_access_token()
        if refresh_success:
            return token_manager.get_valid_token()
    
    # If refresh fails or no refresh token, need to re-authenticate
    print("🔄 Token refresh failed, starting new OAuth flow...")
    
    # Always revert to outbound.token.fetch as the primary scope
    primary_scope = 'outbound.token.fetch'
    
    print(f"🎯 Reverting to primary scope for re-authentication: {primary_scope}")
    
    # Perform new OAuth flow with primary scope
    new_token = await perform_descope_oauth_flow_with_scopes(oauth_endpoints, callback_url, [primary_scope])
    
    if new_token:
        return new_token
    else:
        print("❌ Failed to get new token through OAuth flow")
        return None

def fix_tool_schema(schema):
    """Fix common schema issues in tool definitions"""
    if not isinstance(schema, dict):
        return schema
    
    # Create a deep copy to avoid modifying the original
    fixed_schema = json.loads(json.dumps(schema))
    
    def fix_schema_recursive(obj):
        if isinstance(obj, dict):
            # Fix array schemas missing items
            if obj.get('type') == 'array' and 'items' not in obj:
                obj['items'] = {'type': 'string'}  # Default to string items
            
            # Fix object schemas missing properties
            if obj.get('type') == 'object' and 'properties' not in obj:
                obj['properties'] = {}
            
            # Recursively fix nested objects
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    fix_schema_recursive(value)
        
        elif isinstance(obj, list):
            # Fix array schemas in lists
            for item in obj:
                if isinstance(item, (dict, list)):
                    fix_schema_recursive(item)
    
    fix_schema_recursive(fixed_schema)
    return fixed_schema

async def handle_auth_error_and_reauth(oauth_endpoints, current_scopes, callback_url, error_code=None):
    """Handle 400, 401, or 403 errors by requesting additional scopes"""
    print(f"🔐 {error_code or 'Authentication'} Error detected - requesting additional scopes...")
    
    # Get current scopes and add missing ones
    available_scopes = oauth_endpoints.get('scopes_supported', ['outbound.token.fetch'])
    missing_scopes = [scope for scope in available_scopes if scope not in current_scopes]
    
    if not missing_scopes:
        print("⚠️ No additional scopes available")
        return None
    
    print(f"📋 Current scopes: {current_scopes}")
    print(f"📋 Available scopes: {available_scopes}")
    print(f"📋 Missing scopes: {missing_scopes}")
    
    # Request all available scopes (progressive scoping)
    new_scopes = list(set(current_scopes + missing_scopes))
    print(f"🔄 Requesting scopes: {new_scopes}")
    
    # Perform OAuth flow with expanded scopes
    return await perform_descope_oauth_flow_with_scopes(oauth_endpoints, callback_url, new_scopes)

async def perform_descope_oauth_flow_with_scopes(oauth_endpoints, callback_url, requested_scopes):
    """Perform OAuth flow with specific scopes"""
    print(f"🔐 Starting OAuth flow with scopes: {requested_scopes}")
    
    # Start local callback server - try different ports if needed
    callback_ports = [8081, 8082, 8083, 8084, 8085]
    server = None
    callback_port = None
    callback_url = None
    
    for port in callback_ports:
        try:
            server = HTTPServer(('localhost', port), OAuthCallbackHandler)
            callback_port = port
            callback_url = f"http://localhost:{port}/callback"
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {port} is in use, trying next port...")
                continue
            else:
                raise e
    
    if not server:
        print("❌ Could not find an available port for the callback server")
        return None
    
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print(f"🌐 Started callback server on port {callback_port}")
    
    try:
        # Register client dynamically with expanded scopes
        client_info = await register_descope_client_with_scopes(oauth_endpoints, callback_url, requested_scopes)
        if not client_info:
            print("❌ Failed to register client with expanded scopes")
            return None
        
        client_id = client_info.get('client_id')
        print(f"✅ Using dynamically registered client ID: {client_id}")
        
        auth_endpoint = oauth_endpoints['authorization_endpoint']
        token_endpoint = oauth_endpoints.get('token_endpoint')
        
        # Generate PKCE parameters
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        # Build authorization URL with expanded scopes
        scope_string = ' '.join(requested_scopes)
        auth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': callback_url,
            'scope': scope_string,
            'state': 'langgraph-agent-state',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'consent'  # Force consent screen
        }
        
        auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(auth_params)}"
        print(f"🔗 Authorization URL: {auth_url}")
        
        # Open browser for authorization
        print("🌐 Opening browser for expanded scope consent...")
        webbrowser.open(auth_url)
        
        # Wait for callback
        print("⏳ Waiting for OAuth callback...")
        print("   Please complete the authentication in your browser.")
        
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()
        
        while not hasattr(OAuthCallbackHandler, 'auth_code') and not hasattr(OAuthCallbackHandler, 'access_token'):
            if asyncio.get_event_loop().time() - start_time > timeout:
                print("❌ OAuth timeout - no response received")
                return None
            await asyncio.sleep(1)
        
        # Get the authorization code or token
        if hasattr(OAuthCallbackHandler, 'access_token'):
            bearer_token = OAuthCallbackHandler.access_token
            print("✅ Received access token directly")
            
            # Store token info in token manager (for direct token responses)
            token_manager.set_token_info(
                access_token=bearer_token,
                refresh_token=None,  # No refresh token for direct responses
                expires_in=3600,  # Default 1 hour
                scopes=requested_scopes,
                client_id=client_id,
                token_endpoint=token_endpoint
            )
            
        elif hasattr(OAuthCallbackHandler, 'auth_code'):
            auth_code = OAuthCallbackHandler.auth_code
            print(f"✅ Received authorization code: {auth_code}")
            
            # Exchange code for token
            if token_endpoint:
                bearer_token = await exchange_code_for_descope_token(auth_code, token_endpoint, callback_url, client_id, code_verifier)
                if not bearer_token:
                    return None
            else:
                print("❌ No token endpoint found to exchange authorization code")
                return None
        else:
            print("❌ No authorization code or token received")
            return None
        
        print(f"✅ Successfully obtained Descope bearer token with expanded scopes: {bearer_token[:20]}...")
        
        # Log token manager status
        if token_manager.refresh_token:
            print(f"🔄 Refresh token available: {token_manager.refresh_token[:20]}...")
        else:
            print("⚠️ No refresh token available - will need re-authentication on expiration")
        
        return bearer_token
        
    finally:
        # Shutdown callback server
        server.shutdown()
        server_thread.join(timeout=1)

async def register_descope_client_with_scopes(oauth_endpoints, callback_url, requested_scopes):
    """Register a new client with Descope using specific scopes"""
    print("📝 Registering client with expanded scopes...")
    
    registration_endpoint = oauth_endpoints.get('registration_endpoint')
    if not registration_endpoint:
        print("❌ No registration endpoint found")
        return None
    
    # Use the first scope as the primary scope (progressive scoping revert)
    primary_scope = requested_scopes[0] if requested_scopes else 'tool1'
    print(f"🎯 Primary scope (for DCR revert): {primary_scope}")
    
    # Client registration payload
    registration_data = {
        "client_name": "LangGraph MCP Agent (Expanded Scopes)",
        "redirect_uris": [callback_url],
        "response_types": ["code"],
        "grant_types": ["authorization_code"],
        "token_endpoint_auth_method": "none",  # Public client
        "scope": primary_scope  # Use primary scope for DCR
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"📤 Registering client at: {registration_endpoint}")
            print(f"📋 Registration data: {json.dumps(registration_data, indent=2)}")
            
            response = await client.post(
                registration_endpoint,
                json=registration_data,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            
            print(f"📥 Registration response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                client_info = response.json()
                print(f"✅ Client registered successfully!")
                print(f"📋 Client info: {json.dumps(client_info, indent=2)}")
                return client_info
            else:
                print(f"❌ Registration failed: {response.status_code}")
                print(f"📋 Response: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error during client registration: {e}")
        return None

async def register_descope_client(oauth_endpoints, callback_url):
    """Register a new client with Descope using dynamic client registration"""
    print("📝 Registering client with Descope...")
    
    registration_endpoint = oauth_endpoints.get('registration_endpoint')
    if not registration_endpoint:
        print("❌ No registration endpoint found")
        return None
    
    # Client registration payload - don't specify scope, let server decide
    registration_data = {
        "client_name": "LangGraph MCP Agent",
        "redirect_uris": [callback_url],
        "response_types": ["code"],
        "grant_types": ["authorization_code"],
        "token_endpoint_auth_method": "none"  # Public client
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"📤 Registering client at: {registration_endpoint}")
            print(f"📋 Registration data: {json.dumps(registration_data, indent=2)}")
            
            response = await client.post(
                registration_endpoint,
                json=registration_data,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            
            print(f"📥 Registration response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                client_info = response.json()
                print(f"✅ Client registered successfully!")
                print(f"📋 Client info: {json.dumps(client_info, indent=2)}")
                return client_info
            else:
                print(f"❌ Registration failed: {response.status_code}")
                print(f"📋 Response: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error during client registration: {e}")
        return None

async def perform_descope_oauth_flow(oauth_endpoints, mcp_server_url):
    """Perform Descope OAuth flow"""
    print("🔐 Starting Descope OAuth flow...")
    
    # Start local callback server - try different ports if needed
    callback_ports = [8081, 8082, 8083, 8084, 8085]
    server = None
    callback_port = None
    callback_url = None
    
    for port in callback_ports:
        try:
            server = HTTPServer(('localhost', port), OAuthCallbackHandler)
            callback_port = port
            callback_url = f"http://localhost:{port}/callback"
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {port} is in use, trying next port...")
                continue
            else:
                raise e
    
    if not server:
        print("❌ Could not find an available port for the callback server")
        return None
    
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print(f"🌐 Started callback server on port {callback_port}")
    
    try:
        # Register client dynamically
        client_info = await register_descope_client(oauth_endpoints, callback_url)
        if not client_info:
            print("❌ Failed to register client, falling back to hardcoded client ID")
            client_id = "UDMwcHlITndWcjNzTzVjUFQ4N2hPUVlmNkxmVzpUUEEzM1F1b1hScnp0RHRFTWlvdFZRbUs0MmQ4Wmc="
            # Always use outbound.token.fetch as the default scope
            default_scope = 'outbound.token.fetch'
        else:
            client_id = client_info.get('client_id')
            print(f"✅ Using dynamically registered client ID: {client_id}")
            
            # Always use outbound.token.fetch as the default scope
            default_scope = 'outbound.token.fetch'
            print(f"🎯 Using default scope: {default_scope}")
        
        auth_endpoint = oauth_endpoints['authorization_endpoint']
        token_endpoint = oauth_endpoints.get('token_endpoint')
        
        print(f"🔗 Authorization endpoint: {auth_endpoint}")
        if token_endpoint:
            print(f"🔗 Token endpoint: {token_endpoint}")
        
        # Generate PKCE parameters
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        print(f"🔐 Generated PKCE code_challenge: {code_challenge}")
        
        # Build authorization URL with Descope-specific parameters including PKCE
        auth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': callback_url,
            'scope': default_scope,
            'state': 'langgraph-agent-state',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'login'  # Descope-specific parameter
        }
        
        auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(auth_params)}"
        print(f"🔗 Authorization URL: {auth_url}")
        
        # Open browser for authorization
        print("🌐 Opening browser for Descope authentication...")
        webbrowser.open(auth_url)
        
        # Wait for callback
        print("⏳ Waiting for OAuth callback...")
        print("   Please complete the authentication in your browser.")
        
        # Wait for authorization code or token
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()
        
        while not hasattr(OAuthCallbackHandler, 'auth_code') and not hasattr(OAuthCallbackHandler, 'access_token'):
            if asyncio.get_event_loop().time() - start_time > timeout:
                print("❌ OAuth timeout - no response received")
                return None
            
            await asyncio.sleep(1)
        
        # Get the authorization code or token
        if hasattr(OAuthCallbackHandler, 'access_token'):
            bearer_token = OAuthCallbackHandler.access_token
            print("✅ Received access token directly")
            
            # Store token info in token manager (for direct token responses)
            token_manager.set_token_info(
                access_token=bearer_token,
                refresh_token=None,  # No refresh token for direct responses
                expires_in=3600,  # Default 1 hour
                scopes=oauth_endpoints.get('scopes_supported', ['tool1']),
                client_id=client_id,
                token_endpoint=token_endpoint
            )
            
        elif hasattr(OAuthCallbackHandler, 'auth_code'):
            auth_code = OAuthCallbackHandler.auth_code
            print(f"✅ Received authorization code: {auth_code}")
            
            # Exchange code for token
            if token_endpoint:
                bearer_token = await exchange_code_for_descope_token(auth_code, token_endpoint, callback_url, client_id, code_verifier)
                if not bearer_token:
                    return None
            else:
                print("❌ No token endpoint found to exchange authorization code")
                return None
        else:
            print("❌ No authorization code or token received")
            return None
        
        print(f"✅ Successfully obtained Descope bearer token: {bearer_token[:20]}...")
        
        # Log token manager status
        if token_manager.refresh_token:
            print(f"🔄 Refresh token available: {token_manager.refresh_token[:20]}...")
        else:
            print("⚠️ No refresh token available - will need re-authentication on expiration")
        
        return bearer_token
        
    finally:
        # Shutdown callback server
        server.shutdown()
        server_thread.join(timeout=1)

async def exchange_code_for_descope_token(auth_code, token_endpoint, callback_url, client_id, code_verifier):
    """Exchange authorization code for Descope access token with PKCE"""
    print("🔄 Exchanging authorization code for Descope access token with PKCE...")
    
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': callback_url,
                'client_id': client_id,
                'code_verifier': code_verifier
            }
            
            response = await client.post(
                token_endpoint,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            print(f"📡 Token exchange response: {response.status_code}")
            
            if response.status_code == 200:
                token_response = response.json()
                print(f"📋 Token response: {json.dumps(token_response, indent=2)}")
                
                if 'access_token' in token_response:
                    access_token = token_response['access_token']
                    refresh_token = token_response.get('refresh_token')
                    expires_in = token_response.get('expires_in')
                    
                    # Store token info in token manager
                    token_manager.set_token_info(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_in=expires_in,
                        scopes=token_response.get('scope', '').split(),
                        client_id=client_id,
                        token_endpoint=token_endpoint
                    )
                    
                    return access_token
                else:
                    print(f"❌ No access_token in response")
                    return None
            else:
                print(f"❌ Token exchange failed: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error during token exchange: {e}")
        return None

async def test_bearer_token_validity(mcp_server_url, bearer_token):
    """Test if bearer token is valid by making a simple request"""
    print("🔍 Testing bearer token validity...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Try different endpoints to test token validity
            test_urls = [
                mcp_server_url.replace('/mcp', '/health'),
                mcp_server_url.replace('/mcp', '/status'),
                mcp_server_url.replace('/mcp', '/ping'),
                mcp_server_url  # Try the MCP endpoint directly
            ]
            
            for test_url in test_urls:
                try:
                    response = await client.get(
                        test_url,
                        headers={"Authorization": f"Bearer {bearer_token}"},
                        timeout=5.0
                    )
                    print(f"📡 {test_url}: {response.status_code}")
                    
                    if response.status_code == 401:
                        print("🚨 Bearer token is invalid or expired")
                        return False
                    elif response.status_code == 200:
                        print("✅ Bearer token appears valid")
                        return True
                    elif response.status_code == 404:
                        print(f"⚠️ Endpoint not found: {test_url}")
                        continue
                    else:
                        print(f"⚠️ Unexpected response from {test_url}: {response.status_code}")
                        continue
                        
                except Exception as e:
                    print(f"⚠️ Error testing {test_url}: {e}")
                    continue
            
            print("⚠️ Could not determine token validity - no endpoints responded")
            return None  # Unknown status
            
    except Exception as e:
        print(f"❌ Error testing token validity: {e}")
        return False

async def test_descope_mcp_connection(mcp_server_url, bearer_token):
    """Test MCP connection using Descope bearer token"""
    print("🔗 Testing MCP connection with Descope bearer token...")
    
    # First, test if the bearer token is valid
    token_valid = await test_bearer_token_validity(mcp_server_url, bearer_token)
    
    if token_valid is False:
        print("❌ Bearer token is invalid - cannot proceed with MCP connection")
        return None
    elif token_valid is None:
        print("⚠️ Could not verify token validity - proceeding anyway")
    
    try:
        # Create MultiServerMCPClient with Descope bearer token
        client = MultiServerMCPClient(
            {
                "descope_crm": {
                    "transport": "streamable_http",
                    "url": mcp_server_url,
                    "headers": {
                        "Authorization": f"Bearer {bearer_token}",
                        "Content-Type": "application/json",
                        "X-Client-Type": "langgraph-agent"
                    },
                }
            }
        )
        
        print("✅ MultiServerMCPClient created with Descope token!")
        print(f"🔗 Connecting to: {mcp_server_url}")
        print(f"🔐 Using transport: streamable_http")
        print(f"🔑 Bearer token: {bearer_token[:20]}...")
        
        # Get tools from the MCP server with better error handling
        print("📡 Attempting to get tools from MCP server...")
        print(f"🔑 Using bearer token: {bearer_token[:20]}...")
        print(f"🌐 Connecting to: {mcp_server_url}")
        
        try:
            # Test basic connectivity first
            print("🔍 Testing basic MCP server connectivity...")
            all_tools = await client.get_tools()
            print(f"✅ Loaded {len(all_tools)} tools from Descope MCP server")
        except Exception as tools_error:
            print(f"❌ Error getting tools: {tools_error}")
            print("🔄 This might be due to session termination or authentication issues")
            
            # Try to get more specific error information
            if "Session terminated" in str(tools_error):
                print("🚨 Session termination detected - this usually means:")
                print("   1. Bearer token is invalid or expired")
                print("   2. Server is rejecting the authentication")
                print("   3. MCP server is having issues")
                print("   4. Network connectivity problems")
                
                # Try to validate the bearer token and handle auth errors
                print("🔍 Attempting to validate bearer token...")
                try:
                    async with httpx.AsyncClient() as test_client:
                        # Try a simple request to see if token is valid
                        test_response = await test_client.get(
                            mcp_server_url.replace('/mcp', '/health'),
                            headers={"Authorization": f"Bearer {bearer_token}"},
                            timeout=5.0
                        )
                        print(f"📡 Health check response: {test_response.status_code}")
                        
                        # Handle authentication errors (400, 401, 403)
                        if test_response.status_code in [400, 401, 403]:
                            print(f"🚨 Authentication error ({test_response.status_code}) - token may need additional scopes")
                            # Get OAuth endpoints for re-authentication
                            oauth_endpoints = await discover_descope_endpoints(mcp_server_url)
                            callback_url = "http://localhost:8081/callback"  # Default callback
                            
                            # Get current scopes from token manager
                            current_scopes = token_manager.scopes or ['outbound.token.fetch']
                            
                            # Handle the auth error and request additional scopes
                            new_token = await handle_auth_error_and_reauth(
                                oauth_endpoints, 
                                current_scopes, 
                                callback_url, 
                                f"{test_response.status_code}"
                            )
                            
                            if new_token:
                                print("✅ Successfully obtained new token with additional scopes")
                                # Update the token in token manager
                                token_manager.access_token = new_token
                                return await test_descope_mcp_connection(mcp_server_url, new_token)
                            else:
                                print("❌ Failed to obtain new token with additional scopes")
                                return None
                                
                        elif test_response.status_code == 200:
                            print("✅ Bearer token appears valid")
                        else:
                            print(f"⚠️ Unexpected response: {test_response.status_code}")
                except Exception as health_error:
                    print(f"⚠️ Could not test token validity: {health_error}")
            
            return None
        
        # Filter out tools with invalid schemas and fix schema issues
        valid_tools = []
        for i, tool in enumerate(all_tools):
            try:
                # Check and fix tool schema
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    if hasattr(tool.args_schema, 'model_fields'):
                        # Pydantic model - validate it
                        tool.args_schema.model_fields
                    elif isinstance(tool.args_schema, dict):
                        # Dict schema - check and fix common issues
                        fixed_schema = fix_tool_schema(tool.args_schema)
                        if fixed_schema != tool.args_schema:
                            tool.args_schema = fixed_schema
                            print(f"   🔧 Fixed schema for {tool.name}")
                    else:
                        # Unknown schema type - skip
                        raise ValueError(f"Unknown schema type: {type(tool.args_schema)}")
                
                print(f"   ✅ {i+1}. {tool.name}: {tool.description}")
                valid_tools.append(tool)
            except Exception as tool_error:
                print(f"   ⚠️ {i+1}. {tool.name}: {tool.description} (SKIPPED - Schema error: {str(tool_error)[:100]}...)")
        
        print(f"📋 Using {len(valid_tools)} valid tools out of {len(all_tools)} total")
        
        if not valid_tools:
            print("❌ No valid tools found after schema validation")
            return None
        
        # Create agent with valid tools only
        agent = create_react_agent(model, valid_tools)
        print("✅ Created LangGraph agent with valid Descope MCP tools!")
        
        # Test the agent
        print("\n🧪 Testing agent with Descope authentication...")
        test_response = await agent.ainvoke({
            "messages": [HumanMessage(content="Hello, can you help me with your available CRM operations?")]
        })
        print(f"✅ Agent response: {test_response['messages'][-1].content}")
        
        # Store the agent with current scopes for progressive scoping
        # Always default to outbound.token.fetch if no scopes are available
        agent._current_scopes = token_manager.scopes or ['outbound.token.fetch']
        
        return agent
        
    except Exception as e:
        print(f"❌ Error testing MCP connection: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return None

async def interactive_descope_session(mcp_server_url, bearer_token):
    """Run interactive session with Descope authentication"""
    print("\n💬 Starting interactive session with Descope authentication...")
    
    try:
        client = MultiServerMCPClient(
            {
                "descope_crm": {
                    "transport": "streamable_http",
                    "url": mcp_server_url,
                    "headers": {
                        "Authorization": f"Bearer {bearer_token}",
                        "Content-Type": "application/json",
                        "X-Client-Type": "langgraph-agent"
                    },
                }
            }
        )
        
        tools = await client.get_tools()
        agent = create_react_agent(model, tools)
        
        print("✅ Interactive session ready!")
        print("💬 Type 'quit' to exit.")
        
        while True:
            user_input = input("\n🤖 You: ")
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            try:
                response = await agent.ainvoke({
                    "messages": [HumanMessage(content=user_input)]
                })
                print(f"🤖 Agent: {response['messages'][-1].content}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("👋 Goodbye!")
        
    except Exception as e:
        print(f"❌ Error in interactive session: {e}")

async def main():
    """Main function for Descope OAuth discovery and MCP connection"""
    print("🚀 Descope OAuth Discovery & MCP Agent")
    print("=" * 50)
    
    # MCP server URL to connect to
    mcp_server_url = "https://hubspot-crm.preview.descope.org/mcp"
    
    # Step 1: Discover Descope OAuth endpoints
    print("🔍 Step 1: Discovering Descope OAuth endpoints...")
    oauth_endpoints = await discover_descope_endpoints(mcp_server_url)
    
    print(f"✅ Discovered endpoints: {oauth_endpoints}")
    
    # Step 2: Perform Descope OAuth flow
    print("\n🔐 Step 2: Performing Descope OAuth authentication...")
    bearer_token = await perform_descope_oauth_flow(oauth_endpoints, mcp_server_url)
    
    if not bearer_token:
        print("❌ Failed to obtain Descope bearer token. Cannot connect to MCP server.")
        return
    
    # Step 3: Test MCP connection with Descope token
    print("\n🔗 Step 3: Testing MCP connection with Descope token...")
    success = await test_descope_mcp_connection(mcp_server_url, bearer_token)
    
    if success:
        print("\n🎉 SUCCESS! Descope OAuth and MCP connection completed!")
        print(f"📝 Bearer token (first 20 chars): {bearer_token[:20]}...")
        print("\n💡 You can now use this bearer token in your environment:")
        print(f"   export DESCOPE_BEARER_TOKEN='{bearer_token}'")
        
        # Ask if user wants interactive session
        choice = input("\nWould you like to start an interactive session? (y/n): ")
        if choice.lower() in ['y', 'yes']:
            await interactive_descope_session(mcp_server_url, bearer_token)
    else:
        print("\n❌ Failed to connect to MCP server with Descope token.")

if __name__ == "__main__":
    asyncio.run(main())
