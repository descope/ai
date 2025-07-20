from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    descope_project_id: str
    descope_api_base_url: str
    
    class Config:
        env_file = ".env"
    
    @property
    def issuer_candidates(self) -> str:
        # the 'iss' field is the Descope Project ID.
        return [self.descope_project_id, f'https://api.descope.com/v1/apps/{self.descope_project_id}']
    
    @property
    def audience(self) -> str:
        return self.descope_project_id
    
    @property
    def jwks_url(self) -> str:
        return f"{self.descope_api_base_url.rstrip('/')}/{self.descope_project_id}/.well-known/jwks.json"

@lru_cache()
def get_settings():
    return Settings()