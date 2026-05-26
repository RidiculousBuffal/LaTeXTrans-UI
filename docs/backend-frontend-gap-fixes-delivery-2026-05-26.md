# Backend/Frontend 差距修复交付说明

更新时间：2026-05-26

对应审阅文档：`docs/backend-frontend-implementation-gap-review-2026-05-26.md`  
对应 PRD：`docs/fastapi-react-refactor-prd.md`

## 1. 交付结论

本轮已按审阅文档中的问题清单完成修复，并在 review 反馈后继续补齐了两个遗留点，覆盖：

- P0-1：取消任务仅改状态、未真正中断执行
- P0-2：失败路径未保证日志/元数据归档
- P1-3：任务列表轮询停止条件不正确
- P1-4：历史检索缺少时间范围前端入口
- P1-5：同一 arXiv ID 聚合展示未实现
- P1-6：结构化日志能力未真正接入
- review follow-up：运行时 artifact 收尾上传的事务一致性问题
- review follow-up：失败类型分布未实现

当前状态：

- 前后端主链路继续保持可用。
- 审阅中指出的 6 个缺口，以及 review follow-up 指出的 2 个遗留点，均已补齐到“可运行、可验证”的状态。
- 已补充后端测试覆盖关键修复点。

## 2. 修复项对照

### 2.1 P0-1 取消任务语义修复

修复内容：

- `POST /tasks/{id}/cancel` 不再只是简单把任务写成 `CANCELED`。
- worker 执行过程中新增持续取消检查：
  - 下载准备后检查
  - 每个 project 开始前检查
  - 状态切换前检查
  - 翻译流水线返回后检查
  - 成功态写入前再次检查
- 一旦检测到取消：
  - 不再继续写入 `SUCCEEDED`
  - 不再继续成功收尾
  - 最终统一落为 `CANCELED`
  - 记录取消事件日志

实现位置：

- `backend/app/services/task_service.py`
- `backend/app/workers/translation_runner.py`

说明：

- 当前实现为“协作式取消”。
- 如果底层某个单次长调用已经开始，无法在调用中途强杀线程；但会在该步骤结束后的下一个检查点停止。
- 已修正原先“前端显示已取消，但任务最终成功完成”的状态语义冲突。

### 2.2 P0-2 失败任务归档完整性修复

修复内容：

- 将运行时关键归档改为 finally 兜底上传，而不是只放在成功路径尾部。
- 无论任务成功、失败或取消，都会尽量归档以下文件：
  - `task-config.json`
  - `task.log`
  - `task-events.jsonl`
- 新增结构化事件日志文件 `task-events.jsonl`，用于记录任务阶段变化、失败信息、取消信息。
- 若某个归档上传失败，会额外记录任务事件，避免静默丢失。

实现位置：

- `backend/app/workers/translation_runner.py`

对应 artifact 类型：

- `METADATA`
- `LOG`
- `INTERMEDIATE_JSON`

### 2.3 P1-3 任务列表轮询条件修复

修复内容：

- 列表页轮询逻辑不再只看 `items[0].status`。
- 改为：只要当前列表中任意任务仍是非终态，就继续轮询。
- 终态定义仍为：
  - `SUCCEEDED`
  - `FAILED`
  - `CANCELED`

实现位置：

- `frontend/src/hooks/use-polling.ts`
- `frontend/src/pages/tasks-page.tsx`

### 2.4 P1-4 时间范围筛选前端入口补齐

修复内容：

- 任务筛选组件新增：
  - `created_from`
  - `created_to`
- 前端通过 `datetime-local` 输入采集时间范围。
- 请求发出前统一转成 ISO 时间字符串，和后端现有参数保持一致。
- 任务列表页与归档页均接入该筛选能力。

实现位置：

- `frontend/src/components/tasks/task-filters.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/tasks-page.tsx`
- `frontend/src/pages/archives-page.tsx`

### 2.5 P1-5 同一 arXiv ID 聚合展示实现

修复内容：

- 后端归档服务不再只返回逐任务列表。
- 新增归档聚合结构，按以下规则分组：
  - 有 `arxiv_id`：按 `arxiv:{arxiv_id}` 分组
  - 无 `arxiv_id` 上传任务：按 `task:{task_id}` 单独分组，避免误聚合
- 聚合返回字段包括：
  - `group_key`
  - `arxiv_id`
  - `task_count`
  - `artifact_count`
  - `latest_created_at`
  - `latest_task`
  - `tasks`
