from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.sharing import TaskShareGrant
from backend.app.models.task import TranslationTask
from backend.app.models.user import User, UserRole


class AccessService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def can_view_task(self, task: TranslationTask, user: User | None) -> bool:
        if task.visibility == "public":
            return True
        if user is None:
            return False
        if user.role == UserRole.ADMIN:
            return True
        if task.owner_user_id == user.id:
            return True
        # Check direct share
        grant = (
            self.db.query(TaskShareGrant)
            .filter_by(task_id=task.id, grantee_user_id=user.id)
            .first()
        )
        return grant is not None

    def can_manage_task(self, task: TranslationTask, user: User) -> bool:
        """Can modify/delete/share the task."""
        if user.role == UserRole.ADMIN:
            return True
        return task.owner_user_id == user.id

    def filter_tasks_query(self, query, user: User, scope: str = "mine"):
        """Apply visibility filter to a SQLAlchemy query on TranslationTask."""
        from backend.app.models.task import TranslationTask as TT

        if user.role == UserRole.ADMIN and scope == "all":
            return query

        if scope == "mine":
            return query.filter(TT.owner_user_id == user.id)
        elif scope == "public":
            return query.filter(TT.visibility == "public")
        elif scope == "shared":
            shared_task_ids = (
                self.db.query(TaskShareGrant.task_id)
                .filter(TaskShareGrant.grantee_user_id == user.id)
                .subquery()
            )
            return query.filter(TT.id.in_(shared_task_ids))
        else:
            # Default: mine + public + shared
            from sqlalchemy import or_
            shared_task_ids = (
                self.db.query(TaskShareGrant.task_id)
                .filter(TaskShareGrant.grantee_user_id == user.id)
                .subquery()
            )
            return query.filter(
                or_(
                    TT.owner_user_id == user.id,
                    TT.visibility == "public",
                    TT.id.in_(shared_task_ids),
                )
            )
