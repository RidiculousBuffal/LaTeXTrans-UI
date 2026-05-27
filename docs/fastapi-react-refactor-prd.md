# LaTeXTrans 命令行版改造为 FastAPI + React 前后端分离版 PRD

## 1. Executive Summary

- **Problem Statement**: 当前项目以命令行方式运行，核心入口是 `main.py`，适合单人本地执行，但不适合团队内部统一部署、任务归档、任务进度可视化和历史记录检索。现有 `src/UI/UI.py` 是直接耦合 Python 工作流的 Streamlit 界面，不符合本次“前后端分离且不使用 Streamlit”的目标。
- **Proposed Solution**: 将现有 LaTeX 翻译流水线改造为“React 前端 + FastAPI 后端 + MySQL + MinIO”的团队内部系统。保留当前 Python 翻译核心能力，将其封装为后端任务服务，新增任务管理、文件归档、进度追踪、历史记录查询和结果预览能力。
- **Success Criteria**:
  - 团队用户可通过 Web UI 创建翻译任务，并完成从提交到结果下载的完整流程，成功率达到 `>= 95%`。
  - 每个任务必须有明确状态流转，前端可见进度更新延迟不超过 `5s`。
  - 任务产生的输入源文件和翻译产物必须完成归档，归档完整率达到 `100%`。
  - runtime 调试日志和原始运行元数据默认仅保留在后端本地工作目录，不作为对外可下载 artifacts。
  - 用户可按任务名、arXiv ID、状态、创建时间查询历史记录，常规查询响应时间在 `2s` 内。
  - 新系统上线后，现有 CLI 翻译能力保持可用，作为回归验证和应急兜底入口。

## 2. User Experience & Functionality

### User Personas

- **团队研究人员/工程师**: 需要提交论文翻译任务，查看执行进度，下载翻译后的 PDF 和中间产物。
- **项目维护者/管理员**: 需要定位失败任务、查看状态事件与错误摘要、管理归档文件、验证服务运行状态。
- **内部协作者**: 需要复用历史翻译结果，避免重复提交相同论文任务。

### User Stories

- **Story 1**: 作为团队用户，我希望通过网页提交 arXiv ID 或上传 LaTeX 源文件，从而不再依赖本地命令行环境。
- **Story 2**: 作为团队用户，我希望实时看到任务状态和阶段进度，从而知道当前卡在哪个步骤。
- **Story 3**: 作为团队用户，我希望系统自动归档源文件和翻译结果，从而便于后续追溯和复用。
- **Story 4**: 作为团队用户，我希望浏览和检索历史记录，从而快速找到之前的翻译结果。
- **Story 5**: 作为维护者，我希望查看失败原因和结构化日志，从而更快定位编译失败、模型调用失败或输入异常。

### Acceptance Criteria

- **For Story 1**
  - 支持通过 Web 表单提交 `arXiv ID`。
  - 支持上传本地 LaTeX 源文件压缩包，作为后续迭代能力的兼容入口。
  - 提交任务时可配置基础参数，如源语言、目标语言、模型、输出命名。
  - 提交成功后立即返回任务 ID，并进入任务详情页。

- **For Story 2**
  - 任务状态至少包含 `PENDING`、`DOWNLOADING`、`PARSING`、`TRANSLATING`、`VALIDATING`、`GENERATING`、`SUCCEEDED`、`FAILED`、`CANCELED`。
  - 前端任务详情页必须展示当前阶段、阶段说明、开始时间、最近更新时间和错误摘要。
  - 任务列表页必须支持按状态筛选，并展示最近任务。
  - 前端进度刷新可通过轮询实现，MVP 不强制要求 WebSocket。

- **For Story 3**
  - 每个任务必须保存结构化任务记录到 MySQL。
  - 每个任务必须将源文件、翻译后的 LaTeX 工程、最终 PDF 上传到 MinIO。
  - 任务详情页必须提供归档产物下载入口。
  - 系统必须记录文件对象路径、版本信息和上传时间。
  - `task.log`、`task-config.json`、`task-events.jsonl` 这类 runtime 文件默认只保留在后端本地工作目录，不作为 artifacts 下载。

