from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.base import Base
from backend.app.models.task import TaskArtifact, TaskArtifactType, TaskConfig, TaskEvent, TaskSourceType, TaskStatus, TranslationTask
from backend.app.repositories.task_repository import TaskRepository
from backend.app.services.archive_service import ArchiveService
from backend.app.services.task_service import TaskService
from backend.app.workers.translation_runner import _ensure_not_canceled, _finalize_runtime_artifacts, _mark_canceled


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return factory()


def seed_task(
    session: Session,
    *,
    task_id: str,
    status: TaskStatus = TaskStatus.PENDING,
    arxiv_id: str | None = None,
    created_at: datetime | None = None,
) -> TranslationTask:
    timestamp = created_at or datetime.utcnow()
    task = TranslationTask(
        id=task_id,
        task_name=f"task-{task_id}",
        source_type=TaskSourceType.ARXIV if arxiv_id else TaskSourceType.UPLOAD,
        arxiv_id=arxiv_id,
        source_archive_name=None if arxiv_id else f"{task_id}.tar.gz",
        source_language="en",
        target_language="zh",
        model_name="gpt-4.1",
        status=status,
        current_stage=status.value,
        progress_percent=0,
        created_by="tester",
        workspace_dir=f"/tmp/{task_id}",
        output_dir=f"/tmp/{task_id}/output",
        created_at=timestamp,
        updated_at=timestamp,
    )
    task.configs.append(
        TaskConfig(
            env_profile="default",
            config_snapshot_json={"paper_list": [arxiv_id] if arxiv_id else [], "target_language": "zh"},
        )
    )
    task.events.append(
        TaskEvent(
            stage=status.value,
            status=status,
            message="Task created.",
        )
    )
    session.add(task)
    session.commit()
    return task


def test_mark_canceled_sets_terminal_state_and_event_log(tmp_path: Path) -> None:
    session = make_session()
    task = seed_task(session, task_id="cancel-me", status=TaskStatus.TRANSLATING)
    task.canceled_at = datetime.utcnow()
    session.commit()

    repository = TaskRepository(session)
    event_log_path = tmp_path / "events.jsonl"

    _mark_canceled(repository=repository, task_id=task.id, event_log_path=event_log_path)

    refreshed = repository.get_task_by_id(task.id)
    assert refreshed is not None
    assert refreshed.status == TaskStatus.CANCELED
    assert refreshed.current_stage == TaskStatus.CANCELED.value
    assert refreshed.finished_at is not None
    assert refreshed.events[-1].status == TaskStatus.CANCELED
    assert "execution halted" in refreshed.events[-1].message
    assert "CANCELED" in event_log_path.read_text(encoding="utf-8")


def test_ensure_not_canceled_raises_for_canceled_task() -> None:
    session = make_session()
    task = seed_task(session, task_id="stopped", status=TaskStatus.TRANSLATING)
    task.canceled_at = datetime.utcnow()
    session.commit()

    repository = TaskRepository(session)

    try:
        _ensure_not_canceled(repository=repository, task_id=task.id)
    except RuntimeError as exc:
        assert "canceled" in str(exc).lower()
    else:
        raise AssertionError("Expected cancellation check to raise for canceled task.")


