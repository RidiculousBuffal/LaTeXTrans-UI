from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.task_runtime import build_task_timeout_message
from backend.app.db.base import Base
from backend.app.models.task import (
    TaskArtifact,
    TaskArtifactType,
    TaskConfig,
    TaskEngine,
    TaskEvent,
    TaskSourceType,
    TaskStatus,
    TranslationTask,
)
from backend.app.repositories.task_repository import TaskRepository
from backend.app.services.babeldoc_service import BabelDocService
from backend.app.services.archive_service import ArchiveService
from backend.app.services.task_service import TaskService
from backend.app.services.translation_service import TranslationService
from backend.app.schemas.task import TaskCreateRequest
from backend.app.workers import translation_runner
from backend.app.workers.translation_runner import _ensure_not_canceled, _finalize_runtime_artifacts, _handle_translation_subprogress, _mark_canceled


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
        engine=TaskEngine.LATEX,
        source_type=TaskSourceType.ARXIV if arxiv_id else TaskSourceType.UPLOAD,
        arxiv_id=arxiv_id,
        source_archive_name=None if arxiv_id else f"{task_id}.tar.gz",
        source_language="en",
        target_language="ch",
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
            config_snapshot_json={"paper_list": [arxiv_id] if arxiv_id else [], "target_language": "ch"},
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
    assert groups[1].artifact_count == 0
    assert groups[1].latest_task.id == "task-2"


def test_finalize_runtime_artifacts_skips_runtime_debug_uploads(tmp_path: Path) -> None:
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
    assert refreshed.artifacts == []
    assert storage.calls == []


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


def test_handle_translation_subprogress_updates_task_state_and_event_log(tmp_path: Path) -> None:
    session = make_session()
    task = seed_task(session, task_id="subprogress", status=TaskStatus.TRANSLATING)
    repository = TaskRepository(session)
    event_log_path = tmp_path / "task-events.jsonl"
    progress_state: dict[str, tuple[int, int]] = {}

    _handle_translation_subprogress(
        repository=repository,
        task_id=task.id,
        event_log_path=event_log_path,
        payload={
            "phase": "initial_translation",
            "completed": 3,
            "total": 20,
            "message": "Initial translation progress: 3/20 sections completed.",
        },
        progress_state=progress_state,
    )

    refreshed = repository.get_task_by_id(task.id)
    assert refreshed is not None
    assert refreshed.current_stage == "TRANSLATING::INITIAL_TRANSLATION 3/20"
    assert refreshed.progress_percent == 62
    assert refreshed.events[-1].message == "Initial translation progress: 3/20 sections completed."
    assert '"completed": 3' in event_log_path.read_text(encoding="utf-8")


def test_config_snapshot_normalizes_string_mode_to_int() -> None:
    session = make_session()
    task = seed_task(session, task_id="mode-task", status=TaskStatus.PENDING, arxiv_id="2605.23618")
    payload = TaskCreateRequest(
        source_type=TaskSourceType.ARXIV,
        arxiv_id="2605.23618",
        source_language="en",
        target_language="ch",
        model_name="gpt-4.1",
        options={"mode": "0", "update_term": "False", "user_term": ""},
    )

    snapshot = TranslationService().build_config_snapshot(task=task, payload=payload)

    assert snapshot["mode"] == 0
    assert isinstance(snapshot["mode"], int)
    assert snapshot["target_language"] == "ch"
    assert snapshot["runtime"]["task_timeout_seconds"] == TranslationService().settings.task_timeout_seconds


def test_task_detail_configs_do_not_expose_llm_credentials() -> None:
    session = make_session()
    task = seed_task(session, task_id="mask-config", status=TaskStatus.PENDING, arxiv_id="2605.23618")
    task.configs[0].config_snapshot_json = {
        "paper_list": ["2605.23618"],
        "llm_config": {
            "model": "gpt-4.1",
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-test-secret",
        },
    }
    session.commit()

    detail = TaskService(session).get_task_detail(task.id)
    llm_config = detail.configs[0].config_snapshot_json["llm_config"]

    assert llm_config["model"] == "gpt-4.1"
    assert "base_url" not in llm_config
    assert "api_key" not in llm_config


