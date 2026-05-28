# LaTeXTrans arXiv Discovery Frontend Handoff

更新时间：2026-05-28

本文档面向负责前端实现的 agent / 开发者，目标是基于当前已经落地的 backend discovery API，继续完成前端 discovery 相关页面与交互。

关联文档：

- `docs/arxiv-discovery-integration-plan-2026-05-28.md`
- `docs/backend-api-reference-2026-05-26.md`
- `docs/fastapi-react-refactor-prd.md`

---

## 1. 项目背景与这次前端改动的目的

当前 `latex_trans_prod` 已经不是“单纯把 arXiv ID 扔进去做翻译”的小工具，而是一个带任务管理、归档、共享、缓存、用户体系的内部论文工作台。

`docs/arxiv-discovery-integration-plan-2026-05-28.md` 已经明确了下一阶段的主方向：

- 不再只优化单个翻译任务表单
- 要补上“论文从哪里来、如何筛、筛完如何进入翻译”的上游链路
- 通过 `ArxivArchive` 的 `crawl / judge / analyze` 能力，把系统升级成一个 discovery + collection + translate 的闭环

所以前端这次不是“再加一个任务 tab”，而是要补出一条新的使用路径：

`Discover -> Add to Collection -> View Paper Detail -> Decide Translate / Reuse Existing Result`

这条路径的目标是让用户直接在系统里发现论文，而不是在外部看到论文后手工复制 `arxiv_id` 再回来创建任务。

---

## 2. 当前后端已经完成的 discovery 能力

后端已新增 discovery 域模型、迁移、服务和 API，前端现在可以直接开始接入，不需要再等 schema 设计。

### 2.1 已落地的数据域

后端新增了以下表：

- `arxiv_papers`
- `arxiv_paper_reviews`
- `arxiv_collections`
- `arxiv_collection_items`
- `arxiv_paper_task_links`
- `arxiv_discovery_runs`

其中最重要的关系是：

- 一篇论文主记录在 `arxiv_papers`
- 同一篇论文可在不同收藏夹下有不同 `review`
- 用户可建立多个 `collection`
- 一篇论文可加入多个 `collection`
- 论文与翻译任务用 `arxiv_paper_task_links` 做显式关联

### 2.2 已落地的前端可用接口

#### Discovery

- `GET /api/discovery/papers`
- `GET /api/discovery/papers/{paper_id}`
- `GET /api/discovery/daily-digest`
- `POST /api/discovery/papers/{paper_id}/tasks`

#### Collections

- `GET /api/discovery/collections`
- `POST /api/discovery/collections`
- `PATCH /api/discovery/collections/{collection_id}`
- `POST /api/discovery/collections/{collection_id}/items`
- `DELETE /api/discovery/collections/{collection_id}/items/{paper_id}`

#### Admin discovery

- `POST /api/admin/discovery/sync`
- `GET /api/admin/discovery/runs`

说明：

- 所有 discovery 接口都走现有 cookie session 认证
- 接口前缀仍然是 `/api`
- 已复用现有 `axios + withCredentials` 模式即可

### 2.3 已落地的行为约束

这是前端接入时最容易误判的部分：

1. 论文主动作不是“立即翻译”，而是“加入收藏夹”
2. `POST /api/discovery/papers/{paper_id}/tasks` 虽然可用，但属于二级动作
3. 自动翻译策略一期只存配置，不会真的自动触发后台翻译
4. 若已有历史翻译任务，后端会在论文详情和列表里返回 `has_translation` / `tasks` / `latest_task`
5. 任务仍然复用现有 `TaskService`，不是另一套翻译系统

---

## 3. 后端响应模型摘要

这里只列前端实现最常用的字段，不重复抄全量 backend schema。

### 3.1 `DiscoveryPaperSummaryResponse`

用于 `GET /api/discovery/papers`

核心字段：

- `id`
- `arxiv_id`
- `primary_category`
- `title_en`
- `title_zh`
- `abstract_en`
- `abstract_zh`
- `authors_json`
- `subjects_json`
- `comments`
- `pdf_url`
- `abs_url`
- `worth_read`
- `comment`
- `has_translation`
- `translation_task_count`
- `collections[]`
- `scraped_at`
- `source_run_date`

其中：

