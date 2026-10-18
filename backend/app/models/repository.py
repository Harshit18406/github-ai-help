from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    clone_url: Mapped[str] = mapped_column(Text)
    local_path: Mapped[str] = mapped_column(Text)
    default_branch: Mapped[str] = mapped_column(String(120), default="main")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="repositories")
    files = relationship("RepositoryFile", back_populates="repository", cascade="all, delete-orphan")
    tasks = relationship("CodingTask", back_populates="repository", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("owner_id", "clone_url", name="uq_owner_clone_url"),)

class RepositoryFile(Base):
    __tablename__ = "repository_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size: Mapped[int] = mapped_column(default=0)
    repository = relationship("Repository", back_populates="files")
