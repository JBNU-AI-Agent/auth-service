from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class RefreshTokenInDB(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked: bool = False

    class Config:
        populate_by_name = True


class RefreshTokenCreate(BaseModel):
    user_id: str
    token_hash: str
    expires_at: datetime
