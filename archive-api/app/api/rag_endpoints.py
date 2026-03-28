import uuid
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.logger import logger
from app.db.database import get_db
from app.repositories.archive_repo import ArchiveRepository
from app.schemas.contracts import (
    RagIndexResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from app.core.redis import get_redis

router = APIRouter(prefix="/rag", tags=["RAG"])

RAG_SEARCH_TIMEOUT = 15


@router.post(
    "/index/{archive_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RagIndexResponse,
)
async def rag_index_archive(
    archive_id: str,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Triggers vector indexing for an archive via Redis Pub/Sub.
    """
    repo = ArchiveRepository(session)
    archive = await repo.get_archive_by_id(archive_id)

    if not archive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archive with ID {archive_id} not found.",
        )

    correlation_id = str(uuid.uuid4())
    payload = json.dumps({
        "archive_id": archive_id,
        "correlation_id": correlation_id,
    })
    await redis.publish("rag_index_commands", payload)
    logger.info(f"[RAG Index] Published to rag_index_commands | archive_id={archive_id} | correlation_id={correlation_id}")

    return RagIndexResponse(
        archive_id=archive_id,
        correlation_id=correlation_id,
        message="Vector indexing task has been queued.",
    )


@router.post(
    "/search",
    status_code=status.HTTP_200_OK,
    response_model=RagSearchResponse,
)
async def rag_search(
    request: RagSearchRequest,
    redis: Redis = Depends(get_redis),
):
    """
    Performs semantic vector search via Redis Pub/Sub.
    Waits for RAG service response with timeout.
    """
    correlation_id = str(uuid.uuid4())
    payload = json.dumps({
        "query": request.query,
        "top_k": request.top_k,
        "correlation_id": correlation_id,
    })

    response_channel = f"rag_responses:{correlation_id}"
    pubsub = redis.pubsub()
    await pubsub.subscribe(response_channel)

    await redis.publish("rag_search_requests", payload)
    logger.info(f"[RAG Search] Published to rag_search_requests | correlation_id={correlation_id}")

    try:
        async def wait_for_response():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    return json.loads(message["data"])

        result = await asyncio.wait_for(wait_for_response(), timeout=RAG_SEARCH_TIMEOUT)

    except asyncio.TimeoutError:
        logger.warning(f"[RAG Search] Timeout waiting for response | correlation_id={correlation_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="RAG service did not respond in time. Please try again later.",
        )
    finally:
        await pubsub.unsubscribe(response_channel)
        await pubsub.aclose()

    return RagSearchResponse(
        correlation_id=correlation_id,
        query=request.query,
        answer=result.get("answer", ""),
    )