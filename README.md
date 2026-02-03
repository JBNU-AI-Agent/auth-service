# Authentic - AI Agent 인증 서버

FastAPI 기반 인증 서버. AI Agent/MCP 서버 인증용.

## 주요 기능

- **Google OAuth 로그인** (`@jbnu.ac.kr` 도메인만 허용)
- **JWT 토큰 인증** (RS256 비대칭키 방식)
- **JWKS 엔드포인트** (공개키 배포)

## 기술 스택

- **Framework**: FastAPI
- **Database**: MongoDB Cloud
- **Package Manager**: uv
- **인증**: Google OAuth 2.0 + JWT (RS256)
- **배포**: AWS EC2

## 왜 RS256인가?

JWT 서명 알고리즘으로 RS256(비대칭키)을 사용합니다.

| | HS256 (대칭키) | RS256 (비대칭키) |
|---|---|---|
| 키 | 하나의 시크릿 공유 | 개인키/공개키 분리 |
| 서명 | 시크릿으로 서명 | **개인키**로 서명 |
| 검증 | 같은 시크릿으로 검증 | **공개키**로 검증 |
| 키 유출 시 | 토큰 위조 가능 | 공개키는 유출돼도 무방 |

**RS256 선택 이유:**
- 메인 백엔드, MCP 서버 등 **여러 서비스가 토큰 검증** 필요
- 검증 서버는 **공개키만** 가지므로 토큰 위조 불가능
- Auth 서버 장애 시에도 공개키 캐싱하면 **검증 지속 가능**
- JWKS 엔드포인트로 **키 로테이션 용이**

```
┌──────────────┐              ┌──────────────┐
│  Auth 서버   │   공개키     │  메인 백엔드  │
│  (개인키)    │ ───────────▶ │  (공개키)    │
└──────────────┘              └──────────────┘
   서명만 가능                   검증만 가능
```

## 토큰 정책

| 토큰 | 만료 시간 | 용도 |
|------|-----------|------|
| Access Token | 15분 | API 인증 |
| Refresh Token | 1주 | Access Token 갱신 |

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│              인증 서버 (Authentic)                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [로그인] Google OAuth                              │
│  User → /auth/google → Google 인증 → JWT 발급       │
│                                                     │
│  [토큰 검증] 외부 서버에서 (RS256)                   │
│  /.well-known/jwks.json → 공개키 조회 → 토큰 검증   │
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
│   │   ├── jwt.py           # JWT 발급/검증 (RS256)
│   │   ├── security.py      # RSA 키 관리
│   │   ├── dependencies.py  # FastAPI 의존성 주입
│   │   ├── exceptions.py    # 커스텀 예외
│   │   ├── logging.py       # 인증 이벤트 로깅
│   │   └── rate_limit.py    # Rate Limiting
│   ├── models/
│   │   ├── user.py          # 유저 모델
│   │   └── token.py         # 토큰 모델
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

### 인증

| Method | Path | 설명 |
|--------|------|------|
| GET | `/auth/google` | Google OAuth 로그인 시작 |
| GET | `/auth/google/callback` | OAuth 콜백 → JWT 토큰 발급 |
| POST | `/auth/refresh` | Refresh Token으로 토큰 갱신 |
| POST | `/auth/logout` | 로그아웃 (Refresh Token 폐기) |
| GET | `/auth/me` | 현재 사용자 정보 조회 |

### 공개키 (JWKS)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/.well-known/jwks.json` | RS256 공개키 조회 (토큰 검증용) |
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

# JWT RSA Keys (선택 - 미설정 시 자동 생성)
# JWT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----
# JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----

# Server
ALLOWED_EMAIL_DOMAIN=jbnu.ac.kr
CORS_ORIGINS=["http://localhost:3000"]
```

### RSA 키 설정

| 환경 | 키 관리 방식 |
|------|-------------|
| 로컬 개발 | 자동 생성 (`keys/` 폴더) |
| 배포 (EC2 등) | 환경변수로 주입 |

**배포 시 키 생성:**
```bash
# RSA 키 쌍 생성
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem

# 환경변수용 단일 라인 변환
awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' private.pem
awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' public.pem
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

### 3. 토큰 검증 (외부 서버에서)

메인 백엔드나 MCP 서버에서 JWT를 검증하는 방법:

```python
import httpx
from jose import jwt, jwk
from jose.utils import base64url_decode

# 1. JWKS에서 공개키 가져오기
jwks = httpx.get("http://auth-server/.well-known/jwks.json").json()

# 2. 토큰 헤더에서 kid 추출
header = jwt.get_unverified_header(token)
kid = header["kid"]

# 3. 해당 kid의 공개키 찾기
key = next(k for k in jwks["keys"] if k["kid"] == kid)

# 4. 토큰 검증 (서명 확인 + 만료 체크)
payload = jwt.decode(
    token,
    key,
    algorithms=["RS256"],
    audience="your-service"  # 필요시
)
```

**핵심**: Auth 서버에 요청하지 않고 **공개키만으로 검증** 가능

## JWT Payload

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

| 필드 | 설명 |
|------|------|
| `sub` | 사용자 고유 ID |
| `email` | 이메일 주소 |
| `role` | 권한 (user, admin) |
| `type` | 토큰 타입 (access) |
| `exp` | 만료 시간 (Unix timestamp) |
| `iat` | 발급 시간 (Unix timestamp) |
