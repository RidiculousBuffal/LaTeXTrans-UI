from __future__ import annotations

import io
import mimetypes
import tarfile
from datetime import timedelta
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from backend.app.core.config import get_settings
from backend.app.models.task import TaskArtifact, TaskArtifactType, TranslationTask


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = Minio(
            self._normalize_endpoint(self.settings.minio_url),
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self._resolve_secure(),
        )

    def build_object_prefix(self, task_id: str, artifact_type: str) -> str:
        return f"{task_id}/{artifact_type.lower()}"

    def build_object_key(self, task_id: str, artifact_type: str, file_name: str) -> str:
        return f"{self.build_object_prefix(task_id, artifact_type)}/{file_name}"

    def build_artifact(
        self,
        *,
        task: TranslationTask,
        artifact_type: TaskArtifactType,
        file_path: str | Path,
        metadata: dict | None = None,
    ) -> TaskArtifact:
        path = Path(file_path)
        content_type, _ = mimetypes.guess_type(path.name)
        file_size = path.stat().st_size if path.exists() and path.is_file() else None
        return TaskArtifact(
            task=task,
            artifact_type=artifact_type,
            object_key=self.build_object_key(task.id, artifact_type.value.lower(), path.name),
            file_name=path.name,
            content_type=content_type,
            file_size=file_size,
            metadata_json={"local_path": str(path), **(metadata or {})},
        )

    def ensure_bucket(self) -> None:
        bucket = self.settings.minio_bucket_tasks
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def upload_path(
        self,
        *,
        task: TranslationTask,
        artifact_type: TaskArtifactType,
        file_path: str | Path,
        metadata: dict | None = None,
    ) -> TaskArtifact:
        path = Path(file_path)
        self.ensure_bucket()

        upload_path = path
        content_type, _ = mimetypes.guess_type(path.name)
        extra_metadata = dict(metadata or {})

        if path.is_dir():
            upload_path = self._archive_directory(path)
            content_type = "application/gzip"
            extra_metadata["source_directory"] = str(path)

        object_key = self.build_object_key(task.id, artifact_type.value.lower(), upload_path.name)
        self.client.fput_object(
            self.settings.minio_bucket_tasks,
            object_key,
            str(upload_path),
            content_type=content_type,
        )

        artifact = self.build_artifact(
            task=task,
            artifact_type=artifact_type,
            file_path=upload_path,
            metadata={
                "bucket": self.settings.minio_bucket_tasks,
                "uploaded_from": str(path),
                **extra_metadata,
            },
        )
        artifact.object_key = object_key
        artifact.content_type = content_type
        artifact.metadata_json = {
            "bucket": self.settings.minio_bucket_tasks,
            "uploaded_from": str(path),
            **extra_metadata,
        }
        return artifact

    def get_download_url(self, object_key: str, expires: timedelta | None = None) -> str | None:
        try:
            return self.client.presigned_get_object(
                self.settings.minio_bucket_tasks,
                object_key,
                expires=expires or timedelta(hours=1),
            )
        except S3Error:
            return None

    def _archive_directory(self, directory: Path) -> Path:
        archive_path = directory.with_suffix(".tar.gz")
        if archive_path.exists():
            archive_path.unlink()

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(directory, arcname=directory.name)
        return archive_path

    def _normalize_endpoint(self, url: str) -> str:
        return url.removeprefix("https://").removeprefix("http://").rstrip("/")

    def _resolve_secure(self) -> bool:
        if self.settings.minio_url.startswith("https://"):
            return True
        return self.settings.minio_secure
