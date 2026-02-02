from fastapi import APIRouter
from app.core.jwt import get_jwks

router = APIRouter(tags=["jwks"])


@router.get("/.well-known/jwks.json")
async def jwks():
    """공개키 JWKS 엔드포인트"""
    return get_jwks()
