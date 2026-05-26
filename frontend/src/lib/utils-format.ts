import dayjs from "dayjs"
import relativeTime from "dayjs/plugin/relativeTime"

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