def test_task_detail_and_artifact_list_only_expose_delivery_artifacts() -> None:
    session = make_session()
    task = seed_task(session, task_id="artifact-filter", status=TaskStatus.SUCCEEDED, arxiv_id="2605.23618")
    task.artifacts.extend(
        [
            TaskArtifact(
                artifact_type=TaskArtifactType.FINAL_PDF,
                object_key="final.pdf",
                file_name="final.pdf",
                content_type="application/pdf",
                file_size=1,
                version=1,
            ),
            TaskArtifact(
                artifact_type=TaskArtifactType.EXTRACTED_SOURCE,
                object_key="source.tar.gz",
                file_name="source.tar.gz",
                content_type="application/gzip",
                file_size=1,
                version=1,
            ),
            TaskArtifact(
                artifact_type=TaskArtifactType.LOG,
                object_key="runtime.log",
                file_name="runtime.log",
                content_type="text/plain",
                file_size=1,
                version=1,
            ),
        ]
    )
    session.commit()

    service = TaskService(session)
    detail = service.get_task_detail(task.id)
    listed = service.list_artifacts(task.id)
    logs = service.list_logs(task.id)

    assert {artifact.artifact_type for artifact in detail.artifacts} == {
        TaskArtifactType.FINAL_PDF,
        TaskArtifactType.EXTRACTED_SOURCE,
    }
    assert {artifact.artifact_type for artifact in listed.items} == {
        TaskArtifactType.FINAL_PDF,
        TaskArtifactType.EXTRACTED_SOURCE,
    }
    assert logs.exists is False
    assert logs.content == ""


def test_run_task_marks_failed_when_pdf_missing(monkeypatch, tmp_path: Path) -> None:
    session = make_session()
    task = seed_task(session, task_id="missing-pdf", status=TaskStatus.PENDING, arxiv_id="2605.22781")
    workspace_dir = tmp_path / "workspace"
    runtime_dir = workspace_dir / "runtime"
    sources_dir = workspace_dir / "sources"
    output_dir = workspace_dir / "output"
    project_dir = sources_dir / "2605.22781"
    translated_project_dir = output_dir / f"{task.target_language}_{project_dir.name}"

    runtime_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)
    translated_project_dir.mkdir(parents=True, exist_ok=True)

    runtime_dirs = {
        "workspace_dir": str(workspace_dir),
        "runtime_dir": str(runtime_dir),
        "sources_dir": str(sources_dir),
        "output_dir": str(output_dir),
    }

    class FakeTranslationService:
        class settings:
            task_timeout_seconds = 1200

        def ensure_runtime_dirs(self, *, task: TranslationTask):
            return runtime_dirs

        def normalize_mode(self, value):
            return 0

    class FakePipelineService:
        def prepare_sources(self, *, config, workspace_dir):
            archive = sources_dir / "2605.22781.tar.gz"
            archive.write_text("dummy", encoding="utf-8")
            return [str(project_dir)], [archive]

        def run_translation_pipeline(self, *, config, project_dir, output_dir, progress_callback=None):
            return None

        def find_generated_pdf(self, *, translated_project_dir, target_language):
            return None

    class FakeStorageService:
        def upload_path(self, *, task: TranslationTask, artifact_type: TaskArtifactType, file_path, metadata=None):
            path = Path(file_path)
            if path.is_dir():
                file_name = path.name
                file_size = 0
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)
                file_name = path.name
                file_size = path.stat().st_size
            return TaskArtifact(
                task=task,
                artifact_type=artifact_type,
                object_key=f"{task.id}/{artifact_type.value.lower()}/{file_name}",
                file_name=file_name,
                content_type="application/octet-stream",
                file_size=file_size,
                version=1,
                metadata_json=metadata or {},
            )

    monkeypatch.setattr(translation_runner, "TranslationService", lambda: FakeTranslationService())
    monkeypatch.setattr(translation_runner, "PipelineService", lambda: FakePipelineService())
    monkeypatch.setattr(translation_runner, "StorageService", lambda: FakeStorageService())

    translation_runner._run_task(task_id=task.id, db=session)

    refreshed = TaskRepository(session).get_task_by_id(task.id)
    assert refreshed is not None
    assert refreshed.status == TaskStatus.FAILED
    assert refreshed.current_stage == TaskStatus.FAILED.value
    assert refreshed.error_message is not None
    assert "missing PDF output" in refreshed.error_message


def test_babeldoc_service_validate_pdf_file_rejects_non_pdf() -> None:
    service = BabelDocService()

    try:
        service.validate_pdf_file("paper.zip")
    except ValueError as exc:
        assert "Only .pdf files are supported." in str(exc)
    else:
        raise AssertionError("Expected non-pdf file to be rejected.")


def test_babeldoc_runtime_env_uses_workspace_local_home(tmp_path: Path) -> None:
    service = BabelDocService()

    env = service.build_runtime_env(workspace_dir=tmp_path)

    assert env["HOME"] == str(Path.home())
    assert "XDG_CACHE_HOME" not in env or not env["XDG_CACHE_HOME"].startswith(str(tmp_path))


def test_task_engine_enum_reads_lowercase_database_value() -> None:
    session = make_session()
    task = seed_task(session, task_id="engine-lowercase", status=TaskStatus.SUCCEEDED, arxiv_id="2605.10000")
    session.execute(
        text("UPDATE translation_tasks SET engine = 'latex' WHERE id = :task_id"),
        {"task_id": task.id},
    )
    session.commit()
    session.expire_all()

    reloaded = TaskRepository(session).get_task_by_id(task.id)

    assert reloaded is not None
    assert reloaded.engine == TaskEngine.LATEX


def test_list_logs_reads_local_runtime_log_file(tmp_path: Path) -> None:
    session = make_session()
    task = seed_task(session, task_id="log-task", status=TaskStatus.TRANSLATING, arxiv_id="2605.10001")
    task.workspace_dir = str(tmp_path / "workspace")
    session.commit()

    runtime_dir = Path(task.workspace_dir) / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    log_path = runtime_dir / "task.log"
    log_path.write_text("line1\nline2\n", encoding="utf-8")

    response = TaskService(session).list_logs(task.id)

    assert response.exists is True
    assert response.path == str(log_path)
    assert response.content == "line1\nline2\n"
    assert response.size_bytes == len("line1\nline2\n".encode("utf-8"))


def test_babeldoc_config_snapshot_records_engine_fields() -> None:
    session = make_session()
    task = seed_task(session, task_id="babeldoc-task", status=TaskStatus.PENDING)
    task.engine = TaskEngine.BABELDOC
    task.source_type = TaskSourceType.PDF_UPLOAD
    task.source_archive_name = "paper.pdf"
    session.commit()

    payload = TaskCreateRequest(
        engine=TaskEngine.BABELDOC,
        source_type=TaskSourceType.PDF_UPLOAD,
        source_archive_name="paper.pdf",
        target_language="zh",
        model_name="gpt-4.1",
        options={"qps": "10", "pool_max_workers": "12"},
    )

    snapshot = TranslationService().build_config_snapshot(task=task, payload=payload)

    assert snapshot["engine"] == "babeldoc"
    assert snapshot["source_type"] == "pdf_upload"
    assert snapshot["babeldoc"]["qps"] == 10
    assert snapshot["babeldoc"]["pool_max_workers"] == 12
    assert snapshot["babeldoc"]["openai_api_key_configured"] in {True, False}


def test_run_babeldoc_task_registers_pdf_artifacts(monkeypatch, tmp_path: Path) -> None:
    session = make_session()
    task = seed_task(session, task_id="babeldoc-run", status=TaskStatus.PENDING)
    task.engine = TaskEngine.BABELDOC
    task.source_type = TaskSourceType.PDF_UPLOAD
    task.source_archive_name = "sample.pdf"
    task.configs[0].config_snapshot_json = {
        "engine": "babeldoc",
        "source_type": "pdf_upload",
        "source_archive_name": "sample.pdf",
        "runtime": {"options": {}},
        "babeldoc": {"qps": 20, "pool_max_workers": 20},
    }
    session.commit()

    workspace_dir = tmp_path / "workspace"
    runtime_dir = workspace_dir / "runtime"
    sources_dir = workspace_dir / "sources"
    output_dir = workspace_dir / "output"
    babeldoc_output_dir = output_dir / "babeldoc"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    sources_dir.mkdir(parents=True, exist_ok=True)
    babeldoc_output_dir.mkdir(parents=True, exist_ok=True)
    (sources_dir / "sample.pdf").write_text("pdf-source", encoding="utf-8")
    translated_pdf = babeldoc_output_dir / "sample-zh.pdf"
    translated_pdf.write_text("translated-pdf", encoding="utf-8")

    runtime_dirs = {
        "workspace_dir": str(workspace_dir),
        "runtime_dir": str(runtime_dir),
        "sources_dir": str(sources_dir),
        "output_dir": str(output_dir),
        "babeldoc_output_dir": str(babeldoc_output_dir),
    }

    class FakeTranslationService:
        class settings:
            task_timeout_seconds = 1200

        def ensure_runtime_dirs(self, *, task: TranslationTask):
            return runtime_dirs

    class FakeBabelDocService:
        class settings:
            task_timeout_seconds = 1200

        def build_runtime_env(self, *, workspace_dir):
            return {"HOME": str(workspace_dir)}

        def build_command(self, **kwargs):
            return ["babeldoc", "--files", "sample.pdf"]

        def run_command(self, **kwargs):
            class Result:
                returncode = 0

            return Result()

        def find_translated_pdf(self, *, output_dir, original_name=None):
            return str(translated_pdf)

    class FakeStorageService:
        def upload_path(self, *, task: TranslationTask, artifact_type: TaskArtifactType, file_path, metadata=None):
            path = Path(file_path)
            file_name = path.name
            file_size = path.stat().st_size if path.exists() and path.is_file() else 0
            return TaskArtifact(
                task=task,
                artifact_type=artifact_type,
                object_key=f"{task.id}/{artifact_type.value.lower()}/{file_name}",
                file_name=file_name,
                content_type="application/octet-stream",
                file_size=file_size,
                version=1,
                metadata_json=metadata or {},
            )

    monkeypatch.setattr(translation_runner, "TranslationService", lambda: FakeTranslationService())
    monkeypatch.setattr(translation_runner, "BabelDocService", lambda: FakeBabelDocService())
    monkeypatch.setattr(translation_runner, "StorageService", lambda: FakeStorageService())

    translation_runner._run_task(task_id=task.id, db=session)

    refreshed = TaskRepository(session).get_task_by_id(task.id)
    assert refreshed is not None
    assert refreshed.status == TaskStatus.SUCCEEDED
    assert {artifact.artifact_type for artifact in refreshed.artifacts} == {
        TaskArtifactType.SOURCE_PDF,
        TaskArtifactType.TRANSLATED_PDF,
        TaskArtifactType.BABELDOC_OUTPUT,
    }


def test_run_babeldoc_task_marks_failed_on_timeout(monkeypatch, tmp_path: Path) -> None:
    session = make_session()
    task = seed_task(session, task_id="babeldoc-timeout", status=TaskStatus.PENDING)
    task.engine = TaskEngine.BABELDOC
    task.source_type = TaskSourceType.PDF_UPLOAD
    task.source_archive_name = "sample.pdf"
    task.configs[0].config_snapshot_json = {
        "engine": "babeldoc",
        "source_type": "pdf_upload",
        "source_archive_name": "sample.pdf",
        "runtime": {"options": {}, "task_timeout_seconds": 1200},
        "babeldoc": {"qps": 20, "pool_max_workers": 20},
    }
    session.commit()

    workspace_dir = tmp_path / "workspace"
    runtime_dir = workspace_dir / "runtime"
    sources_dir = workspace_dir / "sources"
    output_dir = workspace_dir / "output"
    babeldoc_output_dir = output_dir / "babeldoc"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    sources_dir.mkdir(parents=True, exist_ok=True)
    babeldoc_output_dir.mkdir(parents=True, exist_ok=True)
    (sources_dir / "sample.pdf").write_text("pdf-source", encoding="utf-8")

    runtime_dirs = {
        "workspace_dir": str(workspace_dir),
        "runtime_dir": str(runtime_dir),
        "sources_dir": str(sources_dir),
        "output_dir": str(output_dir),
        "babeldoc_output_dir": str(babeldoc_output_dir),
    }

    class FakeTranslationService:
        class settings:
            task_timeout_seconds = 1200

        def ensure_runtime_dirs(self, *, task: TranslationTask):
            return runtime_dirs

    class FakeBabelDocService:
        class settings:
            task_timeout_seconds = 1200

        def build_runtime_env(self, *, workspace_dir):
            return {"HOME": str(workspace_dir)}

        def build_command(self, **kwargs):
            return ["babeldoc", "--files", "sample.pdf"]

        def run_command(self, **kwargs):
            raise RuntimeError(build_task_timeout_message(timeout_seconds=1200, context="Translation task"))

        def find_translated_pdf(self, *, output_dir, original_name=None):
            return None

    class FakeStorageService:
        def upload_path(self, *, task: TranslationTask, artifact_type: TaskArtifactType, file_path, metadata=None):
            raise AssertionError("Artifacts should not upload after timeout.")

    monkeypatch.setattr(translation_runner, "TranslationService", lambda: FakeTranslationService())
    monkeypatch.setattr(translation_runner, "BabelDocService", lambda: FakeBabelDocService())
    monkeypatch.setattr(translation_runner, "StorageService", lambda: FakeStorageService())

    translation_runner._run_task(task_id=task.id, db=session)

    refreshed = TaskRepository(session).get_task_by_id(task.id)
    assert refreshed is not None
    assert refreshed.status == TaskStatus.FAILED
    assert refreshed.error_message is not None
    assert "timeout" in refreshed.error_message.lower()
