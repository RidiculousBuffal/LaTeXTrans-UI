export const taskStatuses = [
  "PENDING",
  "DOWNLOADING",
  "PARSING",
  "TRANSLATING",
  "VALIDATING",
  "GENERATING",
  "SUCCEEDED",
  "FAILED",
  "CANCELED",
] as const

export type TaskStatus = (typeof taskStatuses)[number]

export const taskEngines = ["latex", "babeldoc"] as const
export type TaskEngine = (typeof taskEngines)[number]

export const sourceTypes = ["arxiv", "upload", "pdf_upload"] as const
export type SourceType = (typeof sourceTypes)[number]

export const artifactTypes = [
  "SOURCE_ARCHIVE",
  "SOURCE_PDF",
  "EXTRACTED_SOURCE",
  "TRANSLATED_PROJECT",
  "FINAL_PDF",
  "TRANSLATED_PDF",
  "BABELDOC_OUTPUT",
  "LOG",
  "METADATA",
  "INTERMEDIATE_JSON",
] as const

export type ArtifactType = (typeof artifactTypes)[number]

export type TaskSummary = {
  id: string
  task_name: string
  engine: TaskEngine
  source_type: SourceType
  arxiv_id: string | null
  source_archive_name: string | null
  source_language: string
  target_language: string
  model_name: string
  status: TaskStatus
  current_stage: TaskStatus
  progress_percent: number
  error_message: string | null
  created_by: string
  owner_user_id: string | null
  visibility: "private" | "public"
  result_source: "EXECUTED" | "CACHE_HIT"
  quota_cost: number
  workspace_dir: string | null
  output_dir: string | null
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
  canceled_at: string | null
}

export type TaskArtifact = {
  id: number
  task_id: string
  artifact_type: ArtifactType
  object_key: string
  file_name: string
  content_type: string
  file_size: number
  version: number
  metadata_json: Record<string, unknown>
  download_url: string
  created_at: string
}

export type TaskEvent = {
  id: number
  task_id: string
  stage: TaskStatus
  status: TaskStatus
  message: string
  details_json: Record<string, unknown>
  created_at: string
}

export type TaskConfig = {
  id: number
  task_id: string
  env_profile: string
  config_snapshot_json: Record<string, unknown>
  created_at: string
}

export type TaskDetail = TaskSummary & {
  artifacts: TaskArtifact[]
  events: TaskEvent[]
  configs: TaskConfig[]
}

export type PaginatedTasks = {
  items: TaskSummary[]
  total: number
  page: number
  page_size: number
}

export type ArtifactListResponse = {
  task_id: string
  items: TaskArtifact[]
}

export type TaskLogsResponse = {
  task_id: string
  path: string | null
  exists: boolean
  content: string
  size_bytes: number
  truncated: boolean
  updated_at: string | null
}

export type FailureSummary = {
  recent_failed_tasks: TaskSummary[]
  failed_stage_counts: Partial<Record<TaskStatus, number>>
  failed_type_counts: Record<string, number>
  total_failed: number
}

export type ArchiveItem = {
  task: TaskSummary
  artifact_count: number
}

export type ArchiveGroup = {
  group_key: string
  arxiv_id: string | null
  task_count: number
  artifact_count: number
  latest_created_at: string
  latest_task: TaskSummary
  tasks: ArchiveItem[]
}

export type PaginatedArchives = {
  items: ArchiveGroup[]
  total: number
  page: number
  page_size: number
}

export type TaskListFilters = {
  page?: number
  page_size?: number
  status?: TaskStatus | ""
  task_name?: string
  arxiv_id?: string
  scope?: "mine" | "shared" | "public" | "all" | ""
  created_from?: string
  created_to?: string
}

export type CreateArxivTaskPayload = {
  engine?: "latex"
  source_type: "arxiv"
  arxiv_id: string
  task_name?: string
  source_language?: string
  target_language?: string
  model_name?: string
  env_profile?: string
  output_name?: string
  options?: {
    mode: string
    update_term: string
    user_term: string
  }
}

export type CreateUploadTaskPayload = {
  file: File
  task_name?: string
  source_language?: string
  target_language?: string
  model_name?: string
  env_profile?: string
  output_name?: string
  options?: {
    mode: string
    update_term: string
    user_term: string
  }
}

export type CreatePdfTaskPayload = {
  file: File
  task_name?: string
  target_language?: string
  model_name?: string
  env_profile?: string
  options?: {
    qps?: string
    pool_max_workers?: string
  }
}

// Auth types
export type UserInfo = {
  id: string
  username: string
  role: "user" | "admin"
  quota_balance: number
  is_active: boolean
}

export type LoginResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

// Sharing types
export type SharingState = {
  task_id: string
  visibility: "private" | "public"
  shared_users: Array<{ user_id: string; username: string }>
}

export type SharingUpdateRequest = {
  visibility?: "private" | "public"
  grant_usernames: string[]
}

// Admin types
export type AdminUserItem = {
  id: string
  username: string
  role: "user" | "admin"
  is_active: boolean
  quota_balance: number
}

export type AdminUserList = {
  items: AdminUserItem[]
  total: number
}

export const terminalStatuses: TaskStatus[] = [
  "SUCCEEDED",
  "FAILED",
  "CANCELED",
]
