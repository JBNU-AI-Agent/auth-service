from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.token import RefreshTokenCreate, RefreshTokenInDB
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository):
    @staticmethod
    def _collection():
        return get_db().refresh_tokens

    @classmethod
    async def create(cls, token: RefreshTokenCreate) -> RefreshTokenInDB:
        doc = {
            **token.model_dump(),
            "created_at": datetime.utcnow(),
            "revoked": False,
        }
        result = await cls._collection().insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return RefreshTokenInDB(**doc)

    @classmethod
    async def get_by_token_hash(cls, token_hash: str) -> Optional[RefreshTokenInDB]:
        doc = await cls._collection().find_one({
            "token_hash": token_hash,
            "revoked": False
        })
        return cls._doc_to_model(doc, RefreshTokenInDB)

    @classmethod
    async def revoke(cls, token_hash: str) -> bool:
        result = await cls._collection().update_one(
            {"token_hash": token_hash},
            {"$set": {"revoked": True}}
        )
        return result.modified_count > 0

    @classmethod
    async def revoke_all_for_user(cls, user_id: str) -> int:
        result = await cls._collection().update_many(
            {"user_id": user_id, "revoked": False},
            {"$set": {"revoked": True}}
        )
        return result.modified_count
