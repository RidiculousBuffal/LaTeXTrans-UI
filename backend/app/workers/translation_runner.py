from __future__ import annotations

import contextlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.app.core.logging import configure_logging
from backend.app.db.session import SessionLocal
from backend.app.models.task import TaskArtifactType, TaskEvent, TaskStatus, TranslationTask
from backend.app.repositories.task_repository import TaskRepository
from backend.app.services.pipeline_service import PipelineService
from backend.app.services.storage_service import StorageService
from backend.app.services.translation_service import TranslationService


configure_logging()
logger = logging.getLogger(__name__)

EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="translation-runner")

PHASE_PROGRESS = {
    TaskStatus.PENDING: 0,
    TaskStatus.DOWNLOADING: 10,
    TaskStatus.PARSING: 25,
    TaskStatus.TRANSLATING: 60,
    TaskStatus.VALIDATING: 80,
    TaskStatus.GENERATING: 95,
    TaskStatus.SUCCEEDED: 100,
    TaskStatus.FAILED: 100,
    TaskStatus.CANCELED: 100,
}


class TaskCanceledError(RuntimeError):
    pass


def submit_task(task_id: str) -> None:
    EXECUTOR.submit(run_task, task_id)


def run_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        _run_task(task_id=task_id, db=db)
    finally:
        db.close()


def _run_task(*, task_id: str, db: Session) -> None:
    repository = TaskRepository(db)
    translation_service = TranslationService()
    pipeline_service = PipelineService()
    storage_service = StorageService()

    task = repository.get_task_by_id(task_id)
    if not task:
        return

    runtime_dirs = translation_service.ensure_runtime_dirs(task=task)
    config = dict(task.configs[-1].config_snapshot_json)
    config["mode"] = translation_service.normalize_mode(config.get("mode", 0))
    config["tex_sources_dir"] = runtime_dirs["sources_dir"]
    config["output_dir"] = runtime_dirs["output_dir"]
    log_path = Path(runtime_dirs["runtime_dir"]) / "task.log"
    metadata_path = Path(runtime_dirs["runtime_dir"]) / "task-config.json"
    event_log_path = Path(runtime_dirs["runtime_dir"]) / "task-events.jsonl"
    metadata_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    projects: list[str] = []
    log_path.touch(exist_ok=True)
    event_log_path.touch(exist_ok=True)
    progress_state: dict[str, tuple[int, int]] = {}

    logger.info(
        "translation_task_started",
        extra={"task_id": task.id, "status": task.status.value, "workspace_dir": runtime_dirs["workspace_dir"]},
    )

    try:
        _ensure_not_canceled(repository=repository, task_id=task_id)
        _set_status(
            repository=repository,
            task_id=task_id,
            status=TaskStatus.DOWNLOADING,
            message="Preparing and downloading translation sources.",
            details={"workspace_dir": runtime_dirs["workspace_dir"]},
            event_log_path=event_log_path,
            set_started=True,
        )

        with log_path.open("a", encoding="utf-8") as log_file, contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            projects, _source_archives = pipeline_service.prepare_sources(
                config=config,
                workspace_dir=runtime_dirs["workspace_dir"],
            )
            _ensure_not_canceled(repository=repository, task_id=task_id)

            for project_dir in projects:
                _ensure_not_canceled(repository=repository, task_id=task_id)
                _set_status(
                    repository=repository,
                    task_id=task_id,
                    status=TaskStatus.PARSING,
                    message="Source project prepared and ready for parsing.",
                    details={"project_dir": project_dir},
                    event_log_path=event_log_path,
                )
                _ensure_not_canceled(repository=repository, task_id=task_id)
                _set_status(
                    repository=repository,
                    task_id=task_id,
                    status=TaskStatus.TRANSLATING,
                    message="Translation pipeline started.",
                    details={"project_dir": project_dir},
                    event_log_path=event_log_path,
                )
                pipeline_service.run_translation_pipeline(
                    config=config,
                    project_dir=project_dir,
                    output_dir=runtime_dirs["output_dir"],
                    progress_callback=lambda payload: _handle_translation_subprogress(
                        repository=repository,
                        task_id=task_id,
                        event_log_path=event_log_path,
                        payload=payload,
                        progress_state=progress_state,
                    ),
                )
                _ensure_not_canceled(repository=repository, task_id=task_id)
                _set_status(
                    repository=repository,
                    task_id=task_id,
                    status=TaskStatus.VALIDATING,
                    message="Translation finished, validating generated files.",
                    details={"project_dir": project_dir},
                    event_log_path=event_log_path,
                )

                translated_project_dir = str(
                    Path(runtime_dirs["output_dir"]) / f"{task.target_language}_{Path(project_dir).name}"
                )
                pdf_path = pipeline_service.find_generated_pdf(
                    translated_project_dir=translated_project_dir,
                    target_language=task.target_language,
                )
                if not pdf_path:
                    raise RuntimeError(
                        "LaTeX compile failed: missing PDF output. "
                        f"Please check logs under {translated_project_dir}/build_* and {log_path}."
                    )
                _ensure_not_canceled(repository=repository, task_id=task_id)
                _set_status(
                    repository=repository,
                    task_id=task_id,
                    status=TaskStatus.GENERATING,
                    message="Registering generated artifacts.",
                    details={"translated_project_dir": translated_project_dir},
                    event_log_path=event_log_path,
                )

                task = _require_task(repository, task_id)
                repository.add_artifact(
                    storage_service.upload_path(
                        task=task,
                        artifact_type=TaskArtifactType.EXTRACTED_SOURCE,
                        file_path=project_dir,
                    )
                )
                repository.add_artifact(
                    storage_service.upload_path(
                        task=task,
                        artifact_type=TaskArtifactType.TRANSLATED_PROJECT,
                        file_path=translated_project_dir,
                    )
                )

                if pdf_path:
                    repository.add_artifact(
                        storage_service.upload_path(
                            task=task,
                            artifact_type=TaskArtifactType.FINAL_PDF,
                            file_path=pdf_path,
                        )
                    )

        repository.commit()
        _ensure_not_canceled(repository=repository, task_id=task_id)
        _set_status(
            repository=repository,
            task_id=task_id,
            status=TaskStatus.SUCCEEDED,
            message="Translation task completed successfully.",
            details={"project_count": len(projects)},
            event_log_path=event_log_path,
            set_finished=True,
        )
        logger.info(
            "translation_task_succeeded",
            extra={"task_id": task_id, "project_count": len(projects)},
        )
    except TaskCanceledError:
        _mark_canceled(repository=repository, task_id=task_id, event_log_path=event_log_path)
        logger.info("translation_task_canceled", extra={"task_id": task_id})
    except Exception as exc:
        _mark_failed(repository=repository, task_id=task_id, exc=exc, event_log_path=event_log_path)
        logger.exception("translation_task_failed", extra={"task_id": task_id})
    finally:
        _finalize_runtime_artifacts(
            repository=repository,
            task_id=task_id,
            storage_service=storage_service,
            metadata_path=metadata_path,
            log_path=log_path,
            event_log_path=event_log_path,
        )


