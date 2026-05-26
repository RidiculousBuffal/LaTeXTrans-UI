# LaTeXTrans FastAPI Backend MVP Handoff

更新时间：2026-05-26

本文档用于给下一个 agent 交接当前后端改造进度。目标是让接手方不需要重新梳理上下文，就能直接继续实现后端的数据库迁移、任务执行和归档能力。

## 1. 本轮已完成内容

本轮已经完成的是“后端 MVP 的接口契约和数据库 schema 骨架”，还没有进入真实任务执行闭环。

### 1.1 新增后端目录结构

已新增：

- `backend/requirements.txt`
- `backend/app/main.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/tasks.py`
- `backend/app/api/routes/archives.py`
- `backend/app/core/config.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/models/task.py`
- `backend/app/repositories/task_repository.py`
- `backend/app/schemas/common.py`
- `backend/app/schemas/task.py`
- `backend/app/services/task_service.py`
- `backend/app/services/translation_service.py`
- `backend/app/services/archive_service.py`
- `backend/app/services/storage_service.py`
- `backend/app/workers/translation_runner.py`

说明：

- 当前代码重点是把 FastAPI API、SQLAlchemy ORM 模型、Pydantic schema、服务层边界先搭起来。
- 目前实现适合继续往下接 Alembic、真实数据库、MinIO 和翻译 worker。

### 1.2 已完成的 API 路由骨架

在 `backend/app/main.py` 中完成了 FastAPI app 初始化，并挂载了 `/api` 前缀。

目前已存在的接口骨架：

- `GET /healthz`
- `POST /api/tasks`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/retry`
- `POST /api/tasks/{task_id}/cancel`
- `GET /api/tasks/{task_id}/artifacts`
- `GET /api/tasks/{task_id}/logs`
- `GET /api/archives`

说明：

- 这些接口与 PRD 中的 MVP API Surface 基本对齐。
- 现阶段接口主要完成参数结构、服务层分发和响应模型映射。
- 还没有真正调度后台翻译任务，也没有接入对象存储下载地址生成。

### 1.3 已完成的数据库模型设计

在 `backend/app/models/task.py` 中实现了四张核心表的 ORM 模型：

- `translation_tasks`
- `task_artifacts`
- `task_events`
- `task_configs`

#### translation_tasks

核心字段已包含：

- `id`
- `task_name`
- `source_type`
- `arxiv_id`
- `source_archive_name`
- `source_language`
- `target_language`
- `model_name`
- `status`
- `current_stage`
- `progress_percent`
- `error_message`
- `created_by`
- `workspace_dir`
- `output_dir`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`
- `canceled_at`

状态枚举已经定义：

- `PENDING`
- `DOWNLOADING`
- `PARSING`
- `TRANSLATING`
- `VALIDATING`
- `GENERATING`
- `SUCCEEDED`
- `FAILED`
- `CANCELED`

#### task_artifacts

已包含：

- `artifact_type`
- `object_key`
- `file_name`
- `content_type`
- `file_size`
- `version`
- `metadata_json`

artifact 类型枚举已定义：

- `SOURCE_ARCHIVE`
- `EXTRACTED_SOURCE`
- `TRANSLATED_PROJECT`
- `FINAL_PDF`
- `LOG`
- `METADATA`
- `INTERMEDIATE_JSON`

#### task_events

用于记录阶段时间线和结构化事件：

- `task_id`
- `stage`
- `status`
- `message`
- `details_json`
- `created_at`

#### task_configs

用于保留任务参数快照：

- `task_id`
- `env_profile`
- `config_snapshot_json`
- `created_at`

### 1.4 已完成的 Pydantic schema

在 `backend/app/schemas/task.py` 中已实现：

- `TaskCreateRequest`
- `TaskSummaryResponse`
- `TaskDetailResponse`
- `TaskListResponse`
- `TaskRetryResponse`
- `TaskCancelResponse`
- `ArtifactListResponse`
- `TaskLogsResponse`
- `ArchiveListResponse`

