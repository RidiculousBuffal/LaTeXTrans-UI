from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.cache import CacheEntryStatus
from backend.app.models.task import (
    TaskArtifact,
    TaskArtifactType,
    TaskConfig,
    TaskEngine,
    TaskEvent,
    TaskResultSource,
    TaskSourceType,
    TaskStatus,
    TranslationTask,
)
from backend.app.models.user import User, UserRole
from backend.app.repositories.task_repository import TaskRepository
from backend.app.schemas.task import (
    ArchiveListResponse,
    ArtifactListResponse,
    FailureSummaryResponse,
    TaskCancelResponse,
    TaskArtifactResponse,
    TaskConfigResponse,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskListResponse,
    TaskLogsResponse,
    TaskRetryResponse,
    TaskSummaryResponse,
)
from backend.app.services.access_service import AccessService
from backend.app.services.archive_service import ArchiveService
from backend.app.services.babeldoc_service import BabelDocService
from backend.app.services.cache_service import CacheService
from backend.app.services.quota_service import QuotaService
from backend.app.services.storage_service import StorageService
from backend.app.services.translation_service import TranslationService


class TaskService:
    _VISIBLE_ARTIFACT_TYPES = frozenset(
        {
            TaskArtifactType.EXTRACTED_SOURCE,
            TaskArtifactType.TRANSLATED_PROJECT,
            TaskArtifactType.FINAL_PDF,
            TaskArtifactType.SOURCE_PDF,
            TaskArtifactType.TRANSLATED_PDF,
            TaskArtifactType.BABELDOC_OUTPUT,
        }
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TaskRepository(db)
        self.settings = get_settings()
        self.translation_service = TranslationService()
        self.babeldoc_service = BabelDocService()
        self.archive_service = ArchiveService()
        self.storage_service = StorageService()

    def create_task(self, payload: TaskCreateRequest, owner: User) -> TaskDetailResponse:
        options = payload.options or {}
        model_name = payload.model_name or self.settings.openai_model or "gpt-4.1"

        # Cache lookup for arXiv tasks
        cache_service = CacheService(self.db)
        cache_key = None
        cache_entry = None
        normalized_arxiv_id = None

        if self.settings.cache_enabled and payload.source_type == TaskSourceType.ARXIV and payload.arxiv_id:
            cache_key, normalized_arxiv_id, _ = cache_service.get_cache_key_for_arxiv(
                engine=payload.engine.value,
                arxiv_id=payload.arxiv_id,
                source_language=payload.source_language,
                target_language=payload.target_language,
                model_name=model_name,
                options=options,
            )
            cache_entry = cache_service.lookup(cache_key)

        if cache_entry:
            # Cache hit: create task record and copy artifacts
            task = self._create_task_record(payload, owner=owner, result_source="CACHE_HIT", quota_cost=0)
            task.cache_entry_id = cache_entry.id
            self._copy_cache_artifacts(task, cache_entry)
            task.status = TaskStatus.SUCCEEDED
            task.current_stage = TaskStatus.SUCCEEDED.value
            task.progress_percent = 100
            task.started_at = datetime.utcnow()
            task.finished_at = datetime.utcnow()
            cache_service.record_hit(cache_entry)
            self.repository.commit()
            return self.get_task_detail(task.id, current_user=owner)

        # Quota check
        bypass_quota = self.settings.admin_tasks_bypass_quota and owner.role == UserRole.ADMIN
        if not bypass_quota:
            quota_service = QuotaService(self.db)
            quota_service.check_and_deduct(owner, task_id="pending", cost=1)

        task = self._create_task_record(payload, owner=owner, result_source="EXECUTED", quota_cost=1 if not bypass_quota else 0)
        task.quota_charged = not bypass_quota

        # Create cache building entry
        if self.settings.cache_enabled and cache_key and payload.arxiv_id:
            existing = cache_service.lookup_building(cache_key)
            if not existing:
                cache_service.create_building(
                    cache_key=cache_key,
                    engine=payload.engine.value,
                    source_fingerprint_type="arxiv",
                    normalized_arxiv_id=normalized_arxiv_id,
                    source_file_hash=None,
                    source_language=payload.source_language,
                    target_language=payload.target_language,
                    model_name=model_name,
                    options=options,
                    canonical_task_id=task.id,
                )

        # Update quota ledger with real task_id
        if not bypass_quota:
            self.db.query(__import__('backend.app.models.quota', fromlist=['UserQuotaLedger']).UserQuotaLedger).filter_by(
                reason_ref_id="pending", user_id=owner.id
            ).update({"reason_ref_id": task.id})

        self.repository.commit()

        from backend.app.workers.translation_runner import submit_task
        submit_task(task.id)
        return self.get_task_detail(task.id, current_user=owner)

    def create_upload_task(
        self,
        *,
        file: UploadFile,
        task_name: str | None,
        source_language: str,
        target_language: str,
        model_name: str | None,
        env_profile: str,
        output_name: str | None,
        options: dict,
        owner: User,
    ) -> TaskDetailResponse:
        self._validate_upload_file(file)

        # Compute file hash for cache
        file_bytes = file.file.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file.file.seek(0)

        model = model_name or self.settings.openai_model or "gpt-4.1"
        cache_service = CacheService(self.db)
        cache_key = None
        cache_entry = None

        if self.settings.cache_enabled:
            cache_key, _ = cache_service.get_cache_key_for_file(
                engine=TaskEngine.LATEX.value,
                file_hash=file_hash,
                source_language=source_language,
                target_language=target_language,
                model_name=model,
                options=options,
            )
            cache_entry = cache_service.lookup(cache_key)

        payload = TaskCreateRequest(
            engine=TaskEngine.LATEX,
            task_name=task_name,
            source_type=TaskSourceType.UPLOAD,
            source_archive_name=file.filename,
            source_language=source_language,
            target_language=target_language,
            model_name=model_name,
            env_profile=env_profile,
            output_name=output_name,
            options=options,
        )

        if cache_entry:
            task = self._create_task_record(payload, owner=owner, result_source="CACHE_HIT", quota_cost=0)
            task.source_file_hash = file_hash
            task.cache_entry_id = cache_entry.id
            self._copy_cache_artifacts(task, cache_entry)
            task.status = TaskStatus.SUCCEEDED
            task.current_stage = TaskStatus.SUCCEEDED.value
            task.progress_percent = 100
            task.started_at = datetime.utcnow()
            task.finished_at = datetime.utcnow()
            cache_service.record_hit(cache_entry)
            self.repository.commit()
            return self.get_task_detail(task.id, current_user=owner)

        bypass_quota = self.settings.admin_tasks_bypass_quota and owner.role == UserRole.ADMIN
        if not bypass_quota:
            quota_service = QuotaService(self.db)
            quota_service.check_and_deduct(owner, task_id="pending", cost=1)

        task = self._create_task_record(payload, owner=owner, result_source="EXECUTED", quota_cost=1 if not bypass_quota else 0)
        task.source_file_hash = file_hash
        task.quota_charged = not bypass_quota

        if self.settings.cache_enabled and cache_key:
            existing = cache_service.lookup_building(cache_key)
            if not existing:
                cache_service.create_building(
                    cache_key=cache_key,
                    engine=TaskEngine.LATEX.value,
                    source_fingerprint_type="file",
                    normalized_arxiv_id=None,
                    source_file_hash=file_hash,
                    source_language=source_language,
                    target_language=target_language,
                    model_name=model,
                    options=options,
                    canonical_task_id=task.id,
                )

        runtime_dirs = self.translation_service.ensure_runtime_dirs(task=task)
        destination = Path(runtime_dirs["sources_dir"]) / Path(file.filename or "upload.tar.gz").name
        try:
            with destination.open("wb") as output:
                output.write(file_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store upload: {exc}",
            ) from exc
        finally:
            file.file.close()

        if not bypass_quota:
            from backend.app.models.quota import UserQuotaLedger
            self.db.query(UserQuotaLedger).filter_by(reason_ref_id="pending", user_id=owner.id).update(
                {"reason_ref_id": task.id}
            )

        self.repository.commit()
        from backend.app.workers.translation_runner import submit_task
        submit_task(task.id)
        return self.get_task_detail(task.id, current_user=owner)

    def create_pdf_task(
        self,
        *,
        file: UploadFile,
        task_name: str | None,
        target_language: str,
        model_name: str | None,
        env_profile: str,
        options: dict,
        owner: User,
    ) -> TaskDetailResponse:
        try:
            self.babeldoc_service.validate_pdf_file(file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        # Compute file hash for cache
        file_bytes = file.file.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file.file.seek(0)

        model = model_name or self.settings.openai_model or "gpt-4.1"
        cache_service = CacheService(self.db)
        cache_key = None
        cache_entry = None

        if self.settings.cache_enabled:
            cache_key, _ = cache_service.get_cache_key_for_file(
                engine=TaskEngine.BABELDOC.value,
                file_hash=file_hash,
                source_language="en",
                target_language=target_language,
                model_name=model,
                options=options,
            )
            cache_entry = cache_service.lookup(cache_key)

        payload = TaskCreateRequest(
            engine=TaskEngine.BABELDOC,
            task_name=task_name,
            source_type=TaskSourceType.PDF_UPLOAD,
            source_archive_name=file.filename,
            source_language="en",
            target_language=target_language,
            model_name=model_name,
            env_profile=env_profile,
            options=options,
        )

        if cache_entry:
            task = self._create_task_record(payload, owner=owner, result_source="CACHE_HIT", quota_cost=0)
            task.source_file_hash = file_hash
            task.cache_entry_id = cache_entry.id
            self._copy_cache_artifacts(task, cache_entry)
            task.status = TaskStatus.SUCCEEDED
            task.current_stage = TaskStatus.SUCCEEDED.value
            task.progress_percent = 100
            task.started_at = datetime.utcnow()
            task.finished_at = datetime.utcnow()
            cache_service.record_hit(cache_entry)
            self.repository.commit()
            return self.get_task_detail(task.id, current_user=owner)

        bypass_quota = self.settings.admin_tasks_bypass_quota and owner.role == UserRole.ADMIN
        if not bypass_quota:
            quota_service = QuotaService(self.db)
            quota_service.check_and_deduct(owner, task_id="pending", cost=1)

        task = self._create_task_record(payload, owner=owner, result_source="EXECUTED", quota_cost=1 if not bypass_quota else 0)
        task.source_file_hash = file_hash
        task.quota_charged = not bypass_quota

        if self.settings.cache_enabled and cache_key:
            existing = cache_service.lookup_building(cache_key)
            if not existing:
                cache_service.create_building(
                    cache_key=cache_key,
                    engine=TaskEngine.BABELDOC.value,
                    source_fingerprint_type="file",
                    normalized_arxiv_id=None,
                    source_file_hash=file_hash,
                    source_language="en",
                    target_language=target_language,
                    model_name=model,
                    options=options,
                    canonical_task_id=task.id,
                )

        runtime_dirs = self.translation_service.ensure_runtime_dirs(task=task)
        destination = Path(runtime_dirs["sources_dir"]) / Path(file.filename or "document.pdf").name
        try:
            with destination.open("wb") as output:
                output.write(file_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store PDF upload: {exc}",
            ) from exc
        finally:
            file.file.close()

        if not bypass_quota:
            from backend.app.models.quota import UserQuotaLedger
            self.db.query(UserQuotaLedger).filter_by(reason_ref_id="pending", user_id=owner.id).update(
                {"reason_ref_id": task.id}
            )

        self.repository.commit()
        from backend.app.workers.translation_runner import submit_task
        submit_task(task.id)
        return self.get_task_detail(task.id, current_user=owner)

    def list_tasks(
        self,
        *,
        page: int,
        page_size: int,
        status_filter: str | None = None,
        task_name: str | None = None,
        arxiv_id: str | None = None,
        scope: str = "mine",
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        current_user: User,
    ) -> TaskListResponse:
        tasks, total = self.repository.list_tasks(
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            task_name=task_name,
            arxiv_id=arxiv_id,
            created_from=created_from,
            created_to=created_to,
            scope=scope,
            current_user=current_user,
            db=self.db,
        )
        return TaskListResponse(
            items=[TaskSummaryResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_task_detail(self, task_id: str, current_user: User | None = None) -> TaskDetailResponse:
        task = self._require_task(task_id)
        if current_user is not None:
            access = AccessService(self.db)
            if not access.can_view_task(task, current_user):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return self._build_task_detail_response(task)

    def retry_task(self, task_id: str, current_user: User) -> TaskRetryResponse:
        task = self._require_task(task_id)
        self._require_manage_access(task, current_user)
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
        return TaskRetryResponse(task=self.get_task_detail(task_id, current_user=current_user), message="Task re-queued.")

    def cancel_task(self, task_id: str, current_user: User) -> TaskCancelResponse:
        task = self._require_task(task_id)
        self._require_manage_access(task, current_user)
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
        return TaskCancelResponse(task=self.get_task_detail(task_id, current_user=current_user), message="Task canceled.")

    def list_artifacts(self, task_id: str, current_user: User) -> ArtifactListResponse:
        task = self._require_task(task_id)
        access = AccessService(self.db)
        if not access.can_view_task(task, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return ArtifactListResponse(
            task_id=task.id,
            items=[
                self._to_artifact_response(artifact)
                for artifact in task.artifacts
                if self._is_visible_artifact(artifact)
            ],
        )

    def list_logs(self, task_id: str, current_user: User) -> TaskLogsResponse:
        task = self._require_task(task_id)
        access = AccessService(self.db)
        if not access.can_view_task(task, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        if not task.workspace_dir:
            return TaskLogsResponse(task_id=task.id, exists=False, content="")

        log_path = Path(task.workspace_dir) / "runtime" / "task.log"
        if not log_path.exists():
            return TaskLogsResponse(task_id=task.id, path=str(log_path), exists=False, content="")

        max_bytes = 64 * 1024
        size_bytes = log_path.stat().st_size
        truncated = size_bytes > max_bytes

        with log_path.open("rb") as handle:
            if truncated:
                handle.seek(-max_bytes, 2)
            content = handle.read().decode("utf-8", errors="replace")

        if truncated:
            content = "[log truncated to last 64KB]\n" + content

        return TaskLogsResponse(
            task_id=task.id,
            path=str(log_path),
            exists=True,
            content=content,
            size_bytes=size_bytes,
            truncated=truncated,
            updated_at=datetime.utcfromtimestamp(log_path.stat().st_mtime),
        )

    def delete_task(self, task_id: str, current_user: User) -> None:
        task = self._require_task(task_id)
        self._require_manage_access(task, current_user)
        self.db.delete(task)
        self.db.commit()

    def list_archives(
        self,
        *,
        page: int,
        page_size: int,
        status_filter: str | None = None,
        task_name: str | None = None,
        arxiv_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        scope: str = "mine",
        current_user: User,
    ) -> ArchiveListResponse:
        # Fetch all matching tasks with scope-aware access control (no pagination yet —
        # grouping happens in memory, then we slice).
        tasks, _ = self.repository.list_tasks(
            page=1,
            page_size=10_000,
            status_filter=status_filter,
            task_name=task_name,
            arxiv_id=arxiv_id,
            created_from=created_from,
            created_to=created_to,
            scope=scope if current_user.role == UserRole.ADMIN or scope != "all" else "all",
            current_user=current_user,
            db=self.db,
        )
        grouped_items = self.archive_service.build_archive_groups(tasks)
        total = len(grouped_items)
        start = (page - 1) * page_size
        end = start + page_size
        return ArchiveListResponse(items=grouped_items[start:end], total=total, page=page, page_size=page_size)

    def get_failure_summary(self, *, limit: int = 20, current_user: User) -> FailureSummaryResponse:
        tasks, total = self.repository.list_tasks(
            page=1,
            page_size=limit,
            status_filter=TaskStatus.FAILED.value,
            scope="all" if current_user.role == UserRole.ADMIN else "mine",
            current_user=current_user,
            db=self.db,
        )
        stage_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for task in tasks:
            stage_counts[task.current_stage] = stage_counts.get(task.current_stage, 0) + 1
            failure_type = self._classify_failure_type(task.error_message)
            type_counts[failure_type] = type_counts.get(failure_type, 0) + 1
        return FailureSummaryResponse(
            recent_failed_tasks=[TaskSummaryResponse.model_validate(task) for task in tasks],
            failed_stage_counts=stage_counts,
            failed_type_counts=type_counts,
            total_failed=total,
        )

    def _require_task(self, task_id: str) -> TranslationTask:
        task = self.repository.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
        return task

    def _require_manage_access(self, task: TranslationTask, user: User) -> None:
        access = AccessService(self.db)
        if not access.can_manage_task(task, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

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

    def _create_task_record(
        self,
        payload: TaskCreateRequest,
        owner: User,
        result_source: str = "EXECUTED",
        quota_cost: int = 1,
    ) -> TranslationTask:
        task_id = str(uuid.uuid4())
        task_name = self._sanitize_task_name(payload.task_name or self._derive_task_name(payload))
        model_name = payload.model_name or self.settings.openai_model or "gpt-4.1"
        workspace_dir = str(Path(self.settings.task_workspace_root) / f"{task_name}-{task_id}")
        output_dir = str(Path(workspace_dir) / "output")

        task = TranslationTask(
            id=task_id,
            task_name=task_name,
            engine=payload.engine,
            source_type=payload.source_type,
            arxiv_id=payload.arxiv_id,
            source_archive_name=payload.source_archive_name,
            source_language=payload.source_language,
            target_language=payload.target_language,
            model_name=model_name,
            status=TaskStatus.PENDING,
            current_stage=TaskStatus.PENDING.value,
            progress_percent=0,
            created_by=owner.username,
            owner_user_id=owner.id,
            visibility="private",
            result_source=result_source,
            quota_cost=quota_cost,
            quota_charged=False,
            workspace_dir=workspace_dir,
            output_dir=output_dir,
        )

        snapshot = self.translation_service.build_config_snapshot(task=task, payload=payload)
        config = TaskConfig(task=task, env_profile=payload.env_profile, config_snapshot_json=snapshot)
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

    def _copy_cache_artifacts(self, task: TranslationTask, cache_entry) -> None:
        """Copy artifact records from the canonical task to the new task (same MinIO objects)."""
        if not cache_entry.canonical_task_id:
            return
        canonical_task = self.repository.get_task_by_id(cache_entry.canonical_task_id)
        if not canonical_task:
            return
        for artifact in canonical_task.artifacts:
            if not self._is_visible_artifact(artifact):
                continue
            new_artifact = TaskArtifact(
                task_id=task.id,
                artifact_type=artifact.artifact_type,
                object_key=artifact.object_key,
                file_name=artifact.file_name,
                content_type=artifact.content_type,
                file_size=artifact.file_size,
                version=artifact.version,
                metadata_json=artifact.metadata_json,
            )
            self.db.add(new_artifact)

    def _build_task_detail_response(self, task: TranslationTask) -> TaskDetailResponse:
        summary = TaskSummaryResponse.model_validate(task)
        return TaskDetailResponse(
            **summary.model_dump(),
            artifacts=[
                self._to_artifact_response(artifact)
                for artifact in task.artifacts
                if self._is_visible_artifact(artifact)
            ],
            events=[event for event in task.events],
            configs=[self._to_config_response(config) for config in task.configs],
        )

    def _is_visible_artifact(self, artifact: TaskArtifact) -> bool:
        return artifact.artifact_type in self._VISIBLE_ARTIFACT_TYPES

    def _to_config_response(self, config: TaskConfig) -> TaskConfigResponse:
        sanitized_snapshot = dict(config.config_snapshot_json or {})
        llm_config = sanitized_snapshot.get("llm_config")
        if isinstance(llm_config, dict):
            sanitized_snapshot["llm_config"] = {
                key: value
                for key, value in llm_config.items()
                if key not in {"base_url", "api_key"}
            }
        return TaskConfigResponse(
            id=config.id,
            task_id=config.task_id,
            env_profile=config.env_profile,
            config_snapshot_json=sanitized_snapshot,
            created_at=config.created_at,
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

    def _classify_failure_type(self, error_message: str | None) -> str:
        if not error_message:
            return "unknown"
        normalized = error_message.lower()
        if "timeout" in normalized:
            return "timeout"
        if "api" in normalized or "openai" in normalized or "rate limit" in normalized:
            return "model_call_error"
        if "compile" in normalized or "latex" in normalized or ".pdf" in normalized:
            return "compile_error"
        if "archive" in normalized or "extract" in normalized or "zip" in normalized or "tar" in normalized:
            return "input_archive_error"
        if "download" in normalized or "arxiv" in normalized:
            return "source_download_error"
        if "upload" in normalized or "minio" in normalized or "bucket" in normalized:
            return "artifact_upload_error"
        if "json" in normalized or "metadata" in normalized:
            return "metadata_error"
        return "runtime_error"
