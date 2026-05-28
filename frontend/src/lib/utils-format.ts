import dayjs from "dayjs"
import relativeTime from "dayjs/plugin/relativeTime"

import type {
  CollectionTranslationMode,
  DiscoveryRunStatus,
  TranslateDecision,
} from "@/lib/types"

dayjs.extend(relativeTime)

export function formatDateTime(value: string | null) {
  if (!value) {
    return "—"
  }

  return dayjs(value).format("YYYY-MM-DD HH:mm:ss")
}

export function formatRelativeTime(value: string | null) {
  if (!value) {
    return "—"
  }

  return dayjs(value).fromNow()
}

export function formatPercent(value: number) {
  return `${Math.max(0, Math.min(100, Math.round(value)))}%`
}

export function formatFileSize(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  const units = ["KB", "MB", "GB", "TB"]
  let size = bytes / 1024
  let unitIndex = 0

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }

  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`
}

export function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message
  }

  return "Unexpected error"
}

export function toTitleCase(value: string) {
  return value.toLowerCase().replaceAll("_", " ")
}

export function formatBooleanFilter(value: boolean | "") {
  if (value === "") {
    return "all"
  }

  return value ? "yes" : "no"
}

export function formatCollectionTranslationMode(mode: CollectionTranslationMode) {
  return mode === "auto" ? "Auto translate" : "Manual translate"
}

export function formatTranslateDecision(decision: TranslateDecision) {
  switch (decision) {
    case "manual_requested":
      return "Manual requested"
    case "auto_queued":
      return "Auto queued"
    case "translated":
      return "Translated"
    case "pending":
    default:
      return "Pending"
  }
}

export function formatDiscoveryRunStatus(status: DiscoveryRunStatus) {
  switch (status) {
    case "RUNNING":
      return "Running"
    case "SUCCEEDED":
      return "Succeeded"
    case "FAILED":
      return "Failed"
    case "PENDING":
    default:
      return "Pending"
  }
}
