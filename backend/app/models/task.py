from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class TaskSourceType(str, enum.Enum):
    ARXIV = "arxiv"
    UPLOAD = "upload"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PARSING = "PARSING"
    TRANSLATING = "TRANSLATING"
    VALIDATING = "VALIDATING"
    GENERATING = "GENERATING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class TaskArtifactType(str, enum.Enum):
    SOURCE_ARCHIVE = "SOURCE_ARCHIVE"
    EXTRACTED_SOURCE = "EXTRACTED_SOURCE"
    TRANSLATED_PROJECT = "TRANSLATED_PROJECT"
    FINAL_PDF = "FINAL_PDF"
    LOG = "LOG"
    METADATA = "METADATA"
    INTERMEDIATE_JSON = "INTERMEDIATE_JSON"


class TranslationTask(Base):
    __tablename__ = "translation_tasks"
    __table_args__ = (
        Index("ix_translation_tasks_status_created_at", "status", "created_at"),
        Index("ix_translation_tasks_arxiv_id_created_at", "arxiv_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[TaskSourceType] = mapped_column(
        Enum(TaskSourceType, native_enum=False),
        nullable=False,
    )
    arxiv_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_archive_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    target_language: Mapped[str] = mapped_column(String(16), nullable=False, default="ch")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default=TaskStatus.PENDING.value)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="internal-user")
    workspace_dir: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_dir: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artifacts: Mapped[list[TaskArtifact]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskArtifact.created_at",
    )
    events: Mapped[list[TaskEvent]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskEvent.created_at",
    )
    configs: Mapped[list[TaskConfig]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskConfig.created_at",
    )


class TaskArtifact(Base):
    __tablename__ = "task_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("translation_tasks.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[TaskArtifactType] = mapped_column(
        Enum(TaskArtifactType, native_enum=False),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    task: Mapped[TranslationTask] = relationship(back_populates="artifacts")


class TaskEvent(Base):
    __tablename__ = "task_events"
    __table_args__ = (
        Index("ix_task_events_task_id_created_at", "task_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("translation_tasks.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    task: Mapped[TranslationTask] = relationship(back_populates="events")


class TaskConfig(Base):
    __tablename__ = "task_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("translation_tasks.id", ondelete="CASCADE"), nullable=False)
    env_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    config_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    task: Mapped[TranslationTask] = relationship(back_populates="configs")
