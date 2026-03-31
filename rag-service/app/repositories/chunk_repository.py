from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import DocumentChunk
from app.core.logger import logger

class ChunkRepository:
    
    @staticmethod
    async def save_chunks(session: AsyncSession, chunks: list[DocumentChunk]) -> None:
        """Saves a list of DocumentChunk instances to the database."""
        try:
            session.add_all(chunks)
            await session.commit()
        except Exception as e:
            logger.error(f"Error saving chunks to DB: {e}", exc_info=True)
            await session.rollback()
            raise

    @staticmethod
    async def search_similar_chunks(
        session: AsyncSession, 
        query_embedding: list[float], 
        limit: int = 10
    ) -> list[DocumentChunk]:
        """
        Performs a global semantic vector search across all chunks in the database.
        Returns the top 'limit' chunks most similar to the query_embedding.
        """
        try:
            stmt = (
                select(DocumentChunk)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error during global vector search in DB: {e}", exc_info=True)
            raise