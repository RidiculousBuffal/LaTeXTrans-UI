from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.services.babeldoc_service import BabelDocService
from backend.app.static_assets import FRONTEND_DIST_DIR, create_frontend_response


settings = get_settings()
configure_logging()
BabelDocService().validate_executable()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' https: http:; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
    )
    return response


@app.on_event("startup")
def bootstrap_admin() -> None:
    """Create admin user on startup if explicitly enabled."""
    if not settings.admin_bootstrap_enabled:
        return
    from backend.app.db.session import SessionLocal
    from backend.app.models.user import User, UserRole
    from backend.app.services.auth_service import hash_password
    from backend.app.services.quota_service import QuotaService

    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(username=settings.admin_bootstrap_username).first()
        if not existing:
            admin = User(
                username=settings.admin_bootstrap_username,
                password_hash=hash_password(settings.admin_bootstrap_password),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.flush()
            QuotaService(db).initialize_quota(admin)
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


if FRONTEND_DIST_DIR.is_dir():

    @app.get("/", include_in_schema=False)
    async def frontend_index(request: Request):
        return create_frontend_response(request=request, full_path="", api_prefix=settings.api_prefix)


    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_assets(request: Request, full_path: str):
        return create_frontend_response(request=request, full_path=full_path, api_prefix=settings.api_prefix)
