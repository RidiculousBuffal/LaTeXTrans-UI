from backend.app.models.task import TaskStatus


PHASE_PROGRESS = {
    TaskStatus.PENDING.value: 0,
    TaskStatus.DOWNLOADING.value: 10,
    TaskStatus.PARSING.value: 25,
    TaskStatus.TRANSLATING.value: 60,
    TaskStatus.VALIDATING.value: 80,
    TaskStatus.GENERATING.value: 95,
    TaskStatus.SUCCEEDED.value: 100,
}
