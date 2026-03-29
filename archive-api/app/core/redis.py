from redis.asyncio import Redis, ConnectionPool
from fastapi import Request
from app.core.config import settings


def create_redis_pool() -> ConnectionPool:
    return ConnectionPool.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
    )


async def get_redis(request: Request) -> Redis:
    return Redis(connection_pool=request.app.state.redis_pool)