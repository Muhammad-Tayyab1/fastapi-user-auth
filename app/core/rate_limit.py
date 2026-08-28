from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Fixed-window limiter for a single API process.

    Production deployments with multiple workers should replace this store with Redis.
    """

    def __init__(self) -> None:
        self._attempts: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window: timedelta) -> None:
        now = datetime.now(UTC)
        cutoff = now - window
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= limit:
                retry_after = max(1, int((attempts[0] + window - now).total_seconds()))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(now)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


rate_limiter = InMemoryRateLimiter()


def client_ip(request: Request) -> str:
    # Do not trust X-Forwarded-For unless a trusted proxy is configured at deployment.
    return request.client.host if request.client else "unknown"

