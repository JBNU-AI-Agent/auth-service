from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.core.database import get_db
from app.models.user import UserCreate, UserInDB, UserRole


class UserRepository:
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
        doc = await cls._collection().find_one({"_id": ObjectId(user_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            return UserInDB(**doc)
        return None

    @classmethod
    async def get_by_email(cls, email: str) -> Optional[UserInDB]:
        doc = await cls._collection().find_one({"email": email})
        if doc:
            doc["_id"] = str(doc["_id"])
            return UserInDB(**doc)
        return None

    @classmethod
    async def get_by_google_id(cls, google_id: str) -> Optional[UserInDB]:
        doc = await cls._collection().find_one({"google_id": google_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return UserInDB(**doc)
        return None

    @classmethod
    async def update(cls, user_id: str, **fields) -> Optional[UserInDB]:
        fields["updated_at"] = datetime.utcnow()
        await cls._collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": fields}
        )
        return await cls.get_by_id(user_id)
