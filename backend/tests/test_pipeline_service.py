import io
import tarfile
import tempfile
import zipfile
from pathlib import Path

import pytest

from backend.app.services.pipeline_service import PipelineService


def test_safe_extract_zip_blocks_path_traversal() -> None:
    service = PipelineService()
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / "bad.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("../evil.txt", "boom")

        with zipfile.ZipFile(archive_path, "r") as zf:
            with pytest.raises(ValueError):
                service._safe_extract_zip(zf, Path(tmpdir) / "out")


def test_safe_extract_tar_blocks_path_traversal() -> None:
    service = PipelineService()
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / "bad.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tf:
            info = tarfile.TarInfo("../evil.txt")
            payload = b"boom"
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))

        with tarfile.open(archive_path, "r:gz") as tf:
            with pytest.raises(ValueError):
                service._safe_extract_tar(tf, Path(tmpdir) / "out")
