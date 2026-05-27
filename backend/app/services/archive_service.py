from collections import defaultdict

from backend.app.models.task import TaskArtifactType, TranslationTask
from backend.app.schemas.task import ArchiveGroupItem, ArchiveListItem, TaskSummaryResponse


class ArchiveService:
    _VISIBLE_ARTIFACT_TYPES = frozenset(
        {
            TaskArtifactType.EXTRACTED_SOURCE,
            TaskArtifactType.TRANSLATED_PROJECT,
            TaskArtifactType.FINAL_PDF,
        }
    )

    def build_archive_item(self, task: TranslationTask) -> ArchiveListItem:
        return ArchiveListItem(
            task=TaskSummaryResponse.model_validate(task),
            artifact_count=sum(1 for artifact in task.artifacts if artifact.artifact_type in self._VISIBLE_ARTIFACT_TYPES),
        )

    def build_archive_groups(self, tasks: list[TranslationTask]) -> list[ArchiveGroupItem]:
        grouped_tasks: dict[str, list[TranslationTask]] = defaultdict(list)

        for task in tasks:
            grouped_tasks[self._build_group_key(task)].append(task)

        items: list[ArchiveGroupItem] = []
        for group_key, group_tasks in grouped_tasks.items():
            sorted_tasks = sorted(group_tasks, key=lambda item: item.created_at, reverse=True)
            latest_task = sorted_tasks[0]
            archive_items = [self.build_archive_item(task) for task in sorted_tasks]
            items.append(
                ArchiveGroupItem(
                    group_key=group_key,
                    arxiv_id=latest_task.arxiv_id,
                    task_count=len(sorted_tasks),
                    artifact_count=sum(item.artifact_count for item in archive_items),
                    latest_created_at=latest_task.created_at,
                    latest_task=TaskSummaryResponse.model_validate(latest_task),
                    tasks=archive_items,
                )
            )

        items.sort(key=lambda item: item.latest_created_at, reverse=True)
        return items

    def _build_group_key(self, task: TranslationTask) -> str:
        if task.arxiv_id:
            return f"arxiv:{task.arxiv_id}"
        return f"task:{task.id}"
