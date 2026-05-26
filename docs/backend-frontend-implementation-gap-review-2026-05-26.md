# Backend/Frontend 实现差距审阅（对照 PRD）

更新时间：2026-05-26

对照文档：`docs/fastapi-react-refactor-prd.md`  
审阅范围：`backend/`、`frontend/`

## 1. 总体结论

当前前后端主链路已经基本打通（任务创建、任务查询、详情、归档列表、工件下载链接、失败摘要接口均可见实现），但仍存在若干与 PRD 不一致的关键缺口，主要集中在：

- 取消任务语义与真实执行不一致
- 失败任务归档不完整
- 任务轮询策略边界条件错误
- 历史检索与聚合能力未完全落地
- 结构化日志未完成接入

## 2. 关键问题清单（按严重级别）

### P0

1. 取消任务仅改状态，未真正中断执行
- 现状：
  - `POST /tasks/{id}/cancel` 将任务标记为 `CANCELED`，但 worker 在任务开始后没有持续检查取消信号。
  - 代码位置：
    - `backend/app/services/task_service.py`（取消接口逻辑）
    - `backend/app/workers/translation_runner.py`（仅启动时检查一次 `CANCELED`）
- 风险：
  - 用户看到“已取消”，任务仍可能继续翻译并上传产物，状态语义冲突。
- 对应 PRD：
  - Story 2 状态流转可观测性要求。

2. 失败路径未保证日志/元数据归档
- 现状：
  - `metadata` 与 `log` 的 artifact 上传位于成功路径尾部；
  - 异常路径仅写入 `FAILED` 事件，不保证日志和元数据可下载。
  - 代码位置：
    - `backend/app/workers/translation_runner.py`
- 风险：
  - 失败任务排查资料不完整，无法满足“失败任务日志下载”与“归档完整率”目标。
- 对应 PRD：
  - Story 3 归档完整性
  - Story 5 失败任务日志可追溯
  - Evaluation 中“失败任务也保留必要日志与中间元数据”

### P1

3. 任务列表轮询停止条件不正确
- 现状：
  - 列表页轮询仅依据 `items[0].status` 判断是否继续。
  - 若第一条任务已终态，但其他任务仍运行，会提前停止轮询。
  - 代码位置：
    - `frontend/src/pages/tasks-page.tsx`
- 风险：
  - “最近任务”显示可能滞后，不满足前端进度实时性预期。
- 对应 PRD：
  - Story 2 的轮询刷新要求（MVP 可轮询）。

4. 历史检索缺少“时间范围”前端入口
- 现状：
  - 后端 `list_tasks/list_archives` 已支持 `created_from/created_to`；
  - 前端筛选组件未提供时间范围输入。
  - 代码位置：
    - 后端：`backend/app/api/routes/tasks.py`、`backend/app/api/routes/archives.py`
    - 前端：`frontend/src/components/tasks/task-filters.tsx`
- 风险：
  - PRD 要求的历史检索维度在 UI 层不完整。
- 对应 PRD：
  - Story 4：按时间范围检索历史任务。

5. 同一 arXiv ID 聚合展示未实现
- 现状：
  - 归档页面为逐任务列表；
  - 后端归档服务仅返回 `artifact_count`，无聚合结构。
  - 代码位置：
    - `frontend/src/pages/archives-page.tsx`
    - `backend/app/services/archive_service.py`
- 风险：
  - 用户无法快速复用同一论文的历史翻译结果。
- 对应 PRD：
  - Story 4：同一 arXiv ID 历史任务聚合展示。

6. 结构化日志能力未真正接入
- 现状：
  - 依赖包含 `python-json-logger`；
  - 但未看到统一 logger 配置与结构化字段输出链路，当前主要是 stdout/stderr 重定向到文件。
  - 代码位置：
    - `backend/requirements.txt`
    - `backend/app/workers/translation_runner.py`
- 风险：
  - 不利于后续日志平台接入、失败类型分析、跨任务检索。
- 对应 PRD：
  - Story 5：后端结构化日志。

## 3. “留空 / mock / 假实现”核查结果

在 `backend/app` 与 `frontend/src` 主业务链路内，未发现明显的前端静态 mock 数据驱动页面、或后端接口级 `NotImplementedError` 留空实现。  
当前主要问题不是“假接口”，而是“真实链路已接通但能力不完整/语义不严谨”。

## 4. 当前测试覆盖缺口

已存在测试偏基础：

- 路由注册检查：`backend/tests/test_app_import.py`
- 压缩包路径穿越防护：`backend/tests/test_pipeline_service.py`

尚缺关键场景测试：

- 取消后不再继续执行与不再写入成功态
- 失败路径日志与 metadata 工件归档
- 轮询策略（列表页有运行中任务时应持续刷新）
- 历史筛选时间范围参数联动

## 5. 建议修复优先级

1. 先修 P0：取消语义与失败归档完整性。
2. 再修 P1：轮询策略、时间范围筛选、arXiv 聚合、结构化日志。
3. 同步补充测试，至少覆盖上述 P0/P1 场景，避免回归。

