# Authentic - AI Agent 인증 서버

FastAPI 기반 인증 서버. AI Agent/MCP 서버 인증용.

## 주요 기능

- **Google OAuth 로그인** (`@jbnu.ac.kr` 도메인만 허용)
- **JWT 토큰 인증** (RS256)
- **Client Credentials Grant** (MCP/Agent 서버 간 통신용)
- **JWKS 엔드포인트** (공개키 배포)

## 기술 스택

- **Framework**: FastAPI
- **Database**: MongoDB Cloud (기존 클러스터)
- **인증**: Google OAuth 2.0 + JWT (RS256)
- **배포**: AWS EC2

## 토큰 정책

| 토큰 | 만료 시간 |
|------|-----------|
| Access Token | 15분 |
| Refresh Token | 1주 (MongoDB TTL) |

## 아키텍처

```
[사용자 로그인]
User → Google OAuth → 인증서버 → JWT 발급

[서버 간 통신]
MCP/Agent → Client Credentials → 인증서버 → JWT 발급

[토큰 검증]
외부 서버 → JWKS 엔드포인트에서 공개키 조회 → 토큰 검증
```

## 프로젝트 구조

```
app/
├── main.py              # FastAPI 앱 진입점
├── config.py            # 환경 설정
├── models/              # MongoDB 모델
├── schemas/             # Pydantic 스키마
├── routers/             # API 엔드포인트
├── services/            # 비즈니스 로직
├── repositories/        # DB 접근 (Repository 패턴)
└── core/                # JWT, 보안 유틸
```

## API 엔드포인트 (예정)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/auth/google` | Google OAuth 시작 |
| GET | `/auth/google/callback` | OAuth 콜백 |
| POST | `/auth/refresh` | 토큰 갱신 |
| POST | `/auth/logout` | 로그아웃 |
| POST | `/auth/token` | Client Credentials |
| GET | `/.well-known/jwks.json` | 공개키 조회 |

## 설정

```bash
cp .env.example .env
# .env 파일 수정
```

## 실행

```bash
uv sync
uv run uvicorn app.main:app --reload
```
