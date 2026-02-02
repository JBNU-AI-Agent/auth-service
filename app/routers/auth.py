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
)
from app.services.auth import AuthService
from app.services.client import ClientService
from app.core.jwt import decode_access_token, create_client_access_token
from app.repositories.user import UserRepository
from app.repositories.client import ClientRepository
from app.models.client import ClientCreate

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


@router.get("/google")
async def google_login(request: Request):
    """Google OAuth 로그인 시작"""
    return await oauth.google.authorize_redirect(
        request,
        settings.google_redirect_uri
    )


@router.get("/google/callback")
async def google_callback(request: Request):
    """Google OAuth 콜백"""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")

    email = user_info.get("email")
    if not AuthService.is_allowed_email(email):
        raise HTTPException(
            status_code=403,
            detail=f"Only @{settings.allowed_email_domain} emails are allowed"
        )

    user = await AuthService.get_or_create_user(
        google_id=user_info.get("sub"),
        email=email,
        name=user_info.get("name"),
        picture=user_info.get("picture")
    )

    access_token, refresh_token = await AuthService.create_tokens(user)

    # TODO: 프론트엔드로 리다이렉트 (쿼리 파라미터 또는 쿠키로 토큰 전달)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    """Refresh token으로 새 토큰 발급"""
    result = await AuthService.refresh_tokens(body.refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token, refresh_token = result
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout(request: Request):
    """로그아웃 (모든 refresh token 폐기)"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    count = await AuthService.logout(payload["sub"])
    return {"message": "Logged out", "revoked_tokens": count}


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request):
    """현재 로그인한 유저 정보"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await UserRepository.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role.value
    )


# ==================== Client Credentials ====================

@router.post("/token", response_model=ClientTokenResponse)
async def client_credentials_token(body: ClientCredentialsRequest):
    """
    Client Credentials Grant - MCP/Agent용 토큰 발급

    서버 간 통신에 사용. 사용자 로그인 없이 client_id/secret으로 인증.
    """
    client = await ClientService.authenticate_client(
        client_id=body.client_id,
        client_secret=body.client_secret
    )

    if not client:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    access_token = create_client_access_token(
        client_id=client.client_id,
        client_type=client.client_type.value,
        scopes=client.scopes
    )

    return ClientTokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/clients", response_model=ClientRegisterResponse)
async def register_client(body: ClientRegisterRequest, request: Request):
    """
    새 클라이언트(MCP서버/Agent) 등록

    주의: client_secret은 이 응답에서만 확인 가능. 안전하게 저장하세요.
    """
    # 관리자 권한 체크 (TODO: 나중에 강화)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin authentication required")

    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    client_create = ClientCreate(
        name=body.name,
        client_type=body.client_type,
        scopes=body.scopes
    )

    client, client_secret = await ClientService.register_client(client_create)

    return ClientRegisterResponse(
        client_id=client.client_id,
        client_secret=client_secret,
        name=client.name,
        client_type=client.client_type,
        scopes=client.scopes
    )


@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(request: Request):
    """등록된 클라이언트 목록 조회 (관리자용)"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin authentication required")

    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

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
