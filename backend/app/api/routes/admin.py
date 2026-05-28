from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.cache import TranslationCacheEntry
from backend.app.models.quota import UserQuotaAccount
from backend.app.models.user import User, UserRole
from backend.app.schemas.admin import (
    AdminDiscoveryRunListResponse,
    AdminDiscoverySyncRequest,
    AdminChangePasswordRequest,
    AdminCreateUserRequest,
    CacheEntryItem,
    CacheListResponse,
    QuotaAdjustRequest,
    QuotaAdjustResponse,
    UserAdminItem,
    UserListResponse,
)
from backend.app.schemas.discovery import DiscoveryRunResponse
from backend.app.services.auth_service import hash_password, require_admin
from backend.app.services.arxiv_pipeline_service import ArxivPipelineService
from backend.app.services.cache_service import CacheService
from backend.app.services.quota_service import QuotaService
from backend.app.workers.discovery_jobs import execute_discovery_run
from backend.app.workers.huey_app import is_async_huey_enabled

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserListResponse:
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for user in users:
        account = db.query(UserQuotaAccount).filter_by(user_id=user.id).first()
        items.append(
            UserAdminItem(
                id=user.id,
                username=user.username,
                role=user.role.value,
                is_active=user.is_active,
                quota_balance=account.balance if account else 0,
            )
        )
    return UserListResponse(items=items, total=total)


@router.post("/users", response_model=UserAdminItem, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserAdminItem:
    existing = db.query(User).filter_by(username=payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")

    new_user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole(payload.role),
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    quota_service = QuotaService(db)
    account = quota_service.initialize_quota(new_user, operator_user_id=admin.id)
    if payload.initial_quota > 0:
        account = quota_service.admin_adjust(
            user=new_user,
            delta=payload.initial_quota,
            reason="initial grant by admin",
            operator_user_id=admin.id,
        )
    db.commit()
    db.refresh(new_user)

    return UserAdminItem(
        id=new_user.id,
        username=new_user.username,
        role=new_user.role.value,
        is_active=new_user.is_active,
        quota_balance=account.balance,
    )


@router.patch("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    user_id: str,
    payload: AdminChangePasswordRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not payload.new_password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password cannot be empty.")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


@router.post("/users/{user_id}/quota-adjustments", response_model=QuotaAdjustResponse)
def adjust_quota(
    user_id: str,
    payload: QuotaAdjustRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> QuotaAdjustResponse:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    quota_service = QuotaService(db)
    account = quota_service.admin_adjust(
        user=user,
        delta=payload.delta,
        reason=payload.reason,
        operator_user_id=admin.id,
    )
    db.commit()
    return QuotaAdjustResponse(user_id=user.id, new_balance=account.balance, delta=payload.delta)


@router.get("/cache", response_model=CacheListResponse)
def list_cache(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> CacheListResponse:
    total = db.query(TranslationCacheEntry).count()
    entries = (
        db.query(TranslationCacheEntry)
        .order_by(TranslationCacheEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        CacheEntryItem(
            id=entry.id,
            cache_key=entry.cache_key,
            engine=entry.engine,
            status=entry.status.value,
            hit_count=entry.hit_count,
            canonical_task_id=entry.canonical_task_id,
            created_at=entry.created_at.isoformat(),
        )
        for entry in entries
    ]
    return CacheListResponse(items=items, total=total)


@router.post("/cache/{cache_entry_id}/invalidate", status_code=status.HTTP_204_NO_CONTENT)
def invalidate_cache(
    cache_entry_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    entry = db.get(TranslationCacheEntry, cache_entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cache entry not found.")
    cache_service = CacheService(db)
    cache_service.invalidate(entry)
    db.commit()


@router.post("/discovery/sync", response_model=DiscoveryRunResponse, status_code=status.HTTP_202_ACCEPTED)
def sync_discovery(
    payload: AdminDiscoverySyncRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> DiscoveryRunResponse:
    pipeline = ArxivPipelineService(db)
    run_date = date.fromisoformat(payload.source_run_date) if payload.source_run_date else date.today()
    run = pipeline.create_run(
        current_user=admin,
        trigger_source="admin_manual",
        source_run_date=run_date,
        force_refresh=payload.force_refresh,
    )
    if payload.run_inline:
        run = pipeline.execute_run(run.id)
    elif is_async_huey_enabled():
        execute_discovery_run(run.id)
    else:
        run = pipeline.execute_run(run.id)
    return DiscoveryRunResponse.model_validate(run)


@router.get("/discovery/runs", response_model=AdminDiscoveryRunListResponse)
def list_discovery_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminDiscoveryRunListResponse:
    repository = ArxivPipelineService(db).repository
    runs, total = repository.list_runs(page=page, page_size=page_size)
    return AdminDiscoveryRunListResponse(
        items=[DiscoveryRunResponse.model_validate(run) for run in runs],
        total=total,
        page=page,
        page_size=page_size,
    )
