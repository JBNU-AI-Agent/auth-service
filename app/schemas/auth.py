from datetime import datetime
from pydantic import BaseModel
from typing import Any, Optional


class ErrorResponse(BaseModel):
    timestamp: str
    path: str
    status: int
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
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
