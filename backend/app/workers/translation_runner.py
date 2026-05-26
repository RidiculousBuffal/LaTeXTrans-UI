from __future__ import annotations

import contextlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.task import TaskArtifactType, TaskEvent, TaskStatus, TranslationTask
from backend.app.repositories.task_repository import TaskRepository
from backend.app.services.pipeline_service import PipelineService
from backend.app.services.storage_service import StorageService
from backend.app.services.translation_service import TranslationService


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

    try:
        if task.status == TaskStatus.CANCELED:
            return

        runtime_dirs = translation_service.ensure_runtime_dirs(task=task)
        config = dict(task.configs[-1].config_snapshot_json)
        config["tex_sources_dir"] = runtime_dirs["sources_dir"]
        config["output_dir"] = runtime_dirs["output_dir"]
        log_path = Path(runtime_dirs["runtime_dir"]) / "task.log"
        metadata_path = Path(runtime_dirs["runtime_dir"]) / "task-config.json"
        metadata_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

        _set_status(
            repository=repository,
            task=task,
            status=TaskStatus.DOWNLOADING,
            message="Preparing and downloading translation sources.",
            details={"workspace_dir": runtime_dirs["workspace_dir"]},
            set_started=True,
        )

        with log_path.open("a", encoding="utf-8") as log_file, contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            projects, source_archives = pipeline_service.prepare_sources(
                config=config,
                workspace_dir=runtime_dirs["workspace_dir"],
            )

            for source_archive in source_archives:
                repository.add_artifact(
                    storage_service.upload_path(
                        task=task,
                        artifact_type=TaskArtifactType.SOURCE_ARCHIVE,
                        file_path=source_archive,
                    )
                )

            for project_dir in projects:
                _set_status(
                    repository=repository,
                    task=task,
                    status=TaskStatus.PARSING,
                    message="Source project prepared and ready for parsing.",
                    details={"project_dir": project_dir},
                )
                _set_status(
                    repository=repository,
                    task=task,
                    status=TaskStatus.TRANSLATING,
                    message="Translation pipeline started.",
                    details={"project_dir": project_dir},
                )
                pipeline_service.run_translation_pipeline(
                    config=config,
                    project_dir=project_dir,
                    output_dir=runtime_dirs["output_dir"],
                )
                _set_status(
                    repository=repository,
                    task=task,
                    status=TaskStatus.VALIDATING,
                    message="Translation finished, validating generated files.",
                    details={"project_dir": project_dir},
                )

                translated_project_dir = str(
                    Path(runtime_dirs["output_dir"]) / f"{task.target_language}_{Path(project_dir).name}"
                )
                pdf_path = pipeline_service.find_generated_pdf(
                    translated_project_dir=translated_project_dir,
                    target_language=task.target_language,
                )

                _set_status(
                    repository=repository,
                    task=task,
                    status=TaskStatus.GENERATING,
                    message="Registering generated artifacts.",
                    details={"translated_project_dir": translated_project_dir},
                )

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

        repository.add_artifact(
            storage_service.upload_path(
                task=task,
                artifact_type=TaskArtifactType.METADATA,
                file_path=metadata_path,
            )
        )
        repository.add_artifact(
            storage_service.upload_path(
                task=task,
                artifact_type=TaskArtifactType.LOG,
                file_path=log_path,
            )
        )

        repository.commit()

        _set_status(
            repository=repository,
            task=task,
            status=TaskStatus.SUCCEEDED,
            message="Translation task completed successfully.",
            details={"project_count": len(projects)},
            set_finished=True,
        )
    except Exception as exc:
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


def _set_status(
    *,
    repository: TaskRepository,
    task: TranslationTask,
    status: TaskStatus,
    message: str,
    details: dict | None = None,
    set_started: bool = False,
    set_finished: bool = False,
) -> None:
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
