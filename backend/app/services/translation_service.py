from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.models.task import TranslationTask
from backend.app.schemas.task import TaskCreateRequest


class TranslationService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_config_snapshot(
        self,
        *,
        task: TranslationTask,
        payload: TaskCreateRequest,
    ) -> dict:
        paper_list = [payload.arxiv_id] if payload.arxiv_id else []
        return {
            "paper_list": paper_list,
            "source_type": payload.source_type.value,
            "source_archive_name": payload.source_archive_name,
            "source_language": payload.source_language,
            "target_language": payload.target_language,
            "llm_config": {
                "model": task.model_name,
                "base_url": self.settings.openai_base_url,
            },
            "tex_sources_dir": task.workspace_dir,
            "output_dir": task.output_dir,
            "runtime": {
                "task_id": task.id,
                "output_name": payload.output_name,
                "options": payload.options,
            },
        }
