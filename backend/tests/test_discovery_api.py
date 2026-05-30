from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models.discovery import (
    ArxivCollection,
    ArxivCollectionItem,
    ArxivDiscoveryRun,
    ArxivDiscoveryRunStatus,
    ArxivPaper,
    ArxivPaperEnrichment,
    ArxivPaperReview,
    ArxivPaperReviewType,
)
from backend.app.models.task import TaskEngine, TaskSourceType, TaskStatus, TranslationTask
from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import hash_password
from backend.app.services.quota_service import QuotaService


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

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides = original


def _create_user(db: Session, username: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        username=username,
        password_hash=hash_password("supersecret123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    QuotaService(db).initialize_quota(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client: TestClient, username: str, password: str = "supersecret123") -> None:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def test_discovery_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/discovery/papers" in paths
    assert "/api/discovery/papers/{paper_id}" in paths
    assert "/api/discovery/collections" in paths
    assert "/api/discovery/daily-digest" in paths


def test_list_papers_and_collections_for_current_user(client: TestClient, db_session: Session) -> None:
    settings = get_settings()
    settings.auth_register_enabled = False
    user = _create_user(db_session, "alice")
    other_user = _create_user(db_session, "bob")

    paper = ArxivPaper(
        arxiv_id="2501.00001",
        primary_category="cs.AI",
        title_en="A Useful Paper",
        abstract_en="This paper studies useful systems.",
        authors_json=["Alice", "Bob"],
        pdf_url="https://arxiv.org/pdf/2501.00001.pdf",
        abs_url="https://arxiv.org/abs/2501.00001",
        subjects_json=["cs.AI"],
        comments="12 pages",
        scraped_at=datetime.utcnow(),
        source_run_date=date(2026, 5, 28),
    )
    db_session.add(paper)
    db_session.flush()

    # 全局 enrichment（title_zh / abstract_zh 归属于此）
    db_session.add(
        ArxivPaperEnrichment(
            paper_id=paper.id,
            enrichment_type="global_summary",
            model_name="gpt-4.1-mini",
            title_zh="一篇有用的论文",
            abstract_zh="这是中文摘要。",
        )
    )

    collection = ArxivCollection(
        user_id=user.id,
        name="Daily AI",
        description="papers to watch",
        categories_json=["cs.AI"],
        prefer_keywords="useful,systems",
        avoid_keywords="biology",
    )
    db_session.add(collection)
    db_session.flush()

    db_session.add(
        ArxivPaperReview(
            paper_id=paper.id,
            collection_id=collection.id,
            review_type=ArxivPaperReviewType.DAILY_JUDGE,
            model_name="gpt-4.1-mini",
            worth_read=True,
            comment="值得跟进。",
            raw_result_json={"judgment": {"worth_read": True}},
        )
    )
    db_session.add(
        ArxivCollectionItem(
            collection_id=collection.id,
            paper_id=paper.id,
            added_by_user_id=user.id,
        )
    )

    private_task = TranslationTask(
        id="task-1",
        task_name="arxiv-2501.00001",
        engine=TaskEngine.LATEX,
        source_type=TaskSourceType.ARXIV,
        arxiv_id="2501.00001",
        source_language="en",
        target_language="ch",
        model_name="gpt-4.1",
        status=TaskStatus.SUCCEEDED,
        current_stage=TaskStatus.SUCCEEDED.value,
        progress_percent=100,
        created_by=user.username,
        owner_user_id=user.id,
        visibility="private",
    )
    hidden_task = TranslationTask(
        id="task-2",
        task_name="arxiv-2501.00001-hidden",
        engine=TaskEngine.LATEX,
        source_type=TaskSourceType.ARXIV,
        arxiv_id="2501.00001",
        source_language="en",
        target_language="ch",
        model_name="gpt-4.1",
        status=TaskStatus.SUCCEEDED,
        current_stage=TaskStatus.SUCCEEDED.value,
        progress_percent=100,
        created_by=other_user.username,
        owner_user_id=other_user.id,
        visibility="private",
    )
    db_session.add(private_task)
    db_session.add(hidden_task)
    db_session.add(
        ArxivDiscoveryRun(
            trigger_source="admin_manual",
            requested_by_user_id=user.id,
            source_run_date=date(2026, 5, 28),
            status=ArxivDiscoveryRunStatus.SUCCEEDED,
            categories_json=["cs.AI"],
            total_papers=1,
            total_reviews=1,
            total_worth_read=1,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    from backend.app.services.arxiv_persistence_service import ArxivPersistenceService

    ArxivPersistenceService(db_session).link_task_to_paper_by_arxiv_id(task=private_task, created_by_user_id=user.id)
    ArxivPersistenceService(db_session).link_task_to_paper_by_arxiv_id(task=hidden_task, created_by_user_id=other_user.id)
    db_session.commit()

    _login(client, "alice")

    papers_response = client.get("/api/discovery/papers")
    assert papers_response.status_code == 200
    payload = papers_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["arxiv_id"] == "2501.00001"
    assert payload["items"][0]["title_zh"] == "一篇有用的论文"
    assert payload["items"][0]["has_translation"] is True
    assert payload["items"][0]["translation_task_count"] == 1
    assert payload["items"][0]["collections"][0]["collection_name"] == "Daily AI"

    detail_response = client.get(f"/api/discovery/papers/{paper.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["reviews"]) == 1
    assert len(detail["tasks"]) == 1
    assert detail["latest_task"]["id"] == "task-1"

    collections_response = client.get("/api/discovery/collections")
    assert collections_response.status_code == 200
    collections = collections_response.json()
    assert collections["total"] == 1
    assert collections["items"][0]["item_count"] == 1
    assert collections["items"][0]["items"][0]["paper"]["arxiv_id"] == "2501.00001"

    digest_response = client.get("/api/discovery/daily-digest")
    assert digest_response.status_code == 200
    digest = digest_response.json()
    assert digest["run"]["status"] == "SUCCEEDED"
    assert digest["groups"][0]["category"] == "cs.AI"


def test_create_and_update_collection_via_api(client: TestClient, db_session: Session) -> None:
    _create_user(db_session, "alice")
    _login(client, "alice")

    create_response = client.post(
        "/api/discovery/collections",
        json={
            "name": "Vision",
            "description": "vision papers",
            "categories_json": ["cs.CV", "cs.AI"],
            "translation_mode": "manual",
        },
    )
    assert create_response.status_code == 201
    collection = create_response.json()
    assert collection["name"] == "Vision"
    assert collection["categories_json"] == ["cs.CV", "cs.AI"]

    update_response = client.patch(
        f"/api/discovery/collections/{collection['id']}",
        json={
            "translation_mode": "auto",
            "auto_translate_enabled": True,
            "prefer_keywords": "multimodal",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["translation_mode"] == "auto"
    assert updated["auto_translate_enabled"] is True
    assert updated["prefer_keywords"] == "multimodal"


def test_admin_sync_queues_run_when_async_huey_enabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _create_user(db_session, "admin", role=UserRole.ADMIN)
    collection = ArxivCollection(
        user_id=admin.id,
        name="Math",
        categories_json=["cs.MA"],
    )
    db_session.add(collection)
    db_session.commit()

    queued: list[str] = []

    def fake_async_enabled() -> bool:
        return True

    def fake_enqueue(run_id: str):
        queued.append(run_id)
        return None

    monkeypatch.setattr("backend.app.api.routes.admin.is_async_huey_enabled", fake_async_enabled)
    monkeypatch.setattr("backend.app.api.routes.admin.execute_discovery_run", fake_enqueue)

    _login(client, "admin")
    response = client.post(
        "/api/admin/discovery/sync",
        json={"source_run_date": "2026-05-28", "force_refresh": True},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "PENDING"
    assert queued == [payload["id"]]


def test_admin_sync_falls_back_to_inline_when_async_huey_disabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _create_user(db_session, "admin2", role=UserRole.ADMIN)
    collection = ArxivCollection(
        user_id=admin.id,
        name="Math",
        categories_json=["cs.MA"],
    )
    db_session.add(collection)
    db_session.commit()

    monkeypatch.setattr("backend.app.api.routes.admin.is_async_huey_enabled", lambda: False)

    def fake_execute_run(self, run_id: str):
        run = self.repository.get_run(run_id)
        assert run is not None
        run.status = ArxivDiscoveryRunStatus.SUCCEEDED
        run.started_at = datetime.utcnow()
        run.finished_at = datetime.utcnow()
        self.repository.commit()
        return run

    monkeypatch.setattr("backend.app.api.routes.admin.ArxivPipelineService.execute_run", fake_execute_run)

    _login(client, "admin2")
    response = client.post(
        "/api/admin/discovery/sync",
        json={"source_run_date": "2026-05-28", "force_refresh": True},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "SUCCEEDED"
