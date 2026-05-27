from fastapi import FastAPI, Request
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
