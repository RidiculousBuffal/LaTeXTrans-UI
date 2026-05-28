from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from backend.app.models.discovery import (
    ArxivCollectionTranslationMode,
    ArxivDiscoveryRunStatus,
    ArxivPaperReviewType,
    ArxivTranslateDecision,
)
from backend.app.schemas.common import APIModel
from backend.app.schemas.task import TaskDetailResponse, TaskSummaryResponse


class DiscoveryCollectionCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    categories_json: list[str] = Field(default_factory=list)
    prefer_keywords: str | None = None
    avoid_keywords: str | None = None
    translation_mode: ArxivCollectionTranslationMode = ArxivCollectionTranslationMode.MANUAL
    auto_translate_enabled: bool = False


class DiscoveryCollectionUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    categories_json: list[str] | None = None
    prefer_keywords: str | None = None
    avoid_keywords: str | None = None
    translation_mode: ArxivCollectionTranslationMode | None = None
    auto_translate_enabled: bool | None = None


class DiscoveryCollectionItemCreateRequest(APIModel):
    paper_id: int
    note: str | None = None
    translate_decision: ArxivTranslateDecision = ArxivTranslateDecision.PENDING


class DiscoveryPaperTaskCreateRequest(APIModel):
    collection_id: int | None = None
    task_name: str | None = Field(default=None, max_length=255)
    source_language: str = Field(default="en", max_length=16)
    target_language: str = Field(default="ch", max_length=16)
    model_name: str | None = Field(default=None, max_length=128)
    env_profile: str = Field(default="default", max_length=64)
    output_name: str | None = Field(default=None, max_length=255)
    options: dict[str, Any] = Field(default_factory=dict)


class DiscoverySyncRequest(APIModel):
    source_run_date: date | None = None
    force_refresh: bool = False
    run_inline: bool = False


class DiscoveryCollectionMembershipResponse(APIModel):
    item_id: int
    collection_id: int
    collection_name: str
    translate_decision: ArxivTranslateDecision
    note: str | None
    created_at: datetime
    updated_at: datetime


class DiscoveryPaperReviewResponse(APIModel):
    id: int
    collection_id: int
    collection_name: str
    review_type: ArxivPaperReviewType
    model_name: str
    worth_read: bool
    title_zh: str | None
    abstract_zh: str | None
    comment: str | None
    raw_result_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class DiscoveryPaperSummaryResponse(APIModel):
    id: int
    arxiv_id: str
    primary_category: str | None
    published_at: datetime | None
    scraped_at: datetime
    title_en: str
    abstract_en: str
    authors_json: list[str]
    pdf_url: str | None
    abs_url: str | None
    subjects_json: list[str]
    comments: str | None
    source_run_date: date | None
    title_zh: str | None = None
    abstract_zh: str | None = None
    worth_read: bool | None = None
    comment: str | None = None
    has_translation: bool = False
    translation_task_count: int = 0
    collections: list[DiscoveryCollectionMembershipResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DiscoveryPaperDetailResponse(DiscoveryPaperSummaryResponse):
    reviews: list[DiscoveryPaperReviewResponse] = Field(default_factory=list)
    tasks: list[TaskSummaryResponse] = Field(default_factory=list)
    latest_task: TaskSummaryResponse | None = None


class DiscoveryPaperListResponse(APIModel):
    items: list[DiscoveryPaperSummaryResponse]
    total: int
    page: int
    page_size: int


class DiscoveryCollectionItemResponse(APIModel):
    id: int
    collection_id: int
    paper_id: int
    added_by_user_id: str | None
    note: str | None
    translate_decision: ArxivTranslateDecision
    created_at: datetime
    updated_at: datetime
    paper: DiscoveryPaperSummaryResponse


class DiscoveryCollectionResponse(APIModel):
    id: int
    user_id: str
    name: str
    description: str | None
    categories_json: list[str]
    prefer_keywords: str | None
    avoid_keywords: str | None
    translation_mode: ArxivCollectionTranslationMode
    auto_translate_enabled: bool
    item_count: int = 0
    items: list[DiscoveryCollectionItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DiscoveryCollectionListResponse(APIModel):
    items: list[DiscoveryCollectionResponse]
    total: int


class DiscoveryRunResponse(APIModel):
    id: str
    trigger_source: str
    requested_by_user_id: str | None
    source_run_date: date
    status: ArxivDiscoveryRunStatus
    categories_json: list[str]
    total_papers: int
    total_reviews: int
    total_worth_read: int
    error_message: str | None
    summary_json: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DiscoveryRunListResponse(APIModel):
    items: list[DiscoveryRunResponse]
    total: int
    page: int
    page_size: int


class DiscoveryDailyDigestGroupResponse(APIModel):
    category: str
    papers: list[DiscoveryPaperSummaryResponse]


class DiscoveryDailyDigestResponse(APIModel):
    run: DiscoveryRunResponse | None = None
    groups: list[DiscoveryDailyDigestGroupResponse] = Field(default_factory=list)


class DiscoveryPaperTaskResponse(APIModel):
    task: TaskDetailResponse
    paper: DiscoveryPaperDetailResponse