其中 `TaskCreateRequest` 已支持：

- `source_type=arxiv|upload`
- `arxiv_id`
- `source_archive_name`
- `source_language`
- `target_language`
- `model_name`
- `created_by`
- `env_profile`
- `output_name`
- `options`

并已做基本校验：

- `source_type=arxiv` 时必须提供 `arxiv_id`
- `source_type=upload` 时必须提供 `source_archive_name`

### 1.5 已完成的服务层职责拆分

目前服务层已有：

- `TaskService`
- `TranslationService`
- `ArchiveService`
- `StorageService`

当前职责如下：

#### TaskService

负责：

- 创建任务记录
- 写入初始化事件
- 写入配置快照
- 查询任务列表
- 查询任务详情
- 重试任务
- 取消任务
- 查询产物列表
- 查询日志列表
- 查询归档列表

#### TranslationService

当前只做一件事：

- 根据请求和默认配置生成 `config_snapshot_json`

这是后续接入真实翻译执行前的重要过渡点。下一个 agent 可以继续把这里扩展成：

- 生成运行时目录
- 生成 TOML 配置
- 组装 `CoordinatorAgent` 需要的 config
- 触发真实翻译流水线

#### ArchiveService

当前只做一件事：

- 将任务对象映射成归档列表项

后续应扩展为：

- 归档清单组装
- 产物可见性控制
- 统一下载元数据结构

#### StorageService

当前只做了对象路径前缀的占位逻辑：

- `task_id/artifact_type/...`

后续应扩展为：

- MinIO client 初始化
- bucket 检查
- 上传接口
- 下载签名 URL
- 文件元数据读取

### 1.6 已完成的配置项整理

在 `backend/app/core/config.py` 中新增了独立后端配置读取逻辑，采用 `pydantic-settings`。

已支持：

- `BACKEND_DATABASE_URL`
- `MYSQL_USERNAME`
- `MYSQL_PASSWORD`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MINIO_URL`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`

并在 `.env.example` 中新增了：

- `BACKEND_DATABASE_URL=`

说明：

- 如果未配置 `BACKEND_DATABASE_URL`，当前会自动拼接 MySQL DSN。
- 这意味着接手方只要补齐 `.env` 即可直接接数据库。

## 2. 本轮做过的验证

本轮使用了项目虚拟环境中的 Python：

- `.venv/bin/python`

已执行的验证包括：

### 2.1 语法编译检查

执行过：

```bash
.venv/bin/python -m py_compile $(find backend -name '*.py' | sort)
```

结果：

- 通过

### 2.2 依赖安装

已执行：

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

结果：

- FastAPI、SQLAlchemy、Alembic、PyMySQL、pydantic-settings、MinIO 等已安装进当前 `.venv`

### 2.3 FastAPI 路由导入验证

已执行等价导入检查：

```python
from backend.app.main import app
print(sorted({route.path for route in app.routes}))
```

验证通过，当前可见路由包括：

- `/healthz`
- `/api/openapi.json`
- `/api/docs`
- `/api/redoc`
- `/api/tasks`
- `/api/tasks/{task_id}`
- `/api/tasks/{task_id}/retry`
- `/api/tasks/{task_id}/cancel`
- `/api/tasks/{task_id}/artifacts`
- `/api/tasks/{task_id}/logs`
- `/api/archives`

## 3. 当前明确还没完成的内容

这些是下一位 agent 不需要重新判断、可以直接继续做的事项。

### 3.1 数据库还未真正落库

目前只有 ORM 模型，没有完成：

- Alembic 初始化
- 初始 migration 生成
- migration 执行脚本
- 本地数据库联调

也就是说：

- 当前代码可以导入
- 但还没有真正建表

### 3.2 任务创建还未进入真实执行

现在 `POST /api/tasks` 做的是：

- 写入任务主记录
- 写入配置快照
- 写入一条 `PENDING` 事件

还没有做：

