from abc import ABC, abstractmethod

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger


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
        await self.session.execute(
            text("""
                INSERT INTO word_indices (archive_id, filename, scores)
                VALUES (:archive_id, :filename, :scores::jsonb)
                ON CONFLICT (archive_id, filename)
                DO UPDATE SET scores = EXCLUDED.scores
            """),
            {"archive_id": archive_id, "filename": filename, "scores": scores},
        )
        await self.session.flush()

    async def bulk_upsert_indices(self, records: list[dict]) -> None:
        """
        Bulk upsert — one query for all documents.
        Each record: {"archive_id": ..., "filename": ..., "scores": {...}}
        """
        if not records:
            return

        values_clause = ", ".join(
            f"(:archive_id_{i}, :filename_{i}, :scores_{i}::jsonb)"
            for i in range(len(records))
        )
        params = {}
        for i, record in enumerate(records):
            params[f"archive_id_{i}"] = record["archive_id"]
            params[f"filename_{i}"] = record["filename"]
            params[f"scores_{i}"] = record["scores"]

        await self.session.execute(
            text(f"""
                INSERT INTO word_indices (archive_id, filename, scores)
                VALUES {values_clause}
                ON CONFLICT (archive_id, filename)
                DO UPDATE SET scores = EXCLUDED.scores
            """),
            params,
        )
        await self.session.flush()
        logger.info(f"Bulk upserted {len(records)} index records.")

    async def get_index(
        self, archive_id: str, filename: str
    ) -> dict | None:
        """Get index for a specific file."""
        result = await self.session.execute(
            text("""
                SELECT scores FROM word_indices
                WHERE archive_id = :archive_id AND filename = :filename
            """),
            {"archive_id": archive_id, "filename": filename},
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
        result = await self.session.execute(
            text("""
                SELECT archive_id, filename, scores -> :word AS score
                FROM word_indices
                WHERE scores ? :word
                ORDER BY (scores -> :word)::float DESC
                LIMIT :limit
            """),
            {"word": word.lower(), "limit": limit},
        )
        rows = result.fetchall()
        return [
            {"archive_id": row[0], "filename": row[1], "score": float(row[2])}
            for row in rows
        ]