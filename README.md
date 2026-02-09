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
│   ├── main.py                # FastAPI 앱, 글로벌 예외 핸들러
│   ├── config.py              # 환경 변수 설정 (Pydantic Settings)
│   ├── core/
│   │   ├── database.py        # MongoDB 연결 (Motor async)
│   │   ├── jwt.py             # JWT 발급/검증 (RS256)
│   │   ├── security.py        # RSA 키 관리, 토큰 해싱
│   │   ├── dependencies.py    # FastAPI 의존성 (인증 미들웨어)
│   │   ├── exceptions.py      # ErrorCode enum, 커스텀 예외 클래스
│   │   ├── logging.py         # 구조화된 인증 이벤트 로깅
│   │   └── rate_limit.py      # IP 기반 Rate Limiting
│   ├── models/
│   │   ├── user.py            # User 도메인 모델 (UserInDB, UserCreate)
│   │   └── token.py           # RefreshToken 도메인 모델
│   ├── repositories/
│   │   ├── base.py            # BaseRepository (공통 CRUD, ObjectId 변환)
│   │   ├── user.py            # UserRepository (조회, 생성, 수정)
│   │   └── token.py           # RefreshTokenRepository (발급, 폐기)
│   ├── routers/
│   │   ├── auth.py            # 인증 API 엔드포인트
│   │   └── jwks.py            # JWKS 공개키 엔드포인트
│   ├── schemas/
│   │   └── auth.py            # API 요청/응답 스키마 (TokenResponse, ErrorResponse)
│   └── services/
│       └── auth.py            # 인증 비즈니스 로직 (OAuth, 토큰 관리)
├── tests/
│   ├── conftest.py            # 테스트 설정 (TestClient)
│   ├── test_auth.py           # 인증 API 테스트
│   ├── test_health.py         # 헬스체크 테스트
│   ├── test_jwt.py            # JWT 발급/검증 테스트
│   └── test_rate_limit.py     # Rate Limiting 테스트
├── keys/                      # RSA 키 쌍 (자동 생성, git 제외)
├── .env.example               # 환경 변수 템플릿
├── pyproject.toml
└── uv.lock
```

### 레이어 구조

```
Router (HTTP 요청/응답) → Service (비즈니스 로직) → Repository (DB 접근)
         ↓                        ↓                        ↓
  요청 파싱, 응답 포맷팅      검증, 예외 발생          MongoDB CRUD
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

### 로컬 개발

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

### Docker

```bash
# 빌드 및 실행 (포트 8880)
docker compose up --build -d

# 로그 확인
docker compose logs -f

# 중지
docker compose down
```

## 배포 (CI/CD)

GitHub Actions를 통해 `main` 브랜치 push 시 AWS EC2에 자동 배포됩니다.

### 배포 흐름

```
main push → GitHub Actions → SSH EC2 → git pull → .env 생성 → docker compose up --build -d → health check
```

### GitHub Secrets 설정

GitHub 리포 → **Settings → Secrets and variables → Actions**에서 등록:

| Secret | 설명 |
|---|---|
| `SSH_PRIVATE_KEY` | EC2 접속용 PEM 키 파일 내용 전체 |
| `SSH_HOST` | EC2 퍼블릭 IP |
| `SSH_USERNAME` | EC2 SSH 유저명 (`ubuntu`) |
| `MONGODB_URI` | MongoDB Atlas 연결 문자열 |
| `MONGODB_DB_NAME` | MongoDB 데이터베이스 이름 |
| `GOOGLE_CLIENT_ID` | Google OAuth 클라이언트 ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 클라이언트 시크릿 |
| `GOOGLE_REDIRECT_URI` | OAuth 콜백 URL (`http://<EC2_IP>:8880/auth/google/callback`) |
| `JWT_PRIVATE_KEY` | RSA 개인키 (PEM 형식) |
| `JWT_PUBLIC_KEY` | RSA 공개키 (PEM 형식) |
| `ALLOWED_EMAIL_DOMAIN` | 허용 이메일 도메인 |
| `CORS_ORIGINS` | CORS 허용 출처 목록 |

## Rate Limiting

API 요청 제한이 적용됩니다:

| 엔드포인트 | 제한 |
|-----------|------|
| 로그인 시도 | 분당 5회 |
| 토큰 발급/갱신 | 분당 10회 |

제한 초과 시 `429 Too Many Requests` 응답

## 에러 처리

모든 API 에러는 통일된 포맷으로 응답합니다.

### 에러 응답 포맷

```json
{
  "timestamp": "2025-01-15T12:00:00+00:00",
  "path": "/auth/refresh",
  "status": 401,
  "code": "TOKEN_EXPIRED",
  "message": "Token has expired",
  "details": null
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `timestamp` | string | 에러 발생 시각 (ISO 8601) |
| `path` | string | 요청 경로 |
| `status` | int | HTTP 상태 코드 |
| `code` | string | 머신 리더블 에러 코드 |
| `message` | string | 사람이 읽을 수 있는 에러 메시지 |
| `details` | object \| null | 추가 정보 (Validation 에러 시 필드별 오류) |

### 에러 코드 목록

| 코드 | HTTP 상태 | 설명 |
|------|-----------|------|
| `INVALID_CREDENTIALS` | 401 | 유효하지 않은 인증 정보 |
| `TOKEN_EXPIRED` | 401 | 토큰 만료 |
| `INSUFFICIENT_PERMISSION` | 403 | 권한 부족 |
| `INVALID_EMAIL_DOMAIN` | 403 | 허용되지 않은 이메일 도메인 |
| `USER_NOT_FOUND` | 404 | 사용자를 찾을 수 없음 |
| `OAUTH_FAILED` | 400 | OAuth 인증 실패 |
| `USER_INFO_NOT_FOUND` | 400 | OAuth 제공자에서 사용자 정보 조회 실패 |
| `VALIDATION_ERROR` | 422 | 요청 유효성 검증 실패 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 제한 초과 |
| `INTERNAL_ERROR` | 500 | 서버 내부 오류 |

### Validation 에러

요청 유효성 검증 실패 시 `details`에 필드별 오류가 포함됩니다:

```json
{
  "timestamp": "2025-01-15T12:00:00+00:00",
  "path": "/auth/refresh",
  "status": 422,
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": {
    "refresh_token": "Field required"
  }
}
```

### 예외 처리 구조

3단계 글로벌 예외 핸들러로 모든 에러를 캐치합니다:

```
1. AuthException       → 커스텀 비즈니스 예외 (에러 코드 포함)
2. RequestValidationError → Pydantic 유효성 검증 실패
3. Exception           → 예상치 못한 서버 오류 (500)
```

클라이언트는 `code` 필드로 에러 종류를 구분할 수 있습니다:

```python
response = requests.post("/auth/refresh", json={"refresh_token": "..."})
if response.status_code != 200:
    error = response.json()
    if error["code"] == "TOKEN_EXPIRED":
        # 재로그인 유도
    elif error["code"] == "INVALID_CREDENTIALS":
        # 잘못된 토큰 처리
```

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