- 启动后台线程/进程
- 更新 `DOWNLOADING -> PARSING -> TRANSLATING -> VALIDATING -> GENERATING`
- 调用 `CoordinatorAgent.workflow_latextrans()`
- 捕获运行异常并写回 `FAILED`
- 成功后落 `SUCCEEDED`

### 3.3 MinIO 还只是占位

当前没有真正实现：

- 创建 bucket
- 上传输入源文件
- 上传 PDF
- 上传日志
- 上传翻译后工程目录
- 生成下载链接

### 3.4 上传文件链路还没接

虽然 schema 中支持 `source_type=upload` 和 `source_archive_name`，但还没有：

- FastAPI `UploadFile`
- 上传压缩包保存
- 文件大小限制
- 解压安全校验
- 路径穿越防护

### 3.5 现有 CLI/核心翻译工作流还未被服务化复用

目前还没有把这些逻辑从 `main.py` 里真正抽出来：

- 下载 arXiv 源文件
- 解压输入
- 组合配置
- 调用 `CoordinatorAgent`

下一阶段需要考虑：

- 是把现有 CLI 能力拆出纯 service
- 还是先在 worker 中直接复用现有配置格式

建议先走“最小改动复用”，不要一开始大改翻译核心。

### 3.6 没有测试文件

当前还未补：

- API 单元测试
- service 测试
- repository 测试
- 集成测试

## 4. 交接时需要特别注意的仓库状态

当前 `git status --short` 可见：

- `.env.example` 已修改
- `backend/` 为新增目录
- `src/UI/UI.py` 处于删除状态
- `.DS_Store` 未跟踪

注意：

- `src/UI/UI.py` 的删除不是本轮为了后端骨架主动做的，不要默认回滚，也不要默认提交，需要先确认它是不是用户之前就在处理的改动。
- `.DS_Store` 不要提交。
- `backend/__pycache__` 和子目录 `__pycache__` 是因为执行 Python 导入检查生成的，建议下一个 agent 清理后再决定是否补 `.gitignore`。

## 5. 推荐给下一个 agent 的执行顺序

下面是建议的详细执行计划，按这个顺序推进返工最少。

### 第一步：补数据库迁移

目标：

- 让当前 ORM 模型可以真正建表

建议任务：

1. 初始化 `alembic`
2. 配置 `alembic.ini` 和 `env.py`
3. 将 `backend.app.db.base.Base.metadata` 接入 Alembic
4. 生成初始 migration
5. 本地跑一次 upgrade
6. 验证 4 张核心表结构是否与当前 ORM 一致

