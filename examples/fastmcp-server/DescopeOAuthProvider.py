import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from pydantic import AnyHttpUrl
from descope import DescopeClient
from descope.exceptions import DescopeException
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.server.auth.provider import (
    AuthorizationParams,
    AuthorizationCode,
    RefreshToken,
    AccessToken,
    RegistrationError,
    AuthorizeError,
    TokenError,
    OAuthAuthorizationServerProvider
)

# Set up logger
logger = logging.getLogger(__name__)

class DescopeAuthorizationCode(AuthorizationCode):
    pass

class DescopeRefreshToken(RefreshToken):
    pass

class DescopeAccessToken(AccessToken):
    pass

class DescopeOAuthProvider(OAuthAuthorizationServerProvider[
    DescopeAuthorizationCode,
    DescopeRefreshToken,
    DescopeAccessToken
]):
    def __init__(
        self,
        project_id: str,
        management_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        self.project_id = project_id
        self.client_id = client_id
        self.client_secret = client_secret
        
        logger.info(f"Initializing Descope provider for project: {project_id}")
        logger.debug(f"Client ID: {client_id}")
        
        try:
            self.descope_client = DescopeClient(
                project_id=project_id,
                management_key=management_key
            )
            logger.info("Successfully connected to Descope")
        except Exception as e:
            logger.error(f"Failed to initialize Descope connection: {str(e)}")
            raise

    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        """Retrieve client information from Descope"""
        logger.debug(f"Attempting to fetch client: {client_id}")
        try:
            if client_id == self.client_id:
                client_info = OAuthClientInformationFull(
                    client_id=client_id,
                    client_secret=self.client_secret,
                    redirect_uris=[f"https://api.descope.com/oauth2/v1/authorize"]
                )
                logger.debug(f"Found client: {client_id}")
                return client_info
            logger.warning(f"Client not found: {client_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching client {client_id}: {str(e)}")
            raise

    async def authorize(
        self, 
        client: OAuthClientInformationFull, 
        params: AuthorizationParams
    ) -> str:
        """Generate Descope authorization URL"""
        logger.info(f"Authorizing client: {client.client_id}")
        logger.debug(f"Authorization params: {params}")
        
        try:
            auth_url = "https://api.descope.com/oauth2/v1/authorize"
            
            query_params = {
                "response_type": "code",
                "client_id": client.client_id,
                "redirect_uri": str(params.redirect_uri),
                "state": params.state,
                "scope": " ".join(params.scopes) if params.scopes else "openid",
                "code_challenge": params.code_challenge,
                "code_challenge_method": "S256"
            }
            
            final_url = f"{auth_url}?{urlencode(query_params)}"
            logger.debug(f"Generated authorization URL: {final_url}")
            return final_url
        except Exception as e:
            logger.error(f"Authorization failed: {str(e)}")
            raise AuthorizeError("server_error", str(e))

    async def load_authorization_code(
        self, 
        client: OAuthClientInformationFull, 
        authorization_code: str
    ) -> Optional[DescopeAuthorizationCode]:
        """Validate authorization code"""
        logger.debug(f"Validating authorization code: {authorization_code}")
        
        try:
            token = self.descope_client.oauth.exchange_code(
                code=authorization_code,
                redirect_uri=client.redirect_uris[0]
            )
            
            logger.debug("Successfully validated authorization code")
            return DescopeAuthorizationCode(
                code=authorization_code,
                scopes=token.get("scope", "").split(),
                expires_at=float(token["expires_in"]),
                client_id=client.client_id,
                code_challenge="",  # Should be stored during authorize
                redirect_uri=AnyHttpUrl(client.redirect_uris[0]),
                redirect_uri_provided_explicitly=True
            )
        except DescopeException as e:
            logger.error(f"Descope validation error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Authorization code validation failed: {str(e)}")
            return None

    async def exchange_authorization_code(
        self, 
        client: OAuthClientInformationFull, 
        authorization_code: DescopeAuthorizationCode
    ) -> OAuthToken:
        """Exchange auth code for tokens"""
        logger.info(f"Exchanging auth code for client: {client.client_id}")
        
        try:
            token = self.descope_client.oauth.exchange_code(
                code=authorization_code.code,
                redirect_uri=str(authorization_code.redirect_uri)
            )
            
            logger.debug("Successfully exchanged authorization code")
            return OAuthToken(
                access_token=token["access_token"],
                refresh_token=token["refresh_token"],
                expires_in=token["expires_in"],
                token_type=token["token_type"],
                scope=token.get("scope", "")
            )
        except DescopeException as e:
            error_msg = f"Descope exchange error: {str(e)}"
            logger.error(error_msg)
            raise TokenError("invalid_grant", error_msg)
        except Exception as e:
            error_msg = f"Token exchange failed: {str(e)}"
            logger.error(error_msg)
            raise TokenError("server_error", error_msg)

    async def load_access_token(self, token: str) -> Optional[DescopeAccessToken]:
        """Validate access token"""
        logger.info("Validating access token")
        
        try:
            token_info = self.descope_client.validate_token(token)
            
            logger.debug("Access token validation successful")
            return DescopeAccessToken(
                token=token,
                client_id=token_info.get("client_id", ""),
                scopes=token_info.get("scope", "").split(),
                expires_at=token_info.get("exp")
            )
        except DescopeException as e:
            logger.error(f"Descope token validation error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Access token validation failed: {str(e)}")
            return None

    async def revoke_token(
        self,
        token: DescopeAccessToken | DescopeRefreshToken
    ) -> None:
        """Revoke token"""
        logger.info(f"Revoking token for client: {token.client_id}")
        
        try:
            if isinstance(token, DescopeAccessToken):
                self.descope_client.logout(token.token)
                logger.debug("Successfully revoked access token")
            else:
                self.descope_client.logout(refresh_token=token.token)
                logger.debug("Successfully revoked refresh token")
        except DescopeException as e:
            logger.error(f"Descope revocation error: {str(e)}")
            raise TokenError("invalid_request", "Token revocation failed")
        except Exception as e:
            logger.error(f"Token revocation failed: {str(e)}")
            raise TokenError("server_error", str(e))

def construct_redirect_uri(redirect_uri_base: str, **params: str | None) -> str:
    """Helper function to construct redirect URIs with query parameters"""
    logger.debug(f"Constructing redirect URI with params: {params}")
    parsed_uri = urlparse(redirect_uri_base)
    query_params = [(k, v) for k, vs in parse_qs(parsed_uri.query) for v in vs]
    for k, v in params.items():
        if v is not None:
            query_params.append((k, v))

    constructed_uri = urlunparse(parsed_uri._replace(query=urlencode(query_params)))
    logger.debug(f"Constructed URI: {constructed_uri}")
    return constructed_uri 