import hashlib
import os
import secrets
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

KEYS_DIR = Path(__file__).parent.parent.parent / "keys"


def generate_rsa_keys():
    """RS256용 RSA 키 쌍 생성"""
    KEYS_DIR.mkdir(exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Private key 저장
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    (KEYS_DIR / "private_key.pem").write_bytes(private_pem)

    # Public key 저장
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (KEYS_DIR / "public_key.pem").write_bytes(public_pem)

    print(f"Keys generated at {KEYS_DIR}")


def load_private_key() -> str:
    """
    Private key 로드
    1순위: JWT_PRIVATE_KEY 환경 변수
    2순위: keys/private_key.pem 파일 (없으면 자동 생성)
    """
    if os.environ.get("JWT_PRIVATE_KEY"):
        return os.environ["JWT_PRIVATE_KEY"]

    key_path = KEYS_DIR / "private_key.pem"
    if not key_path.exists():
        generate_rsa_keys()
    return key_path.read_text()


def load_public_key() -> str:
    """
    Public key 로드
    1순위: JWT_PUBLIC_KEY 환경 변수
    2순위: keys/public_key.pem 파일 (없으면 자동 생성)
    """
    if os.environ.get("JWT_PUBLIC_KEY"):
        return os.environ["JWT_PUBLIC_KEY"]

    key_path = KEYS_DIR / "public_key.pem"
    if not key_path.exists():
        generate_rsa_keys()
    return key_path.read_text()


def hash_token(token: str) -> str:
    """토큰 해싱 (DB 저장용)"""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    """랜덤 refresh token 생성"""
    return secrets.token_urlsafe(32)
