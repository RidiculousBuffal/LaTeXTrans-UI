from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, JSON, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


def _enum_values(enum_type: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_type]


class ArxivPaperReviewType(str, enum.Enum):
    DAILY_JUDGE = "daily_judge"


class ArxivCollectionTranslationMode(str, enum.Enum):
    MANUAL = "manual"
    AUTO = "auto"


class ArxivTranslateDecision(str, enum.Enum):
    PENDING = "pending"
    MANUAL_REQUESTED = "manual_requested"
    AUTO_QUEUED = "auto_queued"
    TRANSLATED = "translated"


class ArxivDiscoveryRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ArxivPaper(Base):
    __tablename__ = "arxiv_papers"
    __table_args__ = (
        Index("ix_arxiv_papers_arxiv_id", "arxiv_id", unique=True),
        Index("ix_arxiv_papers_primary_category_run_date", "primary_category", "source_run_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arxiv_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    primary_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    abstract_en: Mapped[str] = mapped_column(Text, nullable=False)
    authors_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    pdf_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    abs_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subjects_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_run_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    reviews: Mapped[list[ArxivPaperReview]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ArxivPaperReview.created_at.desc()",
    )
    enrichments: Mapped[list[ArxivPaperEnrichment]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ArxivPaperEnrichment.created_at.desc()",
    )
    collection_items: Mapped[list[ArxivCollectionItem]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ArxivCollectionItem.created_at.desc()",
    )
    task_links: Mapped[list[ArxivPaperTaskLink]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
        order_by="ArxivPaperTaskLink.created_at.desc()",
    )


class ArxivCollection(Base):
    __tablename__ = "arxiv_collections"
    __table_args__ = (
        Index("ix_arxiv_collections_user_id", "user_id"),
        Index("ix_arxiv_collections_user_id_name", "user_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    categories_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    prefer_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    avoid_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation_mode: Mapped[ArxivCollectionTranslationMode] = mapped_column(
        Enum(ArxivCollectionTranslationMode, native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ArxivCollectionTranslationMode.MANUAL,
    )
    auto_translate_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list[ArxivCollectionItem]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="ArxivCollectionItem.created_at.desc()",
    )
    reviews: Mapped[list[ArxivPaperReview]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="ArxivPaperReview.created_at.desc()",
    )


class ArxivPaperReview(Base):
    __tablename__ = "arxiv_paper_reviews"
    __table_args__ = (
        Index("ix_arxiv_paper_reviews_paper_id", "paper_id"),
        Index("ix_arxiv_paper_reviews_collection_id", "collection_id"),
        Index(
            "ix_arxiv_paper_reviews_unique_scope",
            "paper_id",
            "collection_id",
            "review_type",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("arxiv_papers.id", ondelete="CASCADE"), nullable=False)
    collection_id: Mapped[int] = mapped_column(ForeignKey("arxiv_collections.id", ondelete="CASCADE"), nullable=False)
    review_type: Mapped[ArxivPaperReviewType] = mapped_column(
        Enum(ArxivPaperReviewType, native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ArxivPaperReviewType.DAILY_JUDGE,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    worth_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    paper: Mapped[ArxivPaper] = relationship(back_populates="reviews")
    collection: Mapped[ArxivCollection] = relationship(back_populates="reviews")


class ArxivCollectionItem(Base):
    __tablename__ = "arxiv_collection_items"
    __table_args__ = (
        Index("ix_arxiv_collection_items_collection_id", "collection_id"),
        Index("ix_arxiv_collection_items_paper_id", "paper_id"),
        Index("ix_arxiv_collection_items_unique_pair", "collection_id", "paper_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("arxiv_collections.id", ondelete="CASCADE"), nullable=False)
    paper_id: Mapped[int] = mapped_column(ForeignKey("arxiv_papers.id", ondelete="CASCADE"), nullable=False)
    added_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    translate_decision: Mapped[ArxivTranslateDecision] = mapped_column(
        Enum(ArxivTranslateDecision, native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ArxivTranslateDecision.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    collection: Mapped[ArxivCollection] = relationship(back_populates="items")
    paper: Mapped[ArxivPaper] = relationship(back_populates="collection_items")


class ArxivPaperTaskLink(Base):
    __tablename__ = "arxiv_paper_task_links"
    __table_args__ = (
        Index("ix_arxiv_paper_task_links_paper_id", "paper_id"),
        Index("ix_arxiv_paper_task_links_task_id", "task_id"),
        Index("ix_arxiv_paper_task_links_unique_pair", "paper_id", "task_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("arxiv_papers.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey("translation_tasks.id", ondelete="CASCADE"), nullable=False)
    link_type: Mapped[str] = mapped_column(String(32), nullable=False, default="arxiv_id_match")
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())

    paper: Mapped[ArxivPaper] = relationship(back_populates="task_links")
    task: Mapped["TranslationTask"] = relationship()


class ArxivPaperEnrichment(Base):
    """全局 paper enrichment，存储与 collection 无关的 AI 加工结果（中文标题、中文摘要等）。"""

    __tablename__ = "arxiv_paper_enrichments"
    __table_args__ = (
        Index("ix_arxiv_paper_enrichments_paper_id", "paper_id"),
        Index(
            "ix_arxiv_paper_enrichments_unique_scope",
            "paper_id",
            "enrichment_type",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("arxiv_papers.id", ondelete="CASCADE"), nullable=False)
    enrichment_type: Mapped[str] = mapped_column(String(64), nullable=False, default="global_summary")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    title_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    raw_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    paper: Mapped[ArxivPaper] = relationship(back_populates="enrichments")


class ArxivDiscoveryRun(Base):
    __tablename__ = "arxiv_discovery_runs"
    __table_args__ = (
        Index("ix_arxiv_discovery_runs_status_created_at", "status", "created_at"),
        Index("ix_arxiv_discovery_runs_source_run_date", "source_run_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trigger_source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    requested_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ArxivDiscoveryRunStatus] = mapped_column(
        Enum(ArxivDiscoveryRunStatus, native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=ArxivDiscoveryRunStatus.PENDING,
    )
    categories_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    total_papers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_worth_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
