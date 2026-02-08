from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # MongoDB
    mongodb_uri: str
    mongodb_db_name: str = "authentic"

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # JWT
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_private_key: Optional[str] = None
    jwt_public_key: Optional[str] = None

    # Server
    allowed_email_domain: str = "jbnu.ac.kr"
    cors_origins: List[str] = ["http://localhost:3000"]


settings = Settings()
