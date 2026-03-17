import io
import uuid
import re
from pathlib import Path
import traceback
from typing import Any

from app.core.logger import logger
from app.services.s3_service import S3Service
from app.services.extractor import ExtractorFactory
from app.schemas.contracts import ArchiveStatus
from app.models.archive import ExtractedFile
from app.repositories.archive_repo import ArchiveRepository
from app.db.database import AsyncSessionLocal


class ArchiveService:
    def __init__(self, s3_client: Any):
        self.s3_service = S3Service(s3_client)

    @staticmethod
    def generate_archive_metadata(original_filename: str) -> tuple[str, str]:
        archive_id = str(uuid.uuid4())
        clean_name = Path(original_filename).name
        clean_name = re.sub(r'[^a-zA-Z0-9.\-_]', '_', clean_name)
        if not clean_name or clean_name == "_":
            clean_name = "unnamed_archive.zip"
        s3_object_name = f"{archive_id[:8]}_{clean_name}"
        return archive_id, s3_object_name

    async def process_archive_background(
        self, archive_id: str, filename: str, file_bytes: bytes, s3_object_name: str
    ) -> None:
        """Background task with its own isolated DB transaction."""
        logger.info(f"Starting background processing for archive ID={archive_id}")
        uploaded_to_s3 = False
        
        async with AsyncSessionLocal() as session:
            repo = ArchiveRepository(session)
            
            try:
                file_obj = io.BytesIO(file_bytes)
                await self.s3_service.upload_archive(file_obj, s3_object_name)
                uploaded_to_s3 = True
                
                file_obj.seek(0) 
                extractor = ExtractorFactory.get_extractor(filename)
                
                db_extracted_files = []
                for doc in extractor.extract(file_obj):
                    db_extracted_files.append(
                        ExtractedFile(
                            archive_id=archive_id,
                            file_name=doc.original_filename,
                            size_bytes=doc.file_size,
                            content=doc.content
                        )
                    )
                    
                if db_extracted_files:
                    await repo.save_extracted_files(db_extracted_files)
                
                await repo.update_status(archive_id, ArchiveStatus.COMPLETED)
                
                await session.commit()
                logger.info(f"Archive ID={archive_id} successfully processed and saved to DB!")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing archive ID={archive_id}: {e}")
                logger.debug(traceback.format_exc())
                
                if uploaded_to_s3:
                    try:
                        await self.s3_service.delete_file(s3_object_name)
                    except Exception as s3_err:
                        logger.warning(f"Failed to cleanup S3 object {s3_object_name}: {s3_err}")
                try:
                    await repo.update_status(archive_id, ArchiveStatus.FAILED, error_message=str(e))
                    await session.commit()
                except Exception as db_err:
                    logger.critical(f"Failed to update status in DB for {archive_id}: {db_err}")
                
    def get_full_s3_url(self, s3_object_name: str) -> str:
        """Helper method for GET endpoint: builds URL dynamically."""
        return f"{self.s3_service.endpoint_url}/{self.s3_service.bucket_name}/{s3_object_name}"