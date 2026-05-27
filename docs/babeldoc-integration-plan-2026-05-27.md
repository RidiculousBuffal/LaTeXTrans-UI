# BabelDOC PDF 翻译接入计划

更新时间：2026-05-27

## 1. 背景

当前 `latex_trans_prod` 已基本完成 LaTeX 翻译主链路的后端任务化和前端页面化，现有系统已经具备以下能力：

- FastAPI 后端任务系统
- MySQL 任务记录、事件记录、配置快照持久化
- MinIO 产物归档与预签名下载
- React + shadcn/ui 前端任务创建、任务列表、任务详情、归档页面
- LaTeX 翻译任务的异步执行和状态追踪

目前系统只覆盖两类输入：

- `arxiv`，由后端下载论文源码
- `upload`，由用户上传 LaTeX 源码压缩包

而新的业务目标是将 [BabelDOC](https://github.com/funstory-ai/BabelDOC) 的 PDF 翻译能力也纳入现有系统，使用户除了 LaTeX 翻译外，还可以直接上传 PDF 并发起翻译任务。

## 2. 目标

本次接入的目标是：

- 在不破坏现有 LaTeX 翻译链路的前提下，新增 BabelDOC PDF 翻译能力
- 将 BabelDOC 纳入统一的任务系统、归档系统和前端任务视图
- 让前端用户可以通过 Web 页面提交 PDF 翻译任务、查看进度、下载产物
- 保持 CLI 本地翻译方式仍可独立使用，作为调试和兜底入口

## 3. 范围

### 3.1 本期范围

- 新增 BabelDOC 任务类型
- 支持上传单个 PDF 文件并创建翻译任务
- 在后端使用受控 CLI 子进程调用 BabelDOC
- 归档输入 PDF、翻译后 PDF、日志、运行元数据
- 在前端新增 PDF 翻译任务创建入口
- 在任务详情页展示 BabelDOC 任务的状态、日志和产物

### 3.2 本期不做

- 不改写 BabelDOC 内部实现
- 不直接绑定 BabelDOC 的内部 Python API 作为稳定依赖
- 不做多文件批量 PDF 提交
- 不做 PDF 在线预览器
- 不做 BabelDOC 高级参数的全量前端开放
- 不改变现有 LaTeX 任务的提交和运行方式

## 4. 关键设计决策

### 4.1 BabelDOC 采用 CLI 引擎接入，而不是内部 Python API

建议将 BabelDOC 作为受控子进程调用，理由如下：

- 当前用户已经在本地通过 `babeldoc ...` 命令稳定使用该能力
- CLI 方式最贴近已有使用习惯和真实运行路径
- 可以将 BabelDOC 与当前 FastAPI 服务进程解耦，降低 import 级别耦合风险
- 后续如果 BabelDOC 内部 API 变化，CLI 封装层更容易隔离影响

因此，MVP 推荐实现为：

`FastAPI Task Runner -> BabelDOC CLI subprocess -> runtime 目录 -> MinIO 归档`

### 4.2 在任务模型中引入 `engine`

当前任务模型主要按 `source_type` 区分输入来源，但 BabelDOC 和现有 LaTeX 翻译本质上是两套执行引擎。仅靠 `source_type` 难以清晰表达执行路径，因此建议新增任务引擎字段：

- `latex`
- `babeldoc`

同时保留输入来源字段，用于区分任务来源：

- `arxiv`
- `upload`
- `pdf_upload`

这样可以形成清晰组合：

- `engine=latex, source_type=arxiv`
- `engine=latex, source_type=upload`
- `engine=babeldoc, source_type=pdf_upload`

### 4.3 统一复用现有任务生命周期

建议 BabelDOC 任务继续复用现有通用任务状态枚举：

- `PENDING`
- `DOWNLOADING`
- `PARSING`
- `TRANSLATING`
- `VALIDATING`
- `GENERATING`
- `SUCCEEDED`
- `FAILED`
- `CANCELED`

说明：

- 对 BabelDOC 任务，`DOWNLOADING` 一般不会使用
- `PARSING` 可表示“校验 PDF / 准备运行目录 / 组装命令”
- `TRANSLATING` 表示 BabelDOC 正在执行
- `VALIDATING` 表示校验输出文件是否生成
- `GENERATING` 表示归档产物和登记 artifact

这样可以最大限度减少前端状态枚举和任务列表逻辑改动。

## 5. 现状对齐

结合当前仓库实现，现有结构已经适合承接 BabelDOC：

- `backend/app/services/task_service.py`
  - 负责创建任务、创建上传任务、查询任务、取消、重试
- `backend/app/workers/translation_runner.py`
  - 负责线程池提交与实际任务执行
- `backend/app/services/translation_service.py`
  - 负责构造配置快照和 runtime 目录
- `backend/app/services/storage_service.py`
  - 负责 MinIO 归档和下载地址生成
- `frontend/src/pages/new-task-page.tsx`
  - 当前只有 `arxiv` 和 `upload` 两个 tab

因此，本次接入不需要推翻现有结构，而是沿着当前任务系统继续扩展。

## 6. 后端改造方案

### 6.1 数据模型改造

建议对任务模型做如下扩展。

#### `TranslationTask`

新增字段：

- `engine`: `latex | babeldoc`

调整枚举：

- `TaskSourceType`
  - 保留 `arxiv`
  - 保留 `upload`
  - 新增 `pdf_upload`

建议默认规则：

- 现有创建 LaTeX 任务接口默认 `engine=latex`
- 新增 PDF 任务接口默认 `engine=babeldoc`

#### `TaskArtifactType`

建议新增或细化以下 artifact 类型：

- `SOURCE_PDF`
- `TRANSLATED_PDF`
- `BABELDOC_OUTPUT`

保留已有通用类型：

- `LOG`
- `METADATA`

说明：

- `SOURCE_PDF` 用于归档原始上传 PDF
- `TRANSLATED_PDF` 用于归档翻译后的最终 PDF
- `BABELDOC_OUTPUT` 用于归档 BabelDOC 运行输出目录或其打包压缩产物

#### `TaskConfig`

`config_snapshot_json` 建议新增 BabelDOC 专属配置快照，例如：

```json
{
  "engine": "babeldoc",
  "source_type": "pdf_upload",
  "source_file_name": "paper.pdf",
  "target_language": "zh",
  "runtime": {
    "task_id": "uuid"
  },
  "babeldoc": {
    "binary": "babeldoc",
    "qps": 20,
    "pool_max_workers": 20,
    "openai_model": "reuse backend OPENAI_MODEL",
    "openai_base_url": "reuse backend OPENAI_BASE_URL"
  }
}
```

注意：

- `api_key` 不建议原样回写进任务快照
- 如需记录，可仅保留来源信息或是否配置成功的布尔标记

### 6.2 配置层改造

建议在 `backend/app/core/config.py` 中只新增 BabelDOC 的运行参数，不单独新增一套 OpenAI 凭据配置。

建议新增：

- `babeldoc_bin`
- `babeldoc_qps`
- `babeldoc_pool_max_workers`
- `babeldoc_output_subdir`

建议默认命名示例：

- `BABELDOC_BIN=babeldoc`
- `BABELDOC_QPS=20`
- `BABELDOC_POOL_MAX_WORKERS=20`

OpenAI 相关配置直接复用现有后端 settings，从 `.env` 读取即可：

- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`

也就是说，BabelDOC 最终命令中的以下参数由现有后端配置提供：

- `--openai-model`
- `--openai-base-url`
- `--openai-api-key`

设计原则：

- BabelDOC 复用现有 LaTeX 流程的 OpenAI 配置来源
- 避免维护两套模型与密钥配置
- 避免前端直接传密钥
- 避免把 CLI 参数硬编码在代码里

### 6.3 服务层新增职责

建议新增以下服务文件：

- `backend/app/services/babeldoc_service.py`
- `backend/app/services/babeldoc_command_builder.py`

职责建议如下。

#### `BabelDocService`

负责：

- 校验上传 PDF
- 构造 BabelDOC 运行目录
- 生成 CLI 命令参数
- 执行子进程
- 解析输出目录
- 定位翻译后 PDF

#### `babeldoc_command_builder`

负责：

- 将系统配置和任务配置拼成最终命令
- 统一做参数转义和列表化，避免直接拼接 shell 字符串

命令构建示意：

```python
[
    "babeldoc",
    "--openai",
    "--qps", "20",
    "--pool-max-workers", "20",
    "--openai-model", "...",
    "--openai-base-url", "...",
    "--openai-api-key", "...",
    "--files", "/abs/path/input.pdf",
    "--output", "/abs/path/output",
]
```

### 6.4 Worker 调度改造

当前 `translation_runner.py` 只包含 LaTeX 执行路径，建议改为按 `engine` 分发：

- `engine=latex` -> 走现有 LaTeX pipeline
- `engine=babeldoc` -> 走 BabelDOC runner

推荐结构：

- `submit_task(task_id)` 保持不变
- `_run_task(...)` 中读取 task.engine
- 将执行逻辑拆分为：
  - `_run_latex_task(...)`
  - `_run_babeldoc_task(...)`

这样可以保证：

- 队列和线程池逻辑不变
- 失败处理、取消、最终归档逻辑尽量复用
- 代码结构比单文件堆叠分支更清晰

### 6.5 BabelDOC 运行目录约定

建议沿用当前任务 runtime 结构，在每个任务工作区内创建：

- `workspace/`
- `workspace/sources/`
- `workspace/runtime/`
- `workspace/output/`

对 BabelDOC 任务建议具体约定：

- 上传 PDF 存在 `workspace/sources/<original_name>.pdf`
- BabelDOC 输出目录使用 `workspace/output/babeldoc/`
- 标准日志落在 `workspace/runtime/task.log`
- 命令参数快照落在 `workspace/runtime/task-config.json`
- 事件流落在 `workspace/runtime/task-events.jsonl`

### 6.6 状态与事件设计

建议 BabelDOC 任务至少写入以下事件：

1. `PENDING`
   - Task created and queued.
2. `PARSING`
   - PDF uploaded and runtime prepared.
3. `TRANSLATING`
   - BabelDOC process started.
4. `VALIDATING`
   - Checking translated PDF outputs.
5. `GENERATING`
   - Registering artifacts and upload records.
6. `SUCCEEDED` 或 `FAILED`

建议将以下信息写入 `details_json`：

- 输入文件名
- 命令路径
- 输出目录
- 生成文件列表
- 失败时的退出码

### 6.7 失败处理

BabelDOC 接入后，失败来源主要会新增以下几类：

- PDF 文件格式异常
- BabelDOC 可执行文件不存在
- OpenAI 接口配置错误
- 子进程返回非零退出码
- 输出目录存在但未生成最终 PDF

建议在 `error_message` 中保留简洁错误摘要，在 `task.log` 中保留完整 stderr/stdout。

失败分类建议：

- `INPUT_ERROR`
- `BABELDOC_BOOT_ERROR`
- `BABELDOC_PROCESS_ERROR`
- `OUTPUT_VALIDATION_ERROR`
- `STORAGE_ERROR`

### 6.8 取消能力

当前系统已支持任务取消，但 BabelDOC 任务若已进入子进程执行，仅修改数据库状态还不够。

MVP 阶段建议：

- 先保持与当前系统一致的“软取消”能力
- worker 在进入关键阶段前检查取消状态
- 子进程启动后，先不实现强杀进程

增强阶段可考虑：

- 记录 `subprocess.Popen` 句柄
- 在检测到取消时终止 BabelDOC 子进程

## 7. API 改造方案

### 7.1 推荐新增独立接口

建议新增：

- `POST /api/tasks/pdf`

而不是直接复用现有 `POST /api/tasks/upload`，原因如下：

- 语义更清晰
- 便于与 LaTeX archive upload 区分
- 更适合后续扩展 BabelDOC 参数
- 前端和后端校验逻辑更容易维护

### 7.2 请求参数建议

表单字段建议如下：

- `file`: 必填，只允许 `.pdf`
- `task_name`: 可选
- `target_language`: 可选，默认 `zh`
- `model_name`: 可选，默认后端配置
- `created_by`: 可选
- `env_profile`: 可选，默认 `default`
- `options`: 可选，字符串化 JSON

其中 `options` MVP 先只开放少量字段，例如：

- `qps`
- `pool_max_workers`

### 7.3 响应结构

建议复用现有 `TaskDetailResponse`，只是在返回中包含：

- `engine=babeldoc`
- `source_type=pdf_upload`

这样前端现有任务详情页和任务列表页可以最小成本支持新任务。

## 8. 前端改造方案

### 8.1 新建任务页

当前 `frontend/src/pages/new-task-page.tsx` 有两个入口：

- `arxiv`
- `upload`

建议新增第三个 tab：

- `pdf`

页面文案建议：

- 标题仍保留 “Create a translation task”
- 新增说明 “Upload a PDF and run BabelDOC translation”

### 8.2 PDF 表单字段

MVP 页面字段建议保持最简：

- PDF 文件
- 可选任务名

其余参数先由后端默认值填充，避免前端表单一开始过重。

后续可逐步开放：

- 目标语言
- 模型名称
- 并发参数

### 8.3 类型定义

需要调整：

- `frontend/src/lib/types.ts`

建议新增：

- `TaskEngine = "latex" | "babeldoc"`
- `SourceType` 增加 `"pdf_upload"`

同时需要更新：

- `CreatePdfTaskPayload`

### 8.4 API 封装

需要调整：

- `frontend/src/lib/api.ts`

建议新增：

- `createPdfTask(payload)`

使用 `multipart/form-data` 调用：

- `POST /api/tasks/pdf`

### 8.5 任务列表与详情页展示

建议新增以下轻量展示：

- 在任务列表中展示 `engine`
- 在任务详情中展示任务引擎和输入类型
- BabelDOC 任务若没有 LaTeX 工程产物，不强求与 LaTeX 页面完全一致

任务详情页重点展示：

- 原始 PDF
- 翻译后 PDF
- 日志文件
- 输出目录压缩包

## 9. 数据库迁移建议

建议新增一版 Alembic migration，完成以下变更：

1. `translation_tasks` 增加 `engine` 字段
2. `task_artifacts.artifact_type` 枚举增加 PDF 相关类型
3. 如有必要，为 `engine + created_at` 增加索引

兼容策略：

- 历史任务统一补默认值 `engine=latex`

## 10. 安全与配置要求

### 10.1 不要在代码或文档中硬编码 API Key

你当前本地 shell 函数里包含 `--openai-api-key` 明文参数。接入系统后，不建议继续沿用这种方式。

建议改为：

- BabelDOC 与现有 LaTeX 任务统一通过后端 `.env` 读取同一套 OpenAI 配置
- 仅后端进程持有密钥
- 前端不展示也不传递密钥

### 10.2 命令执行安全

建议：

- 使用 `subprocess.run([...], shell=False)` 或 `Popen([...], shell=False)`
- 不直接拼接 shell 字符串
- 对输入文件路径和输出目录使用绝对路径

### 10.3 上传限制

建议：

- 限制只允许单个 PDF
- 校验 MIME 与扩展名
- 使用现有 `max_upload_bytes` 做大小约束

## 11. 测试计划

### 11.1 后端单元测试

建议新增测试覆盖：

- PDF 上传文件校验
- BabelDOC 命令构造
- engine 路由分发
- 运行失败时的状态写入
- 输出文件缺失时的失败处理

### 11.2 后端集成测试

建议通过 mock subprocess 的方式验证：

- 成功任务可进入 `SUCCEEDED`
- 失败任务可进入 `FAILED`
- artifacts 可被正确登记

### 11.3 前端测试

建议至少验证：

- 新建任务页 PDF tab 可提交
- API 错误 toast 正常显示
- 任务详情页可展示 BabelDOC 任务基础信息

### 11.4 人工联调

建议至少准备一份真实 PDF，完成如下验证：

1. 从前端上传 PDF
2. 后端成功创建任务
3. worker 运行 BabelDOC
4. 前端轮询看到状态变化
5. 最终下载翻译后 PDF
6. 归档页可看到该任务

## 12. 开发顺序

建议按以下顺序实施：

### 阶段 1：文档和接口设计

- 明确任务模型变更
- 明确 API 设计
- 明确产物归档类型

### 阶段 2：后端最小可运行接入

- 增加 `engine`
- 增加 `pdf_upload`
- 增加 `POST /api/tasks/pdf`
- 增加 BabelDOC CLI runner
- 完成 runtime 日志与 artifact 归档

### 阶段 3：前端最小可用支持

- 新建任务页增加 PDF tab
- API 封装增加 `createPdfTask`
- 任务列表与详情页支持 `engine=babeldoc`

### 阶段 4：测试和交付

- 跑后端测试
- 用真实 PDF 联调
- 补充 API 文档和交付说明

## 13. 推荐的首批实现清单

第一批开发建议直接落以下内容：

1. 后端
- 新增 `TaskEngine`
- 扩展 `TaskSourceType`
- 新增 `POST /api/tasks/pdf`
- 新增 `BabelDocService`
- 改造 `translation_runner.py` 按 `engine` 分发

2. 前端
- 新增 PDF 提交 tab
- 新增 `createPdfTask`
- 补充 `types.ts` 中的 `engine` 和 `pdf_upload`

3. 文档
- 更新 API 文档
- 更新前后端交付文档

## 14. 风险与缓解

### 风险 1：BabelDOC 输出目录结构与预期不一致

缓解：

- 先通过一份真实 PDF 样本确认输出目录结构
- 将“查找最终 PDF”的逻辑单独封装

### 风险 2：CLI 长时间运行导致日志不可观测

缓解：

- 标准输出和错误输出统一重定向到 `task.log`
- 定期写入任务事件

### 风险 3：配置错误导致任务批量失败

缓解：

- 增加启动时配置校验
- 创建 BabelDOC 任务前做必要配置检查

### 风险 4：前端与现有 LaTeX 页面耦合过深

缓解：

- 先只做最小展示
- 不强求 PDF 任务完全复用 LaTeX 产物展示模型

## 15. 建议的下一步

如果认可本计划，建议按以下顺序立即开工：

1. 先做后端模型和 API 变更
2. 再做 BabelDOC runner
3. 跑通一个真实 PDF 的后端链路
4. 最后接前端 PDF 页面

这样可以优先把最高风险的执行链路跑通，再补页面，避免先做 UI 后发现底层运行模型不合适。
