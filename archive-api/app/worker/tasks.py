import asyncio
import aioboto3
from celery import Task
from celery.exceptions import MaxRetriesExceededError

from app.core.config import settings
from app.core.logger import logger
from app.core.celery_app import celery_app
from app.db.database import AsyncSessionLocal
from app.repositories.archive_repo import ArchiveRepository
from app.schemas.contracts import ArchiveStatus
from app.services.archive_svc import ArchiveService 
from app.core.exceptions import NonRetryableError
from app.core.s3 import get_s3_client


async def _execute_processing_command(archive_id: str) -> None:
    """Asynchronous Command Handler."""
    async with get_s3_client() as s3_client:
        processor = ArchiveService(s3_client=s3_client)
        await processor.process_archive(archive_id)


async def _execute_dlq_fallback(archive_id: str, error_msg: str) -> None:
    """Dead Letter Queue (DLQ) logic: safely mark the archive as FAILED."""
    async with AsyncSessionLocal() as session:
        repo = ArchiveRepository(session)
        await repo.update_status(
            archive_id=archive_id,
            status=ArchiveStatus.FAILED,
            error_message=error_msg,
        )
        await session.commit()


@celery_app.task(
    bind=True, 
    max_retries=3, 
    default_retry_delay=10, 
    acks_late=True,
    reject_on_worker_lost=True
)
def process_archive_task(self: Task, archive_id: str) -> None:
    """Synchronous Celery wrapper."""
    logger.info(f"[Task ID: {self.request.id}] Start processing archive: {archive_id}")
    
    try:
        asyncio.run(_execute_processing_command(archive_id))
        logger.info(f"[Task ID: {self.request.id}] Archive {archive_id} processed successfully.")

    except NonRetryableError as fatal_exc:
        logger.error(f"Fatal error for archive {archive_id}. Fail fast. Details: {fatal_exc}")
        asyncio.run(_execute_dlq_fallback(archive_id, str(fatal_exc)))

    except Exception as exc:
        logger.warning(
            f"Temporary error for archive {archive_id}. "
            f"Attempt {self.request.retries + 1}/{self.max_retries}. Details: {exc}"
        )
        try:
            backoff = self.default_retry_delay * (2 ** self.request.retries)
            self.retry(exc=exc, countdown=backoff)
            
        except MaxRetriesExceededError:
            logger.critical(f"[DLQ] Archive {archive_id} has exhausted the retry limit.")
            asyncio.run(_execute_dlq_fallback(archive_id, f"Maximum number of retries exceeded: {exc}"))
            raise