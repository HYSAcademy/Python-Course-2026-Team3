import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.logger import logger
from app.core.redis_client import init_redis_pool, get_redis_client, close_redis_pool
from app.services.pubsub_handler import RedisSubscriber
from app.services.handlers import handle_index_command, handle_search_request
from app.api.system import router as system_router

subscriber: RedisSubscriber | None = None
subscriber_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global subscriber, subscriber_task
    
    logger.info("Starting RAG Service infrastructure.")
    
    try:
        init_redis_pool()
        redis_client = get_redis_client()
        subscriber = RedisSubscriber(redis_client)
        subscriber.register_handler("rag_index_commands", handle_index_command)
        subscriber.register_handler("rag_search_requests", handle_search_request)
        subscriber_task = asyncio.create_task(subscriber.start())
        
        yield  
        
    finally:
        logger.info("Shutting down RAG Service infrastructure.")
        
        if subscriber:
            await subscriber.stop()
        
        if subscriber_task:
            subscriber_task.cancel()
            try:
                await subscriber_task
            except asyncio.CancelledError:
                pass
                
        await close_redis_pool()
            
        logger.info("RAG Service stopped cleanly.")

app = FastAPI(title=settings.project_name, lifespan=lifespan)
app.include_router(system_router)