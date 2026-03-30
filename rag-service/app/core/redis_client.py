from redis.asyncio import ConnectionPool, Redis
from app.core.config import settings

redis_pool: ConnectionPool | None = None

def init_redis_pool():
    global redis_pool
    redis_pool = ConnectionPool.from_url(settings.redis_url, decode_responses=True)

def get_redis_client() -> Redis:
    if not redis_pool:
        raise RuntimeError("Redis pool is not initialized")
    return Redis(connection_pool=redis_pool)

async def close_redis_pool():
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()