from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.services.babeldoc_command_builder import build_babeldoc_command


class BabelDocService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def validate_executable(self) -> str:
        configured = self.settings.babeldoc_bin
        path = Path(configured)
        if path.is_absolute():
            if path.exists() and os.access(path, os.X_OK):
                return str(path)
            raise RuntimeError(
                f"BabelDOC executable not found: {configured}. "
                "Please install BabelDOC or set BABELDOC_BIN correctly in .env before starting the backend."
            )

        resolved = shutil.which(configured)
        if resolved:
            return resolved
        raise RuntimeError(
            f"BabelDOC executable not found: {configured}. "
            "Please install BabelDOC or set BABELDOC_BIN correctly in .env before starting the backend."
        )

    def validate_pdf_file(self, file_name: str | None) -> None:
        if not file_name:
            raise ValueError("PDF file is required.")
        if not file_name.lower().endswith(".pdf"):
            raise ValueError("Only .pdf files are supported.")

    def build_runtime_env(self, *, workspace_dir: str | Path) -> dict[str, str]:
        workspace = Path(workspace_dir)
        home_dir = workspace / "runtime" / "babeldoc-home"
        home_dir.mkdir(parents=True, exist_ok=True)
        cache_dir = home_dir / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["HOME"] = str(home_dir)
        env["XDG_CACHE_HOME"] = str(cache_dir)
        return env

    def build_command(
        self,
        *,
        input_pdf: str | Path,
        output_dir: str | Path,
        working_dir: str | Path,
        target_language: str,
        model_name: str,
        options: dict[str, object] | None = None,
    ) -> list[str]:
        options = options or {}
        qps = self._optional_int(options.get("qps"))
        pool_max_workers = self._optional_int(options.get("pool_max_workers"))
        return build_babeldoc_command(
            settings=self.settings,
            input_pdf=input_pdf,
            output_dir=output_dir,
            working_dir=working_dir,
            target_language=target_language,
            model_name=model_name,
            qps=qps,
            pool_max_workers=pool_max_workers,
        )

    def run_command(
        self,
        *,
        command: list[str],
        env: dict[str, str],
        log_path: str | Path,
    ) -> subprocess.CompletedProcess[str]:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            return subprocess.run(
                command,
                check=False,
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )

    def find_translated_pdf(self, *, output_dir: str | Path, original_name: str | None = None) -> str | None:
        output_path = Path(output_dir)
        pdfs = sorted(output_path.rglob("*.pdf"))
        if not pdfs:
            return None

        stem = Path(original_name).stem if original_name else None
        if stem:
            exact = [pdf for pdf in pdfs if pdf.stem == stem]
            if exact:
                return str(exact[0])

            prefixed = [pdf for pdf in pdfs if stem in pdf.stem]
            if prefixed:
                return str(prefixed[0])

        ranked = sorted(
            pdfs,
            key=lambda pdf: (
                "mono" not in pdf.name.lower(),
                "translated" not in pdf.name.lower(),
                "dual" in pdf.name.lower(),
                len(pdf.name),
            ),
        )
        return str(ranked[0])

    def _optional_int(self, value: object) -> int | None:
        if value is None or value == "":
            return None
        return int(value)
