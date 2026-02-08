from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Type

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(ABC):
    """MongoDB Repository 공통 추상 클래스"""

    @staticmethod
    @abstractmethod
    def _collection():
        """컬렉션 반환"""
        ...

    @staticmethod
    def _doc_to_model(doc: dict | None, model_cls: Type[T]) -> Optional[T]:
        """MongoDB 문서를 Pydantic 모델로 변환 (_id → str)"""
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return model_cls(**doc)

    @staticmethod
    def _to_object_id(doc_id: str) -> Optional[ObjectId]:
        """문자열을 ObjectId로 변환. 잘못된 형식이면 None 반환."""
        try:
            return ObjectId(doc_id)
        except InvalidId:
            return None

    @classmethod
    async def get_by_id(cls, doc_id: str, model_cls: Type[T]) -> Optional[T]:
        """ID로 문서 조회"""
        oid = cls._to_object_id(doc_id)
        if oid is None:
            return None
        doc = await cls._collection().find_one({"_id": oid})
        return cls._doc_to_model(doc, model_cls)

    @classmethod
    async def delete_by_id(cls, doc_id: str) -> bool:
        """ID로 문서 삭제"""
        oid = cls._to_object_id(doc_id)
        if oid is None:
            return False
        result = await cls._collection().delete_one({"_id": oid})
        return result.deleted_count > 0
