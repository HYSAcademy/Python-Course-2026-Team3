from sqlalchemy import String, Integer, Text, Index
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.core.db import Base

class DocumentChunk(Base):
    """
    Model representing a chunk of a document, including its text and vector embedding.
    """
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    archive_id: Mapped[str] = mapped_column(String, nullable=False)
    
    filename: Mapped[str] = mapped_column(String, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)

    __table_args__ = (
        Index("ix_document_chunks_archive_id", "archive_id"),
        {"extend_existing": True}
    )