- **For Story 4**
  - 历史任务列表支持按 `arXiv ID`、任务状态、提交人、时间范围检索。
  - 用户可以进入任务详情页查看任务参数、状态时间线和最终产物。
  - 系统对同一 `arXiv ID` 的历史任务提供聚合展示。

- **For Story 5**
  - 失败任务必须展示失败阶段和异常摘要。
  - 后端必须记录结构化日志，便于后续接入日志平台。
  - 管理员可通过接口查询最近失败任务和失败类型分布。

### Non-Goals

- 本期不保留 Streamlit 作为正式产品界面。
- 本期不重写核心翻译算法，不改变 `CoordinatorAgent` 主导的翻译能力本身。
- 本期不做复杂权限系统，如多角色审批流、细粒度 RBAC。
- 本期不做全文协作编辑器，不支持在线修改 LaTeX 内容后实时再编译。
- 本期不做大规模多租户 SaaS 化能力，目标是团队内部部署。

## 3. AI System Requirements

### Tool Requirements

- 继续复用当前 Python 翻译流水线：
  - `main.py`
  - `src/agents/coordinator_agent.py`
  - `ParserAgent`
  - `TranslatorAgent`
  - `ValidatorAgent`
  - `GeneratorAgent`
- 后端需将现有同步/命令式流程封装为可被任务系统调用的服务层。
- 后端需要具备以下基础组件：
  - FastAPI REST API
  - 后台任务执行器
  - MySQL 持久化
  - MinIO 文件归档
  - 结构化日志
- 前端需要具备以下基础页面：
  - 登录后首页或任务工作台
  - 创建任务页
  - 任务列表页
  - 任务详情页
  - 历史归档页

### Evaluation Strategy

- **功能正确性**
  - 选取不少于 `10` 篇真实论文样本，覆盖 arXiv 下载、源文件解压、翻译、校验、编译、归档全链路。
  - 验证任务状态是否完整流转，最终产物是否与数据库记录和对象存储记录一致。

- **归档正确性**
  - 抽样核对数据库中的任务记录、MinIO 中的对象路径和页面展示是否一致。
  - 验证失败任务仍能保留必要的状态事件、错误摘要和可交付产物索引。

- **可用性**
  - 让至少 `3` 位内部用户完成一次从提交到下载的端到端试用。
  - 核验用户无需接触命令行即可完成常见操作。

- **稳定性**
  - 连续执行批量任务，观察任务状态一致性、文件上传成功率和失败重试表现。
  - 验证任务执行过程中服务重启后的恢复策略是否可接受。

## 4. Technical Specifications

### Architecture Overview

当前项目的真实工作流是：

`main.py -> 读取 config/.env -> 下载/解压 TeX -> CoordinatorAgent -> Parser -> Translator -> Validator -> Generator -> 输出 PDF`

目标改造后的推荐架构是：

`React Web App -> FastAPI API -> Task Service -> Translation Worker -> MySQL + MinIO`

建议拆分如下：

- **Frontend (React)**
  - 负责任务创建、任务列表、任务详情、历史记录、结果下载和基础可视化。
  - 不直接接触翻译核心逻辑，只通过 HTTP API 获取和提交数据。

- **Backend API (FastAPI)**
  - 提供任务创建、查询、取消、重试、下载地址生成等接口。
  - 负责参数校验、任务状态管理、鉴权接入点、归档元数据管理。

- **Task Runner / Worker**
  - 负责实际调用当前 Python 翻译流水线。
  - 将现有 `CoordinatorAgent.workflow_latextrans()` 封装为可观测的任务执行单元。
  - 在关键节点写入任务状态和阶段进度。

- **MySQL**
  - 保存任务主记录、状态流转、参数快照、错误信息、产物元数据、操作审计字段。

