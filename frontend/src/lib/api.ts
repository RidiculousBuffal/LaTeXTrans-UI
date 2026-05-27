import axios from "axios"

import type {
  AdminUserItem,
  AdminUserList,
  AuthConfig,
  ArtifactListResponse,
  CreateArxivTaskPayload,
  CreatePdfTaskPayload,
  CreateUploadTaskPayload,
  FailureSummary,
  LoginResponse,
  PaginatedArchives,
  PaginatedTasks,
  SharingState,
  SharingUpdateRequest,
  TaskDetail,
  TaskListFilters,
  TaskLogsResponse,
  UserInfo,
} from "@/lib/types"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 20_000,
  withCredentials: true,
})

// Redirect to /login on 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const requestUrl = error.config?.url ?? ""
      const isSessionProbe = requestUrl.endsWith("/auth/me") || requestUrl.endsWith("/auth/config")
      if (
        !isSessionProbe &&
        !window.location.pathname.startsWith("/login") &&
        !window.location.pathname.startsWith("/register") &&
        !window.location.pathname.startsWith("/landing")
      ) {
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)

function buildSearchParams(filters: TaskListFilters) {
  return Object.fromEntries(
    Object.entries(filters)
      .filter(([, value]) => value !== undefined && value !== "")
      .map(([key, value]) => {
        if (
          (key === "created_from" || key === "created_to") &&
          typeof value === "string" &&
          value.length > 0
        ) {
          return [key, new Date(value).toISOString()]
        }
        return [key, value]
      })
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
  status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

async function withApiError<T>(promise: Promise<{ data: T }>) {
  try {
    const response = await promise
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new ApiError(getApiErrorMessage(error), error.response?.status)
    }
    throw new ApiError(getApiErrorMessage(error))
  }
}

// Auth
export function register(username: string, password: string) {
  return withApiError(api.post<UserInfo>("/auth/register", { username, password }))
}

export function login(username: string, password: string) {
  return withApiError(api.post<LoginResponse>("/auth/login", { username, password }))
}

export function logout() {
  return withApiError(api.post<void>("/auth/logout"))
}

export function getMe() {
  return withApiError(api.get<UserInfo>("/auth/me"))
}

export function getAuthConfig() {
  return withApiError(api.get<AuthConfig>("/auth/config"))
}

// Tasks
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
  if (payload.task_name) formData.append("task_name", payload.task_name)
  if (payload.source_language) formData.append("source_language", payload.source_language)
  if (payload.target_language) formData.append("target_language", payload.target_language)
  if (payload.model_name) formData.append("model_name", payload.model_name)
  if (payload.env_profile) formData.append("env_profile", payload.env_profile)
  if (payload.output_name) formData.append("output_name", payload.output_name)
  if (payload.options) formData.append("options", JSON.stringify(payload.options))

  return withApiError(
    api.post<TaskDetail>("/tasks/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  )
}

export function createPdfTask(payload: CreatePdfTaskPayload) {
  const formData = new FormData()
  formData.append("file", payload.file)
  if (payload.task_name) formData.append("task_name", payload.task_name)
  if (payload.target_language) formData.append("target_language", payload.target_language)
  if (payload.model_name) formData.append("model_name", payload.model_name)
  if (payload.env_profile) formData.append("env_profile", payload.env_profile)
  if (payload.options) formData.append("options", JSON.stringify(payload.options))

  return withApiError(
    api.post<TaskDetail>("/tasks/pdf", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  )
}

export function retryTask(taskId: string) {
  return withApiError(api.post<{ task: TaskDetail; message: string }>(`/tasks/${taskId}/retry`))
}

export function cancelTask(taskId: string) {
  return withApiError(api.post<{ task: TaskDetail; message: string }>(`/tasks/${taskId}/cancel`))
}

export function deleteTask(taskId: string) {
  return withApiError(api.delete<void>(`/tasks/${taskId}`))
}

export function listArtifacts(taskId: string) {
  return withApiError(api.get<ArtifactListResponse>(`/tasks/${taskId}/artifacts`))
}

export function getTaskLogs(taskId: string) {
  return withApiError(api.get<TaskLogsResponse>(`/tasks/${taskId}/logs`))
}

export function getFailureSummary(limit = 20) {
  return withApiError(
    api.get<FailureSummary>("/tasks/failures/summary", { params: { limit } })
  )
}

// Sharing
export function getTaskSharing(taskId: string) {
  return withApiError(api.get<SharingState>(`/tasks/${taskId}/sharing`))
}

export function updateTaskSharing(taskId: string, payload: SharingUpdateRequest) {
  return withApiError(api.put<SharingState>(`/tasks/${taskId}/sharing`, payload))
}

// Archives
export function listArchives(filters: TaskListFilters) {
  return withApiError(
    api.get<PaginatedArchives>("/archives", { params: buildSearchParams(filters) })
  )
}

// Admin
export function adminListUsers(page = 1, pageSize = 20) {
  return withApiError(
    api.get<AdminUserList>("/admin/users", { params: { page, page_size: pageSize } })
  )
}

export function adminAdjustQuota(userId: string, delta: number, reason: string) {
  return withApiError(
    api.post<{ user_id: string; new_balance: number; delta: number }>(
      `/admin/users/${userId}/quota-adjustments`,
      { delta, reason }
    )
  )
}

export function adminCreateUser(payload: {
  username: string
  password: string
  role: "user" | "admin"
  initial_quota: number
}) {
  return withApiError(api.post<AdminUserItem>("/admin/users", payload))
}

export function adminChangePassword(userId: string, newPassword: string) {
  return withApiError(api.patch(`/admin/users/${userId}/password`, { new_password: newPassword }))
}
