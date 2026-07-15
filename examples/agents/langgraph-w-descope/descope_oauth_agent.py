import os
import asyncio
import webbrowser
import json
import urllib.parse
import base64
import hashlib
import time
import pickle
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
    """Manages OAuth tokens with automatic refresh capability and local storage"""
    
    def __init__(self, storage_file="token_storage.pkl"):
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.scopes = []
        self.client_id = None
        self.token_endpoint = None
        self.callback_url = None
        self.storage_file = storage_file
        self.load_from_storage()
    
    def set_token_info(self, access_token, refresh_token=None, expires_in=None, scopes=None, client_id=None, token_endpoint=None, callback_url=None):
        """Set token information and calculate expiration"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.token_endpoint = token_endpoint
        self.callback_url = callback_url
        self.scopes = scopes or []
        
        if expires_in:
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        else:
            # Default to 1 hour if no expiration provided
            self.token_expires_at = datetime.now() + timedelta(hours=1)
        
        print(f"🔑 Token set, expires at: {self.token_expires_at}")
        # Save to storage after setting token info
        self.save_to_storage()
    
    def save_to_storage(self):
        """Save token information to local storage"""
        try:
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_expires_at': self.token_expires_at,
                'scopes': self.scopes,
                'client_id': self.client_id,
                'token_endpoint': self.token_endpoint,
                'callback_url': self.callback_url,
                'client_secret': getattr(self, 'client_secret', None),
                'registration_endpoint': getattr(self, 'registration_endpoint', None)
            }
            
            print(f"💾 Saving token data: access_token={'✅' if self.access_token else '❌'}, refresh_token={'✅' if self.refresh_token else '❌'}")
            
            with open(self.storage_file, 'wb') as f:
                pickle.dump(token_data, f)
            print(f"💾 Token data saved to {self.storage_file}")
        except Exception as e:
            print(f"❌ Error saving token data: {e}")
    
    def load_from_storage(self):
        """Load token information from local storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'rb') as f:
                    token_data = pickle.load(f)
                
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expires_at = token_data.get('token_expires_at')
                self.scopes = token_data.get('scopes', [])
                self.client_id = token_data.get('client_id')
                self.token_endpoint = token_data.get('token_endpoint')
                self.callback_url = token_data.get('callback_url')
                self.client_secret = token_data.get('client_secret')
                self.registration_endpoint = token_data.get('registration_endpoint')
                
                print(f"💾 Token data loaded from {self.storage_file}")
                if self.access_token:
                    print(f"🔑 Loaded access token: {self.access_token[:20]}...")
                if self.refresh_token:
                    print(f"🔄 Loaded refresh token: {self.refresh_token[:20]}...")
                if self.client_id:
                    print(f"🔑 Loaded client ID: {self.client_id[:20]}...")
            else:
                print(f"📁 No token storage file found at {self.storage_file}")
        except Exception as e:
            print(f"❌ Error loading token data: {e}")
    
    def clear_storage(self):
        """Clear token information from local storage"""
        try:
            if os.path.exists(self.storage_file):
                os.remove(self.storage_file)
                print(f"🗑️ Token storage cleared: {self.storage_file}")
            
            # Clear in-memory data
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None
            self.scopes = []
            self.client_id = None
            self.token_endpoint = None
            self.client_secret = None
            self.registration_endpoint = None
        except Exception as e:
            print(f"❌ Error clearing token storage: {e}")
    
    def save_client_info(self, client_id, client_secret=None, registration_endpoint=None):
        """Save client registration information"""
        self.client_id = client_id
        self.client_secret = client_secret
        self.registration_endpoint = registration_endpoint
        self.save_to_storage()
        print(f"💾 Client info saved: {client_id[:20]}...")
    
    def get_stored_client_id(self):
        """Get stored client ID if available"""
        return self.client_id
    
    def get_stored_callback_url(self):
        """Get stored callback URL if available"""
        return self.callback_url
    
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
                    # Save updated token info to storage
                    self.save_to_storage()
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
    
    # Class variables to store OAuth data
    auth_code = None
    code_verifier = None
    oauth_error = None
    
    @classmethod
    def clear_oauth_data(cls):
        """Clear all stored OAuth data"""
        cls.auth_code = None
        cls.code_verifier = None
        cls.oauth_error = None
        print("🧹 OAuth callback handler data cleared")
    
    def do_GET(self):
        """Handle OAuth callback"""
        print(f"🌐 OAuth callback received: {self.path}")
        print(f"🌐 Full request: {self.command} {self.path}")
        print(f"🌐 Headers: {dict(self.headers)}")
        print(f"🌐 Client address: {self.client_address}")
        
        if self.path == '/test':
            # Simple test endpoint to verify server is working
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Callback server is working!")
            print(f"✅ Test endpoint hit")
        elif self.path.startswith('/callback?code='):
            # Handle direct callback with code (for testing)
            print(f"🔧 Manual callback test: {self.path}")
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                auth_code = query_params['code'][0]
                print(f"✅ Manual test - received authorization code: {auth_code}")
                
                # Store the code
                OAuthCallbackHandler.auth_code = auth_code
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html_content = """
                <html>
                <body>
                    <h1>Manual Test Successful!</h1>
                    <p>Authorization code received and stored.</p>
                </body>
                </html>
                """
                self.wfile.write(html_content.encode('utf-8'))
        elif self.path.startswith('/callback'):
            # Parse the callback URL
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            print(f"🔍 Query parameters: {query_params}")
            
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
                error_description = query_params.get('error_description', [''])[0]
                print(f"❌ OAuth error: {error} - {error_description}")
                
                # Store the error for the main process
                OAuthCallbackHandler.oauth_error = f"{error}: {error_description}"
                
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_html = f"""
                <html>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Error: {error}</p>
                    <p>Description: {error_description}</p>
                    <p>Please check the terminal for more details.</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode('utf-8'))
        else:
            print(f"🌐 Non-callback request: {self.path}")
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
    
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
        'default_scope': 'outbound.token.fetch calendar:read'  # Always use this as the primary scope
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
                if name not in ['well_known', 'scopes_supported', 'default_scope', 'supports_refresh_token']:
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

async def get_valid_bearer_token(oauth_endpoints, actual_callback_url):
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
    
    # Always revert to base scopes for re-authentication
    base_scopes = ['outbound.token.fetch', 'calendar:read']
    
    print(f"🎯 Reverting to base scopes for re-authentication: {base_scopes}")
    
    # Perform new OAuth flow with base scopes
    new_token = await perform_descope_oauth_flow_with_scopes(oauth_endpoints, actual_callback_url, base_scopes)
    
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

async def handle_auth_error_and_reauth(oauth_endpoints, current_scopes, actual_callback_url, error_code=None):
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
    return await perform_descope_oauth_flow_with_scopes(oauth_endpoints, actual_callback_url, new_scopes)

async def validate_token_scopes(bearer_token, required_scopes=None):
    """Validate that the bearer token has the required scopes"""
    if not required_scopes:
        required_scopes = ['outbound.token.fetch', 'calendar:read']
    
    print(f"🔍 Validating token scopes...")
    print(f"🔍 Required scopes: {required_scopes}")
    
    # Get current scopes from token manager
    current_scopes = token_manager.scopes or []
    print(f"🔍 Current token scopes: {current_scopes}")
    
    # Check if all required scopes are present
    missing_scopes = [scope for scope in required_scopes if scope not in current_scopes]
    
    if missing_scopes:
        print(f"❌ Missing required scopes: {missing_scopes}")
        return False
    else:
        print(f"✅ All required scopes present: {required_scopes}")
        return True

async def update_mcp_client_with_new_token(mcp_client, new_token):
    """Update MCP client with new token"""
    if mcp_client and hasattr(mcp_client, 'update_token'):
        try:
            await mcp_client.update_token(new_token)
            print(f"✅ MCP client updated with new token: {new_token[:20]}...")
            return True
        except Exception as e:
            print(f"❌ Failed to update MCP client token: {e}")
            return False
    else:
        print("⚠️ MCP client doesn't support token updates, need to recreate")
        return False

async def handle_session_termination(mcp_server_url):
    """Handle session termination by refreshing token or re-authenticating"""
    print("🚨 Session terminated - attempting to recover...")
    
    # Try to refresh the token first
    if token_manager.refresh_token:
        print("🔄 Attempting token refresh...")
        refresh_success = await token_manager.refresh_access_token()
        if refresh_success:
            print("✅ Token refreshed successfully")
            return token_manager.access_token
        else:
            print("❌ Token refresh failed")
    
    # If refresh fails, need to re-authenticate
    print("🔄 Token refresh failed, starting new OAuth flow...")
    
    # Get OAuth endpoints
    oauth_endpoints = await discover_descope_endpoints(mcp_server_url)
    if not oauth_endpoints:
        print("❌ Failed to discover OAuth endpoints")
        return None
    
    # Perform new OAuth flow
    new_token = await perform_descope_oauth_flow(oauth_endpoints, mcp_server_url, None)
    if new_token:
        print("✅ New authentication successful")
        return new_token
    else:
        print("❌ New authentication failed")
        return None

async def perform_descope_oauth_flow_with_scopes(oauth_endpoints, actual_callback_url, requested_scopes, client_id_override=None):
    """Perform OAuth flow with specific scopes"""
    print(f"🔐 Starting OAuth flow with scopes: {requested_scopes}")
    
    # Clear any cached OAuth data before starting scope upgrade
    print("🧹 Clearing cached OAuth data before scope upgrade")
    OAuthCallbackHandler.clear_oauth_data()
    
    # Start local callback server - try different ports if needed
    callback_ports = [8085, 8081, 8082, 8083, 8084]
    server = None
    callback_port = None
    actual_actual_callback_url = None
    
    for port in callback_ports:
        try:
            # Try to bind to all interfaces, not just localhost
            server = HTTPServer(('0.0.0.0', port), OAuthCallbackHandler)
            callback_port = port
            actual_actual_callback_url = f"http://localhost:{port}/callback"
            print(f"✅ Successfully bound callback server to port {port}")
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {port} is in use, trying next port...")
                continue
            else:
                print(f"❌ Error binding to port {port}: {e}")
                continue
    
    if not server:
        print("❌ Could not find an available port for the callback server")
        return None
    
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print(f"🌐 Started callback server on port {callback_port}")
    
    try:
        # Use client ID override if provided, otherwise check for stored client ID, otherwise register dynamically
        if client_id_override:
            print(f"🔑 Using provided client ID: {client_id_override}")
            client_id = client_id_override
        else:
            # Check for stored client ID first (from initial authentication)
            stored_client_id = token_manager.get_stored_client_id()
            if stored_client_id:
                print(f"🔑 Using stored client ID for scope upgrade: {stored_client_id}")
                client_id = stored_client_id
            else:
                # Register client dynamically with expanded scopes if no stored client ID
                print("🔑 No stored client ID found, registering new client for scope upgrade")
                client_info = await register_descope_client_with_scopes(oauth_endpoints, actual_actual_callback_url, requested_scopes)
                if not client_info:
                    print("❌ Failed to register client with expanded scopes")
                    return None
                
                client_id = client_info.get('client_id')
                client_secret = client_info.get('client_secret')
                print(f"✅ Using dynamically registered client ID: {client_id}")
                
                # Save client information to storage for future scope upgrades
                print("💾 Storing client info for future scope upgrades")
                token_manager.save_client_info(
                    client_id, 
                    client_secret, 
                    oauth_endpoints.get('registration_endpoint')
                )
        
        auth_endpoint = oauth_endpoints['authorization_endpoint']
        token_endpoint = oauth_endpoints.get('token_endpoint')
        
        # Generate PKCE parameters (RFC 7636 compliant)
        # Code verifier: 43-128 characters, unreserved characters
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        # Ensure it's at least 43 characters
        if len(code_verifier) < 43:
            code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        
        # Code challenge: SHA256 hash of code verifier, base64url encoded
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        # Store code_verifier in callback handler for later use
        OAuthCallbackHandler.code_verifier = code_verifier
        
        print(f"🔐 Generated PKCE code_challenge: {code_challenge}")
        print(f"🔐 Stored code_verifier: {code_verifier[:10]}...")
        
        # Build authorization URL with expanded scopes
        # Always include base scopes
        base_scopes = ['outbound.token.fetch', 'calendar:read']
        all_scopes = list(set(base_scopes + requested_scopes))
        scope_string = ' '.join(all_scopes)
        print(f"🎯 Requesting scopes: {scope_string}")
        auth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': actual_callback_url,
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
        print(f"   Expected callback URL: {actual_callback_url}")
        
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check for callback data
            if hasattr(OAuthCallbackHandler, 'auth_code') and OAuthCallbackHandler.auth_code:
                print(f"✅ Received fresh authorization code: {OAuthCallbackHandler.auth_code}")
                break
            elif hasattr(OAuthCallbackHandler, 'access_token') and OAuthCallbackHandler.access_token:
                print(f"✅ Received fresh access token: {OAuthCallbackHandler.access_token}")
                break
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                print("❌ OAuth timeout - no response received")
                print(f"   Expected callback URL: {actual_callback_url}")
                print("\n🔧 Manual fallback: You can paste the callback URL manually")
                print("   Look for a URL that starts with the callback URL above")
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
                token_endpoint=token_endpoint,
                callback_url=actual_callback_url
            )
            
        elif hasattr(OAuthCallbackHandler, 'auth_code'):
            auth_code = OAuthCallbackHandler.auth_code
            print(f"✅ Received authorization code: {auth_code}")
            
            # Exchange code for token
            if token_endpoint:
                # Get the stored code_verifier
                stored_code_verifier = OAuthCallbackHandler.code_verifier
                if not stored_code_verifier:
                    print("❌ No code_verifier found in callback handler")
                    return None
                
                bearer_token = await exchange_code_for_descope_token(auth_code, token_endpoint, actual_callback_url, client_id, stored_code_verifier)
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

async def register_descope_client_with_scopes(oauth_endpoints, actual_callback_url, requested_scopes):
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
        "redirect_uris": [actual_callback_url],
        "response_types": ["code"],
        "grant_types": ["authorization_code"],
        "token_endpoint_auth_method": "none",  # Public client
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

async def register_descope_client(oauth_endpoints, actual_callback_url):
    """Register a new client with Descope using dynamic client registration"""
    print("📝 Registering client with Descope...")
    
    registration_endpoint = oauth_endpoints.get('registration_endpoint')
    if not registration_endpoint:
        print("❌ No registration endpoint found")
        return None
    
    # Client registration payload - don't specify scope, let server decide
    registration_data = {
        "client_name": "LangGraph MCP Agent",
        "redirect_uris": [actual_callback_url],
        "response_types": ["code"],
        "grant_types": ["authorization_code"],
        "token_endpoint_auth_method": "none"  # Public client
    }
    
    print(f"📋 Registration data redirect_uris: {registration_data['redirect_uris']}")
    
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

async def perform_descope_oauth_flow(oauth_endpoints, mcp_server_url, client_id_override=None):
    """Perform Descope OAuth flow"""
    print("🔐 Starting Descope OAuth flow...")
    
    # Clear stored client ID for initial authentication to force DCR
    print("🧹 Clearing stored client ID for initial authentication")
    token_manager.client_id = None
    token_manager.save_to_storage()
    
    # Clear any cached OAuth data before starting initial authentication
    print("🧹 Clearing cached OAuth data before initial authentication")
    OAuthCallbackHandler.clear_oauth_data()
    
    # Start local callback server - try different ports if needed
    callback_ports = [8085, 8081, 8082, 8083, 8084]
    server = None
    callback_port = None
    actual_callback_url = None
    
    for port in callback_ports:
        try:
            # Try to bind to all interfaces, not just localhost
            server = HTTPServer(('0.0.0.0', port), OAuthCallbackHandler)
            callback_port = port
            actual_callback_url = f"http://localhost:{port}/callback"
            print(f"✅ Successfully bound callback server to port {port}")
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"⚠️ Port {port} is in use, trying next port...")
                continue
            else:
                print(f"❌ Error binding to port {port}: {e}")
                continue
    
    if not server:
        print("❌ Could not find an available port for the callback server")
        return None
    
    server_thread = Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print(f"🌐 Started callback server on port {callback_port}")
    print(f"🔗 Callback URL: {actual_callback_url}")
    
    # Give the server a moment to start
    import time
    time.sleep(0.5)
    
    # Test if server is actually listening
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', callback_port))
        sock.close()
        if result == 0:
            print(f"✅ Callback server is listening on port {callback_port}")
        else:
            print(f"❌ Callback server is NOT listening on port {callback_port}")
    except Exception as e:
        print(f"❌ Error testing callback server: {e}")
    
    try:
        # Use client ID override if provided, otherwise check for stored client ID, otherwise register dynamically
        if client_id_override:
            print(f"🔑 Using provided client ID: {client_id_override}")
            client_id = client_id_override
            default_scope = 'outbound.token.fetch calendar:read'
            print(f"🎯 Using default scope: {default_scope}")
        else:
            # Check for stored client ID first
            stored_client_id = token_manager.get_stored_client_id()
            if stored_client_id:
                print(f"🔑 Using stored client ID: {stored_client_id}")
                client_id = stored_client_id
                default_scope = 'outbound.token.fetch calendar:read'
                print(f"🎯 Using default scope: {default_scope}")
            else:
                # Register client dynamically with the correct callback URL
                print(f"🔗 Registering client with callback URL: {actual_callback_url}")
                client_info = await register_descope_client(oauth_endpoints, actual_callback_url)
                if not client_info:
                    print("❌ Failed to register client, falling back to hardcoded client ID")
                    client_id = "UDMwcHlITndWcjNzTzVjUFQ4N2hPUVlmNkxmVzpUUEEzM1F1b1hScnp0RHRFTWlvdFZRbUs0MmQ4Wmc="
                    # Always use outbound.token.fetch and calendar:read as the default scope
                    default_scope = 'outbound.token.fetch calendar:read'
                else:
                    client_id = client_info.get('client_id')
                    client_secret = client_info.get('client_secret')
                    print(f"✅ Using dynamically registered client ID: {client_id}")
                    
                    # Save client info after successful initial authentication for future scope upgrades
                    print("💾 Storing client info for future scope upgrades")
                    token_manager.save_client_info(
                        client_id, 
                        client_secret, 
                        oauth_endpoints.get('registration_endpoint')
                    )
                    
                    # Verify the registered redirect URIs match our callback URL
                    registered_redirect_uris = client_info.get('redirect_uris', [])
                    print(f"🔍 Registered redirect URIs: {registered_redirect_uris}")
                    if actual_callback_url not in registered_redirect_uris:
                        print(f"⚠️ WARNING: Callback URL {actual_callback_url} not in registered URIs!")
                        print(f"   This might cause redirect mismatches")
                    
                    # Always use outbound.token.fetch and calendar:read as the default scope
                    default_scope = 'outbound.token.fetch calendar:read'
                    print(f"🎯 Using default scope: {default_scope}")
        
        auth_endpoint = oauth_endpoints['authorization_endpoint']
        token_endpoint = oauth_endpoints.get('token_endpoint')
        
        print(f"🔗 Authorization endpoint: {auth_endpoint}")
        if token_endpoint:
            print(f"🔗 Token endpoint: {token_endpoint}")
        
        # Generate PKCE parameters (RFC 7636 compliant)
        # Code verifier: 43-128 characters, unreserved characters
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        # Ensure it's at least 43 characters
        if len(code_verifier) < 43:
            code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        
        # Code challenge: SHA256 hash of code verifier, base64url encoded
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        # Store code_verifier in callback handler for later use
        OAuthCallbackHandler.code_verifier = code_verifier
        
        print(f"🔐 Generated PKCE code_challenge: {code_challenge}")
        print(f"🔐 Stored code_verifier: {code_verifier[:10]}...")
        
        # Build authorization URL with Descope-specific parameters including PKCE
        auth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': actual_callback_url,
            'scope': default_scope,
            'state': 'langgraph-agent-state',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'login'  # Descope-specific parameter
        }
        
        print(f"🔗 Authorization URL redirect_uri: {auth_params['redirect_uri']}")
        
        auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(auth_params)}"
        print(f"🔗 Authorization URL: {auth_url}")
        
        # Open browser for authorization
        print("🌐 Opening browser for Descope authentication...")
        webbrowser.open(auth_url)
        
        # Wait for callback
        print("⏳ Waiting for OAuth callback...")
        print("   Please complete the authentication in your browser.")
        print(f"   Expected callback URL: {actual_callback_url}")
        
        # Wait for authorization code or token
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()
        
        print(f"⏳ Waiting for OAuth callback on {actual_callback_url}...")
        print(f"   You should see '🌐 OAuth callback received' when the callback arrives")
        
        # Check if callback data is already available
        if hasattr(OAuthCallbackHandler, 'auth_code') and OAuthCallbackHandler.auth_code:
            print(f"✅ Found existing auth_code: {OAuthCallbackHandler.auth_code}")
        elif hasattr(OAuthCallbackHandler, 'access_token') and OAuthCallbackHandler.access_token:
            print(f"✅ Found existing access_token: {OAuthCallbackHandler.access_token}")
        elif hasattr(OAuthCallbackHandler, 'oauth_error') and OAuthCallbackHandler.oauth_error:
            print(f"❌ Found existing oauth_error: {OAuthCallbackHandler.oauth_error}")
        else:
            # Wait for callback data
            print("⏳ Waiting for OAuth callback...")
            print("   If the callback doesn't arrive, you can manually paste the callback URL")
            
        while True:
            # Check for callback data
            if hasattr(OAuthCallbackHandler, 'auth_code') and OAuthCallbackHandler.auth_code:
                print(f"✅ Received fresh authorization code: {OAuthCallbackHandler.auth_code}")
                break
            elif hasattr(OAuthCallbackHandler, 'access_token') and OAuthCallbackHandler.access_token:
                print(f"✅ Received fresh access token: {OAuthCallbackHandler.access_token}")
                break
            elif hasattr(OAuthCallbackHandler, 'oauth_error') and OAuthCallbackHandler.oauth_error:
                print(f"❌ Received OAuth error: {OAuthCallbackHandler.oauth_error}")
                break
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                print("❌ OAuth timeout - no response received")
                print(f"   Expected callback URL: {actual_callback_url}")
                print("   Please check if you completed the authentication in your browser")
                print("\n🔧 Manual fallback: You can paste the callback URL manually")
                print("   Look for a URL that starts with the callback URL above")
                return None
            
            # Print a heartbeat every 10 seconds
            elapsed = asyncio.get_event_loop().time() - start_time
            if int(elapsed) % 10 == 0 and elapsed > 0:
                print(f"⏳ Still waiting... ({int(elapsed)}s elapsed)")
            
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
                token_endpoint=token_endpoint,
                callback_url=actual_callback_url
            )
            
        elif hasattr(OAuthCallbackHandler, 'auth_code'):
            auth_code = OAuthCallbackHandler.auth_code
            print(f"✅ Received authorization code: {auth_code}")
            
            # Exchange code for token
            if token_endpoint:
                # Get the stored code_verifier
                stored_code_verifier = OAuthCallbackHandler.code_verifier
                if not stored_code_verifier:
                    print("❌ No code_verifier found in callback handler")
                    return None
                
                bearer_token = await exchange_code_for_descope_token(auth_code, token_endpoint, actual_callback_url, client_id, stored_code_verifier)
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

async def exchange_code_for_descope_token(auth_code, token_endpoint, actual_callback_url, client_id, code_verifier):
    """Exchange authorization code for Descope access token with PKCE"""
    print("🔄 Exchanging authorization code for Descope access token with PKCE...")
    print(f"🔐 Using code_verifier: {code_verifier[:10]}... (length: {len(code_verifier)})")
    print(f"🔐 Auth code: {auth_code}")
    print(f"🔐 Client ID: {client_id}")
    print(f"🔐 Redirect URI: {actual_callback_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': actual_callback_url,
                'client_id': client_id,
                'code_verifier': code_verifier
            }
            
            print(f"📤 Token request data: {token_data}")
            
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
                        token_endpoint=token_endpoint,
                        callback_url=actual_callback_url
                    )
                    
                    print(f"🔑 New token scopes: {token_response.get('scope', 'No scopes returned')}")
                    print(f"🔑 Token stored in manager: {token_manager.access_token[:20]}...")
                    
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
    print(f"🔑 Token length: {len(bearer_token)} characters")
    print(f"🔑 Token starts with: {bearer_token[:10]}...")
    print(f"🔑 Token ends with: ...{bearer_token[-10:]}")
    
    # First, test if the bearer token is valid
    token_valid = await test_bearer_token_validity(mcp_server_url, bearer_token)
    
    if token_valid is False:
        print("❌ Bearer token is invalid - cannot proceed with MCP connection")
        return None
    elif token_valid is None:
        print("⚠️ Could not verify token validity - proceeding anyway")
    
    try:
        # Create MultiServerMCPClient with Descope bearer token
        print(f"🔑 Using bearer token for MCP client: {bearer_token[:20]}...")
        print(f"🔑 Full bearer token: {bearer_token}")
        
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
            # Test basic connectivity first with retry
            print("🔍 Testing basic MCP server connectivity...")
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    print(f"🔄 Attempt {attempt + 1}/{max_retries}...")
                    all_tools = await client.get_tools()
                    print(f"✅ Loaded {len(all_tools)} tools from Descope MCP server")
                    break
                except Exception as retry_error:
                    print(f"⚠️ Attempt {attempt + 1} failed: {retry_error}")
                    if attempt < max_retries - 1:
                        print(f"⏳ Waiting {retry_delay} seconds before retry...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise retry_error
            
            # Test a simple tool call to verify the connection works
            print("🔍 Testing tool execution...")
            try:
                # Try to call a simple tool to verify the token works
                test_result = await client.call_tool("list-contacts", {"limit": "1"})
                print(f"✅ Tool execution successful: {test_result}")
            except Exception as tool_error:
                print(f"⚠️ Tool execution failed: {tool_error}")
                print("⚠️ This might indicate token scope issues")
                
        except Exception as tools_error:
            print(f"❌ Error getting tools: {tools_error}")
            print(f"❌ Error type: {type(tools_error).__name__}")
            print(f"❌ Error details: {str(tools_error)}")
            print("🔄 This might be due to session termination or authentication issues")
            
            # Check if it's a specific error type
            if "TaskGroup" in str(tools_error):
                print("🔄 Detected TaskGroup error - this usually means session termination")
            elif "401" in str(tools_error) or "Unauthorized" in str(tools_error):
                print("🔄 Detected authentication error - token might be invalid or expired")
            elif "403" in str(tools_error) or "Forbidden" in str(tools_error):
                print("🔄 Detected permission error - token might lack required scopes")
            
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
                            actual_callback_url = "http://localhost:8081/callback"  # Default callback
                            
                            # Get current scopes from token manager
                            current_scopes = token_manager.scopes or ['outbound.token.fetch']
                            
                            # Handle the auth error and request additional scopes
                            new_token = await handle_auth_error_and_reauth(
                                oauth_endpoints, 
                                current_scopes, 
                                actual_callback_url, 
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
        print(f"🔑 Using bearer token for interactive session: {bearer_token[:20]}...")
        print(f"🔑 Full bearer token: {bearer_token}")
        
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

async def manual_code_extraction():
    """Manually extract authorization code from callback URL"""
    print("🔧 Manual Code Extraction Mode")
    print("=" * 40)
    
    # Get the callback URL from user
    actual_callback_url = input("Please paste the callback URL you were redirected to: ").strip()
    
    if not actual_callback_url:
        print("❌ No callback URL provided")
        return None
    
    # Parse the callback URL to extract the code
    try:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(actual_callback_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            auth_code = query_params['code'][0]
            print(f"✅ Extracted authorization code: {auth_code}")
            return auth_code
        else:
            print(f"❌ No authorization code found in URL: {actual_callback_url}")
            return None
            
    except Exception as e:
        print(f"❌ Error parsing callback URL: {e}")
        return None

async def perform_descope_oauth_flow_manual(oauth_endpoints, mcp_server_url):
    """Perform Descope OAuth flow with manual code extraction"""
    print("🔐 Starting Descope OAuth flow with manual code extraction...")
    
    # Register client dynamically (without callback server)
    actual_callback_url = "http://localhost:8085/callback"  # We'll use this for registration
    
    try:
        # Register client dynamically
        print(f"🔗 Registering client with callback URL: {actual_callback_url}")
        client_info = await register_descope_client(oauth_endpoints, actual_callback_url)
        if not client_info:
            print("❌ Failed to register client, falling back to hardcoded client ID")
            client_id = "UDMwcHlITndWcjNzTzVjUFQ4N2hPUVlmNkxmVzpUUEEzM1F1b1hScnp0RHRFTWlvdFZRbUs0MmQ4Wmc="
            default_scope = 'outbound.token.fetch'
        else:
            client_id = client_info.get('client_id')
            print(f"✅ Using dynamically registered client ID: {client_id}")
            default_scope = 'outbound.token.fetch'
        
        auth_endpoint = oauth_endpoints['authorization_endpoint']
        token_endpoint = oauth_endpoints.get('token_endpoint')
        
        # Generate PKCE parameters
        code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        if len(code_verifier) < 43:
            code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        print(f"🔐 Generated PKCE code_challenge: {code_challenge}")
        print(f"🔐 Generated code_verifier: {code_verifier[:10]}...")
        
        # Build authorization URL
        auth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': actual_callback_url,
            'scope': default_scope,
            'state': 'langgraph-agent-state',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'login'
        }
        
        auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(auth_params)}"
        print(f"🔗 Authorization URL: {auth_url}")
        
        # Open browser for authorization
        print("🌐 Opening browser for Descope authentication...")
        webbrowser.open(auth_url)
        
        print("\n" + "="*60)
        print("🔧 MANUAL CODE EXTRACTION REQUIRED")
        print("="*60)
        print("1. Complete the authentication in your browser")
        print("2. Copy the callback URL you were redirected to")
        print("3. Paste it below")
        print("="*60)
        
        # Get authorization code manually
        auth_code = await manual_code_extraction()
        if not auth_code:
            print("❌ No authorization code provided")
            return None
        
        # Exchange code for token
        print(f"🔄 Exchanging authorization code for token...")
        bearer_token = await exchange_code_for_descope_token(auth_code, token_endpoint, actual_callback_url, client_id, code_verifier)
        
        if bearer_token:
            print(f"✅ Successfully obtained Descope bearer token: {bearer_token[:20]}...")
            return bearer_token
        else:
            print("❌ Failed to exchange authorization code for token")
            return None
            
    except Exception as e:
        print(f"❌ Error in manual OAuth flow: {e}")
        return None

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
    
    # Step 2: Perform Descope OAuth flow with manual code extraction
    print("\n🔐 Step 2: Performing Descope OAuth authentication with manual code extraction...")
    bearer_token = await perform_descope_oauth_flow_manual(oauth_endpoints, mcp_server_url)
    
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