- 分页语义也同步修正为“先聚合，再分页”，避免同一 arXiv 结果被拆到不同页。
- 前端归档页已改为消费聚合结果。

实现位置：

- `backend/app/schemas/task.py`
- `backend/app/services/archive_service.py`
- `backend/app/repositories/task_repository.py`
- `backend/app/services/task_service.py`
- `frontend/src/lib/types.ts`
- `frontend/src/pages/archives-page.tsx`

### 2.6 P1-6 结构化日志接入

修复内容：

- 新增统一日志配置入口，使用 `python-json-logger` 输出 JSON 结构化日志。
- 后端启动时初始化 root logger。
- worker 在关键生命周期输出结构化日志：
  - 任务开始
  - 状态切换
  - 任务成功
  - 任务失败
  - 任务取消
  - artifact 上传失败

实现位置：

- `backend/app/core/logging.py`
- `backend/app/main.py`
- `backend/app/workers/translation_runner.py`

### 2.7 Review Follow-up: artifact 收尾上传事务修复

修复内容：

- 运行时 artifact 收尾上传从“整批 add 后统一 commit”改为“每个成功 artifact 单独 commit”。
- 这样当后续某个 artifact 上传失败时：
  - 不会把前面已经成功写入数据库的 artifact 记录一起回滚掉
  - 不会出现 MinIO 中已有文件、数据库中却无对应 artifact 记录的状态不一致
- 上传失败时仍会额外记录任务事件，保留失败证据。

实现位置：

- `backend/app/workers/translation_runner.py`

### 2.8 Review Follow-up: 失败类型分布补齐

修复内容：

- `GET /api/tasks/failures/summary` 在原有 `failed_stage_counts` 之外，新增 `failed_type_counts`。
- 当前基于 `error_message` 做轻量失败类型归类，输出例如：
  - `timeout`
  - `model_call_error`
  - `compile_error`
  - `input_archive_error`
  - `source_download_error`
  - `artifact_upload_error`
  - `metadata_error`
  - `runtime_error`
  - `unknown`
- 前端任务页右侧 Failure pulse 已同步展示 failure type counts。

实现位置：

- `backend/app/schemas/task.py`
- `backend/app/services/task_service.py`
- `frontend/src/lib/types.ts`
- `frontend/src/pages/tasks-page.tsx`

## 3. 验证情况

已完成验证：

- 后端语法检查：
  - `python -m compileall backend/app`
- 后端测试：
  - `.venv/bin/python -m pytest backend/tests`
- 前端类型检查：
  - `npm run typecheck`（`frontend/`）

结果：

- 后端测试 `6 passed`
- 前端 TypeScript 类型检查通过

新增/覆盖的关键测试点：

- 取消后进入终态 `CANCELED`
- 取消事件会写入事件日志
- 同一 `arxiv_id` 归档聚合结构正确
- artifact 收尾上传在“先成功后失败”时不丢前面成功的数据库记录
- failure summary 返回 `failed_type_counts`

测试文件：

- `backend/tests/test_task_runtime_behaviors.py`

## 4. 已知边界

当前仍有一个需要如实说明的边界：

- 取消任务目前是“协作式取消”，不是操作系统级强制中断。
- 如果底层翻译流程正在执行一个不可中断的长步骤，需要等该步骤返回后，worker 才会在下一个检查点结束任务。

这意味着：

- 当前版本已经解决“取消语义错误”和“取消后仍成功完成”的问题。
- 但如果后续需要“秒级硬中断”，还需要继续改造底层翻译流水线或执行模型。

## 5. 供 review 人员重点复核的点

建议重点复核以下内容：

- 取消中的任务是否最终稳定落到 `CANCELED`，且不会再写 `SUCCEEDED`
- 失败任务详情中是否能拿到日志/metadata/structured event log
- 归档页是否确实按 `arXiv ID` 聚合，而非仅前端视觉拼接
- 时间范围筛选参数是否与后端查询语义一致
- 列表页存在多个运行中任务时，轮询是否持续

## 6. 主要改动文件

- `backend/app/core/logging.py`
- `backend/app/main.py`
- `backend/app/repositories/task_repository.py`
- `backend/app/schemas/task.py`
- `backend/app/services/archive_service.py`
- `backend/app/services/task_service.py`
- `backend/app/workers/translation_runner.py`
- `backend/tests/test_task_runtime_behaviors.py`
- `frontend/src/components/tasks/task-filters.tsx`
- `frontend/src/hooks/use-polling.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/pages/archives-page.tsx`
- `frontend/src/pages/tasks-page.tsx`
