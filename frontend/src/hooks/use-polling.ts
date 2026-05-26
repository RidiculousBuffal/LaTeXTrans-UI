import { terminalStatuses, type TaskStatus } from "@/lib/types"

export function getTaskPollingInterval(status?: TaskStatus | null) {
  if (!status || terminalStatuses.includes(status)) {
    return false
  }

  return 5_000
}

export function getTaskDetailPollingInterval(status?: TaskStatus | null) {
  if (!status || terminalStatuses.includes(status)) {
    return false
  }

  return 3_000
}
