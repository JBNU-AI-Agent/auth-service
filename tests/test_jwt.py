import pytest

from app.core.jwt import (
    create_access_token,
    decode_access_token,
    get_jwks,
)
from app.core.exceptions import InvalidCredentialsException


def test_create_access_token():
    """사용자 Access Token 생성 테스트"""
    token = create_access_token(
        user_id="test_user_id",
        email="test@jbnu.ac.kr",
        role="user"
    )

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token():
    """Access Token 디코딩 테스트"""
    token = create_access_token(
        user_id="test_user_id",
        email="test@jbnu.ac.kr",
        role="admin"
    )

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "test_user_id"
    assert payload["email"] == "test@jbnu.ac.kr"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_decode_invalid_token():
    """잘못된 토큰 디코딩 시 예외 발생"""
    with pytest.raises(InvalidCredentialsException):
        decode_access_token("invalid_token")


def test_get_jwks():
    """JWKS 공개키 조회 테스트"""
    jwks = get_jwks()

    assert "keys" in jwks
    assert len(jwks["keys"]) > 0

    key = jwks["keys"][0]
    assert key["kty"] == "RSA"
    assert key["use"] == "sig"
    assert key["alg"] == "RS256"
    assert "n" in key
    assert "e" in key