- **MinIO**
  - 保存原始输入、解压后的源文件、翻译后的工程目录、PDF 和必要的中间产物索引。

### Recommended Module Boundaries

- **保留现有领域能力**
  - `src/agents/*`
  - `src/formats/latex/*`

- **新增后端模块建议**
  - `backend/app/main.py`
  - `backend/app/api/`
  - `backend/app/services/task_service.py`
  - `backend/app/services/translation_service.py`
  - `backend/app/services/storage_service.py`
  - `backend/app/services/archive_service.py`
  - `backend/app/repositories/`
  - `backend/app/models/`
  - `backend/app/schemas/`
  - `backend/app/workers/`

- **新增前端模块建议**
  - `frontend/src/pages/TasksPage.tsx`
  - `frontend/src/pages/TaskDetailPage.tsx`
  - `frontend/src/pages/NewTaskPage.tsx`
  - `frontend/src/pages/ArchivesPage.tsx`
  - `frontend/src/components/StatusBadge.tsx`
  - `frontend/src/components/ProgressTimeline.tsx`
  - `frontend/src/services/api.ts`

### Recommended Tech Stack & Packages

以下技术栈是面向“团队内部部署 + 长任务执行 + 归档 + 进度可视化”这一目标的推荐组合，且尽量与当前 Python 代码结构保持兼容。

#### Backend Recommended Stack

- **Python Runtime**
  - 建议继续使用当前 Python 技术栈，新增独立 `backend/` 目录承载 FastAPI 服务。

- **Web API**
  - `fastapi`
  - `uvicorn`
  - 用途：提供 REST API、OpenAPI 文档、参数校验和服务启动能力。

- **Configuration**
  - `pydantic`
  - `pydantic-settings`
  - `python-dotenv`
  - 用途：统一管理 `.env`、服务配置、数据库和对象存储连接配置。

- **Database**
  - `sqlalchemy`
  - `alembic`
  - `pymysql`
  - 用途：管理 MySQL 持久化、模型映射和数据库迁移。
  - 说明：MVP 建议优先采用 `SQLAlchemy + PyMySQL` 的同步方案，先降低复杂度；后续若确实有高并发压力，再评估全异步驱动。

- **Object Storage**
  - `minio`
  - 用途：上传和下载源文件、PDF、日志、翻译工程和中间产物。

- **File Upload / Download**
  - `python-multipart`
  - 用途：支持前端上传压缩包和表单文件。

- **HTTP / External Calls**
  - `httpx`
  - 用途：调用外部服务、健康检查、后续统一封装内部 HTTP 访问。

- **Task Execution**
  - `concurrent.futures` 或独立 worker 进程
  - `celery` + `redis` 作为后续增强
  - 用途：执行长耗时翻译任务，避免阻塞 API 请求线程。
  - 说明：MVP 可先用“API 服务 + 本地任务执行器/独立 worker 进程”打通闭环；如果团队并发任务变多，再升级为 `Celery + Redis + Worker`。

- **Retry / Resilience**
  - `tenacity`
  - 用途：为 MinIO 上传、外部下载、部分可重试步骤提供退避重试。

- **Logging**
  - `python-json-logger`
  - 用途：输出结构化 JSON 日志，便于后续接入日志平台。

- **Testing**
  - `pytest`
  - `pytest-asyncio`
  - `httpx`
  - 用途：接口测试、服务测试、异步流程测试。

#### Frontend Recommended Stack

- **Framework**
  - `react`
  - `react-dom`
  - `typescript`
  - 用途：构建前端页面和类型安全的数据交互层。

- **Build Tool**
  - `vite`
  - 用途：本地开发、生产构建、前后端分离静态资源打包。
  - 说明：新项目不建议使用已废弃的 CRA 路线，建议直接以 `React + TypeScript + Vite` 起步。

- **Routing**
  - `react-router-dom`
  - 用途：任务列表、详情、创建页、归档页等多页面路由管理。

