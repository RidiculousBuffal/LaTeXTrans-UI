from __future__ import annotations

from pathlib import Path

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
            "mode": payload.options.get("mode", 0),
            "update_term": payload.options.get("update_term", "False"),
            "user_term": payload.options.get("user_term", ""),
            "category": {},
            "llm_config": {
                "model": task.model_name,
                "base_url": self.settings.openai_base_url,
                "api_key": self.settings.openai_api_key,
            },
            "tex_sources_dir": str(Path(task.workspace_dir) / "sources"),
            "output_dir": task.output_dir,
            "runtime": {
                "task_id": task.id,
                "output_name": payload.output_name,
                "options": payload.options,
            },
        }

    def ensure_runtime_dirs(self, *, task: TranslationTask) -> dict[str, str]:
        workspace_dir = Path(task.workspace_dir)
        sources_dir = workspace_dir / "sources"
        output_dir = Path(task.output_dir)
        runtime_dir = workspace_dir / "runtime"

        for directory in (workspace_dir, sources_dir, output_dir, runtime_dir):
            directory.mkdir(parents=True, exist_ok=True)

        return {
            "workspace_dir": str(workspace_dir),
            "sources_dir": str(sources_dir),
            "output_dir": str(output_dir),
            "runtime_dir": str(runtime_dir),
        }
