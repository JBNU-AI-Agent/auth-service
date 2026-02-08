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
async def test_me_without_auth(client: AsyncClient):
    """인증 없이 /me 접근 시 에러"""
    response = await client.get("/auth/me")

    assert response.status_code in (401, 403)
