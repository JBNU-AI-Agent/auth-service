from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user import UserCreate, UserInDB, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    @staticmethod
    def _collection():
        return get_db().users

    @classmethod
    async def create(cls, user: UserCreate) -> UserInDB:
        now = datetime.utcnow()
        doc = {
            **user.model_dump(),
            "role": UserRole.USER,
            "created_at": now,
            "updated_at": now,
        }
        result = await cls._collection().insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return UserInDB(**doc)

    @classmethod
    async def get_by_id(cls, user_id: str) -> Optional[UserInDB]:
        return await super().get_by_id(user_id, UserInDB)

    @classmethod
    async def get_by_email(cls, email: str) -> Optional[UserInDB]:
        doc = await cls._collection().find_one({"email": email})
        return cls._doc_to_model(doc, UserInDB)

    @classmethod
    async def get_by_google_id(cls, google_id: str) -> Optional[UserInDB]:
        doc = await cls._collection().find_one({"google_id": google_id})
        return cls._doc_to_model(doc, UserInDB)

    @classmethod
    async def update(cls, user_id: str, **fields) -> Optional[UserInDB]:
        oid = cls._to_object_id(user_id)
        if oid is None:
            return None
        fields["updated_at"] = datetime.utcnow()
        await cls._collection().update_one(
            {"_id": oid},
            {"$set": fields}
        )
        return await cls.get_by_id(user_id)
