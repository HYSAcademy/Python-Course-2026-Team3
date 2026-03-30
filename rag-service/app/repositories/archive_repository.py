from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import logger

class ArchiveRepository:
    
    @staticmethod
    async def get_extracted_files(session: AsyncSession, archive_id: str) -> list[dict]:
        """Fetches the list of extracted files for a given archive_id from the database.
        Returns a list of dictionaries with 'file_name' and 's3_object_name' keys"""
        try:
            stmt = text("SELECT file_name, s3_object_name FROM extracted_files WHERE archive_id = :id")
            result = await session.execute(stmt, {"id": archive_id})
            
            return [dict(row) for row in result.mappings().fetchall()]
            
        except Exception as e:
            logger.error(f"Error fetching files for archive '{archive_id}': {e}", exc_info=True)
            raise