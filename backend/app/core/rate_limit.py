import time
from collections import defaultdict

from app.config import get_settings

settings = get_settings()

_attempts: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits() -> None:
    _attempts.clear()


def check_login_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window = settings.login_rate_window_seconds
    limit = settings.login_rate_limit

    _attempts[client_ip] = [t for t in _attempts[client_ip] if now - t < window]

    if len(_attempts[client_ip]) >= limit:
        return False

    _attempts[client_ip].append(now)
    return True