建议新增文件：

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/*.py`

建议同时补：

- 一个简单的 `backend/scripts/init_db.py` 或 README 命令说明

### 第二步：把任务执行链路接起来

目标：

- `POST /api/tasks` 创建后能真正开始跑翻译

MVP 建议实现方式：

- 先不要上 Celery
- 先使用 FastAPI 后台线程、本地线程池或单独 worker 进程

建议新增或修改：

- 扩展 `backend/app/workers/translation_runner.py`
- 新增真正的 `run_task(task_id: str)` 入口
- 在 `TaskService.create_task()` 成功后调度这个 runner

runner 最少要完成：

1. 根据任务配置准备工作目录
2. 如果是 `arxiv`，下载源码
3. 如果是 `upload`，读取上传的压缩包
4. 更新状态为 `DOWNLOADING`
5. 解压后更新状态为 `PARSING`
6. 调用 `CoordinatorAgent.workflow_latextrans()`
7. 在关键节点写入 `TaskEvent`
8. 成功后更新 `SUCCEEDED`
9. 失败后写 `FAILED` 和 `error_message`

重要建议：

- 状态推进不要只写任务主表，必须同步写 `task_events`
- 错误信息建议保留“短摘要 + 日志文件”

### 第三步：把当前 CLI 流程拆成可复用服务

目标：

- 避免 worker 直接复制 `main.py` 逻辑

应优先抽离的能力：

- 从 arXiv ID 下载源文件
- 解压源文件
- 解析项目目录
- 组装 `CoordinatorAgent` 所需 config

建议做法：

- 新建 `backend/app/services/pipeline_service.py`
- 复用已有：
  - `src/formats/latex/utils.py`
  - `src/agents/coordinator_agent.py`

建议不要做的事：

- 不要一开始就重写 `CoordinatorAgent`
- 不要先改动翻译核心 agent 内部逻辑

### 第四步：接 MinIO 归档

目标：

- 成功任务和失败任务都要能归档关键产物

建议最小归档集合：

- 原始输入压缩包或 arXiv 下载源
- 解压后的源目录压缩包
- 翻译后工程目录压缩包
- 最终 PDF
- 运行日志
- 配置快照 JSON

建议实现：

1. 在 `StorageService` 中初始化 MinIO client
2. 增加 bucket 检查
3. 增加 `upload_file`
4. 增加 `upload_directory_as_zip`
5. 增加 `presigned_get_url`
6. 在任务成功/失败路径写入 `task_artifacts`

建议对象路径规则：

- `{task_id}/source/...`
- `{task_id}/translated/...`
- `{task_id}/pdf/...`
- `{task_id}/logs/...`
- `{task_id}/metadata/...`

### 第五步：补上传接口

目标：

- 支持前端上传 LaTeX 源码压缩包

建议实现：

1. 修改 `POST /api/tasks`
2. 支持 `multipart/form-data`
3. 同时兼容：
   - 纯 JSON 的 arXiv 提交
   - 上传文件的表单提交

建议注意：

- 文件大小限制
- 扩展名白名单
- 解压目录隔离
- 防止 zip slip

### 第六步：补测试

目标：

- 给后续前端联调提供稳定基线

建议优先级：

1. schema 校验测试
2. task service 测试
3. API 路由测试
4. migration smoke test
5. worker 状态流转测试

## 6. 建议下一个 agent 优先落的具体小目标

如果希望下一位 agent 一次完成一个清晰里程碑，建议优先做这个组合：

### 推荐里程碑 A

- Alembic 初始化
- 本地建表成功
- `POST /api/tasks` 可写入真实 MySQL
- `GET /api/tasks` 和 `GET /api/tasks/{task_id}` 可查真实数据

这是最稳的一步，因为：

- 不会过早耦合翻译执行细节
- 能尽快让前端先开始联调“任务列表 / 任务详情”

### 推荐里程碑 B

在 A 基础上继续：

- 增加本地后台任务执行器
- 打通 `PENDING -> ... -> SUCCEEDED/FAILED`
- 先不接 MinIO，只先跑本地文件系统归档

这是最适合快速验证端到端状态流的第二步。

### 推荐里程碑 C

在 B 基础上继续：

- 接 MinIO
- 落 `task_artifacts`
- 提供下载/查看链接

## 7. 关键代码入口提示

下一个 agent 可以优先从这些文件开始看：

- PRD：`docs/fastapi-react-refactor-prd.md`
- FastAPI 入口：`backend/app/main.py`
- 路由：`backend/app/api/routes/tasks.py`
- ORM：`backend/app/models/task.py`
- schema：`backend/app/schemas/task.py`
- 服务层：`backend/app/services/task_service.py`
- 当前 CLI 入口：`main.py`
- 翻译总控：`src/agents/coordinator_agent.py`
- LaTeX 下载/解压工具：`src/formats/latex/utils.py`

## 8. 接手建议结论

结论很明确：

- 当前已经不是“从零开始”
- 现在最值得做的是把“schema 骨架”推进到“真实可落库、可执行、可归档”的后端 MVP

最建议下一个 agent 直接执行的工作顺序是：

1. 先完成 Alembic 和 MySQL 建表
2. 再把 `POST /api/tasks` 接到后台 runner
3. 再抽出可复用的翻译 pipeline service
4. 再补 MinIO 归档
5. 最后补上传和测试

如果时间只够做一件事，优先做：

- Alembic + MySQL 真正落库

因为这是后续所有联调和任务执行的基础。
