from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.core.database import connect_db, close_db
from app.routers import auth, jwks


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Authentic",
    description="AI Agent/MCP 인증 서버",
    version="0.1.0",
    lifespan=lifespan,
)

# 세션 미들웨어 (OAuth state 저장용)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.google_client_secret,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router)
app.include_router(jwks.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
