from __future__ import annotations

import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
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
    FailureSummaryResponse,
    TaskCancelResponse,
    TaskArtifactResponse,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskListResponse,
    TaskLogsResponse,
    TaskRetryResponse,
    TaskSummaryResponse,
)
from backend.app.services.archive_service import ArchiveService
from backend.app.services.storage_service import StorageService
from backend.app.services.translation_service import TranslationService


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TaskRepository(db)
        self.settings = get_settings()
        self.translation_service = TranslationService()
        self.archive_service = ArchiveService()
        self.storage_service = StorageService()

    def create_task(self, payload: TaskCreateRequest) -> TaskDetailResponse:
        task = self._create_task_record(payload)

        from backend.app.workers.translation_runner import submit_task

        submit_task(task.id)

        return self.get_task_detail(task.id)

    def create_upload_task(
        self,
        *,
        file: UploadFile,
        task_name: str | None,
        source_language: str,
        target_language: str,
        model_name: str | None,
        created_by: str | None,
        env_profile: str,
        output_name: str | None,
        options: dict[str, str],
    ) -> TaskDetailResponse:
        self._validate_upload_file(file)
        payload = TaskCreateRequest(
            task_name=task_name,
            source_type=TaskSourceType.UPLOAD,
            source_archive_name=file.filename,
            source_language=source_language,
            target_language=target_language,
            model_name=model_name,
            created_by=created_by,
            env_profile=env_profile,
            output_name=output_name,
            options=options,
        )
        task = self._create_task_record(payload)
        runtime_dirs = self.translation_service.ensure_runtime_dirs(task=task)
        destination = Path(runtime_dirs["sources_dir"]) / Path(file.filename or "upload.tar.gz").name

        try:
            with destination.open("wb") as output:
                shutil.copyfileobj(file.file, output)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store upload: {exc}",
            ) from exc
        finally:
            file.file.close()

        from backend.app.workers.translation_runner import submit_task

        submit_task(task.id)
        return self.get_task_detail(task.id)

    def list_tasks(
        self,
        *,
        page: int,
        page_size: int,
        status_filter: str | None = None,
        task_name: str | None = None,
        arxiv_id: str | None = None,
        created_by: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> TaskListResponse:
        tasks, total = self.repository.list_tasks(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            task_name=task_name,
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
        return self._build_task_detail_response(task)

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
        from backend.app.workers.translation_runner import submit_task

        submit_task(task.id)
        return TaskRetryResponse(task=self.get_task_detail(task_id), message="Task re-queued.")

    def cancel_task(self, task_id: str) -> TaskCancelResponse:
        task = self._require_task(task_id)
        if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Terminal tasks cannot be canceled.",
            )

        cancel_time = datetime.utcnow()
        task.canceled_at = cancel_time
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELED
            task.current_stage = TaskStatus.CANCELED.value
            task.progress_percent = 100
            task.finished_at = cancel_time
        self.repository.add_event(
            TaskEvent(
                task=task,
                stage=TaskStatus.CANCELED.value,
                status=TaskStatus.CANCELED,
                message=(
                    "Task canceled before execution started."
                    if task.status == TaskStatus.CANCELED
                    else "Cancellation requested while task is still running."
                ),
            )
        )
        self.repository.commit()
        return TaskCancelResponse(task=self.get_task_detail(task_id), message="Task canceled.")

    def list_artifacts(self, task_id: str) -> ArtifactListResponse:
        task = self._require_task(task_id)
        return ArtifactListResponse(
            task_id=task.id,
            items=[self._to_artifact_response(artifact) for artifact in task.artifacts],
        )

    def list_logs(self, task_id: str) -> TaskLogsResponse:
        task = self._require_task(task_id)
        log_artifacts = [
            self._to_artifact_response(artifact)
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
        task_name: str | None = None,
        arxiv_id: str | None = None,
        created_by: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> ArchiveListResponse:
        tasks = self.repository.list_tasks_unpaginated(
            status_filter=status_filter,
            task_name=task_name,
            arxiv_id=arxiv_id,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
        )
        grouped_items = self.archive_service.build_archive_groups(tasks)
        total = len(grouped_items)
        start = (page - 1) * page_size
        end = start + page_size
        return ArchiveListResponse(items=grouped_items[start:end], total=total, page=page, page_size=page_size)

    def get_failure_summary(self, *, limit: int = 20) -> FailureSummaryResponse:
        tasks, total = self.repository.list_tasks(
            page=1,
            page_size=limit,
            status_filter=TaskStatus.FAILED.value,
        )
        stage_counts: dict[str, int] = {}
        for task in tasks:
            stage_counts[task.current_stage] = stage_counts.get(task.current_stage, 0) + 1
        return FailureSummaryResponse(
            recent_failed_tasks=[TaskSummaryResponse.model_validate(task) for task in tasks],
            failed_stage_counts=stage_counts,
            total_failed=total,
        )

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

    def _to_artifact_response(self, artifact: TaskArtifact):
        response = TaskArtifactResponse.model_validate(artifact)
        response.download_url = self.storage_service.get_download_url(artifact.object_key)
        return response

    def _create_task_record(self, payload: TaskCreateRequest) -> TranslationTask:
        task_id = str(uuid.uuid4())
        task_name = self._sanitize_task_name(payload.task_name or self._derive_task_name(payload))
        model_name = payload.model_name or self.settings.openai_model or "gpt-4.1"
        created_by = payload.created_by or self.settings.default_created_by
        workspace_dir = str(Path(self.settings.task_workspace_root) / f"{task_name}-{task_id}")
        output_dir = str(Path(workspace_dir) / "output")

        task = TranslationTask(
            id=task_id,
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
        return task

    def _build_task_detail_response(self, task: TranslationTask) -> TaskDetailResponse:
        summary = TaskSummaryResponse.model_validate(task)
        return TaskDetailResponse(
            **summary.model_dump(),
            artifacts=[self._to_artifact_response(artifact) for artifact in task.artifacts],
            events=[event for event in task.events],
            configs=[config for config in task.configs],
        )

    def _sanitize_task_name(self, value: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
        return sanitized or f"task-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    def _validate_upload_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload file is required.")
        name = file.filename.lower()
        allowed = (".zip", ".tar", ".tar.gz", ".tgz")
        if not any(name.endswith(suffix) for suffix in allowed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .zip, .tar, .tar.gz, or .tgz archives are supported.",
            )
