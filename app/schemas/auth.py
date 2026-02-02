from pydantic import BaseModel
from typing import Optional, List
from app.models.client import ClientType


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ClientTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str


# Client Credentials
class ClientCredentialsRequest(BaseModel):
    client_id: str
    client_secret: str


class ClientRegisterRequest(BaseModel):
    name: str
    client_type: ClientType
    scopes: List[str] = []


class ClientRegisterResponse(BaseModel):
    client_id: str
    client_secret: str  # 최초 1회만 반환
    name: str
    client_type: ClientType
    scopes: List[str]
    message: str = "Save the client_secret securely. It won't be shown again."


class ClientResponse(BaseModel):
    client_id: str
    name: str
    client_type: ClientType
    scopes: List[str]
    is_active: bool
