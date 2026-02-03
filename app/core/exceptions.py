from fastapi import HTTPException, status


class AuthException(HTTPException):
    """인증 관련 기본 예외"""
    pass


class InvalidCredentialsException(AuthException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InsufficientPermissionException(AuthException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class InvalidEmailDomainException(AuthException):
    def __init__(self, allowed_domain: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only @{allowed_domain} emails are allowed",
        )


class RateLimitExceededException(AuthException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


class UserNotFoundException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
