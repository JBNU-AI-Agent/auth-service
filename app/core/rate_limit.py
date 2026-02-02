from datetime import datetime, timedelta
from typing import Dict, Tuple
from fastapi import Request

from app.core.exceptions import RateLimitExceededException


class RateLimiter:
    """
    인메모리 Rate Limiter
    프로덕션에서는 Redis 사용 권장
    """

    def __init__(self):
        # {key: (count, window_start)}
        self._requests: Dict[str, Tuple[int, datetime]] = {}

    def _get_key(self, request: Request, endpoint: str) -> str:
        """IP + 엔드포인트로 키 생성"""
        client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}:{endpoint}"

    def _cleanup_old_entries(self):
        """오래된 엔트리 정리"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, window_start) in self._requests.items()
            if now - window_start > timedelta(minutes=5)
        ]
        for key in expired_keys:
            del self._requests[key]

    def check_rate_limit(
        self,
        request: Request,
        endpoint: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> bool:
        """
        Rate limit 체크

        Args:
            request: FastAPI Request
            endpoint: 엔드포인트 식별자
            max_requests: 윈도우 내 최대 요청 수
            window_seconds: 윈도우 크기 (초)

        Returns:
            True if allowed, raises RateLimitExceededException if exceeded
        """
        self._cleanup_old_entries()

        key = self._get_key(request, endpoint)
        now = datetime.utcnow()

        if key in self._requests:
            count, window_start = self._requests[key]

            # 윈도우 만료 체크
            if now - window_start > timedelta(seconds=window_seconds):
                self._requests[key] = (1, now)
                return True

            # 요청 수 체크
            if count >= max_requests:
                retry_after = window_seconds - int((now - window_start).total_seconds())
                raise RateLimitExceededException(retry_after=max(1, retry_after))

            self._requests[key] = (count + 1, window_start)
        else:
            self._requests[key] = (1, now)

        return True


# 싱글톤 인스턴스
rate_limiter = RateLimiter()


# 설정별 Rate Limit
class RateLimitConfig:
    # 토큰 발급: 분당 10회
    TOKEN_ISSUE = {"max_requests": 10, "window_seconds": 60}

    # 로그인 시도: 분당 5회
    LOGIN = {"max_requests": 5, "window_seconds": 60}

    # Client 인증: 분당 20회
    CLIENT_AUTH = {"max_requests": 20, "window_seconds": 60}

    # 일반 API: 분당 100회
    API = {"max_requests": 100, "window_seconds": 60}
