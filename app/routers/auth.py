from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from app.config import settings
from app.schemas.auth import (
    TokenResponse,
    RefreshRequest,
    UserResponse,
    ClientCredentialsRequest,
    ClientRegisterRequest,
    ClientRegisterResponse,
    ClientResponse,
    ClientTokenResponse,
    ClientUpdateRequest,
)
from app.services.auth import AuthService
from app.services.client import ClientService
from app.core.jwt import decode_access_token, create_client_access_token
from app.core.dependencies import get_current_user, get_current_user_db, require_admin
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidEmailDomainException,
    ClientNotFoundException,
)
from app.core.logging import (
    log_login,
    log_logout,
    log_token_refresh,
    log_client_auth,
    log_client_register,
)
from app.core.rate_limit import rate_limiter, RateLimitConfig
from app.repositories.user import UserRepository
from app.repositories.client import ClientRepository
from app.models.client import ClientCreate
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


# ==================== Client Credentials ====================

@router.post("/token", response_model=ClientTokenResponse)
async def client_credentials_token(body: ClientCredentialsRequest, request: Request):
    """
    Client Credentials Grant - MCP/Agent용 토큰 발급
    """
    ip = get_client_ip(request)
    rate_limiter.check_rate_limit(request, "client_auth", **RateLimitConfig.CLIENT_AUTH)

    client = await ClientService.authenticate_client(
        client_id=body.client_id,
        client_secret=body.client_secret
    )

    if not client:
        log_client_auth(body.client_id, ip=ip, success=False)
        raise InvalidCredentialsException("Invalid client credentials")

    access_token = create_client_access_token(
        client_id=client.client_id,
        client_type=client.client_type.value,
        scopes=client.scopes
    )

    log_client_auth(client.client_id, ip=ip, success=True)

    return ClientTokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


# ==================== Client Management (Admin) ====================

@router.post("/clients", response_model=ClientRegisterResponse)
async def register_client(
    body: ClientRegisterRequest,
    admin: dict = Depends(require_admin)
):
    """새 클라이언트(MCP서버/Agent) 등록"""
    client_create = ClientCreate(
        name=body.name,
        client_type=body.client_type,
        scopes=body.scopes
    )

    client, client_secret = await ClientService.register_client(client_create)
    log_client_register(client.client_id, client.name, admin["sub"])

    return ClientRegisterResponse(
        client_id=client.client_id,
        client_secret=client_secret,
        name=client.name,
        client_type=client.client_type,
        scopes=client.scopes
    )


@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(admin: dict = Depends(require_admin)):
    """등록된 클라이언트 목록 조회"""
    clients = await ClientRepository.list_all()
    return [
        ClientResponse(
            client_id=c.client_id,
            name=c.name,
            client_type=c.client_type,
            scopes=c.scopes,
            is_active=c.is_active
        )
        for c in clients
    ]


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    body: ClientUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """클라이언트 정보 수정"""
    client = await ClientRepository.update(
        client_id=client_id,
        name=body.name,
        scopes=body.scopes
    )

    if not client:
        raise ClientNotFoundException()

    return ClientResponse(
        client_id=client.client_id,
        name=client.name,
        client_type=client.client_type,
        scopes=client.scopes,
        is_active=client.is_active
    )


@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: str,
    admin: dict = Depends(require_admin)
):
    """클라이언트 삭제"""
    deleted = await ClientRepository.delete(client_id)

    if not deleted:
        raise ClientNotFoundException()

    return {"message": "Client deleted", "client_id": client_id}
