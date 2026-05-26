from backend.app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_object_prefix(self, task_id: str, artifact_type: str) -> str:
        return f"{task_id}/{artifact_type.lower()}"
