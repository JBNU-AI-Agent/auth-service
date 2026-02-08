from enum import Enum

from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """API 에러 코드"""
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSION = "INSUFFICIENT_PERMISSION"
    INVALID_EMAIL_DOMAIN = "INVALID_EMAIL_DOMAIN"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    OAUTH_FAILED = "OAUTH_FAILED"
    USER_INFO_NOT_FOUND = "USER_INFO_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AuthException(HTTPException):
    """인증 관련 기본 예외"""
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        headers: dict | None = None,
    ):
        self.error_code = error_code
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class InvalidCredentialsException(AuthException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=ErrorCode.INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            error_code=ErrorCode.TOKEN_EXPIRED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InsufficientPermissionException(AuthException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=ErrorCode.INSUFFICIENT_PERMISSION,
        )


class InvalidEmailDomainException(AuthException):
    def __init__(self, allowed_domain: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only @{allowed_domain} emails are allowed",
            error_code=ErrorCode.INVALID_EMAIL_DOMAIN,
        )


class RateLimitExceededException(AuthException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            headers={"Retry-After": str(retry_after)},
        )


class UserNotFoundException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            error_code=ErrorCode.USER_NOT_FOUND,
        )


class OAuthFailedException(AuthException):
    def __init__(self, detail: str = "OAuth authentication failed"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=ErrorCode.OAUTH_FAILED,
        )


class UserInfoNotFoundException(AuthException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from OAuth provider",
            error_code=ErrorCode.USER_INFO_NOT_FOUND,
        )