- `collections[]` 表示当前用户视角下，这篇论文已经加入了哪些收藏夹
- `worth_read` / `title_zh` / `abstract_zh` / `comment` 来自当前用户可见 review 的聚合结果
- `has_translation=true` 表示当前用户可见范围内，后端能关联到翻译任务

### 3.2 `DiscoveryPaperDetailResponse`

用于 `GET /api/discovery/papers/{paper_id}`

比 summary 多出：

- `reviews[]`
- `tasks[]`
- `latest_task`

前端可直接用它构建 `PaperDetailPage`。

### 3.3 `DiscoveryCollectionResponse`

用于收藏夹列表、创建和更新后的返回

核心字段：

- `id`
- `name`
- `description`
- `categories_json`
- `prefer_keywords`
- `avoid_keywords`
- `translation_mode`
- `auto_translate_enabled`
- `item_count`
- `items[]`

其中 `items[]` 内部会直接带 `paper` 摘要，所以收藏夹页不一定需要额外发论文详情请求。

### 3.4 `DiscoveryDailyDigestResponse`

用于发现首页的“今日聚合”视图：

- `run`
- `groups[]`

其中：

- `run` 是最近一次成功同步的 discovery run
- `groups[].category` 是分类
- `groups[].papers[]` 是该分类下的论文列表

### 3.5 `DiscoveryPaperTaskResponse`

用于从论文直接创建翻译任务：

```json
{
  "task": { "...TaskDetailResponse": "..." },
  "paper": { "...DiscoveryPaperDetailResponse": "..." }
}
```

前端处理建议：

- 成功后直接 toast
- 刷新 discovery 详情 / 列表 query
- 并提供跳转到 `/tasks/{task.id}` 的 CTA

---

## 4. 建议新增的前端信息架构

基于当前产品和已有路由，建议补 3 个页面。

### 4.1 `DiscoverPage`

建议路由：

- `/discover`

用途：

- 发现页主入口
- 展示最近一次同步出的论文
- 支持筛选

建议区块顺序：

1. `Today's Picks`
2. `Worth Reading`
3. `All Papers`
4. `Already Translated`
5. `Quick Collections Entry`

建议筛选：

- `category`
- `keyword`
- `worth_read`
- `translated`
- `collection_id`

建议卡片字段：

- 英文标题
- 中文标题
- arXiv ID
- 分类
- 作者
- 中文摘要
- worth_read badge
- AI comment
- 是否已有翻译结果
- 已加入哪些收藏夹

建议卡片动作：

- 主动作：`Add to Collection`
- 次动作：`View Detail`
- 若 `has_translation=true`，再显示 `View History`

### 4.2 `CollectionsPage`

建议路由：

- `/collections`

用途：

- 管理当前用户的收藏夹
- 配置 discovery 偏好
- 查看每个收藏夹下已加入的论文

建议内容：

- 收藏夹列表
- 新建收藏夹
- 编辑收藏夹
- 每个收藏夹下的论文列表

每个收藏夹至少展示：

- 名称
- 描述
- `categories_json`
- `prefer_keywords`
- `avoid_keywords`
- `translation_mode`
- `auto_translate_enabled`
- `item_count`

### 4.3 `PaperDetailPage`

建议路由：

- `/papers/:paperId`

用途：

- 聚合展示单篇论文信息
- 作为 discovery 与 task system 的桥

建议区块：

1. 论文元信息
2. AI review 列表
3. 已加入的收藏夹
4. 历史翻译任务
5. 最新可用结果入口
6. `Pipeline` 可视化卡片

---

## 5. 路由与导航层改动建议

当前前端路由在 `frontend/src/App.tsx` 中只有：

- `/`
- `/tasks/new`
- `/tasks/:taskId`
- `/archives`
- `/admin`

建议新增：

- `/discover`
- `/collections`
- `/papers/:paperId`

建议 `AppShell` 导航从：

- `Tasks`
- `New Task`
- `Archives`

扩展为：

- `Discover`
- `Collections`
- `Tasks`
- `New Task`
- `Archives`

推荐把 `Discover` 放在最前面，因为这条链路现在是新主入口，而不是附属功能。

---

## 6. 现有前端代码中建议新增的类型

建议在 `frontend/src/lib/types.ts` 中新增以下枚举和类型。

### 6.1 枚举