def _require_task(repository: TaskRepository, task_id: str) -> TranslationTask:
    task = repository.get_task_by_id(task_id)
    if not task:
        raise RuntimeError(f"Task {task_id} no longer exists.")
    return task


def _ensure_not_canceled(*, repository: TaskRepository, task_id: str) -> TranslationTask:
    task = _require_task(repository, task_id)
    if task.canceled_at or task.status == TaskStatus.CANCELED:
        raise TaskCanceledError(f"Task {task_id} has been canceled.")
    return task


def _mark_canceled(
    *,
    repository: TaskRepository,
    task_id: str,
    event_log_path: Path,
) -> None:
    task = repository.get_task_by_id(task_id)
    if not task:
        return

    canceled_at = task.canceled_at or datetime.utcnow()
    task.status = TaskStatus.CANCELED
    task.current_stage = TaskStatus.CANCELED.value
    task.progress_percent = PHASE_PROGRESS[TaskStatus.CANCELED]
    task.error_message = None
    task.finished_at = canceled_at
    task.canceled_at = canceled_at

    repository.add_event(
        TaskEvent(
            task=task,
            stage=TaskStatus.CANCELED.value,
            status=TaskStatus.CANCELED,
            message="Task canceled and execution halted before completion.",
        )
    )
    repository.commit()
    _append_event_log(
        event_log_path=event_log_path,
        payload={
            "timestamp": canceled_at.isoformat(),
            "status": TaskStatus.CANCELED.value,
            "message": "Task canceled and execution halted before completion.",
        },
    )


