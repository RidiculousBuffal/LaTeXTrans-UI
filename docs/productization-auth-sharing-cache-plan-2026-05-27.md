# LaTeXTrans 产品化开发文档：用户体系、任务共享与翻译缓存

更新时间：2026-05-27

关联基线文档：

- `docs/fastapi-react-refactor-prd.md`
- `docs/backend-api-reference-2026-05-26.md`
- `docs/backend-frontend-implementation-gap-review-2026-05-26.md`

## 1. 背景与当前基线

当前项目的基础翻译闭环已经跑通，后端已有以下能力：

- FastAPI 接口已经支持创建 `arxiv`、源码压缩包、PDF 翻译任务。
- MySQL 中已有 `translation_tasks`、`task_artifacts`、`task_events`、`task_configs` 四张核心表。
- MinIO 归档、任务详情、任务日志、任务重试与取消已具备 MVP 形态。
- 前端已有任务列表、详情、创建页、归档页等基本页面。

但从“产品化可多用户使用”的角度看，目前还存在明显缺口：

- 任务归属仍然依赖前端直接传入 `created_by` 字符串，不能代表真实用户身份。
- 没有注册、登录、JWT 鉴权、角色区分、密码存储、管理员入口。
- 没有“翻译额度”概念，任何人都可以无限提交任务。
- 没有共享权限模型，任务默认也没有私有/公开/指定用户共享这类状态。
- 没有针对同一 `arXiv ID` 或同一上传文件内容的翻译缓存，重复任务会重复消耗算力。

本文档定义下一阶段产品化开发方案，目标是在尽量不推翻现有任务系统的前提下，为现有 FastAPI + React 架构补齐最小可用的多用户产品能力。

## 2. 本期范围与原则

本期只覆盖以下三类能力：

1. 用户系统
2. 任务共享
3. 翻译缓存与算力去重

本期不做的内容：

- 不做复杂 RBAC，只保留 `user` / `admin` 两个角色。
- 不做 OAuth、SSO、邮箱验证、找回密码、多因子认证。
- 不做组织、团队、项目空间等多租户模型。
- 不做细粒度 artifact 级权限，先以“任务级权限”控制所有关联产物。
- 不做分布式缓存集群，先以数据库中的缓存元数据 + MinIO 产物复用打通闭环。

本期默认采用以下实现原则：

- 鉴权使用 JWT Bearer Token。
- 注册成功后自动获得初始翻译额度，额度值来自 `.env`。
- MVP 阶段额度按“每次真正启动一次翻译计算”扣减，默认 `1` 次任务消耗 `1` 个额度。
- 命中缓存的请求不重复消耗算力，也不扣减额度。
- 任务默认私有，只有创建者和管理员可见；用户显式共享后，其他人才能访问。

## 3. 目标产品规则

## 3.1 用户与角色

系统只保留两种角色：

- `user`
- `admin`

权限规则如下：

| 能力 | user | admin |
| --- | --- | --- |
| 注册 / 登录 | 是 | 是 |
| 创建翻译任务 | 是，受额度约束 | 是，可配置是否免额度 |
| 查看自己的任务 | 是 | 是 |
| 删除自己的任务 | 是 | 是 |
| 查看公开任务 | 是 | 是 |
| 查看被显式共享给自己的任务 | 是 | 是 |
| 查看任意任务 | 否 | 是 |
| 删除任意任务 | 否 | 是 |
| 调整他人额度 | 否 | 是 |
| 查看所有用户额度 | 否 | 是 |

管理员建议通过 `.env` 提供一组初始化账号，服务启动时自动补齐，不依赖手工写库。

## 3.2 翻译额度

MVP 阶段采用简单额度模型：

- 单位：`translation_quota`
- 默认扣费规则：一次真正执行的翻译任务消耗 `1`
- 缓存命中：`0`
- 管理员手工补充：正数增量
- 管理员手工扣减：可选，建议也支持负数调整

推荐行为：

- 用户注册成功时，自动创建额度账户并写入一条“初始赠送”流水。
- 每次任务提交时，在真正入队前做“缓存检查 -> 额度检查 -> 预留额度/扣额度”。
- 为避免并发超发，额度扣减必须在数据库事务里完成。
- 若任务后续因为系统异常未真正开始，可按策略返还额度。

