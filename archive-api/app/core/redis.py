from redis.asyncio import Redis
from app.core.config import settings

async def get_redis() -> Redis:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()