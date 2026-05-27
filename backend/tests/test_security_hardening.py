from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker
from starlette.datastructures import UploadFile

from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import rate_limiter
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models.quota import UserQuotaAccount, UserQuotaLedger
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
from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import hash_password
from backend.app.services.quota_service import QuotaService
from backend.app.services.task_service import TaskService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        yield db_session

    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides = original_overrides


@pytest.fixture(autouse=True)
def reset_settings_and_rate_limits():
    settings = get_settings()
    original_values = {
        "auth_register_enabled": settings.auth_register_enabled,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "rate_limit_login_limit": settings.rate_limit_login_limit,
        "rate_limit_login_window_seconds": settings.rate_limit_login_window_seconds,
        "rate_limit_register_limit": settings.rate_limit_register_limit,
        "rate_limit_register_window_seconds": settings.rate_limit_register_window_seconds,
        "rate_limit_task_create_limit": settings.rate_limit_task_create_limit,
        "rate_limit_task_create_window_seconds": settings.rate_limit_task_create_window_seconds,
        "max_upload_bytes": settings.max_upload_bytes,
        "upload_stream_chunk_bytes": settings.upload_stream_chunk_bytes,
    }
    rate_limiter._buckets.clear()
    try:
        yield settings
    finally:
        for key, value in original_values.items():
            setattr(settings, key, value)
        rate_limiter._buckets.clear()


def _create_user(db: Session, *, username: str, password: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    QuotaService(db).initialize_quota(user)
    db.commit()
    db.refresh(user)
    return user


def test_register_disabled_by_default(client: TestClient) -> None:
    response = client.post("/api/auth/register", json={"username": "alice", "password": "supersecret123"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Self-service registration is disabled."


def test_login_sets_http_only_cookie_and_me_uses_cookie(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, username="alice", password="supersecret123")

    response = client.post("/api/auth/login", json={"username": "alice", "password": "supersecret123"})

    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in body
    assert body["user"]["username"] == "alice"
    cookie_header = response.headers["set-cookie"]
    assert "latextrans_session=" in cookie_header
    assert "HttpOnly" in cookie_header

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "alice"


def test_login_rate_limit_blocks_repeated_attempts(client: TestClient, reset_settings_and_rate_limits) -> None:
    settings = reset_settings_and_rate_limits
    settings.rate_limit_login_limit = 1
    settings.rate_limit_login_window_seconds = 300

    first = client.post("/api/auth/login", json={"username": "ghost", "password": "wrong"})
    second = client.post("/api/auth/login", json={"username": "ghost", "password": "wrong"})

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.headers["retry-after"] == "300"


def test_non_admin_task_detail_is_sanitized_and_logs_are_forbidden(db_session: Session) -> None:
    user = _create_user(db_session, username="bob", password="supersecret123")
    task = TranslationTask(
        id="task-1",
        task_name="paper",
        engine=TaskEngine.LATEX,
        source_type=TaskSourceType.UPLOAD,
        source_archive_name="paper.tar.gz",
        source_language="en",
        target_language="ch",
        model_name="gpt-4.1",
        status=TaskStatus.FAILED,
        current_stage=TaskStatus.FAILED.value,
        progress_percent=100,
        error_message="LaTeX compile failed: missing PDF output in /srv/runtime/task.log",
        created_by=user.username,
        owner_user_id=user.id,
        visibility="private",
        workspace_dir="/srv/runtime/tasks/paper-task-1",
        output_dir="/srv/runtime/tasks/paper-task-1/output",
    )
    task.artifacts.append(
        TaskArtifact(
            artifact_type=TaskArtifactType.FINAL_PDF,
            object_key="task-1/final/result.pdf",
            file_name="result.pdf",
            content_type="application/pdf",
            file_size=12,
            version=1,
            metadata_json={"local_path": "/srv/runtime/tasks/paper-task-1/output/result.pdf"},
        )
    )
    task.configs.append(
        TaskConfig(
            env_profile="default",
            config_snapshot_json={
                "tex_sources_dir": "/srv/runtime/tasks/paper-task-1/sources",
                "output_dir": "/srv/runtime/tasks/paper-task-1/output",
                "runtime": {"task_id": "task-1", "output_name": "paper"},
            },
        )
    )
    task.events.append(
        TaskEvent(
            stage=TaskStatus.FAILED.value,
            status=TaskStatus.FAILED,
            message="Translation task failed.",
            details_json={
                "command_path": "/usr/local/bin/babeldoc",
                "project_dir": "/srv/runtime/tasks/paper-task-1/project",
                "error": "LaTeX compile failed: missing PDF output in /srv/runtime/task.log",
            },
        )
    )
    db_session.add(task)
    db_session.commit()

    detail = TaskService(db_session).get_task_detail(task.id, current_user=user)

    assert detail.workspace_dir is None
    assert detail.output_dir is None
    assert detail.error_message == "Task failed while compiling translated output."
    assert detail.artifacts[0].metadata_json is None
    assert detail.configs[0].config_snapshot_json == {"runtime": {"output_name": "paper"}}
    assert detail.events[0].details_json == {"error": "Task failed while compiling translated output."}

    with pytest.raises(Exception) as exc_info:
        TaskService(db_session).list_logs(task.id, current_user=user)
    assert getattr(exc_info.value, "status_code", None) == 403


def test_stream_upload_to_temp_enforces_size_limit(db_session: Session, reset_settings_and_rate_limits, tmp_path: Path) -> None:
    settings = reset_settings_and_rate_limits
    settings.max_upload_bytes = 8
    settings.upload_stream_chunk_bytes = 4
    settings.upload_tmp_root = str(tmp_path)

    upload = UploadFile(filename="paper.tar.gz", file=BytesIO(b"0123456789"))
    service = TaskService(db_session)

    with pytest.raises(Exception) as exc_info:
        service._stream_upload_to_temp(upload)

    assert getattr(exc_info.value, "status_code", None) == 413
    assert not any(tmp_path.iterdir())


def test_production_settings_reject_insecure_defaults() -> None:
    with pytest.raises(ValueError):
        Settings(
            environment="production",
            jwt_secret_key="dev-insecure-local-jwt-secret",
            cors_origins=["*"],
            auth_cookie_secure=True,
        )

