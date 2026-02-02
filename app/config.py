from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
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

    # Server
    allowed_email_domain: str = "jbnu.ac.kr"
    cors_origins: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
