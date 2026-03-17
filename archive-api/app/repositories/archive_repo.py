from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.archive import Archive, ExtractedFile
from app.schemas.contracts import ArchiveStatus


class ArchiveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_archive(self, archive: Archive) -> Archive:
        self.session.add(archive)
        await self.session.flush() 
        await self.session.refresh(archive)
        return archive

    async def get_archive_by_id(self, archive_id: str) -> Archive | None:
        result = await self.session.execute(
            select(Archive)
            .where(Archive.id == archive_id)
            .options(selectinload(Archive.extracted_files))
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        archive_id: str,
        status: ArchiveStatus,
        error_message: str | None = None,
    ) -> None:
        archive = await self.get_archive_by_id(archive_id)
        if archive:
            archive.status = status
            archive.error_message = error_message
            await self.session.flush()

    async def save_extracted_files(
        self,
        files: list[ExtractedFile],
    ) -> None:
        await self.session.run_sync(
            lambda session: session.bulk_insert_mappings(
                ExtractedFile,
                [
                    {
                        "archive_id": f.archive_id,
                        "file_name": f.file_name,
                        "size_bytes": f.size_bytes,
                        "content": f.content,
                    }
                    for f in files
                ],
            )
        )

    async def get_failed_archives(self) -> list[Archive]:
        result = await self.session.execute(
            select(Archive)
            .where(Archive.status == ArchiveStatus.FAILED)
            .options(selectinload(Archive.extracted_files))
        )
        return list(result.scalars().all())