from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class CacheEntryStatus(str, enum.Enum):
    BUILDING = "BUILDING"
    READY = "READY"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"


class TranslationCacheEntry(Base):
    __tablename__ = "translation_cache_entries"
    __table_args__ = (
        Index("ix_cache_entries_cache_key", "cache_key", unique=True),
        Index("ix_cache_entries_arxiv_id", "normalized_arxiv_id"),
        Index("ix_cache_entries_file_hash", "source_file_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    engine: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_arxiv_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_fingerprint_type: Mapped[str] = mapped_column(String(16), nullable=False)  # "arxiv" or "file"
    source_language: Mapped[str] = mapped_column(String(16), nullable=False)
    target_language: Mapped[str] = mapped_column(String(16), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    options_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cache_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[CacheEntryStatus] = mapped_column(
        Enum(CacheEntryStatus, native_enum=False),
        nullable=False,
        default=CacheEntryStatus.BUILDING,
    )
    canonical_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    artifact_manifest_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )
