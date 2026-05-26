from datetime import datetime
import json

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.task import (
    ArtifactListResponse,
    FailureSummaryResponse,
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


@router.post("/upload", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
def create_upload_task(
    file: UploadFile = File(...),
    task_name: str | None = Form(default=None),
    source_language: str = Form(default="en"),
    target_language: str = Form(default="ch"),
    model_name: str | None = Form(default=None),
    created_by: str | None = Form(default=None),
    env_profile: str = Form(default="default"),
    output_name: str | None = Form(default=None),
    options: str = Form(default="{}"),
    service: TaskService = Depends(get_task_service),
) -> TaskDetailResponse:
    parsed_options = json.loads(options)
    return service.create_upload_task(
        file=file,
        task_name=task_name,
        source_language=source_language,
        target_language=target_language,
        model_name=model_name,
        created_by=created_by,
        env_profile=env_profile,
        output_name=output_name,
        options=parsed_options,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    task_name: str | None = None,
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
        task_name=task_name,
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


@router.get("/failures/summary", response_model=FailureSummaryResponse)
def get_failure_summary(
    limit: int = Query(default=20, ge=1, le=100),
    service: TaskService = Depends(get_task_service),
) -> FailureSummaryResponse:
    return service.get_failure_summary(limit=limit)
