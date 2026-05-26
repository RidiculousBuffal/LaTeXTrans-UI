# LaTeXTrans Backend API Reference

更新时间：2026-05-26

本文档面向前端接入，覆盖当前后端已经实现的全部接口、请求参数、响应结构和关键枚举。

## 1. Base Info

- 本地开发默认前缀：`/api`
- 健康检查：`GET /healthz`
- OpenAPI JSON：`GET /api/openapi.json`
- Swagger UI：`GET /api/docs`
- ReDoc：`GET /api/redoc`

示例开发地址：

- `http://127.0.0.1:8000/api`

## 2. Core Concepts

### 2.1 Task Source Type

- `arxiv`
- `upload`

### 2.2 Task Status

- `PENDING`
- `DOWNLOADING`
- `PARSING`
- `TRANSLATING`
- `VALIDATING`
- `GENERATING`
- `SUCCEEDED`
- `FAILED`
- `CANCELED`

### 2.3 Artifact Type

- `SOURCE_ARCHIVE`
- `EXTRACTED_SOURCE`
- `TRANSLATED_PROJECT`
- `FINAL_PDF`
- `LOG`
- `METADATA`
- `INTERMEDIATE_JSON`

## 3. Shared Response Models

### 3.1 TaskSummaryResponse

```json
{
  "id": "string",
  "task_name": "string",
  "source_type": "arxiv",
  "arxiv_id": "string|null",
  "source_archive_name": "string|null",
  "source_language": "en",
  "target_language": "zh",
  "model_name": "gpt-5.4",
  "status": "PENDING",
  "current_stage": "PENDING",
  "progress_percent": 0,
  "error_message": "string|null",
  "created_by": "string",
  "workspace_dir": "string|null",
  "output_dir": "string|null",
  "created_at": "2026-05-26T16:00:00Z",
  "updated_at": "2026-05-26T16:00:00Z",
  "started_at": "2026-05-26T16:00:05Z|null",
  "finished_at": "2026-05-26T16:10:00Z|null",
  "canceled_at": "2026-05-26T16:05:00Z|null"
}
```

### 3.2 TaskArtifactResponse

```json
{
  "id": 1,
  "task_id": "string",
  "artifact_type": "FINAL_PDF",
  "object_key": "string",
  "file_name": "string",
  "content_type": "application/pdf",
  "file_size": 12345,
  "version": 1,
  "metadata_json": {
    "bucket": "latex-trans-tasks"
  },
  "download_url": "https://...",
  "created_at": "2026-05-26T16:10:00Z"
}
```

说明：

- `download_url` 是后端生成的 MinIO 预签名下载地址，前端可直接用于下载。
- `metadata_json` 是归档附加信息，字段会因 artifact 类型不同而变化。

### 3.3 TaskEventResponse

```json
{
  "id": 1,
  "task_id": "string",
  "stage": "TRANSLATING",
  "status": "TRANSLATING",
  "message": "Translation pipeline started.",
  "details_json": {
    "project_dir": "..."
  },
  "created_at": "2026-05-26T16:01:00Z"
}
```

### 3.4 TaskConfigResponse

```json
{
  "id": 1,
  "task_id": "string",
  "env_profile": "default",
  "config_snapshot_json": {},
  "created_at": "2026-05-26T16:00:00Z"
}
```

### 3.5 TaskDetailResponse

```json
{
  "...TaskSummaryResponse": "...",
  "artifacts": [],
  "events": [],
  "configs": []
}
```

## 4. API List

### 4.1 Health Check

`GET /healthz`

响应：

```json
{
  "status": "ok"
}
```

### 4.2 Create arXiv Task

`POST /api/tasks`

请求头：

- `Content-Type: application/json`

请求体：

```json
{
  "task_name": "paper-2501-00001",
  "source_type": "arxiv",
  "arxiv_id": "2501.00001",
  "source_language": "en",
  "target_language": "zh",
  "model_name": "gpt-5.4",
  "created_by": "frontend-user",
  "env_profile": "default",
  "output_name": "paper-2501-00001-zh",
  "options": {
    "mode": 0,
    "update_term": "False",
    "user_term": ""
  }
}
```

约束：

- `source_type=arxiv` 时必须提供 `arxiv_id`

响应：

- `201 Created`
- Body 为 `TaskDetailResponse`

### 4.3 Create Upload Task

`POST /api/tasks/upload`

请求头：

- `Content-Type: multipart/form-data`

表单字段：

- `file`: 必填，支持 `.zip`、`.tar`、`.tar.gz`、`.tgz`
- `task_name`: 可选
- `source_language`: 可选，默认 `en`
- `target_language`: 可选，默认 `zh`
- `model_name`: 可选
- `created_by`: 可选
- `env_profile`: 可选，默认 `default`
- `output_name`: 可选
- `options`: 可选，字符串形式 JSON，默认 `"{}"`

示例：

```bash
curl -X POST "http://127.0.0.1:8000/api/tasks/upload" \
  -F 'file=@/path/to/paper.tar.gz' \
  -F 'task_name=my-upload-paper' \
  -F 'source_language=en' \
  -F 'target_language=zh' \
  -F 'created_by=frontend-user' \
  -F 'options={"mode":0}'
```

响应：

- `201 Created`
- Body 为 `TaskDetailResponse`

### 4.4 List Tasks

`GET /api/tasks`

查询参数：

- `page`: 默认 `1`
- `page_size`: 默认 `20`，最大 `100`
- `status`: 可选，对应任务状态枚举
- `task_name`: 可选，模糊匹配
- `arxiv_id`: 可选，精确匹配
- `created_by`: 可选
- `created_from`: 可选，ISO datetime
- `created_to`: 可选，ISO datetime

示例：

