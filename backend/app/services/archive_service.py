from collections import defaultdict
from collections.abc import Callable

from backend.app.models.task import TaskArtifactType, TranslationTask
from backend.app.schemas.task import ArchiveGroupItem, ArchiveListItem, TaskSummaryResponse


class ArchiveService:
    _VISIBLE_ARTIFACT_TYPES = frozenset(
        {
            TaskArtifactType.SOURCE_PDF,
            TaskArtifactType.EXTRACTED_SOURCE,
            TaskArtifactType.TRANSLATED_PROJECT,
            TaskArtifactType.FINAL_PDF,
            TaskArtifactType.TRANSLATED_PDF,
            TaskArtifactType.BABELDOC_OUTPUT,
        }
    )

    def build_archive_item(
        self,
        task: TranslationTask,
        *,
        summary_builder: Callable[[TranslationTask], TaskSummaryResponse] | None = None,
    ) -> ArchiveListItem:
        return ArchiveListItem(
            task=summary_builder(task) if summary_builder else TaskSummaryResponse.model_validate(task),
            artifact_count=sum(1 for artifact in task.artifacts if artifact.artifact_type in self._VISIBLE_ARTIFACT_TYPES),
        )

    def build_archive_groups(
        self,
        tasks: list[TranslationTask],
        *,
        summary_builder: Callable[[TranslationTask], TaskSummaryResponse] | None = None,
    ) -> list[ArchiveGroupItem]:
        grouped_tasks: dict[str, list[TranslationTask]] = defaultdict(list)

        for task in tasks:
            grouped_tasks[self._build_group_key(task)].append(task)

        items: list[ArchiveGroupItem] = []
        for group_key, group_tasks in grouped_tasks.items():
            sorted_tasks = sorted(group_tasks, key=lambda item: item.created_at, reverse=True)
            latest_task = sorted_tasks[0]
            archive_items = [self.build_archive_item(task, summary_builder=summary_builder) for task in sorted_tasks]
            items.append(
                ArchiveGroupItem(
                    group_key=group_key,
                    arxiv_id=latest_task.arxiv_id,
                    task_count=len(sorted_tasks),
                    artifact_count=sum(item.artifact_count for item in archive_items),
                    latest_created_at=latest_task.created_at,
                    latest_task=summary_builder(latest_task) if summary_builder else TaskSummaryResponse.model_validate(latest_task),
                    tasks=archive_items,
                )
            )

        items.sort(key=lambda item: item.latest_created_at, reverse=True)
        return items

    def _build_group_key(self, task: TranslationTask) -> str:
        if task.arxiv_id:
            return f"arxiv:{task.arxiv_id}"
        return f"task:{task.id}"
