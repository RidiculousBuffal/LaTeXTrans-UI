from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.rate_limit import rate_limiter
from backend.app.db.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import AuthConfigResponse, LoginRequest, LoginResponse, MeResponse, RegisterRequest, UserInfo
from backend.app.services.auth_service import (
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from backend.app.services.quota_service import QuotaService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> UserInfo:
    settings = get_settings()
    if not settings.auth_register_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Self-service registration is disabled.")
    rate_limiter.enforce(
        request=request,
        scope="auth-register",
        limit=settings.rate_limit_register_limit,
        window_seconds=settings.rate_limit_register_window_seconds,
    )
    existing = db.query(User).filter_by(username=payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
        is_active=True,
    )
    db.add(user)
    db.flush()

    quota_service = QuotaService(db)
    quota_service.initialize_quota(user)
    db.commit()
    db.refresh(user)

    balance = settings.default_user_translation_quota
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role.value,
        quota_balance=balance,
        is_active=user.is_active,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    settings = get_settings()
    rate_limiter.enforce(
        request=request,
        scope="auth-login",
        limit=settings.rate_limit_login_limit,
        window_seconds=settings.rate_limit_login_window_seconds,
    )
    user = db.query(User).filter_by(username=payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(user)
    set_auth_cookie(response, token)
    quota_service = QuotaService(db)
    balance = quota_service.get_balance(user)

    return LoginResponse(
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserInfo(
            id=user.id,
            username=user.username,
            role=user.role.value,
            quota_balance=balance,
            is_active=user.is_active,
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookie(response)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    quota_service = QuotaService(db)
    balance = quota_service.get_balance(current_user)
    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.value,
        quota_balance=balance,
        is_active=current_user.is_active,
    )


@router.get("/config", response_model=AuthConfigResponse)
def auth_config() -> AuthConfigResponse:
    settings = get_settings()
    return AuthConfigResponse(registration_enabled=settings.auth_register_enabled)