- **Server State / Polling**
  - `@tanstack/react-query`
  - 用途：任务列表获取、任务详情缓存、5 秒轮询任务状态、重试和失效刷新。

- **HTTP Client**
  - `axios`
  - 用途：统一封装 API 请求、超时、错误处理和下载接口。

- **UI Component Library**
  - `shadcn/ui`
  - `tailwindcss`
  - `@tailwindcss/vite`
  - 用途：构建可定制的任务系统 UI，包括表格、表单、弹层、时间线、上传区和状态展示组件。
  - 说明：前端采用 `shadcn/ui` 更适合这类需要长期维护和按业务深度定制的内部系统，组件源码直接进入项目，也更利于后续沉淀自己的设计系统。

- **Forms**
  - `react-hook-form`
  - `zod`
  - `@hookform/resolvers`
  - 用途：实现新建任务表单、参数校验、上传表单和错误提示。

- **Feedback**
  - `sonner`
  - 用途：统一处理提交成功、失败提示和后台任务反馈消息。

- **Charts / Visualization**
  - `recharts`
  - 用途：展示任务状态分布、近期成功率、失败趋势等基础统计图表。
  - 说明：`shadcn/ui` 的图表能力通常与 `recharts` 配合使用；如果首版只做表格和时间线，图表可以延后到 `v1.1`。

- **Utilities**
  - `dayjs`
  - `clsx`
  - 用途：时间格式化、样式类名组织、前端常用工具能力。

- **Testing**
  - `vitest`
  - `@testing-library/react`
  - `@testing-library/jest-dom`
  - `playwright`
  - 用途：组件测试、页面交互测试和前端端到端测试。

#### Suggested Backend Dependency Groups

- **MVP Required**
  - `fastapi`
  - `uvicorn`
  - `pydantic`
  - `pydantic-settings`
  - `sqlalchemy`
  - `alembic`
  - `pymysql`
  - `minio`
  - `python-multipart`
  - `python-dotenv`
  - `httpx`
  - `tenacity`
  - `python-json-logger`

- **MVP Test**
  - `pytest`
  - `pytest-asyncio`

- **v1.1 Optional Enhancement**
  - `celery`
  - `redis`

#### Suggested Frontend Dependency Groups

- **MVP Required**
  - `react`
  - `react-dom`
  - `typescript`
  - `vite`
  - `react-router-dom`
  - `@tanstack/react-query`
  - `axios`
  - `tailwindcss`
  - `@tailwindcss/vite`
  - `react-hook-form`
  - `zod`
  - `@hookform/resolvers`
  - `sonner`
  - `dayjs`
  - `clsx`

- **v1.1 Optional Enhancement**
  - `recharts`

- **Test / QA**
  - `vitest`
  - `@testing-library/react`
  - `@testing-library/jest-dom`
  - `playwright`

#### Suggested Bootstrap Commands

- **Backend**
  - `pip install fastapi uvicorn sqlalchemy alembic pymysql minio python-multipart pydantic-settings python-dotenv httpx tenacity python-json-logger pytest pytest-asyncio`

- **Frontend**
  - `npm create vite@latest frontend -- --template react-ts`
  - `npm install tailwindcss @tailwindcss/vite react-router-dom @tanstack/react-query axios react-hook-form zod @hookform/resolvers sonner dayjs clsx`
  - `npx shadcn@latest init -t vite`
  - `npx shadcn@latest add button card input textarea label select table badge dialog sheet tabs form sonner skeleton progress separator alert`
  - `npm install -D vitest @testing-library/react @testing-library/jest-dom playwright`

#### Suggested Initial shadcn/ui Components

- `button`
- `card`
- `input`
- `textarea`
- `label`
- `select`
- `table`
- `badge`
- `dialog`
- `sheet`
- `tabs`
- `form`
- `sonner`
- `skeleton`
- `progress`
- `separator`
- `alert`

这些组件基本可以覆盖当前项目首版页面所需的任务列表、任务详情、状态展示、表单提交、弹层、通知和加载态。

