from __future__ import annotations

import os
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from backend.src.formats.latex.utils import (
    batch_download_arxiv_tex,
    get_arxiv_category,
    get_profect_dirs,
)


class PipelineService:
    def prepare_sources(self, *, config: dict[str, Any], workspace_dir: str) -> tuple[list[str], list[str]]:
        projects_dir = Path(config["tex_sources_dir"])
        projects_dir.mkdir(parents=True, exist_ok=True)

        paper_list = config.get("paper_list", [])
        if paper_list:
            batch_download_arxiv_tex(paper_list, str(projects_dir))
            if not config.get("user_term"):
                config["category"] = get_arxiv_category(paper_list)
        archives = self.collect_archives(projects_dir)
        self.extract_archives(archives)

        projects = get_profect_dirs(str(projects_dir))
        if not projects:
            raise ValueError(f"No LaTeX projects found under workspace: {workspace_dir}")
        return projects, [str(path) for path in archives]

    def run_translation_pipeline(
        self,
        *,
        config: dict[str, Any],
        project_dir: str,
        output_dir: str,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        from backend.src.agents.coordinator_agent import CoordinatorAgent

        coordinator = CoordinatorAgent(
            config=config,
            project_dir=project_dir,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )
        coordinator.workflow_latextrans()

    def find_generated_pdf(self, *, translated_project_dir: str, target_language: str) -> str | None:
        project_name = os.path.basename(translated_project_dir)
        candidate = Path(translated_project_dir) / f"{target_language}_{project_name}.pdf"
        if candidate.exists():
            return str(candidate)

        pdfs = sorted(Path(translated_project_dir).glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])
        return None

    def collect_archives(self, sources_dir: Path) -> list[Path]:
        archives: list[Path] = []
        for path in sorted(sources_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name.endswith(".tar.gz") or path.name.endswith(".tgz"):
                archives.append(path)
            elif path.suffix in {".zip", ".tar"}:
                archives.append(path)
        return archives

    def extract_archives(self, archives: list[Path]) -> None:
        for archive_path in archives:
            target_dir = self._target_dir_for_archive(archive_path)
            target_dir.mkdir(parents=True, exist_ok=True)
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    self._safe_extract_zip(zip_ref, target_dir)
                continue
            if tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, "r:*") as tar_ref:
                    self._safe_extract_tar(tar_ref, target_dir)

    def _target_dir_for_archive(self, archive_path: Path) -> Path:
        name = archive_path.name
        for suffix in (".tar.gz", ".tgz", ".zip", ".tar"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        return archive_path.parent / name

    def _safe_extract_zip(self, zip_ref: zipfile.ZipFile, target_dir: Path) -> None:
        for member in zip_ref.infolist():
            destination = target_dir / member.filename
            self._assert_safe_path(destination, target_dir)
        zip_ref.extractall(target_dir)

    def _safe_extract_tar(self, tar_ref: tarfile.TarFile, target_dir: Path) -> None:
        for member in tar_ref.getmembers():
            destination = target_dir / member.name
            self._assert_safe_path(destination, target_dir)
        tar_ref.extractall(target_dir)

    def _assert_safe_path(self, destination: Path, base_dir: Path) -> None:
        resolved_base = base_dir.resolve()
        resolved_destination = destination.resolve()
        if resolved_destination != resolved_base and resolved_base not in resolved_destination.parents:
            raise ValueError(f"Unsafe archive entry detected: {destination}")
