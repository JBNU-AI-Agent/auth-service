from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError, ExpiredSignatureError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
import base64

from app.config import settings
from app.core.security import load_private_key, load_public_key
from app.core.exceptions import InvalidCredentialsException, TokenExpiredException


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    private_key = load_private_key()
    return jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Access token 디코딩. 실패 시 예외 발생."""
    try:
        public_key = load_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.jwt_algorithm]
        )
    except ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        raise InvalidCredentialsException("Invalid or malformed token")

    if payload.get("type") != "access":
        raise InvalidCredentialsException("Invalid token type")

    return payload


def get_jwks() -> dict:
    """JWKS 엔드포인트용 공개키 정보"""
    public_key_pem = load_public_key()
    public_key: RSAPublicKey = serialization.load_pem_public_key(
        public_key_pem.encode()
    )

    numbers = public_key.public_numbers()

    # RSA 파라미터를 Base64url로 인코딩
    def int_to_base64url(n: int) -> str:
        byte_length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(
            n.to_bytes(byte_length, byteorder='big')
        ).rstrip(b'=').decode('ascii')

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "key-1",
                "n": int_to_base64url(numbers.n),
                "e": int_to_base64url(numbers.e),
            }
        ]
    }
