from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.document_chunk import DocumentChunk

from app.db.database import Base
from app.schemas.contracts import ArchiveStatus
from app.models.word_index import WordIndex


class Archive(Base):
    __tablename__ = "archives"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    s3_object_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ArchiveStatus] = mapped_column(
        SAEnum(ArchiveStatus), default=ArchiveStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    extracted_files: Mapped[list["ExtractedFile"]] = relationship(
        "ExtractedFile",
        back_populates="archive",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
    word_indices: Mapped[list["WordIndex"]] = relationship(
        "WordIndex",
        back_populates="archive",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="archive",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ExtractedFile(Base):
    __tablename__ = "extracted_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    archive_id: Mapped[str] = mapped_column(
        String, ForeignKey("archives.id", ondelete="CASCADE"), nullable=False
    )
    
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_object_name: Mapped[str] = mapped_column(String, nullable=False)

    archive: Mapped["Archive"] = relationship(
        "Archive",
        back_populates="extracted_files",
        lazy="raise",
    )