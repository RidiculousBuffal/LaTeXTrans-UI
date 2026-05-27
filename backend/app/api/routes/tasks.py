from datetime import datetime
import json

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.rate_limit import rate_limiter
from backend.app.db.session import get_db
from backend.app.models.user import User
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
from backend.app.services.auth_service import get_current_user, get_optional_user
from backend.app.services.task_service import TaskService


router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(db=db)


@router.post("", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    request: Request,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskDetailResponse:
    settings = get_settings()
    rate_limiter.enforce(
        request=request,
        scope="task-create",
        limit=settings.rate_limit_task_create_limit,
        window_seconds=settings.rate_limit_task_create_window_seconds,
    )
    return service.create_task(payload, owner=current_user)


@router.post("/upload", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
def create_upload_task(
    request: Request,
    file: UploadFile = File(...),
    task_name: str | None = Form(default=None),
    source_language: str = Form(default="en"),
    target_language: str = Form(default="ch"),
    model_name: str | None = Form(default=None),
    env_profile: str = Form(default="default"),
    output_name: str | None = Form(default=None),
    options: str = Form(default="{}"),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskDetailResponse:
    settings = get_settings()
    rate_limiter.enforce(
        request=request,
        scope="task-create",
        limit=settings.rate_limit_task_create_limit,
        window_seconds=settings.rate_limit_task_create_window_seconds,
    )
    parsed_options = json.loads(options)
    return service.create_upload_task(
        file=file,
        task_name=task_name,
        source_language=source_language,
        target_language=target_language,
        model_name=model_name,
        env_profile=env_profile,
        output_name=output_name,
        options=parsed_options,
        owner=current_user,
    )


@router.post("/pdf", response_model=TaskDetailResponse, status_code=status.HTTP_201_CREATED)
def create_pdf_task(
    request: Request,
    file: UploadFile = File(...),
    task_name: str | None = Form(default=None),
    target_language: str = Form(default="zh"),
    model_name: str | None = Form(default=None),
    env_profile: str = Form(default="default"),
    options: str = Form(default="{}"),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskDetailResponse:
    settings = get_settings()
    rate_limiter.enforce(
        request=request,
        scope="task-create",
        limit=settings.rate_limit_task_create_limit,
        window_seconds=settings.rate_limit_task_create_window_seconds,
    )
    parsed_options = json.loads(options)
    return service.create_pdf_task(
        file=file,
        task_name=task_name,
        target_language=target_language,
        model_name=model_name,
        env_profile=env_profile,
        options=parsed_options,
        owner=current_user,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    task_name: str | None = None,
    arxiv_id: str | None = None,
    scope: str = Query(default="mine"),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskListResponse:
    return service.list_tasks(
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        task_name=task_name,
        arxiv_id=arxiv_id,
        scope=scope,
        created_from=created_from,
        created_to=created_to,
        current_user=current_user,
    )


@router.get("/failures/summary", response_model=FailureSummaryResponse)
def get_failure_summary(
    limit: int = Query(default=20, ge=1, le=100),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> FailureSummaryResponse:
    return service.get_failure_summary(limit=limit, current_user=current_user)


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskDetailResponse:
    return service.get_task_detail(task_id, current_user=current_user)


@router.post("/{task_id}/retry", response_model=TaskRetryResponse)
def retry_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskRetryResponse:
    return service.retry_task(task_id, current_user=current_user)


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
def cancel_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskCancelResponse:
    return service.cancel_task(task_id, current_user=current_user)


@router.get("/{task_id}/artifacts", response_model=ArtifactListResponse)
def list_artifacts(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> ArtifactListResponse:
    return service.list_artifacts(task_id, current_user=current_user)


@router.get("/{task_id}/logs", response_model=TaskLogsResponse)
def list_logs(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskLogsResponse:
    return service.list_logs(task_id, current_user=current_user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> None:
    service.delete_task(task_id, current_user=current_user)