def test_archive_service_groups_same_arxiv_id() -> None:
    session = make_session()
    base_time = datetime.utcnow()
    first = seed_task(
        session,
        task_id="task-1",
        status=TaskStatus.SUCCEEDED,
        arxiv_id="2501.00001",
        created_at=base_time,
    )
    second = seed_task(
        session,
        task_id="task-2",
        status=TaskStatus.FAILED,
        arxiv_id="2501.00001",
        created_at=base_time + timedelta(minutes=5),
    )
    upload = seed_task(
        session,
        task_id="upload-1",
        status=TaskStatus.SUCCEEDED,
        arxiv_id=None,
        created_at=base_time + timedelta(minutes=10),
    )

    first.artifacts.append(
        TaskArtifact(
            artifact_type=TaskArtifactType.LOG,
            object_key="first/log",
            file_name="first.log",
            content_type="text/plain",
            file_size=1,
            version=1,
        )
    )
    second.artifacts.append(
        TaskArtifact(
            artifact_type=TaskArtifactType.METADATA,
            object_key="second/meta",
            file_name="meta.json",
            content_type="application/json",
            file_size=1,
            version=1,
        )
    )
    upload.artifacts.append(
        TaskArtifact(
            artifact_type=TaskArtifactType.FINAL_PDF,
            object_key="upload/pdf",
            file_name="result.pdf",
            content_type="application/pdf",
            file_size=1,
            version=1,
        )
    )
    session.commit()

    groups = ArchiveService().build_archive_groups([first, second, upload])

    assert len(groups) == 2
    assert groups[0].group_key == "task:upload-1"
    assert groups[1].group_key == "arxiv:2501.00001"
    assert groups[1].task_count == 2
    assert groups[1].artifact_count == 2
    assert groups[1].latest_task.id == "task-2"


def test_finalize_runtime_artifacts_keeps_prior_successful_records_on_later_failure(tmp_path: Path) -> None:
    session = make_session()
    task = seed_task(session, task_id="artifact-task", status=TaskStatus.FAILED)
    repository = TaskRepository(session)

    metadata_path = tmp_path / "task-config.json"
    log_path = tmp_path / "task.log"
    event_log_path = tmp_path / "task-events.jsonl"
    metadata_path.write_text("{}", encoding="utf-8")
    log_path.write_text("log", encoding="utf-8")
    event_log_path.write_text("{}", encoding="utf-8")

    class FakeStorageService:
        def __init__(self) -> None:
            self.calls: list[TaskArtifactType] = []

        def upload_path(self, *, task: TranslationTask, artifact_type: TaskArtifactType, file_path, metadata=None):
            self.calls.append(artifact_type)
            if artifact_type == TaskArtifactType.LOG:
                raise RuntimeError("minio upload failed")
            path = Path(file_path)
            return TaskArtifact(
                task=task,
                artifact_type=artifact_type,
                object_key=f"{task.id}/{artifact_type.value.lower()}/{path.name}",
                file_name=path.name,
                content_type="text/plain",
                file_size=path.stat().st_size,
                version=1,
                metadata_json=metadata or {},
            )

    storage = FakeStorageService()
    _finalize_runtime_artifacts(
        repository=repository,
        task_id=task.id,
        storage_service=storage,  # type: ignore[arg-type]
        metadata_path=metadata_path,
        log_path=log_path,
        event_log_path=event_log_path,
    )

    refreshed = repository.get_task_by_id(task.id)
    assert refreshed is not None
    artifact_names = {(artifact.artifact_type, artifact.file_name) for artifact in refreshed.artifacts}
    assert (TaskArtifactType.METADATA, "task-config.json") in artifact_names
    assert (TaskArtifactType.INTERMEDIATE_JSON, "task-events.jsonl") in artifact_names
    assert (TaskArtifactType.LOG, "task.log") not in artifact_names
    assert any("Failed to upload artifact: task.log" == event.message for event in refreshed.events)


def test_failure_summary_includes_failed_type_counts() -> None:
    session = make_session()
    timeout_task = seed_task(session, task_id="failed-timeout", status=TaskStatus.FAILED)
    timeout_task.error_message = "OpenAI API timeout while translating section 2"
    timeout_task.current_stage = TaskStatus.TRANSLATING.value

    compile_task = seed_task(session, task_id="failed-compile", status=TaskStatus.FAILED)
    compile_task.error_message = "LaTeX compile failed: missing PDF output"
    compile_task.current_stage = TaskStatus.GENERATING.value
    session.commit()

    summary = TaskService(session).get_failure_summary(limit=10)

    assert summary.failed_stage_counts[TaskStatus.TRANSLATING.value] == 1
    assert summary.failed_stage_counts[TaskStatus.GENERATING.value] == 1
    assert summary.failed_type_counts["timeout"] == 1
    assert summary.failed_type_counts["compile_error"] == 1
