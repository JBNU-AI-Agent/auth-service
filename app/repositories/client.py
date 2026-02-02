from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.core.database import get_db
from app.models.client import ClientCreate, ClientInDB


class ClientRepository:
    @staticmethod
    def _collection():
        return get_db().clients

    @classmethod
    async def create(
        cls,
        client: ClientCreate,
        client_id: str,
        client_secret_hash: str
    ) -> ClientInDB:
        now = datetime.utcnow()
        doc = {
            **client.model_dump(),
            "client_id": client_id,
            "client_secret_hash": client_secret_hash,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        result = await cls._collection().insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return ClientInDB(**doc)

    @classmethod
    async def get_by_client_id(cls, client_id: str) -> Optional[ClientInDB]:
        doc = await cls._collection().find_one({
            "client_id": client_id,
            "is_active": True
        })
        if doc:
            doc["_id"] = str(doc["_id"])
            return ClientInDB(**doc)
        return None

    @classmethod
    async def deactivate(cls, client_id: str) -> bool:
        result = await cls._collection().update_one(
            {"client_id": client_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    @classmethod
    async def list_all(cls) -> list[ClientInDB]:
        cursor = cls._collection().find({"is_active": True})
        clients = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            clients.append(ClientInDB(**doc))
        return clients
