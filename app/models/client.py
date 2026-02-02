from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ClientType(str, Enum):
    MCP_SERVER = "mcp_server"
    AI_AGENT = "ai_agent"
    SERVICE = "service"


class ClientInDB(BaseModel):
    id: str = Field(alias="_id")
    client_id: str
    client_secret_hash: str
    name: str
    client_type: ClientType
    scopes: List[str] = []
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class ClientCreate(BaseModel):
    name: str
    client_type: ClientType
    scopes: List[str] = []