本期建议采用“成功占用算力时扣减，不以最终成功与否为准”的口径。原因是即便翻译失败，也已经消耗了模型/CPU/下载等资源。

## 3.3 共享模型

任务共享分两层：

- `public`
  - 对所有登录用户可见、可下载。
- `direct share`
  - 只对被指定的用户可见、可下载。

推荐任务可见性枚举：

- `private`
- `public`

配合一张“定向共享关系表”：

- 任务为 `private` 时，只有 owner、admin、以及被定向授权的用户可访问。
- 任务为 `public` 时，所有登录用户可访问。

这套设计比直接增加多个复杂状态更稳定，原因是：

- “是否全员可见”由 `visibility` 控制。
- “是否共享给指定用户”由关系表控制。
- 二者可以同时存在，逻辑清晰。

## 3.4 缓存模型

缓存目标不是简单“任务去重”，而是“翻译结果去重，任务记录仍可独立存在”。

这点非常重要。原因是：

- 不同用户提交同一论文时，系统仍然应该给每个人保留自己的任务记录。
- 但底层翻译结果可以只计算一次。
- 私有任务的缓存可被系统内部复用，但不应因为缓存复用而把原任务直接暴露给其他用户。

因此本期建议采用：

- “结果缓存”和“任务可见性”分离
- 一个缓存条目对应一份可复用的标准翻译结果
- 一个用户提交新任务时：
  - 如果缓存未命中，走正常翻译，完成后生成缓存条目
  - 如果缓存命中，创建一个新的逻辑任务记录，将其标记为 `CACHE_HIT`，并把 artifact 复用到该任务名下

缓存命中条件不能只看 `arXiv ID` 或文件哈希本身，还必须包含会影响结果的关键参数：

- `engine`
- 标准化后的 `arxiv_id` 或 `source_file_hash`
- `source_language`
- `target_language`
- `model_name`
- 关键翻译参数 `options`
- 缓存版本 `cache_version`

否则会出现“同一论文但语言/模型不同却错误复用结果”的问题。

## 4. 数据模型改造

## 4.1 新增表

### `users`

核心字段建议：

- `id`
- `username`
- `password_hash`
- `role`
- `is_active`
- `created_at`
- `updated_at`
- `last_login_at`

约束建议：

- `username` 唯一索引

### `user_quota_accounts`

核心字段建议：

- `user_id`
- `balance`
- `total_granted`
- `total_consumed`
- `updated_at`

约束建议：

- `user_id` 唯一索引

### `user_quota_ledger`

用途：

- 记录初始赠送、管理员加额、系统扣额、系统返还等流水，便于审计。

核心字段建议：

- `id`
- `user_id`
- `delta`
- `balance_after`
- `reason_type`
- `reason_ref_id`
- `operator_user_id`
- `metadata_json`
- `created_at`

### `task_share_grants`

用途：

- 记录任务被共享给哪些指定用户。

核心字段建议：

- `id`
- `task_id`
- `grantee_user_id`
- `granted_by_user_id`
- `created_at`

约束建议：

- `(task_id, grantee_user_id)` 唯一索引

### `translation_cache_entries`

用途：

- 记录一个可复用的标准翻译结果。

核心字段建议：

- `id`
- `cache_key`
- `engine`
- `normalized_arxiv_id`
- `source_file_hash`
- `source_fingerprint_type`
- `source_language`
- `target_language`
- `model_name`
- `options_hash`
- `cache_version`
- `status`
- `canonical_task_id`
- `artifact_manifest_json`
- `hit_count`
- `last_hit_at`
- `created_at`
- `updated_at`

约束建议：

- `cache_key` 唯一索引
- `normalized_arxiv_id` 普通索引
- `source_file_hash` 普通索引

`status` 推荐枚举：

- `BUILDING`
- `READY`
- `FAILED`
- `INVALIDATED`

## 4.2 修改现有表

### `translation_tasks`

建议新增字段：

- `owner_user_id`
- `visibility`
- `source_file_hash`
- `cache_entry_id`
- `result_source`
- `quota_cost`
- `quota_charged`
- `shared_at`

