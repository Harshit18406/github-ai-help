from sqlalchemy import Text, String, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.core.config import settings
from app.db.base import Base

class CodeChunk(Base):
    __tablename__ = "code_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_line: Mapped[int] = mapped_column(Integer, default=1)
    end_line: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim).with_variant(JSON, "sqlite"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
