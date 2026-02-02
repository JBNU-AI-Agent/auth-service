from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None
    role: UserRole = UserRole.USER


class UserInDB(UserBase):
    id: str = Field(alias="_id")
    google_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    google_id: str
    picture: Optional[str] = None
