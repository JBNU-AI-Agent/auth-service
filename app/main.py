import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.core.database import connect_db, close_db
from app.core.exceptions import AuthException, ErrorCode
from app.routers import auth, jwks

logger = logging.getLogger(__name__)


def _build_error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> dict:
    """표준 에러 응답 본문 생성"""
    body = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "status": status,
        "code": code,
        "message": message,
    }
    if details:
        body["details"] = details
    return body


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


@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException):
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_response(
            request,
            status=exc.status_code,
            code=exc.error_code.value,
            message=exc.detail,
        ),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details[field] = error["msg"]
    return JSONResponse(
        status_code=422,
        content=_build_error_response(
            request,
            status=422,
            code=ErrorCode.VALIDATION_ERROR.value,
            message="Request validation failed",
            details=details,
        ),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            request,
            status=500,
            code=ErrorCode.INTERNAL_ERROR.value,
            message="Internal server error",
        ),
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