### Core Data Flow

1. 用户在 React 页面提交 `arXiv ID` 或源文件。
2. FastAPI 创建任务记录，状态设为 `PENDING`。
3. 后端将任务分发给 Worker 执行。
4. Worker 下载或接收输入文件，上传原始文件到 MinIO，并更新任务状态为 `DOWNLOADING`。
5. Worker 调用当前 LaTeXTrans 翻译流程，按阶段更新状态为 `PARSING`、`TRANSLATING`、`VALIDATING`、`GENERATING`。
6. 任务成功后，将 PDF、翻译工程和可交付中间产物上传到 MinIO，写入 MySQL 元数据，状态置为 `SUCCEEDED`。
7. 若任务失败，写入错误摘要与结构化事件，状态置为 `FAILED`。
8. React 轮询任务详情接口并展示进度、历史和下载入口。

### Suggested MVP API Surface

- `POST /api/tasks`
  - 创建翻译任务
- `GET /api/tasks`
  - 查询任务列表，支持分页和筛选
- `GET /api/tasks/{task_id}`
  - 查询任务详情
- `POST /api/tasks/{task_id}/retry`
  - 重试失败任务
- `POST /api/tasks/{task_id}/cancel`
  - 取消任务
- `GET /api/tasks/{task_id}/artifacts`
  - 查看归档产物列表
- `GET /api/tasks/{task_id}/logs`
  - 查看或下载日志
- `GET /api/archives`
  - 历史归档检索

### Suggested Data Model

- **translation_tasks**
  - `id`
  - `task_name`
  - `source_type`
  - `arxiv_id`
  - `source_language`
  - `target_language`
  - `model_name`
  - `status`
  - `current_stage`
  - `progress_percent`
  - `error_message`
  - `created_by`
  - `created_at`
  - `started_at`
  - `finished_at`

- **task_artifacts**
  - `id`
  - `task_id`
  - `artifact_type`
  - `object_key`
  - `file_name`
  - `content_type`
  - `file_size`
  - `created_at`

- **task_events**
  - `id`
  - `task_id`
  - `stage`
  - `status`
  - `message`
  - `created_at`

- **task_configs**
  - `id`
  - `task_id`
  - `config_snapshot_json`
  - `env_profile`
  - `created_at`

### Integration Points

- **LLM 配置**
  - 当前 `main.py` 已从 `.env` 读取 `OPENAI_MODEL`、`OPENAI_BASE_URL`、`OPENAI_API_KEY`。
  - 改造后建议由 FastAPI 统一读取后端环境配置，不再由前端直接传递敏感密钥。

- **MySQL**
  - 用于存储任务、事件、归档索引、配置快照。
  - 建议后端使用统一 ORM 或 SQLModel/SQLAlchemy 管理。

- **MinIO**
  - 用于保存源文件、输出 PDF、翻译工程和必要中间文件。
  - 建议按 `task_id/artifact_type/...` 组织对象路径。

- **Auth**
  - 本期作为团队内部系统，建议预留统一登录接入点。
  - MVP 可先支持最小鉴权方案，例如反向代理统一鉴权或简单会话登录。
  - 若上线窗口紧，本期可先实现“仅内网访问 + 审计字段预留”，并在后续版本补强。

### Suggested Frontend Pages

- **任务工作台**
  - 展示最近任务、状态分布、失败任务提醒。

- **新建任务页**
  - 支持填写 `arXiv ID`、选择语言、模型和上传源文件。

- **任务列表页**
  - 使用表格展示任务状态、创建时间、执行耗时和操作入口。

- **任务详情页**
  - 展示状态时间线、当前阶段、错误摘要和归档下载列表。

- **历史归档页**
  - 支持按 `arXiv ID`、状态、时间范围筛选和查看历史结果。

### Security & Privacy

