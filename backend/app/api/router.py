from fastapi import APIRouter

from backend.app.api.routes.archives import router as archives_router
from backend.app.api.routes.tasks import router as tasks_router


api_router = APIRouter()
api_router.include_router(tasks_router)
api_router.include_router(archives_router)
