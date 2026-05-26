from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.task import (
    TaskArtifact,
    TaskArtifactType,
    TaskConfig,
    TaskEvent,
    TaskSourceType,
    TaskStatus,
    TranslationTask,
)
from backend.app.repositories.task_repository import TaskRepository
from backend.app.schemas.task import (
    ArchiveListResponse,
    ArtifactListResponse,
    ArchiveListItem,
    TaskCancelResponse,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskListResponse,
    TaskLogsResponse,
    TaskRetryResponse,
    TaskSummaryResponse,
)
from backend.app.services.archive_service import ArchiveService
from backend.app.services.translation_service import TranslationService


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TaskRepository(db)
        self.settings = get_settings()
        self.translation_service = TranslationService()
        self.archive_service = ArchiveService()

    def create_task(self, payload: TaskCreateRequest) -> TaskDetailResponse:
        task_name = payload.task_name or self._derive_task_name(payload)
        model_name = payload.model_name or self.settings.openai_model or "gpt-4.1"
        created_by = payload.created_by or self.settings.default_created_by
        workspace_dir = str(Path(self.settings.task_workspace_root) / task_name)
        output_dir = str(Path(workspace_dir) / "output")

        task = TranslationTask(
            task_name=task_name,
            source_type=payload.source_type,
            arxiv_id=payload.arxiv_id,
            source_archive_name=payload.source_archive_name,
            source_language=payload.source_language,
            target_language=payload.target_language,
            model_name=model_name,
            status=TaskStatus.PENDING,
            current_stage=TaskStatus.PENDING.value,
            progress_percent=0,
            created_by=created_by,
            workspace_dir=workspace_dir,
            output_dir=output_dir,
        )

        snapshot = self.translation_service.build_config_snapshot(task=task, payload=payload)
        config = TaskConfig(
            task=task,
            env_profile=payload.env_profile,
            config_snapshot_json=snapshot,
        )
        event = TaskEvent(
            task=task,
            stage=TaskStatus.PENDING.value,
            status=TaskStatus.PENDING,
            message="Task created and queued for translation.",
            details_json={"source_type": payload.source_type.value},
        )

        try:
            self.repository.add_task(task)
            self.repository.add_config(config)
            self.repository.add_event(event)
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create task: {exc}",
            ) from exc

        return self.get_task_detail(task.id)

    def list_tasks(
        self,
        *,
        page: int,
        page_size: int,
        status_filter: str | None = None,
        arxiv_id: str | None = None,
        created_by: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskListResponse:
        tasks, total = self.repository.list_tasks(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            arxiv_id=arxiv_id,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
        )
        return TaskListResponse(
            items=[TaskSummaryResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_task_detail(self, task_id: str) -> TaskDetailResponse:
        task = self._require_task(task_id)
        return TaskDetailResponse.model_validate(task)

    def retry_task(self, task_id: str) -> TaskRetryResponse:
        task = self._require_task(task_id)
        if task.status not in {TaskStatus.FAILED, TaskStatus.CANCELED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only failed or canceled tasks can be retried.",
            )

        task.status = TaskStatus.PENDING
        task.current_stage = TaskStatus.PENDING.value
        task.progress_percent = 0
        task.error_message = None
        task.started_at = None
        task.finished_at = None
        task.canceled_at = None
        self.repository.add_event(
            TaskEvent(
                task=task,
                stage=TaskStatus.PENDING.value,
                status=TaskStatus.PENDING,
                message="Task has been retried and re-queued.",
            )
        )
        self.repository.commit()
        return TaskRetryResponse(task=self.get_task_detail(task_id), message="Task re-queued.")

    def cancel_task(self, task_id: str) -> TaskCancelResponse:
        task = self._require_task(task_id)
        if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Terminal tasks cannot be canceled.",
            )

        task.status = TaskStatus.CANCELED
        task.current_stage = TaskStatus.CANCELED.value
        task.finished_at = datetime.utcnow()
        task.canceled_at = task.finished_at
        self.repository.add_event(
            TaskEvent(
                task=task,
                stage=TaskStatus.CANCELED.value,
                status=TaskStatus.CANCELED,
                message="Task canceled by user request.",
            )
        )
        self.repository.commit()
        return TaskCancelResponse(task=self.get_task_detail(task_id), message="Task canceled.")

    def list_artifacts(self, task_id: str) -> ArtifactListResponse:
        task = self._require_task(task_id)
        return ArtifactListResponse(
            task_id=task.id,
            items=[artifact for artifact in task.artifacts],
        )

    def list_logs(self, task_id: str) -> TaskLogsResponse:
        task = self._require_task(task_id)
        log_artifacts = [
            artifact
            for artifact in task.artifacts
            if artifact.artifact_type == TaskArtifactType.LOG
        ]
        return TaskLogsResponse(task_id=task.id, items=log_artifacts)

    def list_archives(
        self,
        *,
        page: int,
        page_size: int,
        status_filter: str | None = None,
        arxiv_id: str | None = None,
        created_by: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> ArchiveListResponse:
        tasks, total = self.repository.list_tasks(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            arxiv_id=arxiv_id,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
        )
        items = [self.archive_service.build_archive_item(task) for task in tasks]
        return ArchiveListResponse(items=items, total=total, page=page, page_size=page_size)

    def _require_task(self, task_id: str) -> TranslationTask:
        task = self.repository.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
        return task

    def _derive_task_name(self, payload: TaskCreateRequest) -> str:
        if payload.source_type == TaskSourceType.ARXIV and payload.arxiv_id:
            return f"arxiv-{payload.arxiv_id}"
        if payload.source_archive_name:
            return Path(payload.source_archive_name).stem
        return f"task-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