```bash
curl "http://127.0.0.1:8000/api/tasks?page=1&page_size=20&status=FAILED&task_name=paper"
```

响应：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

### 4.5 Get Task Detail

`GET /api/tasks/{task_id}`

路径参数：

- `task_id`: 任务 ID

响应：

- `200 OK`
- Body 为 `TaskDetailResponse`

前端建议：

- 任务详情页优先使用这个接口
- 它返回任务基础信息、事件时间线、配置快照和 artifact 列表

### 4.6 Retry Task

`POST /api/tasks/{task_id}/retry`

仅允许：

- `FAILED`
- `CANCELED`

响应：

```json
{
  "task": {},
  "message": "Task re-queued."
}
```

### 4.7 Cancel Task

`POST /api/tasks/{task_id}/cancel`

不允许取消的状态：

- `SUCCEEDED`
- `FAILED`
- `CANCELED`

响应：

```json
{
  "task": {},
  "message": "Task canceled."
}
```

### 4.8 List Task Artifacts

`GET /api/tasks/{task_id}/artifacts`

响应：

```json
{
  "task_id": "string",
  "items": [
    {
      "id": 1,
      "task_id": "string",
      "artifact_type": "FINAL_PDF",
      "object_key": "string",
      "file_name": "paper.pdf",
      "content_type": "application/pdf",
      "file_size": 12345,
      "version": 1,
      "metadata_json": {},
      "download_url": "https://...",
      "created_at": "2026-05-26T16:10:00Z"
    }
  ]
}
```

前端建议：

- 下载按钮直接使用 `download_url`
- 可按 `artifact_type` 分组展示

### 4.9 List Task Logs

`GET /api/tasks/{task_id}/logs`

响应结构与 artifact 列表一致，但仅返回 `artifact_type=LOG` 的项：

```json
{
  "task_id": "string",
  "items": []
}
```

### 4.10 Failure Summary

`GET /api/tasks/failures/summary`

查询参数：

- `limit`: 默认 `20`，最大 `100`

响应：

```json
{
  "recent_failed_tasks": [],
  "failed_stage_counts": {
    "TRANSLATING": 2,
    "GENERATING": 1
  },
  "total_failed": 3
}
```

前端建议：

- 可用于管理员面板或失败任务概览卡片

### 4.11 List Archives

`GET /api/archives`

查询参数与 `GET /api/tasks` 一致：

- `page`
- `page_size`
- `status`
- `task_name`
- `arxiv_id`
- `created_by`
- `created_from`
- `created_to`

响应：

```json
{
  "items": [
    {
      "task": {},
      "artifact_count": 4
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

## 5. Frontend Mapping Suggestions

### 5.1 Task List Page

建议使用：

- `GET /api/tasks`

建议展示字段：

- `task_name`
- `source_type`
- `arxiv_id`
- `status`
- `current_stage`
- `progress_percent`
- `created_by`
- `created_at`
- `error_message`

### 5.2 Task Detail Page

建议使用：

- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/artifacts`
- `GET /api/tasks/{task_id}/logs`

建议分区：

- 基础信息
- 状态与进度
- 事件时间线
- 归档产物
- 日志下载

### 5.3 New Task Page

创建 arXiv 任务：

- `POST /api/tasks`

创建上传任务：

- `POST /api/tasks/upload`

### 5.4 Archives Page

建议使用：

- `GET /api/archives`

## 6. Error Semantics

常见 HTTP 状态：

- `200 OK`
- `201 Created`
- `400 Bad Request`
- `404 Not Found`
- `409 Conflict`
- `500 Internal Server Error`

常见场景：

- `400`: 上传文件格式不支持，或请求体字段校验失败
- `404`: `task_id` 不存在
- `409`: 非法重试、非法取消
- `500`: 任务创建失败、上传保存失败、后端内部错误

FastAPI 默认错误结构示例：

```json
{
  "detail": "Task not found."
}
```

## 7. Recommended Polling Strategy

MVP 建议前端轮询：

- 任务列表页：`5s`
- 任务详情页：`3s` 到 `5s`

当任务状态进入以下终态时可停止轮询：

- `SUCCEEDED`
- `FAILED`
- `CANCELED`

## 8. Minimal curl Examples

创建 arXiv 任务：

```bash
curl -X POST "http://127.0.0.1:8000/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "arxiv-2501-00001",
    "source_type": "arxiv",
    "arxiv_id": "2501.00001",
    "source_language": "en",
    "target_language": "zh",
    "created_by": "frontend-agent",
    "options": {"mode": 0}
  }'
```

获取任务列表：

```bash
curl "http://127.0.0.1:8000/api/tasks?page=1&page_size=20"
```

获取任务详情：

```bash
curl "http://127.0.0.1:8000/api/tasks/<task_id>"
```

获取归档产物：

```bash
curl "http://127.0.0.1:8000/api/tasks/<task_id>/artifacts"
```

重试任务：

```bash
curl -X POST "http://127.0.0.1:8000/api/tasks/<task_id>/retry"
```

取消任务：

```bash
curl -X POST "http://127.0.0.1:8000/api/tasks/<task_id>/cancel"
```

## 9. Notes For Frontend Agent

- 后端已支持 `arxiv` 和 `upload` 两种创建方式，前端创建页可以做 Tab 切换。
- `TaskDetailResponse` 已经包含 `artifacts`、`events`、`configs`，大多数详情页场景只打一条详情接口也能先渲染。
- artifact 的 `download_url` 是临时签名地址，不建议长期缓存。
- `status` 和 `current_stage` 在当前实现里通常一致，前端优先展示 `status`，必要时可把 `current_stage` 作为更细的阶段文案来源。
- `failed_stage_counts` 可直接用于失败分布图表或统计卡片。
