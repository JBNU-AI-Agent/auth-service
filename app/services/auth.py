from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.config import settings
from app.models.user import UserCreate, UserInDB
from app.models.token import RefreshTokenCreate
from app.repositories.user import UserRepository
from app.repositories.token import RefreshTokenRepository
from app.core.jwt import create_access_token
from app.core.security import generate_refresh_token, hash_token
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidEmailDomainException,
    TokenExpiredException,
    UserInfoNotFoundException,
    UserNotFoundException,
)


class AuthService:
    @staticmethod
    def is_allowed_email(email: str) -> bool:
        """허용된 이메일 도메인인지 확인"""
        return email.endswith(f"@{settings.allowed_email_domain}")

    @classmethod
    async def handle_google_login(cls, token: dict) -> Tuple[UserInDB, str, str]:
        """Google OAuth 콜백 처리: 유저 정보 검증 → 유저 생성/조회 → 토큰 발급"""
        user_info = token.get("userinfo")
        if not user_info:
            raise UserInfoNotFoundException()

        email = user_info.get("email")
        if not cls.is_allowed_email(email):
            raise InvalidEmailDomainException(settings.allowed_email_domain)

        user = await cls.get_or_create_user(
            google_id=user_info.get("sub"),
            email=email,
            name=user_info.get("name"),
            picture=user_info.get("picture"),
        )
        access_token, refresh_token = await cls.create_tokens(user)
        return user, access_token, refresh_token

    @classmethod
    async def get_or_create_user(
        cls,
        google_id: str,
        email: str,
        name: str,
        picture: Optional[str] = None
    ) -> UserInDB:
        """Google 로그인 후 유저 조회 또는 생성"""
        user = await UserRepository.get_by_google_id(google_id)
        if user:
            if user.name != name or user.picture != picture:
                updated = await UserRepository.update(
                    user.id,
                    name=name,
                    picture=picture
                )
                return updated or user
            return user

        # 신규 유저 생성
        user_create = UserCreate(
            email=email,
            name=name,
            google_id=google_id,
            picture=picture
        )
        return await UserRepository.create(user_create)

    @classmethod
    async def create_tokens(cls, user: UserInDB) -> Tuple[str, str]:
        """Access + Refresh 토큰 쌍 생성"""
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )

        refresh_token = generate_refresh_token()
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        await RefreshTokenRepository.create(
            RefreshTokenCreate(
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                expires_at=expires_at
            )
        )

        return access_token, refresh_token

    @classmethod
    async def refresh_tokens(cls, refresh_token: str) -> Tuple[str, str]:
        """Refresh token으로 새 토큰 쌍 발급. 실패 시 예외 발생."""
        token_hash = hash_token(refresh_token)
        stored_token = await RefreshTokenRepository.get_by_token_hash(token_hash)

        if not stored_token:
            raise InvalidCredentialsException("Invalid refresh token")

        if stored_token.expires_at < datetime.utcnow():
            await RefreshTokenRepository.revoke(token_hash)
            raise TokenExpiredException()

        # 기존 토큰 폐기
        await RefreshTokenRepository.revoke(token_hash)

        # 유저 조회 후 새 토큰 발급
        user = await UserRepository.get_by_id(stored_token.user_id)
        if not user:
            raise UserNotFoundException()

        return await cls.create_tokens(user)

    @classmethod
    async def logout(cls, user_id: str) -> int:
        """유저의 모든 refresh token 폐기"""
        return await RefreshTokenRepository.revoke_all_for_user(user_id)
