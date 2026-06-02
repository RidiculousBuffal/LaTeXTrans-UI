from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from backend.app.models.sharing import TaskShareGrant
from backend.app.models.task import TaskArtifact, TaskConfig, TaskEvent, TranslationTask
from backend.app.models.user import User, UserRole


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_task(self, task: TranslationTask) -> TranslationTask:
        self.db.add(task)
        self.db.flush()
        return task

    def add_event(self, event: TaskEvent) -> TaskEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def add_artifact(self, artifact: TaskArtifact) -> TaskArtifact:
        self.db.add(artifact)
        self.db.flush()
        return artifact

    def add_config(self, config: TaskConfig) -> TaskConfig:
        self.db.add(config)
        self.db.flush()
        return config

    def flush(self) -> None:
        self.db.flush()

    def get_task_by_id(self, task_id: str) -> TranslationTask | None:
        stmt = (
            select(TranslationTask)
            .where(TranslationTask.id == task_id)
            .options(
                selectinload(TranslationTask.artifacts),
                selectinload(TranslationTask.events),
                selectinload(TranslationTask.configs),
            )
        )
        return self._scalar_with_retry(stmt)

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
        scope: str = "mine",
        current_user: User | None = None,
        db: Session | None = None,
    ) -> tuple[list[TranslationTask], int]:
        filters = []
        if status_filter:
            filters.append(TranslationTask.status == status_filter)
        if task_name:
            filters.append(TranslationTask.task_name.ilike(f"%{task_name}%"))
        if arxiv_id:
            filters.append(TranslationTask.arxiv_id == arxiv_id)
        if created_by:
            filters.append(TranslationTask.created_by == created_by)
        if created_from:
            filters.append(TranslationTask.created_at >= created_from)
        if created_to:
            filters.append(TranslationTask.created_at <= created_to)

        # Scope / visibility filter
        scope_filter = self._build_scope_filter(current_user, scope, db or self.db)
        if scope_filter is not None:
            filters.append(scope_filter)

        stmt = (
            select(TranslationTask)
            .where(*filters)
            .options(selectinload(TranslationTask.artifacts))
            .order_by(TranslationTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(TranslationTask).where(*filters)
        items = list(self._scalars_with_retry(stmt).all())
        total = self._scalar_with_retry(count_stmt) or 0
        return items, total

    def _build_scope_filter(self, user: User | None, scope: str, db: Session):
        if user is None:
            if scope == "public":
                return TranslationTask.visibility == "public"
            return None
        if user.role == UserRole.ADMIN and scope == "all":
            return None  # No filter
        if scope == "mine":
            return TranslationTask.owner_user_id == user.id
        elif scope == "public":
            return TranslationTask.visibility == "public"
        elif scope == "shared":
            shared_ids = db.query(TaskShareGrant.task_id).filter_by(grantee_user_id=user.id).subquery()
            return TranslationTask.id.in_(shared_ids)
        else:
            shared_ids = db.query(TaskShareGrant.task_id).filter_by(grantee_user_id=user.id).subquery()
            return or_(
                TranslationTask.owner_user_id == user.id,
                TranslationTask.visibility == "public",
                TranslationTask.id.in_(shared_ids),
            )

    def list_tasks_unpaginated(
        self,
        *,
        status_filter: str | None = None,
        task_name: str | None = None,
        arxiv_id: str | None = None,
        created_by: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[TranslationTask]:
        filters = []
        if status_filter:
            filters.append(TranslationTask.status == status_filter)
        if task_name:
            filters.append(TranslationTask.task_name.ilike(f"%{task_name}%"))
        if arxiv_id:
            filters.append(TranslationTask.arxiv_id == arxiv_id)
        if created_by:
            filters.append(TranslationTask.created_by == created_by)
        if created_from:
            filters.append(TranslationTask.created_at >= created_from)
        if created_to:
            filters.append(TranslationTask.created_at <= created_to)

        stmt = (
            select(TranslationTask)
            .where(*filters)
            .options(selectinload(TranslationTask.artifacts))
            .order_by(TranslationTask.created_at.desc())
        )
        return list(self._scalars_with_retry(stmt).all())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def _scalar_with_retry(self, stmt):
        try:
            return self.db.scalar(stmt)
        except OperationalError as exc:
            if not self._is_retryable_connection_error(exc):
                raise
            self.db.rollback()
            return self.db.scalar(stmt)

    def _scalars_with_retry(self, stmt):
        try:
            return self.db.scalars(stmt)
        except OperationalError as exc:
            if not self._is_retryable_connection_error(exc):
                raise
            self.db.rollback()
            return self.db.scalars(stmt)

    def _is_retryable_connection_error(self, exc: OperationalError) -> bool:
        message = str(exc).lower()
        return "lost connection to mysql server during query" in message or "server has gone away" in message
