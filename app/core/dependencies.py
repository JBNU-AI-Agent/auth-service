from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.jwt import decode_access_token
from app.core.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from app.repositories.user import UserRepository
from app.models.user import UserInDB

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """토큰에서 현재 사용자 정보 추출 (필수)"""
    return decode_access_token(credentials.credentials)


async def get_current_user_db(
    payload: dict = Depends(get_current_user)
) -> UserInDB:
    """DB에서 현재 사용자 조회"""
    if payload.get("type") == "client_credentials":
        raise InvalidCredentialsException("Client token cannot access user endpoints")

    user = await UserRepository.get_by_id(payload["sub"])
    if not user:
        raise UserNotFoundException()

    return user
