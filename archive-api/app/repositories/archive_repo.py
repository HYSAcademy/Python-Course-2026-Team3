from sqlalchemy import select, func, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import selectinload

from app.models.archive import Archive, ExtractedFile
from app.schemas.contracts import ArchiveStatus, SearchResultItem
from app.models.word_index import WordIndex


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
                        "s3_object_name": f.s3_object_name,
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
    
    async def save_word_indices(self, indices: list[WordIndex]) -> None:
        self.session.add_all(indices)

    async def search_bm25(self, query: str, top_k: int = 10) -> list[SearchResultItem]:
        """
        Performs document search using BM25 weights stored in a JSONB field.
        Uses a GIN index for instant key lookup.
        """
        tokens = [word.strip().lower() for word in query.split() if word.strip()]
        
        if not tokens:
            return []

        score_exprs = [
            func.coalesce(cast(WordIndex.scores[token].astext, Float), 0.0)
            for token in tokens
        ]
        
        total_score = sum(score_exprs).label("total_score")

        stmt = (
            select(
                WordIndex.archive_id,
                WordIndex.filename,
                ExtractedFile.s3_object_name,
                total_score
            )
            .join(
                ExtractedFile,
                (WordIndex.archive_id == ExtractedFile.archive_id) & 
                (WordIndex.filename == ExtractedFile.file_name)
            )

            .where(WordIndex.scores.has_any(array(tokens)))
            .order_by(total_score.desc())
            .limit(top_k)
        )

        result = await self.session.execute(stmt)
        rows = result.fetchall()
        search_results = []
        for row in rows:
            search_results.append(
                SearchResultItem(
                    archive_id=row.archive_id,
                    filename=row.filename,
                    s3_object_name=row.s3_object_name,
                    score=round(row.total_score, 4)
                )
            )

        return search_results