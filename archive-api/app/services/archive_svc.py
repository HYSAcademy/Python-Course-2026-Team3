import io
import uuid
import re
import traceback
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import delete

from app.core.logger import logger
from app.services.s3_service import S3Service
from app.services.extractor import ExtractorFactory
from app.services.scoring import ScorerFactory
from app.schemas.contracts import ArchiveStatus
from app.models.archive import ExtractedFile
from app.repositories.archive_repo import ArchiveRepository
from app.db.database import AsyncSessionLocal
from app.models.word_index import WordIndex


class ArchiveService:
    def __init__(self, s3_client: Any):
        self.s3_service = S3Service(s3_client)

    @staticmethod
    def generate_archive_metadata(original_filename: str) -> tuple[str, str]:
        archive_id = str(uuid.uuid4())
        clean_name = Path(original_filename).name
        clean_name = re.sub(r"[^a-zA-Z0-9.\-_]", "_", clean_name)
        if not clean_name or clean_name == "_":
            clean_name = "unnamed_archive.zip"
        s3_object_name = f"{archive_id[:8]}_{clean_name}"
        return archive_id, s3_object_name

    async def upload_stream_to_s3(self, object_name: str, upload_file: UploadFile) -> None:
        """
        Streaming file upload to MinIO directly from FastAPI (Producer).
        """
        logger.info(f"Uploading file '{object_name}' to S3 streamingly...")
        
        try:
            await self.s3_service.upload_archive(upload_file.file, object_name)
        except Exception as e:
            logger.error(f"Failed to stream upload {object_name}: {e}")
            raise e

    async def process_archive(self, archive_id: str) -> None:
        """
        Called from a Celery worker.
        Downloads the archive, extracts it on-the-fly, calculates BM25 scores,
        and streams extracted files directly back to S3.
        """
        logger.info(f"Worker started processing archive ID={archive_id}")

        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(ExtractedFile).where(ExtractedFile.archive_id == archive_id)
            )
            await session.execute(
                delete(WordIndex).where(WordIndex.archive_id == archive_id)
            )
            await session.commit()
            logger.info(f"Cleared old database records for archive {archive_id}")

        async with AsyncSessionLocal() as session:
            repo = ArchiveRepository(session)
            archive = await repo.get_archive_by_id(archive_id)
            if not archive:
                raise ValueError(f"Archive {archive_id} not found in database.")

            try:
                await repo.update_status(archive_id, ArchiveStatus.PROCESSING)
                await session.commit()

                logger.info(f"Downloading {archive.s3_object_name} from S3...")
                try:
                    file_bytes = await self.s3_service.get_archive_bytes(archive.s3_object_name)
                except Exception as e:
                    raise RuntimeError(f"Could not download archive from S3: {e}")

                file_obj = io.BytesIO(file_bytes)

                logger.info(f"Extracting contents of {archive.filename}...")
                extractor = ExtractorFactory.get_extractor(archive.filename)
                
                scorer = ScorerFactory.get_scorer("bm25")
                
                db_extracted_files = []
                db_word_indices = []
                
                for doc in extractor.extract(file_obj):
                    logger.info(f"On-the-fly processing: {doc.original_filename} ({doc.file_size} bytes)")
                    word_scores = scorer.calculate_scores(doc.content)
                    if word_scores:
                        db_word_indices.append(
                            WordIndex(
                                archive_id=archive_id,
                                filename=doc.original_filename,
                                scores=word_scores
                            )
                        )

                    extracted_s3_key = f"extracted/{archive_id}/{doc.original_filename}"
                    doc_stream = io.BytesIO(doc.content.encode('utf-8'))
                    await self.s3_service.upload_archive(doc_stream, extracted_s3_key)

                    db_extracted_files.append(
                        ExtractedFile(
                            archive_id=archive_id,
                            file_name=doc.original_filename,
                            size_bytes=doc.file_size,
                            s3_object_name=extracted_s3_key 
                        )
                    )
                if db_extracted_files:
                    await repo.save_extracted_files(db_extracted_files)
                
                if db_word_indices:
                    await repo.save_word_indices(db_word_indices)

                await repo.update_status(archive_id, ArchiveStatus.COMPLETED)
                await session.commit()
                
                logger.info(f"Archive ID={archive_id} successfully extracted, BM25 indexed, and uploaded to S3!")

            except Exception as e:
                await session.rollback()
                logger.error(f"Extraction failed for archive ID={archive_id}: {e}")
                logger.debug(traceback.format_exc())
                raise e 

    def get_full_s3_url(self, s3_object_name: str) -> str:
        """Helper method for GET endpoint: builds URL dynamically."""
        return f"{self.s3_service.endpoint_url}/{self.s3_service.bucket_name}/{s3_object_name}"