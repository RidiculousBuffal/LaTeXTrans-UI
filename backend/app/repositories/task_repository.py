from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.task import TaskArtifact, TaskConfig, TaskEvent, TranslationTask


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
        return self.db.scalar(stmt)

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

        stmt = (
            select(TranslationTask)
            .where(*filters)
            .options(selectinload(TranslationTask.artifacts))
            .order_by(TranslationTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_stmt = select(func.count()).select_from(TranslationTask).where(*filters)
        items = list(self.db.scalars(stmt).all())
        total = self.db.scalar(count_stmt) or 0
        return items, total

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
