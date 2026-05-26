from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.task import ArchiveListResponse
from backend.app.services.task_service import TaskService


router = APIRouter(prefix="/archives", tags=["archives"])


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db=db)


@router.get("", response_model=ArchiveListResponse)
def list_archives(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    arxiv_id: str | None = None,
    created_by: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    service: TaskService = Depends(get_task_service),
) -> ArchiveListResponse:
    return service.list_archives(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        arxiv_id=arxiv_id,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
    )
