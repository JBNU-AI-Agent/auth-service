from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.core.jwt import decode_access_token
from app.core.exceptions import (
    InvalidCredentialsException,
    InsufficientPermissionException,
)
from app.repositories.user import UserRepository
from app.models.user import UserInDB

security = HTTPBearer()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """토큰에서 현재 사용자 정보 추출 (선택적)"""
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """토큰에서 현재 사용자 정보 추출 (필수)"""
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise InvalidCredentialsException("Invalid or expired token")

    return payload


async def get_current_user_db(
    payload: dict = Depends(get_current_user)
) -> UserInDB:
    """DB에서 현재 사용자 조회"""
    # client_credentials 토큰은 user가 아님
    if payload.get("type") == "client_credentials":
        raise InvalidCredentialsException("Client token cannot access user endpoints")

    user = await UserRepository.get_by_id(payload["sub"])
    if not user:
        raise InvalidCredentialsException("User not found")

    return user


async def require_admin(
    payload: dict = Depends(get_current_user)
) -> dict:
    """관리자 권한 필수"""
    if payload.get("role") != "admin":
        raise InsufficientPermissionException("Admin role required")

    return payload


def require_scopes(*required_scopes: str):
    """특정 스코프 필수 (Client Credentials용)"""
    async def check_scopes(
        payload: dict = Depends(get_current_user)
    ) -> dict:
        if payload.get("type") != "client_credentials":
            # 일반 사용자는 스코프 체크 안 함
            return payload

        token_scopes = set(payload.get("scopes", []))
        if not set(required_scopes).issubset(token_scopes):
            raise InsufficientPermissionException(
                f"Required scopes: {', '.join(required_scopes)}"
            )

        return payload

    return check_scopes
