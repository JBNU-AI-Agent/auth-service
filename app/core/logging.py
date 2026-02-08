import logging
import sys
from datetime import datetime
from typing import Optional

# 로거 설정
logger = logging.getLogger("authentic")
logger.setLevel(logging.INFO)

# 콘솔 핸들러
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# 포맷터
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


def log_auth_event(
    event: str,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    client_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    detail: Optional[str] = None
):
    """인증 이벤트 로깅"""
    log_data = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
        "success": success,
    }
    optional = {
        "user_id": user_id,
        "email": email,
        "client_id": client_id,
        "ip": ip_address,
        "detail": detail,
    }
    log_data.update({k: v for k, v in optional.items() if v is not None})

    if success:
        logger.info(f"AUTH: {log_data}")
    else:
        logger.warning(f"AUTH_FAILED: {log_data}")


def log_login(email: str, ip: Optional[str] = None, success: bool = True):
    log_auth_event("LOGIN", email=email, ip_address=ip, success=success)


def log_logout(user_id: str, ip: Optional[str] = None):
    log_auth_event("LOGOUT", user_id=user_id, ip_address=ip)


def log_token_refresh(user_id: str, success: bool = True):
    log_auth_event("TOKEN_REFRESH", user_id=user_id, success=success)


