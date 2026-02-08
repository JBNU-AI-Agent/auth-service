from fastapi import APIRouter, Depends, Request
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from app.config import settings
from app.schemas.auth import (
    ErrorResponse,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from app.services.auth import AuthService
from app.core.dependencies import get_current_user, get_current_user_db
from app.core.exceptions import (
    AuthException,
    OAuthFailedException,
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


# Swagger 에러 응답 정의
_error_responses = {
    400: {"description": "Bad Request", "model": ErrorResponse},
    401: {"description": "Unauthorized", "model": ErrorResponse},
    403: {"description": "Forbidden", "model": ErrorResponse},
    404: {"description": "Not Found", "model": ErrorResponse},
    422: {"description": "Validation Error", "model": ErrorResponse},
    429: {"description": "Too Many Requests", "model": ErrorResponse},
    500: {"description": "Internal Server Error", "model": ErrorResponse},
}


# ==================== Google OAuth ====================

@router.get("/google", responses={429: _error_responses[429], 500: _error_responses[500]})
async def google_login(request: Request):
    """Google OAuth 로그인 시작"""
    rate_limiter.check_rate_limit(request, "login", **RateLimitConfig.LOGIN)
    return await oauth.google.authorize_redirect(
        request,
        settings.google_redirect_uri
    )


@router.get(
    "/google/callback",
    responses={
        400: _error_responses[400],
        403: _error_responses[403],
        429: _error_responses[429],
        500: _error_responses[500],
    },
)
async def google_callback(request: Request):
    """Google OAuth 콜백"""
    ip = get_client_ip(request)

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        log_login("unknown", ip=ip, success=False)
        raise OAuthFailedException(detail=f"OAuth failed: {str(e)}")

    try:
        user, access_token, refresh_token = await AuthService.handle_google_login(token)
    except AuthException:
        log_login("unknown", ip=ip, success=False)
        raise

    log_login(user.email, ip=ip, success=True)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


# ==================== Token Management ====================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: _error_responses[401],
        404: _error_responses[404],
        422: _error_responses[422],
        429: _error_responses[429],
        500: _error_responses[500],
    },
)
async def refresh_token(body: RefreshRequest, request: Request):
    """Refresh token으로 새 토큰 발급"""
    rate_limiter.check_rate_limit(request, "token_refresh", **RateLimitConfig.TOKEN_ISSUE)

    access_token, new_refresh_token = await AuthService.refresh_tokens(body.refresh_token)
    log_token_refresh("user", success=True)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post(
    "/logout",
    responses={
        401: _error_responses[401],
        500: _error_responses[500],
    },
)
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """로그아웃 (모든 refresh token 폐기)"""
    count = await AuthService.logout(current_user["sub"])
    log_logout(current_user["sub"], ip=get_client_ip(request))

    return {"message": "Logged out", "revoked_tokens": count}


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: _error_responses[401],
        404: _error_responses[404],
        500: _error_responses[500],
    },
)
async def get_me(current_user: UserInDB = Depends(get_current_user_db)):
    """현재 로그인한 유저 정보"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture,
        role=current_user.role.value
    )
