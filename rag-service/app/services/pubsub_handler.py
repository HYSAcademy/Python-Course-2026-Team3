import asyncio
import json
from typing import Callable, Awaitable, Dict
from app.core.logger import logger 
from redis.asyncio import Redis

MessageHandler = Callable[[dict], Awaitable[None]]

class RedisSubscriber:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.pubsub = self.redis.pubsub()
        self._is_running = False
        self._handlers: Dict[str, MessageHandler] = {}

    def register_handler(self, channel: str, handler: MessageHandler):
        """Registers an async handler function for a specific Redis channel."""
        self._handlers[channel] = handler

    async def start(self):
        if not self._handlers:
            logger.warning("Starting subscriber with no registered handlers!")
            return

        channels = list(self._handlers.keys())
        await self.pubsub.subscribe(*channels)
        self._is_running = True
        logger.info(f"RAG Service listening to channels: {channels}.")

        while self._is_running:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    asyncio.create_task(self._dispatch_message(message))
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading from Redis: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _dispatch_message(self, message: dict):
        """Dispatches a message to the appropriate handler based on its channel."""
        channel = message["channel"]
        
        try:
            data = json.loads(message["data"])
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received in channel {channel}: {message['data']}")
            return

        correlation_id = data.get("correlation_id", "UNKNOWN")
        req_logger = logger.bind(correlation_id=correlation_id)
        
        req_logger.info(f"Dispatching message from '{channel}'")

        handler = self._handlers.get(channel)
        if handler:
            try:
                await handler(data)
            except Exception as e:
                req_logger.error(f"Error in handler for {channel}: {e}", exc_info=True)
        else:
            req_logger.warning(f"No handler found for channel '{channel}'")

    async def stop(self):
        self._is_running = False
        await self.pubsub.unsubscribe()
        await self.pubsub.aclose()
        logger.info("Redis Subscriber stopped cleanly.")