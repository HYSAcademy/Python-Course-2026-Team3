from abc import ABC, abstractmethod
from fastapi import Depends
from app.db.database import get_db
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.word_index import WordIndex


class IIndexRepository(ABC):
    """Abstract interface for index storage (Repository Pattern)."""

    @abstractmethod
    async def upsert_index(
        self, archive_id: str, filename: str, scores: dict
    ) -> None: ...

    @abstractmethod
    async def bulk_upsert_indices(
        self, records: list[dict]
    ) -> None: ...

    @abstractmethod
    async def get_index(
        self, archive_id: str, filename: str
    ) -> dict | None: ...

    @abstractmethod
    async def search_by_word(
        self, word: str, limit: int = 10
    ) -> list[dict]: ...


class PgIndexRepository(IIndexRepository):
    """
    PostgreSQL implementation using JSONB + GIN index.
    Uses Upsert (INSERT ... ON CONFLICT) for safe bulk writes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_index(
        self, archive_id: str, filename: str, scores: dict
    ) -> None:
        """Insert or update a single document index."""
        stmt = (
            pg_insert(WordIndex)
            .values(archive_id=archive_id, filename=filename, scores=scores)
            .on_conflict_do_update(
                index_elements=["archive_id", "filename"],
                set_={"scores": scores},
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def bulk_upsert_indices(self, records: list[dict]) -> None:
        """
        Bulk upsert — one query for all documents.
        Each record: {"archive_id": ..., "filename": ..., "scores": {...}}
        """
        if not records:
            return

        stmt = (
            pg_insert(WordIndex)
            .values(records)
            .on_conflict_do_update(
                index_elements=["archive_id", "filename"],
                set_={"scores": pg_insert(WordIndex).excluded.scores},
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()
        logger.info(f"Bulk upserted {len(records)} index records.")

    async def get_index(
        self, archive_id: str, filename: str
    ) -> dict | None:
        """Get index for a specific file."""
        result = await self.session.execute(
            select(WordIndex.scores).where(
                WordIndex.archive_id == archive_id,
                WordIndex.filename == filename,
            )
        )
        row = result.fetchone()
        return row[0] if row else None

    async def search_by_word(
        self, word: str, limit: int = 10
    ) -> list[dict]:
        """
        Search documents containing a word using GIN index.
        Returns top N documents sorted by score descending.
        """
        stmt = (
            select(
                WordIndex.archive_id,
                WordIndex.filename,
                WordIndex.scores[word].label("score"),
            )
            .where(WordIndex.scores.has_key(word))
            .order_by(WordIndex.scores[word].desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()
        return [
            {
                "archive_id": row.archive_id,
                "filename": row.filename,
                "score": float(row.score),
            }
            for row in rows
        ]


async def get_index_repo(
    session: AsyncSession = Depends(get_db),
) -> PgIndexRepository:
    return PgIndexRepository(session)