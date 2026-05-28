from fastapi import APIRouter

from backend.app.api.routes.admin import router as admin_router
from backend.app.api.routes.archives import router as archives_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.discovery import router as discovery_router
from backend.app.api.routes.sharing import router as sharing_router
from backend.app.api.routes.tasks import router as tasks_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(tasks_router)
api_router.include_router(discovery_router)
api_router.include_router(sharing_router)
api_router.include_router(archives_router)
api_router.include_router(admin_router)
