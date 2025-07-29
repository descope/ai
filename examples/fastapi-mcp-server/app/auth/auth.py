from typing import Optional, List
import jwt
from jwt import PyJWKClient
from fastapi import Depends
from fastapi.security import SecurityScopes, HTTPAuthorizationCredentials, HTTPBearer
from app.auth.auth_config import get_settings
from app.auth.exceptions import UnauthenticatedException, UnauthorizedException

class TokenVerifier:
    def __init__(self):
        self.config = get_settings()
        self.jwks_client = PyJWKClient(self.config.jwks_url)
        self.allowed_algorithms = ["RS256"]

    async def __call__(
        self,
        security_scopes: SecurityScopes,
        token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
    ):
        if token is None:
            raise UnauthenticatedException
        
        token = token.credentials

        key = self._get_signing_key(token)

        payload = self._decode_token(token, key)
        if security_scopes.scopes:
            self._enforce_scopes(payload, security_scopes.scopes)
        return payload
    
    def _get_signing_key(self, token: str):
        try:
            return self.jwks_client.get_signing_key_from_jwt(token).key
        except Exception as e:
            raise UnauthorizedException(f"Failed to fetch signing key: {str(e)}")
        
    def _decode_token(self, token: str, key):
        try:
            return jwt.decode(
                token,
                key,
                algorithms=self.allowed_algorithms,
                issuer=self.config.issuer_candidates,
                audience=self.config.audience
            )
        except Exception as e:
            raise UnauthorizedException(f"Token decoding failed: {str(e)}")
        
    def _enforce_scopes(self, payload: dict, required_scopes: List[str]):
        scope_claim = payload.get("scope")
        if scope_claim is None:
            raise UnauthorizedException('Missing required claim: "scope"')
        scopes = scope_claim.split() if isinstance(scope_claim, str) else scope_claim
        missing = [scope for scope in required_scopes if scope not in scopes]
        if missing:
            raise UnauthorizedException(
                f'Missing required scopes: {", ".join(missing)}'
            )