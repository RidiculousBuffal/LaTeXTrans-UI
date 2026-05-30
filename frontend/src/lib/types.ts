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

export const collectionTranslationModes = ["manual", "auto"] as const
export type CollectionTranslationMode = (typeof collectionTranslationModes)[number]

export const translateDecisions = [
  "pending",
  "manual_requested",
  "auto_queued",
  "translated",
] as const
export type TranslateDecision = (typeof translateDecisions)[number]

export const discoveryRunStatuses = ["PENDING", "RUNNING", "SUCCEEDED", "FAILED"] as const
export type DiscoveryRunStatus = (typeof discoveryRunStatuses)[number]

export type DiscoveryPaperListFilters = {
  page?: number
  page_size?: number
  category?: string
  keyword?: string
  worth_read?: boolean | ""
  translated?: boolean | ""
  collection_id?: number | ""
  source_run_date?: string
}

export type DiscoveryCollectionMembership = {
  item_id: number
  collection_id: number
  collection_name: string
  translate_decision: TranslateDecision
  note: string | null
  created_at: string
  updated_at: string
}

export type DiscoveryPaperEnrichment = {
  id: number
  enrichment_type: string
  model_name: string
  title_zh: string | null
  abstract_zh: string | null
  summary_zh: string | null
  keywords_json: string[] | null
  created_at: string
  updated_at: string
}

export type DiscoveryPaperReview = {
  id: number
  collection_id: number
  collection_name: string
  review_type: "daily_judge"
  model_name: string
  worth_read: boolean
  comment: string | null
  raw_result_json: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type DiscoveryPaperSummary = {
  id: number
  arxiv_id: string
  primary_category: string | null
  published_at: string | null
  scraped_at: string
  title_en: string
  abstract_en: string
  authors_json: string[]
  pdf_url: string | null
  abs_url: string | null
  subjects_json: string[]
  comments: string | null
  source_run_date: string | null
  title_zh: string | null
  abstract_zh: string | null
  worth_read: boolean | null
  comment: string | null
  has_translation: boolean
  translation_task_count: number
  collections: DiscoveryCollectionMembership[]
  created_at: string
  updated_at: string
}

export type DiscoveryPaperDetail = DiscoveryPaperSummary & {
  enrichment: DiscoveryPaperEnrichment | null
  reviews: DiscoveryPaperReview[]
  tasks: TaskSummary[]
  latest_task: TaskSummary | null
}

export type PaginatedDiscoveryPapers = {
  items: DiscoveryPaperSummary[]
  total: number
  page: number
  page_size: number
}

export type DiscoveryCollectionItem = {
  id: number
  collection_id: number
  paper_id: number
  added_by_user_id: string | null
  note: string | null
  translate_decision: TranslateDecision
  created_at: string
  updated_at: string
  paper: DiscoveryPaperSummary
}

export type DiscoveryCollection = {
  id: number
  user_id: string
  name: string
  description: string | null
  categories_json: string[]
  prefer_keywords: string | null
  avoid_keywords: string | null
  translation_mode: CollectionTranslationMode
  auto_translate_enabled: boolean
  item_count: number
  items: DiscoveryCollectionItem[]
  created_at: string
  updated_at: string
}

export type DiscoveryCollectionList = {
  items: DiscoveryCollection[]
  total: number
}

export type DiscoveryRun = {
  id: string
  trigger_source: string
  requested_by_user_id: string | null
  source_run_date: string
  status: DiscoveryRunStatus
  categories_json: string[]
  total_papers: number
  total_reviews: number
  total_worth_read: number
  error_message: string | null
  summary_json: Record<string, unknown> | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export type DiscoveryDailyDigestGroup = {
  category: string
  papers: DiscoveryPaperSummary[]
}

export type DiscoveryDailyDigest = {
  run: DiscoveryRun | null
  groups: DiscoveryDailyDigestGroup[]
}

export type DiscoveryPaperTaskResponse = {
  task: TaskDetail
  paper: DiscoveryPaperDetail
}

export type DiscoveryCollectionCreatePayload = {
  name: string
  description?: string
  categories_json?: string[]
  prefer_keywords?: string
  avoid_keywords?: string
  translation_mode?: CollectionTranslationMode
  auto_translate_enabled?: boolean
}

export type DiscoveryCollectionUpdatePayload = {
  name?: string
  description?: string
  categories_json?: string[]
  prefer_keywords?: string
  avoid_keywords?: string
  translation_mode?: CollectionTranslationMode
  auto_translate_enabled?: boolean
}

export type DiscoveryCollectionItemCreatePayload = {
  paper_id: number
  note?: string
  translate_decision?: TranslateDecision
}

export type DiscoveryPaperTaskCreatePayload = {
  collection_id?: number
  task_name?: string
  source_language?: string
  target_language?: string
  model_name?: string
  env_profile?: string
  output_name?: string
  options?: Record<string, unknown>
}

export type AdminDiscoverySyncPayload = {
  source_run_date?: string
  force_refresh?: boolean
  run_inline?: boolean
}

export type AdminDiscoveryRunList = {
  items: DiscoveryRun[]
  total: number
  page: number
  page_size: number
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
  expires_in: number
  user: UserInfo
}

export type AuthConfig = {
  registration_enabled: boolean
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
