from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

client: AsyncIOMotorClient = None
db: AsyncIOMotorDatabase = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    # TTL 인덱스 생성 (refresh_tokens 자동 만료)
    await db.refresh_tokens.create_index(
        "expires_at",
        expireAfterSeconds=0
    )
    # 유저 이메일 유니크 인덱스
    await db.users.create_index("email", unique=True)


async def close_db():
    global client
    if client:
        client.close()


def get_db() -> AsyncIOMotorDatabase:
    return db
