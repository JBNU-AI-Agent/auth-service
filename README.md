# Authentic - AI Agent 인증 서버

FastAPI 기반 인증 서버. AI Agent/MCP 서버 인증용.

## 주요 기능

- **Google OAuth 로그인** (`@jbnu.ac.kr` 도메인만 허용)
- **JWT 토큰 인증** (RS256)
- **Client Credentials Grant** (MCP/Agent 서버 간 통신용)
- **JWKS 엔드포인트** (공개키 배포)

## 기술 스택

- **Framework**: FastAPI
- **Database**: MongoDB Cloud
- **Package Manager**: uv
- **인증**: Google OAuth 2.0 + JWT (RS256)
- **배포**: AWS EC2

## 토큰 정책

| 토큰 | 만료 시간 | 용도 |
|------|-----------|------|
| Access Token | 15분 | API 인증 |
| Refresh Token | 1주 | Access Token 갱신 |
| Client Token | 15분 | MCP/Agent 서버 인증 |

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│              인증 서버 (Authentic)                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [방법 1] Google OAuth - 사용자 로그인               │
│  User → /auth/google → Google 인증 → JWT 발급       │
│                                                     │
│  [방법 2] Client Credentials - 서버 간 통신          │
│  MCP/Agent → /auth/token → client_id/secret → JWT   │
│                                                     │
│  [토큰 검증] - 외부 서버에서                         │
│  /.well-known/jwks.json에서 공개키 조회 → 토큰 검증  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 프로젝트 구조

```
authentic/
├── app/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py            # 환경 설정
│   ├── core/
│   │   ├── database.py      # MongoDB 연결
│   │   ├── jwt.py           # JWT 발급/검증
│   │   ├── security.py      # RSA 키, 해싱
│   │   ├── dependencies.py  # FastAPI 의존성 주입
│   │   ├── exceptions.py    # 커스텀 예외
│   │   ├── logging.py       # 인증 이벤트 로깅
│   │   └── rate_limit.py    # Rate Limiting
│   ├── models/
│   │   ├── user.py          # 유저 모델
│   │   ├── token.py         # 토큰 모델
│   │   └── client.py        # 클라이언트 모델
│   ├── repositories/        # DB 접근 (Repository 패턴)
│   ├── routers/
│   │   ├── auth.py          # 인증 API
│   │   └── jwks.py          # JWKS API
│   ├── schemas/             # Pydantic 스키마
│   └── services/            # 비즈니스 로직
├── keys/                    # RSA 키 쌍 (자동 생성, git 제외)
├── pyproject.toml
└── uv.lock
```

## API 엔드포인트

### 사용자 인증

| Method | Path | 설명 |
|--------|------|------|
| GET | `/auth/google` | Google OAuth 로그인 시작 |
| GET | `/auth/google/callback` | OAuth 콜백 → 토큰 발급 |
| POST | `/auth/refresh` | Refresh Token으로 토큰 갱신 |
| POST | `/auth/logout` | 로그아웃 (Refresh Token 폐기) |
| GET | `/auth/me` | 현재 사용자 정보 조회 |

### Client Credentials (MCP/Agent용)

| Method | Path | 설명 | 권한 |
|--------|------|------|------|
| POST | `/auth/token` | Client 토큰 발급 | - |
| POST | `/auth/clients` | Client 등록 | admin |
| GET | `/auth/clients` | Client 목록 조회 | admin |
| PATCH | `/auth/clients/{client_id}` | Client 수정 | admin |
| DELETE | `/auth/clients/{client_id}` | Client 삭제 | admin |

### 공개키

| Method | Path | 설명 |
|--------|------|------|
| GET | `/.well-known/jwks.json` | JWKS 공개키 조회 |
| GET | `/health` | 헬스체크 |

## 설정

### 1. 환경 변수

```bash
cp .env.example .env
```

```env
# MongoDB
MONGODB_URI=mongodb+srv://...
MONGODB_DB_NAME=authentic

# Google OAuth (Google Cloud Console에서 발급)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# JWT
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Server
ALLOWED_EMAIL_DOMAIN=jbnu.ac.kr
CORS_ORIGINS=["http://localhost:3000"]
```

### 2. Google OAuth 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. APIs & Services → Credentials → OAuth 2.0 Client ID 생성
3. Authorized redirect URIs에 추가:
   - `http://localhost:8000/auth/google/callback` (개발)
   - `https://your-domain.com/auth/google/callback` (프로덕션)

## 실행

```bash
# 의존성 설치
uv sync

# 개발 서버 실행
uv run uvicorn app.main:app --reload

# API 문서
open http://localhost:8000/docs

# 테스트 실행
uv run pytest tests/ -v
```

## Rate Limiting

API 요청 제한이 적용됩니다:

| 엔드포인트 | 제한 |
|-----------|------|
| 로그인 시도 | 분당 5회 |
| 토큰 발급/갱신 | 분당 10회 |
| Client 인증 | 분당 20회 |

제한 초과 시 `429 Too Many Requests` 응답

## 사용 예시

### 1. 사용자 로그인

브라우저에서 `http://localhost:8000/auth/google` 접속

```json
// 응답
{
  "access_token": "eyJhbG...",
  "refresh_token": "xxx",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 2. 토큰 갱신

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "xxx"}'
```

### 3. Client 등록 (관리자)

```bash
curl -X POST http://localhost:8000/auth/clients \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MCP Server 1",
    "client_type": "mcp_server",
    "scopes": ["read", "write"]
  }'
```

```json
// 응답 (client_secret은 이때만 확인 가능!)
{
  "client_id": "client_a1b2c3d4",
  "client_secret": "xxx",
  "name": "MCP Server 1",
  "client_type": "mcp_server",
  "scopes": ["read", "write"]
}
```

### 4. Client 토큰 발급 (MCP/Agent)

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client_a1b2c3d4",
    "client_secret": "xxx"
  }'
```

### 5. 토큰 검증 (외부 서버)

```python
import httpx
from jose import jwt

# JWKS에서 공개키 가져오기
jwks = httpx.get("http://auth-server/.well-known/jwks.json").json()

# 토큰 검증
payload = jwt.decode(token, jwks, algorithms=["RS256"])
```

## JWT Payload

### 사용자 토큰

```json
{
  "sub": "user_id",
  "email": "user@jbnu.ac.kr",
  "role": "user",
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Client 토큰

```json
{
  "sub": "client_id",
  "client_type": "mcp_server",
  "scopes": ["read", "write"],
  "type": "client_credentials",
  "exp": 1234567890,
  "iat": 1234567890
}
```
