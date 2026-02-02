import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_jwks_endpoint(client: AsyncClient):
    """JWKS 엔드포인트 테스트"""
    response = await client.get("/.well-known/jwks.json")

    assert response.status_code == 200

    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) > 0


@pytest.mark.asyncio
async def test_refresh_without_token(client: AsyncClient):
    """Refresh Token 없이 요청 시 에러"""
    response = await client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_auth(client: AsyncClient):
    """인증 없이 /me 접근 시 에러"""
    response = await client.get("/auth/me")

    assert response.status_code == 403  # HTTPBearer가 자동으로 403 반환


@pytest.mark.asyncio
async def test_client_token_invalid_credentials(client: AsyncClient):
    """잘못된 Client Credentials로 토큰 요청"""
    response = await client.post(
        "/auth/token",
        json={
            "client_id": "invalid_client",
            "client_secret": "invalid_secret"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_clients_list_without_admin(client: AsyncClient):
    """관리자가 아닌 경우 Client 목록 조회 실패"""
    response = await client.get("/auth/clients")

    assert response.status_code == 403
