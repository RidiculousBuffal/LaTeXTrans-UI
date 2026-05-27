from __future__ import annotations

from pathlib import Path

from backend.app.core.config import Settings


def build_babeldoc_command(
    *,
    settings: Settings,
    input_pdf: str | Path,
    output_dir: str | Path,
    working_dir: str | Path,
    target_language: str,
    model_name: str,
    qps: int | None = None,
    pool_max_workers: int | None = None,
) -> list[str]:
    command = [
        settings.babeldoc_bin,
        "--openai",
        "--files",
        str(input_pdf),
        "--output",
        str(output_dir),
        "--working-dir",
        str(working_dir),
        "--lang-in",
        "en",
        "--lang-out",
        target_language,
        "--qps",
        str(qps or settings.babeldoc_qps),
        "--pool-max-workers",
        str(pool_max_workers or settings.babeldoc_pool_max_workers),
        "--openai-model",
        model_name,
    ]

    if settings.openai_base_url:
        command.extend(["--openai-base-url", settings.openai_base_url])
    if settings.openai_api_key:
        command.extend(["--openai-api-key", settings.openai_api_key])

    return command
