from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=settings.redis_max_connections,
    socket_timeout=5,
    socket_connect_timeout=3,
    retry_on_timeout=True,
    health_check_interval=30,
    decode_responses=True,
)

redis_client = redis.Redis(connection_pool=redis_pool)


async def get_redis() -> redis.Redis:
    return redis_client
