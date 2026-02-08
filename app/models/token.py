from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class RefreshTokenInDB(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked: bool = False


class RefreshTokenCreate(BaseModel):
    user_id: str
    token_hash: str
    expires_at: datetime
