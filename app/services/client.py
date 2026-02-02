import secrets
import hashlib
from typing import Optional, Tuple
from datetime import datetime, timedelta

from app.config import settings
from app.models.client import ClientCreate, ClientInDB
from app.repositories.client import ClientRepository
from app.core.security import hash_token


def generate_client_credentials() -> Tuple[str, str]:
    """client_id, client_secret 생성"""
    client_id = f"client_{secrets.token_hex(8)}"
    client_secret = secrets.token_urlsafe(32)
    return client_id, client_secret


def verify_client_secret(plain_secret: str, hashed_secret: str) -> bool:
    """client_secret 검증"""
    return hash_token(plain_secret) == hashed_secret


class ClientService:
    @classmethod
    async def register_client(cls, client: ClientCreate) -> Tuple[ClientInDB, str]:
        """
        새 클라이언트 등록
        Returns: (ClientInDB, plain_client_secret)
        주의: client_secret은 이때만 반환되고 다시 조회 불가
        """
        client_id, client_secret = generate_client_credentials()
        client_secret_hash = hash_token(client_secret)

        created = await ClientRepository.create(
            client=client,
            client_id=client_id,
            client_secret_hash=client_secret_hash
        )

        return created, client_secret

    @classmethod
    async def authenticate_client(
        cls,
        client_id: str,
        client_secret: str
    ) -> Optional[ClientInDB]:
        """클라이언트 인증"""
        client = await ClientRepository.get_by_client_id(client_id)
        if not client:
            return None

        if not verify_client_secret(client_secret, client.client_secret_hash):
            return None

        return client