字段说明：

- `owner_user_id`
  - 替代当前不安全的 `created_by` 作为主归属字段。
- `visibility`
  - `private` / `public`
- `source_file_hash`
  - 对上传文件内容做 `sha256`，用于缓存命中。
- `cache_entry_id`
  - 命中缓存时关联标准结果。
- `result_source`
  - `EXECUTED` / `CACHE_HIT`
- `quota_cost`
  - 本次任务按规则需要扣多少额度
- `quota_charged`
  - 是否已经扣过额度

兼容建议：

- `created_by` 暂时保留一段时间，用于兼容旧前端与历史数据展示。
- 新接口全部改为从 JWT 中解析用户，不再信任前端传入 `created_by`。

### `task_artifacts`

当前表结构基本够用，不建议为缓存单独复制一套 artifact 表。

推荐做法：

- 缓存命中后，为新任务补写该任务自己的 artifact 记录
- `object_key` 指向同一份 MinIO 对象
- 这样列表、详情、下载接口可以继续沿用现有逻辑

优点：

- 不必在读取链路里增加“先查任务 artifact，再查缓存 artifact”的双跳逻辑
- 成本只是多几条轻量元数据记录，不会复制文件本身

## 5. 接口设计

## 5.1 认证接口

### `POST /api/auth/register`

用途：

- 用户注册

请求体：

```json
{
  "username": "alice",
  "password": "plain-password"
}
```

行为：

- 创建 `users`
- 创建 `user_quota_accounts`
- 写入初始额度流水

### `POST /api/auth/login`

返回：

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "uuid",
    "username": "alice",
    "role": "user",
    "quota_balance": 10
  }
}
```

### `GET /api/auth/me`

用途：

- 返回当前登录用户信息和额度摘要

## 5.2 管理员额度接口

### `POST /api/admin/users/{user_id}/quota-adjustments`

请求体：

```json
{
  "delta": 10,
  "reason": "manual grant"
}
```

行为：

- 仅 `admin` 可调用
- 更新额度账户
- 写入额度流水

### `GET /api/admin/users`

用途：

- 查询用户列表、角色、额度余额

## 5.3 任务接口改造

以下现有任务接口都要改成“从 JWT 推导用户”：

- `POST /api/tasks`
- `POST /api/tasks/upload`
- `POST /api/tasks/pdf`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/artifacts`
- `POST /api/tasks/{task_id}/retry`
- `POST /api/tasks/{task_id}/cancel`
- `DELETE /api/tasks/{task_id}`

核心变更：

- 删除请求中的 `created_by` 输入字段
- 写入 `owner_user_id`
- 所有查询都必须增加权限过滤

`GET /api/tasks` 推荐增加筛选参数：

- `scope=mine|shared|public|all`
- 其中 `all` 仅 `admin` 可用

## 5.4 共享接口

### `GET /api/tasks/{task_id}/sharing`

返回当前共享状态：

```json
{
  "task_id": "uuid",
  "visibility": "private",
  "shared_users": [
    {
      "user_id": "uuid",
      "username": "bob"
    }
  ]
}
```

### `PUT /api/tasks/{task_id}/sharing`

请求体：

```json
{
  "visibility": "public",
  "shared_user_ids": ["uuid-1", "uuid-2"]
}
```

权限规则：

- 只有任务 owner 或 admin 可以修改

## 5.5 缓存相关接口

MVP 不一定需要把缓存做成大量公开接口，但至少建议补以下管理能力：

### `GET /api/admin/cache`

用途：

- 查看缓存命中、状态、来源任务、最近命中时间

### `POST /api/admin/cache/{cache_entry_id}/invalidate`

用途：

- 失效缓存，便于模型升级、参数变更、缓存污染修复

## 6. 后端实现方案

## 6.1 模块拆分建议

在现有 `backend/app/` 下新增或扩展：

- `models/user.py`
- `models/quota.py`
- `models/sharing.py`
- `models/cache.py`
- `schemas/auth.py`
- `schemas/user.py`
- `schemas/quota.py`
- `schemas/sharing.py`
- `schemas/cache.py`
- `api/routes/auth.py`
- `api/routes/admin.py`
- `services/auth_service.py`
- `services/quota_service.py`
- `services/access_service.py`
- `services/cache_service.py`

