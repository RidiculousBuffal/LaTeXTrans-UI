from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from backend.app.models.task import TaskArtifactType, TaskSourceType, TaskStatus
from backend.app.schemas.common import APIModel


class TaskCreateRequest(APIModel):
    task_name: str | None = Field(default=None, max_length=255)
    source_type: TaskSourceType = TaskSourceType.ARXIV
    arxiv_id: str | None = Field(default=None, max_length=64)
    source_archive_name: str | None = Field(default=None, max_length=255)
    source_language: str = Field(default="en", max_length=16)
    target_language: str = Field(default="zh", max_length=16)
    model_name: str | None = Field(default=None, max_length=128)
    created_by: str | None = Field(default=None, max_length=128)
    env_profile: str = Field(default="default", max_length=64)
    output_name: str | None = Field(default=None, max_length=255)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(self) -> "TaskCreateRequest":
        if self.source_type == TaskSourceType.ARXIV and not self.arxiv_id:
            raise ValueError("arxiv_id is required when source_type is 'arxiv'")
        if self.source_type == TaskSourceType.UPLOAD and not self.source_archive_name:
            raise ValueError("source_archive_name is required when source_type is 'upload'")
        return self


class TaskArtifactResponse(APIModel):
    id: int
    task_id: str
    artifact_type: TaskArtifactType
    object_key: str
    file_name: str
    content_type: str | None
    file_size: int | None
    version: int
    metadata_json: dict[str, Any] | None
    download_url: str | None = None
    created_at: datetime


class TaskEventResponse(APIModel):
    id: int
    task_id: str
    stage: str
    status: TaskStatus
    message: str
    details_json: dict[str, Any] | None
    created_at: datetime


class TaskConfigResponse(APIModel):
    id: int
    task_id: str
    env_profile: str
    config_snapshot_json: dict[str, Any]
    created_at: datetime


class TaskSummaryResponse(APIModel):
    id: str
    task_name: str
    source_type: TaskSourceType
    arxiv_id: str | None
    source_archive_name: str | None
    source_language: str
    target_language: str
    model_name: str
    status: TaskStatus
    current_stage: str
    progress_percent: int
    error_message: str | None
    created_by: str
    workspace_dir: str | None
    output_dir: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    canceled_at: datetime | None


class TaskDetailResponse(TaskSummaryResponse):
    artifacts: list[TaskArtifactResponse] = Field(default_factory=list)
    events: list[TaskEventResponse] = Field(default_factory=list)
    configs: list[TaskConfigResponse] = Field(default_factory=list)


class TaskListResponse(APIModel):
    items: list[TaskSummaryResponse]
    total: int
    page: int
    page_size: int


class TaskRetryResponse(APIModel):
    task: TaskDetailResponse
    message: str


class TaskCancelResponse(APIModel):
    task: TaskDetailResponse
    message: str


class ArtifactListResponse(APIModel):
    task_id: str
    items: list[TaskArtifactResponse]


class TaskLogsResponse(APIModel):
    task_id: str
    items: list[TaskArtifactResponse]


class FailureSummaryResponse(APIModel):
    recent_failed_tasks: list[TaskSummaryResponse]
    failed_stage_counts: dict[str, int]
    failed_type_counts: dict[str, int]
    total_failed: int


class ArchiveListItem(APIModel):
    task: TaskSummaryResponse
    artifact_count: int


class ArchiveGroupItem(APIModel):
    group_key: str
    arxiv_id: str | None
    task_count: int
    artifact_count: int
    latest_created_at: datetime
    latest_task: TaskSummaryResponse
    tasks: list[ArchiveListItem]


class ArchiveListResponse(APIModel):
    items: list[ArchiveGroupItem]
    total: int
    page: int
    page_size: int