- 前端不得暴露模型 API Key、MinIO Secret、数据库凭据。
- 后端必须通过环境变量读取敏感配置，禁止将密钥写入前端构建产物或任务记录明文。
- 文件下载建议采用临时签名 URL 或后端代理下载，避免暴露对象存储内部路径。
- 日志中应避免打印敏感凭据和完整密钥；默认也不对前端开放 runtime 日志下载。
- 对上传文件类型、压缩包解压路径和文件大小做安全限制，避免路径穿越和超大文件风险。

### Key Refactor Notes Based on Current Code

- 当前 `main.py` 同时承担参数解析、配置加载、下载/解压、任务循环和执行入口，后续应拆成“CLI 入口”和“可复用服务层”。
- 当前 `CoordinatorAgent` 已天然适合作为后端任务执行核心，但需要补充任务事件回调或状态上报接口。
- 当前 Streamlit UI 直接写配置文件并直接调用 Python 逻辑，这种模式不适合多用户部署，后续只作为参考，不作为目标架构保留。
- 当前输出以本地目录为中心，后续需要增加“本地工作目录 + MinIO 归档 + MySQL 元数据”的统一归档流程。

## 5. Risks & Roadmap

### Phased Rollout

- **MVP**
  - 建立 FastAPI 后端骨架与 React 前端骨架。
  - 支持创建任务、查看任务列表、查看任务详情。
  - 接入 MySQL 保存任务记录。
  - 接入 MinIO 保存最终 PDF 和原始输入。
  - 封装现有 `CoordinatorAgent` 为后端任务执行入口。
  - 使用轮询实现进度可视化。

- **v1.1**
  - 增加任务事件时间线和失败重试。
  - 增加更完整的归档产物下载能力，包括中间 JSON 和翻译工程目录。
  - 增加历史记录高级筛选和相同 arXiv ID 聚合展示。
  - 增加任务取消和基础并发控制。

- **v2.0**
  - 增加统一登录与权限控制。
  - 增加消息通知能力，如任务完成通知。
  - 增加任务去重、结果复用、缓存命中策略。
  - 增加更细粒度监控、告警和报表统计。

### Technical Risks

- **现有流程可观测性不足**
  - 当前核心流程偏脚本式执行，缺少标准化事件回调，改造时需要补任务状态埋点。

- **长任务执行与服务解耦风险**
  - 翻译任务天然是长耗时操作，不能直接挂在同步 HTTP 请求里，必须通过后台任务或独立 Worker 执行。

- **文件归档体积和一致性风险**
  - 翻译工程、中间文件、PDF 和日志较多，若只在任务结束后统一上传，失败场景下可能出现归档不完整。

- **失败恢复复杂度**
  - 下载失败、模型调用失败、LaTeX 编译失败和对象存储上传失败的恢复策略不同，需要明确阶段性重试边界。

- **前后端改造期间兼容性风险**
  - 若过早改动核心翻译逻辑，可能影响现有 CLI 使用体验。建议先做外层封装，再逐步内聚。

### Open Questions / TBD

- 是否需要首版就支持“上传本地压缩包”与“arXiv ID”双入口同时上线。
- 是否需要对重复 `arXiv ID` 做任务去重或结果复用。
- 团队内部登录体系是否已有现成 SSO，可供 FastAPI/前端后续接入。
- Worker 执行方式是采用 FastAPI 后台任务、Celery，还是独立进程任务队列，需要结合部署方式最终确定。

## Recommended Next Step

建议按以下顺序推进实施文档和代码改造：

1. 先补一份系统改造设计文档，明确目录结构、任务状态机、MySQL 表设计和 MinIO 对象路径规范。
2. 将当前 `main.py` 中的执行流程提炼为可复用服务层，保留 CLI 入口不变。
3. 搭建 FastAPI 后端骨架，先打通“创建任务 -> 执行任务 -> 查询任务”的最小闭环。
4. 搭建 React 前端骨架，先完成任务列表页、创建页和详情页。
5. 最后再补归档增强、重试、取消、鉴权和监控。
