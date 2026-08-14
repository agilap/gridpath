from __future__ import annotations
import redis
from app.config import settings

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """
    Singleton Redis client for redis-py 4.6.0 + Upstash TLS.
    redis-py 4.6.0 accepts ssl_cert_reqs=None directly in from_url().
    Do not upgrade redis-py without testing TLS compatibility first.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.UPSTASH_REDIS_URL,
            ssl_cert_reqs=None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client