职责建议：

- `AuthService`
  - 注册、登录、密码校验、JWT 生成
- `QuotaService`
  - 初始发放、扣额、加额、返还、流水记录
- `AccessService`
  - 任务可见性判断、owner/admin/shared/public 统一判定
- `CacheService`
  - 缓存 key 生成、命中检查、构建锁、缓存写入、失效

## 6.2 任务创建链路改造

当前 `TaskService.create_task/create_upload_task/create_pdf_task` 会直接建任务并调用 `submit_task(task.id)`。

改造后的顺序建议是：

1. 从 JWT 解析当前用户
2. 标准化请求参数
3. 对 arXiv 任务生成标准化 `normalized_arxiv_id`
4. 对上传文件生成 `sha256`
5. 生成 `cache_key`
6. 查缓存
7. 若缓存命中：
   - 创建新任务
   - 直接写入复用 artifact
   - 状态置为 `SUCCEEDED`
   - `result_source=CACHE_HIT`
   - 不扣额度
8. 若缓存未命中：
   - 校验额度
   - 数据库事务中扣减额度
   - 创建任务
   - 写入 `translation_cache_entries(status=BUILDING)`
   - 调用 `submit_task(task.id)`
9. 任务成功后：
   - 上传 artifact
   - 回填缓存条目为 `READY`
10. 任务失败后：
   - 视策略保留 `FAILED` 缓存条目或删除 `BUILDING` 条目

## 6.3 缓存 key 生成规则

推荐输入：

```text
engine
source_fingerprint
source_language
target_language
model_name
normalized_options_json
cache_version
```

其中：

- `source_fingerprint`
  - arXiv 任务：`arxiv:{normalized_arxiv_id}`
  - 上传任务：`file:{sha256}`

最终 `cache_key` 可用稳定 JSON 序列化后再 `sha256`。

`normalized_options_json` 必须去掉无关字段，避免把时间戳、显示名称这类不影响结果的字段混进 key。

## 6.4 并发与防重

要重点处理同一时刻两个用户提交同一篇论文的问题。

建议方案：

- `translation_cache_entries.cache_key` 建唯一索引
- 首个请求创建 `BUILDING` 记录
- 后续请求若发现同 key 的 `BUILDING` 记录：
  - 可创建任务并标记为 `WAITING_FOR_CACHE`
  - 或直接返回“已有同源任务处理中”

本期更推荐第一种，对用户体验更完整。为此可在 `TaskStatus` 基础上新增一个可选状态：

- `WAITING_FOR_CACHE`

若不想改状态枚举，也可以先沿用 `PENDING`，但事件流里要明确说明是在等待缓存构建，而不是排队执行自己的独立翻译。

## 6.5 权限控制落点

权限校验不要散落在各个路由函数里，建议集中在服务层和依赖层：

- `get_current_user`
- `require_admin`
- `access_service.can_view_task(...)`
- `access_service.can_manage_task(...)`

所有任务读取、下载、删除、重试、取消、查看日志都必须走统一权限判定。

特别注意：

- `list_logs` 当前会直接读取本地日志文件，后续必须确保只有 owner 或 admin 可访问。
- artifact 预签名下载地址也必须在权限通过后才能生成。

## 7. 前端改造点

## 7.1 新增页面

- 登录页
- 注册页
- 管理员用户管理页

## 7.2 现有页面改造

### 任务创建页

- 不再手填 `created_by`
- 展示当前用户剩余额度
- 提交前提示本次是否会消耗额度
- 命中缓存后给出明确提示，例如“已复用历史翻译结果”

### 任务列表页

- 增加 `mine / shared / public` 切换
- 管理员可切到 `all`
- 展示任务来源 `EXECUTED / CACHE_HIT`
- 展示可见性 `private / public`

### 任务详情页

- 增加共享设置面板
- owner 可切换公开状态
- owner 可添加/移除指定共享用户
- 对缓存命中任务展示“结果来自缓存复用”

### 管理员页

- 用户列表
- 额度余额
- 加额操作
- 可选的缓存列表与失效操作

