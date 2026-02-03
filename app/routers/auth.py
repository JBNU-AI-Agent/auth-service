from fastapi import APIRouter, HTTPException, Depends, Request
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from app.config import settings
from app.schemas.auth import (
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from app.services.auth import AuthService
from app.core.dependencies import get_current_user, get_current_user_db
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidEmailDomainException,
)
from app.core.logging import (
    log_login,
    log_logout,
    log_token_refresh,
)
from app.core.rate_limit import rate_limiter, RateLimitConfig
from app.models.user import UserInDB

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth 설정
config = Config(environ={
    "GOOGLE_CLIENT_ID": settings.google_client_id,
    "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
})
oauth = OAuth(config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ==================== Google OAuth ====================

@router.get("/google")
async def google_login(request: Request):
    """Google OAuth 로그인 시작"""
    rate_limiter.check_rate_limit(request, "login", **RateLimitConfig.LOGIN)
    return await oauth.google.authorize_redirect(
        request,
        settings.google_redirect_uri
    )


@router.get("/google/callback")
async def google_callback(request: Request):
    """Google OAuth 콜백"""
    ip = get_client_ip(request)

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        log_login("unknown", ip=ip, success=False)
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

    user_info = token.get("userinfo")
    if not user_info:
        log_login("unknown", ip=ip, success=False)
        raise HTTPException(status_code=400, detail="Failed to get user info")

    email = user_info.get("email")
    if not AuthService.is_allowed_email(email):
        log_login(email, ip=ip, success=False)
        raise InvalidEmailDomainException(settings.allowed_email_domain)

    user = await AuthService.get_or_create_user(
        google_id=user_info.get("sub"),
        email=email,
        name=user_info.get("name"),
        picture=user_info.get("picture")
    )

    access_token, refresh_token = await AuthService.create_tokens(user)

    log_login(email, ip=ip, success=True)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


# ==================== Token Management ====================

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, request: Request):
    """Refresh token으로 새 토큰 발급"""
    rate_limiter.check_rate_limit(request, "token_refresh", **RateLimitConfig.TOKEN_ISSUE)

    result = await AuthService.refresh_tokens(body.refresh_token)
    if not result:
        log_token_refresh("unknown", success=False)
        raise InvalidCredentialsException("Invalid refresh token")

    access_token, new_refresh_token = result
    log_token_refresh("user", success=True)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """로그아웃 (모든 refresh token 폐기)"""
    count = await AuthService.logout(current_user["sub"])
    log_logout(current_user["sub"], ip=get_client_ip(request))

    return {"message": "Logged out", "revoked_tokens": count}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user_db)):
    """현재 로그인한 유저 정보"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        role=current_user.role.value
    )


