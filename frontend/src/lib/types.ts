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

export const sourceTypes = ["arxiv", "upload"] as const
export type SourceType = (typeof sourceTypes)[number]

export const artifactTypes = [
  "SOURCE_ARCHIVE",
  "EXTRACTED_SOURCE",
  "TRANSLATED_PROJECT",
  "FINAL_PDF",
  "LOG",
  "METADATA",
  "INTERMEDIATE_JSON",
] as const

export type ArtifactType = (typeof artifactTypes)[number]

export type TaskSummary = {
  id: string
  task_name: string
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
  created_by?: string
  created_from?: string
  created_to?: string
}

export type CreateArxivTaskPayload = {
  source_type: "arxiv"
  arxiv_id: string
  task_name?: string
  source_language?: string
  target_language?: string
  model_name?: string
  created_by?: string
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
  created_by?: string
  env_profile?: string
  output_name?: string
  options?: {
    mode: string
    update_term: string
    user_term: string
  }
}

export const terminalStatuses: TaskStatus[] = [
  "SUCCEEDED",
  "FAILED",
  "CANCELED",
]
