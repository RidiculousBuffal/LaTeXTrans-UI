from backend.app.models.task import TranslationTask
from backend.app.schemas.task import ArchiveListItem, TaskSummaryResponse


class ArchiveService:
    def build_archive_item(self, task: TranslationTask) -> ArchiveListItem:
        return ArchiveListItem(
            task=TaskSummaryResponse.model_validate(task),
            artifact_count=len(task.artifacts),
        )
