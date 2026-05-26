import { terminalStatuses, type TaskStatus, type TaskSummary } from "@/lib/types"

export function getTaskPollingInterval(status?: TaskStatus | null) {
  if (!status || terminalStatuses.includes(status)) {
    return false
  }

  return 5_000
}

export function getTaskListPollingInterval(tasks: TaskSummary[] | undefined) {
  if (!tasks?.length) {
    return false
  }

  return tasks.some((task) => !terminalStatuses.includes(task.status)) ? 5_000 : false
}

export function getTaskDetailPollingInterval(status?: TaskStatus | null) {
  if (!status || terminalStatuses.includes(status)) {
    return false
  }

  return 3_000
}
