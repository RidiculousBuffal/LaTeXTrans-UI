from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.cache import TranslationCacheEntry
from backend.app.models.quota import UserQuotaAccount
from backend.app.models.user import User, UserRole
from backend.app.schemas.admin import (
    AdminChangePasswordRequest,
    AdminCreateUserRequest,
    CacheEntryItem,
    CacheListResponse,
    QuotaAdjustRequest,
    QuotaAdjustResponse,
    UserAdminItem,
    UserListResponse,
)
from backend.app.services.auth_service import hash_password, require_admin
from backend.app.services.cache_service import CacheService
from backend.app.services.quota_service import QuotaService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserListResponse:
    total = db.query(User).count()
    users = db.query(User).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for u in users:
        account = db.query(UserQuotaAccount).filter_by(user_id=u.id).first()
        items.append(
            UserAdminItem(
                id=u.id,
                username=u.username,
                role=u.role.value,
                is_active=u.is_active,
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

    from backend.app.services.quota_service import QuotaService
    import uuid

    new_user = User(
        id=str(uuid.uuid4()),
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=UserRole(payload.role),
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    quota_service = QuotaService(db)
    account = quota_service.initialize_quota(new_user)
    if payload.initial_quota > 0:
        quota_service.admin_adjust(
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
        quota_balance=account.balance + payload.initial_quota,
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
        user=user, delta=payload.delta, reason=payload.reason, operator_user_id=admin.id
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
            id=e.id,
            cache_key=e.cache_key,
            engine=e.engine,
            status=e.status.value,
            hit_count=e.hit_count,
            canonical_task_id=e.canonical_task_id,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
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



@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserListResponse:
    total = db.query(User).count()
    users = db.query(User).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for u in users:
        account = db.query(UserQuotaAccount).filter_by(user_id=u.id).first()
        items.append(
            UserAdminItem(
                id=u.id,
                username=u.username,
                role=u.role.value,
                is_active=u.is_active,
                quota_balance=account.balance if account else 0,
            )
        )
    return UserListResponse(items=items, total=total)


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
        user=user, delta=payload.delta, reason=payload.reason, operator_user_id=admin.id
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
            id=e.id,
            cache_key=e.cache_key,
            engine=e.engine,
            status=e.status.value,
            hit_count=e.hit_count,
            canonical_task_id=e.canonical_task_id,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
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
