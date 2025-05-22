import time
import secrets
import logging
import httpx

from typing import Literal, Any
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse, Response
from starlette.exceptions import HTTPException

from jwcrypto.jwk import JWK
from mcp.server.fastmcp.server import FastMCP
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import (
    OAuthAuthorizationServerProvider,
    OAuthClientInformationFull,
    AuthorizationParams,
    AuthorizationCode,
    AccessToken,
    OAuthToken,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions

logger = logging.getLogger(__name__)

class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_")

    host: str = "localhost"
    port: int = 8000
    server_url: AnyHttpUrl = "http://localhost:8000"

    descope_project_id: str
    descope_client_id: str
    descope_client_secret: str
    callback_path: str = "/callback"
    scope: str = "full_access"

class DescopeOAuthProvider(OAuthAuthorizationServerProvider):
    def __init__(self, settings: ServerSettings):
        self.settings = settings
        self.issuer = f"https://api.descope.com/v1/apps/{settings.descope_project_id}"
        self.auth_url = "https://api.descope.com/oauth2/v1/authorize"
        self.token_url = "https://api.descope.com/oauth2/v1/token"
        self.jwks_url = f"{self.issuer}/.well-known/jwks.json"

        self.clients = {}
        self.auth_codes = {}
        self.tokens = {}
        self.state_cache = {}
        self.token_mapping = {}
        self._jwk = None

    async def get_issuer_url(self) -> str:
        return self.issuer

    async def get_jwk(self) -> JWK:
        if self._jwk is None:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.jwks_url)
                self._jwk = JWK(**resp.json()["keys"][0])
        return self._jwk

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull):
        self.clients[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        state = params.state or secrets.token_hex(16)
        self.state_cache[state] = {
            "redirect_uri": str(params.redirect_uri),
            "client_id": client.client_id,
        }

        return (
            f"{self.auth_url}"
            f"?client_id={self.settings.descope_client_id}"
            f"&redirect_uri={self.settings.server_url}{self.settings.callback_path}"
            f"&response_type=code"
            f"&scope=openid email"
            f"&state={state}"
        )

    async def handle_callback(self, code: str, state: str) -> str:
        state_data = self.state_cache.get(state)
        if not state_data:
            raise ValueError("Invalid state")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{self.settings.server_url}{self.settings.callback_path}",
                    "client_id": self.settings.descope_client_id,
                    "client_secret": self.settings.descope_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise ValueError("Token exchange failed")

            descope_token = resp.json()["access_token"]

        mcp_code = secrets.token_hex(16)
        self.auth_codes[mcp_code] = AuthorizationCode(
            code=mcp_code,
            client_id=state_data["client_id"],
            redirect_uri=AnyHttpUrl(state_data["redirect_uri"]),
            redirect_uri_provided_explicitly=True,
            expires_at=time.time() + 300,
            scopes=[self.settings.scope],
            code_challenge=None,
        )
        self.token_mapping[mcp_code] = descope_token
        return construct_redirect_uri(state_data["redirect_uri"], code=mcp_code, state=state)

    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str) -> AuthorizationCode | None:
        return self.auth_codes.get(authorization_code)

    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        if authorization_code.code not in self.auth_codes:
            raise ValueError("Invalid authorization code")

        mcp_token = f"mcp_{secrets.token_hex(32)}"
        self.tokens[mcp_token] = AccessToken(
            token=mcp_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + 3600,
        )
        self.token_mapping[mcp_token] = self.token_mapping[authorization_code.code]
        del self.auth_codes[authorization_code.code]

        return OAuthToken(
            access_token=mcp_token,
            token_type="bearer",
            expires_in=3600,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        access_token = self.tokens.get(token)
        if not access_token:
            return None
        if access_token.expires_at and access_token.expires_at < time.time():
            del self.tokens[token]
            return None
        return access_token

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        raise NotImplementedError("Refresh tokens not supported.")

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:
        self.tokens.pop(token, None)


def create_mcp_server(settings: ServerSettings) -> FastMCP:
    oauth_provider = DescopeOAuthProvider(settings)

    auth_settings = AuthSettings(
        issuer_url=f"https://api.descope.com/v1/apps/{settings.descope_project_id}",
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[settings.scope],
            default_scopes=[settings.scope],
        ),
        required_scopes=[settings.scope],
    )

    app = FastMCP(
        name="Descope OAuth MCP Server",
        instructions="MCP server using Descope OAuth",
        host=settings.host,
        port=settings.port,
        auth=auth_settings,
        auth_server_provider=oauth_provider,
        debug=True,
    )

    @app.custom_route(settings.callback_path, methods=["GET"])
    async def descope_callback(request: Request) -> Response:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            raise HTTPException(400, "Missing code or state")
        try:
            redirect = await oauth_provider.handle_callback(code, state)
            return RedirectResponse(url=redirect)
        except Exception as e:
            logger.exception("OAuth callback error")
            return JSONResponse(status_code=500, content={"error": "OAuth callback failed"})

    def get_descope_token() -> str:
        access_token = get_access_token()
        if not access_token:
            raise ValueError("Not authenticated")
        token = oauth_provider.token_mapping.get(access_token.token)
        if not token:
            raise ValueError("No token mapping found")
        return token

    @app.tool()
    async def greet(name: str) -> dict[str, str]:
        """Simple test tool."""
        token = get_descope_token()  # Optional: use this to call Descope APIs
        return {"message": f"Hello {name}!"}

    return app


if __name__ == "__main__":
    import click

    logging.basicConfig(level=logging.INFO)

    @click.command()
    @click.option("--port", default=8000, help="Port to run MCP server on")
    @click.option("--host", default="localhost", help="Host to bind MCP server")
    def run_server(port: int, host: str):
        try:
            settings = ServerSettings(host=host, port=port)
        except Exception as e:
            logger.error("Environment variables not configured correctly.")
            logger.error("Required:")
            logger.error("  MCP_DESCOPE_CLIENT_ID")
            logger.error("  MCP_DESCOPE_CLIENT_SECRET")
            logger.error("  MCP_DESCOPE_PROJECT_ID")
            raise e

        server = create_mcp_server(settings)
        server.run()

    run_server()
