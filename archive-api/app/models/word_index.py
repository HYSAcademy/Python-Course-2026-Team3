from sqlalchemy import String, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class WordIndex(Base):
    __tablename__ = "word_indices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    archive_id: Mapped[str] = mapped_column(
        String, ForeignKey("archives.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_word_index_scores_gin", "scores", postgresql_using="gin"),
        Index("ix_word_index_archive_filename", "archive_id", "filename", unique=True),
    )