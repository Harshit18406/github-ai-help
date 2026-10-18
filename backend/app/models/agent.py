from datetime import datetime
from sqlalchemy import Text, String, DateTime, ForeignKey, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("coding_tasks.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="planning")
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    task = relationship("CodingTask", back_populates="runs")
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan", order_by="AgentStep.id")
    changes = relationship("CodeChange", back_populates="run", cascade="all, delete-orphan")
    tests = relationship("TestRun", back_populates="run", cascade="all, delete-orphan")

class AgentStep(Base):
    __tablename__ = "agent_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    run = relationship("AgentRun", back_populates="steps")

class CodeChange(Base):
    __tablename__ = "code_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    original_content: Mapped[str] = mapped_column(Text)
    proposed_content: Mapped[str] = mapped_column(Text)
    diff: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    run = relationship("AgentRun", back_populates="changes")

class TestRun(Base):
    __tablename__ = "test_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    command: Mapped[str] = mapped_column(Text)
    exit_code: Mapped[int] = mapped_column(Integer)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    run = relationship("AgentRun", back_populates="tests")
