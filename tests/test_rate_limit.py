import pytest
from unittest.mock import MagicMock
from app.core.rate_limit import RateLimiter, RateLimitExceededException


def create_mock_request(ip: str = "127.0.0.1"):
    """테스트용 Mock Request 생성"""
    request = MagicMock()
    request.client.host = ip
    return request


def test_rate_limiter_allows_requests():
    """Rate Limiter가 정상 요청을 허용하는지 테스트"""
    limiter = RateLimiter()
    request = create_mock_request()

    # 5회 요청 허용
    for _ in range(5):
        result = limiter.check_rate_limit(
            request,
            "test_endpoint",
            max_requests=5,
            window_seconds=60
        )
        assert result is True


def test_rate_limiter_blocks_excess_requests():
    """Rate Limiter가 초과 요청을 차단하는지 테스트"""
    limiter = RateLimiter()
    request = create_mock_request()

    # 5회 허용
    for _ in range(5):
        limiter.check_rate_limit(
            request,
            "test_endpoint",
            max_requests=5,
            window_seconds=60
        )

    # 6번째 요청은 차단
    with pytest.raises(RateLimitExceededException):
        limiter.check_rate_limit(
            request,
            "test_endpoint",
            max_requests=5,
            window_seconds=60
        )


def test_rate_limiter_different_ips():
    """다른 IP는 별도로 카운트되는지 테스트"""
    limiter = RateLimiter()

    request1 = create_mock_request("192.168.1.1")
    request2 = create_mock_request("192.168.1.2")

    # IP 1에서 5회
    for _ in range(5):
        limiter.check_rate_limit(
            request1,
            "test_endpoint",
            max_requests=5,
            window_seconds=60
        )

    # IP 2에서는 여전히 허용
    result = limiter.check_rate_limit(
        request2,
        "test_endpoint",
        max_requests=5,
        window_seconds=60
    )
    assert result is True


def test_rate_limiter_different_endpoints():
    """다른 엔드포인트는 별도로 카운트되는지 테스트"""
    limiter = RateLimiter()
    request = create_mock_request()

    # endpoint_1에서 5회
    for _ in range(5):
        limiter.check_rate_limit(
            request,
            "endpoint_1",
            max_requests=5,
            window_seconds=60
        )

    # endpoint_2에서는 여전히 허용
    result = limiter.check_rate_limit(
        request,
        "endpoint_2",
        max_requests=5,
        window_seconds=60
    )
    assert result is True