```ts
export const collectionTranslationModes = ["manual", "auto"] as const
export type CollectionTranslationMode = (typeof collectionTranslationModes)[number]

export const translateDecisions = [
  "pending",
  "manual_requested",
  "auto_queued",
  "translated",
] as const
export type TranslateDecision = (typeof translateDecisions)[number]
```

### 6.2 discovery 相关类型

建议新增：

- `DiscoveryCollectionMembership`
- `DiscoveryPaperReview`
- `DiscoveryPaperSummary`
- `DiscoveryPaperDetail`
- `PaginatedDiscoveryPapers`
- `DiscoveryCollectionItem`
- `DiscoveryCollection`
- `DiscoveryCollectionList`
- `DiscoveryRun`
- `DiscoveryDailyDigest`
- `DiscoveryPaperTaskResponse`

建议完全对齐 `backend/app/schemas/discovery.py`，不要在前端重新发明字段名。

---

## 7. 现有前端 API client 中建议新增的方法

建议在 `frontend/src/lib/api.ts` 中新增以下方法。

### 7.1 Discovery 查询

```ts
listDiscoveryPapers(filters)
getDiscoveryPaper(paperId)
getDiscoveryDailyDigest()
```

### 7.2 Collection 管理

```ts
listDiscoveryCollections()
createDiscoveryCollection(payload)
updateDiscoveryCollection(collectionId, payload)
addPaperToCollection(collectionId, payload)
removePaperFromCollection(collectionId, paperId)
```

### 7.3 从论文创建任务

```ts
createTaskFromDiscoveryPaper(paperId, payload)
```

### 7.4 Admin

```ts
adminTriggerDiscoverySync(payload)
adminListDiscoveryRuns(page, pageSize)
```

说明：

- 沿用当前 `withApiError(...)` 封装即可
- 这些接口都是 JSON body，不需要 `FormData`
- 参数命名保持和后端一致，如 `page_size`、`source_run_date`

---

## 8. 建议的 React Query key 设计

建议统一成下面这组 key，避免后面不好失效：

- `["discovery-papers", filters]`
- `["discovery-paper", paperId]`
- `["discovery-daily-digest"]`
- `["discovery-collections"]`
- `["admin-discovery-runs", page, pageSize]`

Mutation 成功后的最小失效建议：

### 8.1 添加论文到收藏夹后

失效：

- `["discovery-papers"]`
- `["discovery-paper", paperId]`
- `["discovery-collections"]`

### 8.2 收藏夹更新后

失效：

- `["discovery-collections"]`
- `["discovery-papers"]`
- 若当前在某个论文详情页，也可失效 `["discovery-paper", paperId]`

### 8.3 从论文创建任务后

失效：

- `["discovery-papers"]`
- `["discovery-paper", paperId]`
- `["tasks"]`
- `["archives"]`

---

## 9. 页面实现建议

### 9.1 `DiscoverPage` MVP

建议第一版先做成：

- 顶部摘要卡片：最近一次 sync 时间、总论文数、总 worth_read 数
- 筛选条
- 论文列表
- 每条论文一组轻量动作

建议先不要在第一页就塞太多复杂图形。

第一版筛选控件可用：

- `Select`: category
- `Input`: keyword
- `Toggle` / `Select`: worth_read
- `Toggle` / `Select`: translated
- `Select`: collection

### 9.2 论文卡片建议

建议复用现有 `Card` 风格，不要另起完全不同的视觉体系。

卡片内重点：

- 标题区：`title_zh` 为主，`title_en` 为辅
- 元信息区：`arxiv_id`、category、authors
- 摘要区：优先展示 `abstract_zh`
- 状态区：
  - worth_read
  - has_translation
  - joined collections

### 9.3 `PaperDetailPage`

建议从上到下：

1. 返回 Discover
2. 标题、arXiv ID、外链
3. 摘要与评论
4. 收藏夹状态
5. 历史任务列表
6. Pipeline 卡片

历史任务列表可直接复用当前任务页已有的一些状态 badge / 时间格式化能力。

### 9.4 `CollectionsPage`

建议左侧或顶部是收藏夹列表，右侧或下方是当前选中收藏夹的详情和论文列表。

MVP 阶段如果要省时间，也可以先做成：

- 一个页面顶部 `Create Collection`
- 下方每个 collection 一张 card
- card 内直接展开 items 列表

