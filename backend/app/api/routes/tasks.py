from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.task import (
    ArtifactListResponse,
    TaskCancelResponse,
    TaskCreateRequest,
    TaskDetailResponse,
    TaskListResponse,
    TaskLogsResponse,
    TaskRetryResponse,
)
from backend.app.services.task_service import TaskService


router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db=db)


@router.post("", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    service: TaskService = Depends(get_task_service),
) -> TaskDetailResponse:
    return service.create_task(payload)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    arxiv_id: str | None = None,
    created_by: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    service: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    return service.list_tasks(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        arxiv_id=arxiv_id,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskDetailResponse:
    return service.get_task_detail(task_id)


@router.post("/{task_id}/retry", response_model=TaskRetryResponse)
def retry_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskRetryResponse:
    return service.retry_task(task_id)


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
def cancel_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskCancelResponse:
    return service.cancel_task(task_id)


@router.get("/{task_id}/artifacts", response_model=ArtifactListResponse)
def list_artifacts(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> ArtifactListResponse:
    return service.list_artifacts(task_id)


@router.get("/{task_id}/logs", response_model=TaskLogsResponse)
def list_logs(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskLogsResponse:
    return service.list_logs(task_id)
