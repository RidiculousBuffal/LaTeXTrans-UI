from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.workers.discovery_jobs import sync_daily_arxiv_digest
from backend.app.workers.huey_app import huey


settings = get_settings()

if huey is not None and hasattr(huey, "periodic_task"):
    from huey import crontab

    @huey.periodic_task(
        crontab(
            minute=str(settings.discovery_schedule_minute),
            hour=str(settings.discovery_schedule_hour),
        )
    )
    def scheduled_sync_daily_arxiv_digest():
        return sync_daily_arxiv_digest()
