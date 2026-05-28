from __future__ import annotations

from datetime import date

from backend.app.db.session import SessionLocal
from backend.app.services.arxiv_pipeline_service import ArxivPipelineService
from backend.app.workers.huey_app import huey


def _run_sync_job(*, source_run_date: date | None = None, force_refresh: bool = False) -> str:
    db = SessionLocal()
    try:
        pipeline = ArxivPipelineService(db)
        run = pipeline.create_run(
            current_user=None,
            trigger_source="scheduled",
            source_run_date=source_run_date or date.today(),
            force_refresh=force_refresh,
        )
        pipeline.execute_run(run.id)
        return run.id
    finally:
        db.close()


if huey is not None:

    @huey.task()
    def sync_daily_arxiv_digest(source_run_date: str | None = None, force_refresh: bool = False) -> str:
        run_date = date.fromisoformat(source_run_date) if source_run_date else None
        return _run_sync_job(source_run_date=run_date, force_refresh=force_refresh)

else:

    def sync_daily_arxiv_digest(source_run_date: str | None = None, force_refresh: bool = False) -> str:
        run_date = date.fromisoformat(source_run_date) if source_run_date else None
        return _run_sync_job(source_run_date=run_date, force_refresh=force_refresh)