## 8. 配置项设计

建议在 `backend/app/core/config.py` 中新增以下配置：

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_EXPIRE_MINUTES`
- `DEFAULT_USER_TRANSLATION_QUOTA`
- `ADMIN_BOOTSTRAP_USERNAME`
- `ADMIN_BOOTSTRAP_PASSWORD`
- `ADMIN_BOOTSTRAP_ENABLED`
- `CACHE_ENABLED`
- `CACHE_VERSION`

可选配置：

- `ADMIN_TASKS_BYPASS_QUOTA`
- `CACHE_BUILD_STALE_MINUTES`

说明：

- `DEFAULT_USER_TRANSLATION_QUOTA` 就是用户注册后的初始翻译额度。
- `CACHE_VERSION` 用于模型升级或翻译逻辑调整后的整体失效。

## 9. 数据迁移与上线顺序

推荐按以下顺序做，避免一次性改太多链路：

### Phase 1：用户与鉴权

- 新增 `users` 表
- 新增 JWT 登录链路
- 将现有任务创建与查询改成基于当前用户
- 保留 `created_by` 只做兼容显示

### Phase 2：额度系统

- 新增额度账户和流水表
- 注册自动赠送初始额度
- 任务提交前做额度检查和扣减
- 管理员支持加额

### Phase 3：共享能力

- 新增 `visibility`
- 新增 `task_share_grants`
- 任务列表、详情、下载、删除全部补权限校验

### Phase 4：缓存能力

- 新增 `translation_cache_entries`
- 接入 arXiv ID 和文件哈希去重
- 命中缓存时直接复用产物

### Phase 5：前端收口

- 登录注册页
- 额度展示
- 共享管理
- 管理员页
- 缓存命中提示

## 10. 测试与验收

## 10.1 后端测试

至少覆盖以下场景：

- 用户注册后获得默认额度
- 用户登录后可拿到 JWT
- 普通用户不能访问管理员接口
- 普通用户只能查看自己的私有任务
- 普通用户可查看公开任务
- 普通用户可查看共享给自己的任务
- 普通用户不能查看他人的私有任务
- 额度不足时任务创建失败
- 缓存未命中时扣减额度并创建执行任务
- 缓存命中时不扣额度并直接返回成功任务
- 相同 `cache_key` 并发提交时不重复启动底层翻译

## 10.2 前端验收

- 新用户可以注册、登录、创建任务、查看剩余额度
- 额度不足时前端有明确报错
- 用户能将自己的任务设为公开
- 用户能把任务共享给指定用户
- 其他用户只能看到公开任务和共享给自己的任务
- 命中缓存时用户能感知“本次未重复翻译”

## 10.3 运营验收

- 管理员可以查看用户余额并手工加额
- 管理员可以查看全部任务
- 管理员可以查看并处理缓存异常条目

## 11. 推荐的首批开发清单

为了尽快落地，建议第一批直接做下面这些最小交付：

1. 后端新增 `users`、`user_quota_accounts`、`user_quota_ledger` 三张表
2. 实现 `register/login/me`
3. 将任务创建接口改为从 JWT 读取用户
4. 实现额度检查与管理员加额接口
5. 给 `translation_tasks` 增加 `owner_user_id`、`visibility`、`source_file_hash`、`result_source`、`quota_cost`、`quota_charged`
6. 新增 `task_share_grants`
7. 新增 `translation_cache_entries`
8. 在 `TaskService` 中接入“先查缓存，再决定扣额和入队”的主链路
9. 前端补登录/注册/额度展示/共享设置

## 12. 本文档采用的默认假设

为避免文档停留在开放讨论阶段，本文先固化以下默认假设：

- 默认额度单位为“次”，不是页数、token 数或文件大小。
- 默认一次真实翻译执行消耗 `1` 个额度。
- 默认缓存命中不扣额度。
- 默认任务私有，必须由 owner 主动公开或定向共享。
- 默认管理员账号通过 `.env` 初始化。

如果后续要把额度改成“按页数”或“按 token”计费，可以在现有 `quota_cost` 字段和额度流水基础上平滑演进，不需要推翻当前设计。