不必一开始就做复杂 master-detail layout。

---

## 10. Pipeline 可视化落地建议

产品方案里建议在论文详情页加入：

- `crawl`
- `judge`
- `analyze`
- `persist`
- `translate`

但要注意：

当前 backend 还没有直接返回一份可视化专用 node/edge payload。

所以前端第一版建议：

1. 先本地静态定义 node/edge 结构
2. 用 `DiscoveryPaperDetailResponse` 中已有字段推导节点状态

可先这样映射：

- `crawl`
  - 只要有 `scraped_at` 即视为 `succeeded`
- `judge`
  - 有 `reviews[]` 即视为 `succeeded`
- `analyze`
  - 当前后端将 `analysis` 摘要放在 `review.raw_result_json` 里，可作为详情展示源
- `persist`
  - 有 paper detail 即视为 `succeeded`
- `translate`
  - `has_translation=true` 则视为 `succeeded`
  - 否则若已加入收藏夹，则视为 `pending`
  - 否则显示 `waiting for decision`

如果前端要引入 `@xyflow/react`，请记住：

- 这是只读信息图
- 不要开放拖拽保存
- 不要让用户误以为这是流程编排器

---

## 11. 明确哪些点一期先不要做

为了避免前端 scope 漂移，一期请不要默认实现下面这些东西：

1. 不要单独做 `SubscriptionsPage`
   - 当前 discovery 偏好已经挂在 `collections` 上

2. 不要做“自动翻译真的自动触发”
   - 后端当前只保存策略，不会真的后台批量开任务

3. 不要把发现页做成“点一下就立即翻译”的产品心智
   - 主入口仍然是 `Add to Collection`

4. 不要把 `worth_read` 误当成全局唯一结论
   - 它本质上和 collection 偏好有关

5. 不要先做站外推送、邮件、飞书通知
   - 当前目标是站内闭环

---

## 12. 推荐前端落地顺序

### Phase A：接口与基础类型

1. 补 `types.ts`
2. 补 `api.ts`
3. 补 query keys
4. 补 router 空页面

### Phase B：Collections 先行

原因：

- collection 是 discovery 偏好承载体
- 没有 collection，后面很多“加入收藏夹”的动作无法闭环

建议：

1. `CollectionsPage`
2. 新建 / 编辑收藏夹表单
3. 收藏夹论文列表

### Phase C：Discover 主列表

1. `DiscoverPage`
2. 筛选
3. 论文卡片
4. 加入收藏夹动作
5. 跳详情

### Phase D：Paper Detail

1. 论文元信息
2. review 列表
3. 历史任务列表
4. `Create task from paper`
5. pipeline 卡片

### Phase E：Admin optional

如果时间允许，再把 admin 页 discovery sync 入口接进去：

- 手动触发同步
- 查看 run history

---

## 13. 建议直接修改的现有文件

高概率会改到：

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/app-shell.tsx`

建议新增：

- `frontend/src/pages/discover-page.tsx`
- `frontend/src/pages/collections-page.tsx`
- `frontend/src/pages/paper-detail-page.tsx`
- `frontend/src/components/discovery/*`

---

## 14. 前端接入时的几个注意点

1. 所有 discovery API 都需要登录态
   - 当前 cookie session 已经统一处理，沿用现有 `axios` 实例即可

2. `GET /api/discovery/papers` 的筛选参数是 query string
   - `page`
   - `page_size`
   - `category`
   - `keyword`
   - `worth_read`
   - `translated`
   - `collection_id`
   - `source_run_date`

3. `POST /api/discovery/papers/{paper_id}/tasks` 不是只传 `paper_id`
   - 它支持附带 `collection_id` 和任务参数
   - 但前端可以先只传最小集

4. 创建任务成功后，应跳转到现有 task detail，而不是新做一个“翻译中间页”

5. 论文详情里的 `tasks[]` 只包含当前用户可见的任务
   - 不要假设能看到所有团队任务

---

## 15. 给下一个前端 agent 的一句话总结

当前最正确的实现心智不是“给现有任务页加点发现功能”，而是：

**把系统首页入口逐步从 `Tasks` 转成 `Discover`，让论文先被发现和归档，再决定是否进入翻译。**

这也是本次 backend discovery API 已经为前端铺好的方向。