def _mark_failed(
    *,
    repository: TaskRepository,
    task_id: str,
    exc: Exception,
    event_log_path: Path,
) -> None:
    task = repository.get_task_by_id(task_id)
    if not task:
        return

    task.status = TaskStatus.FAILED
    task.current_stage = TaskStatus.FAILED.value
    task.progress_percent = PHASE_PROGRESS[TaskStatus.FAILED]
    task.error_message = str(exc)
    task.finished_at = datetime.utcnow()
    repository.add_event(
        TaskEvent(
            task=task,
            stage=TaskStatus.FAILED.value,
            status=TaskStatus.FAILED,
            message="Translation task failed.",
            details_json={"error": str(exc)},
        )
    )
    repository.commit()
    _append_event_log(
        event_log_path=event_log_path,
        payload={
            "timestamp": task.finished_at.isoformat() if task.finished_at else datetime.utcnow().isoformat(),
            "status": TaskStatus.FAILED.value,
            "message": "Translation task failed.",
            "details": {"error": str(exc)},
        },
    )


def _finalize_runtime_artifacts(
    *,
    repository: TaskRepository,
    task_id: str,
    storage_service: StorageService,
    metadata_path: Path,
    log_path: Path,
    event_log_path: Path,
) -> None:
    return


def _set_status(
    *,
    repository: TaskRepository,
    task_id: str,
    status: TaskStatus,
    message: str,
    event_log_path: Path,
    details: dict[str, Any] | None = None,
    set_started: bool = False,
    set_finished: bool = False,
) -> None:
    task = _require_task(repository, task_id)
    task.status = status
    task.current_stage = status.value
    task.progress_percent = PHASE_PROGRESS[status]
    if set_started and not task.started_at:
        task.started_at = datetime.utcnow()
    if set_finished:
        task.finished_at = datetime.utcnow()
        task.error_message = None

    repository.add_event(
        TaskEvent(
            task=task,
            stage=status.value,
            status=status,
            message=message,
            details_json=details,
        )
    )
    repository.commit()
    _append_event_log(
        event_log_path=event_log_path,
        payload={
            "timestamp": datetime.utcnow().isoformat(),
            "status": status.value,
            "message": message,
            "details": details,
        },
    )
    logger.info(
        "translation_task_status_changed",
        extra={"task_id": task.id, "status": status.value, "details": details or {}},
    )


def _handle_translation_subprogress(
    *,
    repository: TaskRepository,
    task_id: str,
    event_log_path: Path,
    payload: dict[str, Any],
    progress_state: dict[str, tuple[int, int]],
) -> None:
    phase = str(payload.get("phase") or "translation")
    completed = int(payload.get("completed") or 0)
    total = int(payload.get("total") or 0)
    message = str(payload.get("message") or "Translation sub-progress updated.")

    if total <= 0:
        return

    previous = progress_state.get(phase)
    current = (completed, total)
    if previous == current:
        return
    progress_state[phase] = current

    task = _require_task(repository, task_id)
    task.status = TaskStatus.TRANSLATING
    task.current_stage = f"TRANSLATING::{phase.upper()} {completed}/{total}"

    if phase == "initial_translation":
        task.progress_percent = min(79, 60 + int((completed / total) * 15))
    elif phase == "error_retry":
        task.progress_percent = min(94, 80 + int((completed / total) * 14))

    details = {
        "phase": phase,
        "completed": completed,
        "total": total,
        "message": message,
    }
    repository.add_event(
        TaskEvent(
            task=task,
            stage=task.current_stage,
            status=TaskStatus.TRANSLATING,
            message=message,
            details_json=details,
        )
    )
    repository.commit()
    _append_event_log(
        event_log_path=event_log_path,
        payload={
            "timestamp": datetime.utcnow().isoformat(),
            "status": TaskStatus.TRANSLATING.value,
            "message": message,
            "details": details,
        },
    )
    logger.info(
        "translation_task_subprogress_changed",
        extra={"task_id": task.id, "phase": phase, "completed": completed, "total": total},
    )


def _append_event_log(*, event_log_path: Path, payload: dict[str, Any]) -> None:
    with event_log_path.open("a", encoding="utf-8") as event_log:
        event_log.write(json.dumps(payload, ensure_ascii=False) + "\n")
