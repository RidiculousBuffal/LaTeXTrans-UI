from __future__ import annotations

from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.models.task import TaskEngine, TranslationTask
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
        if payload.engine == TaskEngine.BABELDOC:
            return {
                "engine": payload.engine.value,
                "source_type": payload.source_type.value,
                "source_archive_name": payload.source_archive_name,
                "source_language": payload.source_language,
                "target_language": payload.target_language,
                "runtime": {
                    "task_id": task.id,
                    "output_name": payload.output_name,
                    "options": payload.options,
                    "task_timeout_seconds": self.settings.task_timeout_seconds,
                },
                "babeldoc": {
                    "binary": self.settings.babeldoc_bin,
                    "qps": int(payload.options.get("qps", self.settings.babeldoc_qps)),
                    "pool_max_workers": int(
                        payload.options.get("pool_max_workers", self.settings.babeldoc_pool_max_workers)
                    ),
                    "openai_model": task.model_name,
                    "openai_base_url": bool(self.settings.openai_base_url),
                    "openai_api_key_configured": bool(self.settings.openai_api_key),
                },
                "tex_sources_dir": str(Path(task.workspace_dir) / "sources"),
                "output_dir": task.output_dir,
            }
        return {
            "engine": payload.engine.value,
            "paper_list": paper_list,
            "source_type": payload.source_type.value,
            "source_archive_name": payload.source_archive_name,
            "source_language": payload.source_language,
            "target_language": payload.target_language,
            "mode": self.normalize_mode(payload.options.get("mode", 0)),
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
                "task_timeout_seconds": self.settings.task_timeout_seconds,
            },
        }

    def normalize_mode(self, value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            return int(value)
        return 0

    def ensure_runtime_dirs(self, *, task: TranslationTask) -> dict[str, str]:
        workspace_dir = Path(task.workspace_dir)
        sources_dir = workspace_dir / "sources"
        output_dir = Path(task.output_dir)
        runtime_dir = workspace_dir / "runtime"
        babeldoc_output_dir = output_dir / self.settings.babeldoc_output_subdir

        for directory in (workspace_dir, sources_dir, output_dir, runtime_dir, babeldoc_output_dir):
            directory.mkdir(parents=True, exist_ok=True)

        return {
            "workspace_dir": str(workspace_dir),
            "sources_dir": str(sources_dir),
            "output_dir": str(output_dir),
            "runtime_dir": str(runtime_dir),
            "babeldoc_output_dir": str(babeldoc_output_dir),
        }
