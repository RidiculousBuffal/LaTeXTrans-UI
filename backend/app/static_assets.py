from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST_DIR = REPO_ROOT / "frontend" / "dist"


def resolve_frontend_asset_path(*, dist_dir: Path, asset_path: str) -> Path | None:
    normalized_path = asset_path.lstrip("/")
    base_dir = dist_dir.resolve()

    if not normalized_path:
        index_path = dist_dir / "index.html"
        return index_path if index_path.is_file() else None

    candidate = (dist_dir / normalized_path).resolve()
    if candidate.is_file() and (candidate == base_dir or base_dir in candidate.parents):
        return candidate

    if candidate.is_dir():
        directory_index = (candidate / "index.html").resolve()
        if directory_index.is_file() and (directory_index == base_dir or base_dir in directory_index.parents):
            return directory_index

    return None


def create_frontend_response(*, request: Request, full_path: str, api_prefix: str) -> FileResponse:
    normalized_api_prefix = api_prefix.strip("/")
    if full_path == normalized_api_prefix or full_path.startswith(f"{normalized_api_prefix}/"):
        raise HTTPException(status_code=404, detail="Not Found")

    asset_path = resolve_frontend_asset_path(dist_dir=FRONTEND_DIST_DIR, asset_path=full_path)
    if asset_path is not None:
        return FileResponse(asset_path)

    if "text/html" in request.headers.get("accept", ""):
        index_path = resolve_frontend_asset_path(dist_dir=FRONTEND_DIST_DIR, asset_path="")
        if index_path is not None:
            return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Frontend asset not found.")
