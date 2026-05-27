from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.sharing import TaskShareGrant
from backend.app.models.task import TranslationTask
from backend.app.models.user import User
from backend.app.schemas.admin import SharingState, SharingUpdateRequest
from backend.app.services.access_service import AccessService
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/tasks", tags=["sharing"])


@router.get("/{task_id}/sharing", response_model=SharingState)
def get_sharing(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SharingState:
    task = _require_task(db, task_id)
    access = AccessService(db)
    if not access.can_view_task(task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    grants = db.query(TaskShareGrant).filter_by(task_id=task_id).all()
    shared_users = []
    for g in grants:
        u = db.get(User, g.grantee_user_id)
        if u:
            shared_users.append({"user_id": u.id, "username": u.username})

    return SharingState(task_id=task_id, visibility=task.visibility, shared_users=shared_users)


@router.put("/{task_id}/sharing", response_model=SharingState)
def update_sharing(
    task_id: str,
    payload: SharingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SharingState:
    task = _require_task(db, task_id)
    access = AccessService(db)
    if not access.can_manage_task(task, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only task owner or admin can modify sharing.")

    if payload.visibility is not None:
        if payload.visibility not in {"private", "public"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="visibility must be 'private' or 'public'.")
        task.visibility = payload.visibility

    # Replace direct share list: resolve usernames → user IDs
    db.query(TaskShareGrant).filter_by(task_id=task_id).delete()
    for username in payload.grant_usernames:
        target = db.query(User).filter_by(username=username).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found.",
            )
        grant = TaskShareGrant(
            task_id=task_id,
            grantee_user_id=target.id,
            granted_by_user_id=current_user.id,
        )
        db.add(grant)

    db.commit()
    db.refresh(task)
    return get_sharing(task_id=task_id, db=db, current_user=current_user)


def _require_task(db: Session, task_id: str) -> TranslationTask:
    task = db.get(TranslationTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task
