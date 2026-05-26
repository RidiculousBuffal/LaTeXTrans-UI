import axios from "axios"

import type {
  ArtifactListResponse,
  CreateArxivTaskPayload,
  CreateUploadTaskPayload,
  FailureSummary,
  PaginatedArchives,
  PaginatedTasks,
  TaskDetail,
  TaskListFilters,
} from "@/lib/types"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api",
  timeout: 20_000,
})

function buildSearchParams(filters: TaskListFilters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== "")
  )
}

function getApiErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") {
      return detail
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg)
        .filter((msg): msg is string => typeof msg === "string")
        .join("; ")
    }

    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return "Unexpected API error"
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "ApiError"
  }
}

async function withApiError<T>(promise: Promise<{ data: T }>) {
  try {
    const response = await promise
    return response.data
  } catch (error) {
    throw new ApiError(getApiErrorMessage(error))
  }
}

export function listTasks(filters: TaskListFilters) {
  return withApiError(
    api.get<PaginatedTasks>("/tasks", {
      params: buildSearchParams(filters),
    })
  )
}

export function getTask(taskId: string) {
  return withApiError(api.get<TaskDetail>(`/tasks/${taskId}`))
}

export function createArxivTask(payload: CreateArxivTaskPayload) {
  return withApiError(api.post<TaskDetail>("/tasks", payload))
}

export function createUploadTask(payload: CreateUploadTaskPayload) {
  const formData = new FormData()
  formData.append("file", payload.file)

  if (payload.task_name) {
    formData.append("task_name", payload.task_name)
  }

  formData.append("source_language", payload.source_language)
  formData.append("target_language", payload.target_language)
  formData.append("model_name", payload.model_name)
  formData.append("created_by", payload.created_by)
  formData.append("env_profile", payload.env_profile)

  if (payload.output_name) {
    formData.append("output_name", payload.output_name)
  }

  formData.append("options", JSON.stringify(payload.options))

  return withApiError(
    api.post<TaskDetail>("/tasks/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
  )
}

export function retryTask(taskId: string) {
  return withApiError(
    api.post<{ task: TaskDetail; message: string }>(`/tasks/${taskId}/retry`)
  )
}

export function cancelTask(taskId: string) {
  return withApiError(
    api.post<{ task: TaskDetail; message: string }>(`/tasks/${taskId}/cancel`)
  )
}

export function listArtifacts(taskId: string) {
  return withApiError(api.get<ArtifactListResponse>(`/tasks/${taskId}/artifacts`))
}

export function listLogs(taskId: string) {
  return withApiError(api.get<ArtifactListResponse>(`/tasks/${taskId}/logs`))
}

export function getFailureSummary(limit = 20) {
  return withApiError(
    api.get<FailureSummary>("/tasks/failures/summary", {
      params: { limit },
    })
  )
}

export function listArchives(filters: TaskListFilters) {
  return withApiError(
    api.get<PaginatedArchives>("/archives", {
      params: buildSearchParams(filters),
    })
  )
}
