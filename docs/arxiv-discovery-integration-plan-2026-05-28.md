# LaTeXTrans 后续功能规划：arXiv 发现流与 ArxivArchive 集成

更新时间：2026-05-28

关联文档：

- `docs/fastapi-react-refactor-prd.md`
- `docs/backend-api-reference-2026-05-26.md`
- `docs/productization-auth-sharing-cache-plan-2026-05-27.md`

外部源码来源：

- 本次要并入的 `ArxivArchive` 本地项目路径为 `/Users/hpcow/codes/ArxivArchive`
- 后续 agent 如果需要迁入 discovery 相关代码，应从这个目录中选择性复制 `crawl`、`judge`、`analyze` 相关模块，而不是凭空重写或从别处寻找同名项目

## 1. 背景判断

当前 `latex_trans_prod` 已经完成了原定主线能力：

- 任务创建：支持 `arXiv ID`、源码压缩包、PDF。
- 任务执行：支持 LaTeX 翻译链路与 BabelDOC PDF 翻译链路。
- 任务管理：支持任务列表、详情、日志、取消、重试、失败摘要。
- 归档与复用：支持 MinIO artifacts、历史归档、共享、缓存、基础用户体系。

这意味着产品已经从“翻译引擎封装”进入“如何持续产出高价值内容入口”的阶段。

如果下一阶段还只继续堆“单任务翻译参数”或“页面微调”，价值增量会明显下降。更值得做的是补上“论文从哪里来、如何筛、筛完如何一键进入翻译”的前置链路。

这正是 `ArxivArchive` 的价值所在：

- 它已经具备按分类抓取当日 arXiv 新论文的能力。
- 它已经具备 AI 粗筛、中文标题、中文摘要、worth_read 判断、简短评论。
- 它已经具备日报聚合形态。
- 它和当前项目共用 `arxiv_id` 这一天然桥接主键。

因此，下一个最值得做的新功能，不是再做一个“翻译模式”，而是做一个 **arXiv 发现与转译闭环**。

## 2. 新功能候选池

基于当前产品状态，下一阶段值得考虑的功能可以分成三档。

### 2.1 第一优先级：直接增强主链路

1. `arXiv` 发现中心
   - 每日自动抓取指定分类的新论文。
   - 用 AI 生成中文标题、中文摘要、是否值得阅读、简评。
   - 用户先判断是否值得进入个人收藏夹，而不是系统直接翻译。

2. 收藏夹驱动的发现配置
   - 用户在收藏夹内配置关注分类、关键词偏好和不偏好方向。
   - 系统按所有收藏夹的分类并集执行每日抓取与粗筛。
   - 发现流先以站内列表和收藏夹视角为主，不单独拆出订阅系统。

3. 论文到翻译任务的一键闭环
   - 论文先进入用户自己的收藏夹。
   - 收藏夹中的文章再由用户选择“自动翻译”或“手动翻译”策略。
   - 若系统已有同 `arXiv ID` 历史翻译结果，则优先展示“查看已有结果”而不是重复翻译。

### 2.2 第二优先级：提升团队协作价值

1. 收藏夹 / 阅读清单
   - 每个用户可建立多个收藏夹，并按主题、用途或优先级组织论文。
   - 收藏夹中的文章可配置自动翻译或手动翻译策略。

2. 论文知识页
   - 一个 `arXiv ID` 聚合展示原始元数据、AI 摘要、历史翻译任务、产物、共享状态。

3. 团队推荐流
   - 管理员或核心用户可把某篇论文标为“推荐给团队”。
   - 在首页或发现页做推荐区。

### 2.3 第三优先级：增强算力与内容复用

1. 收藏夹驱动的翻译缓存预热
   - 只对被用户加入特定收藏夹且开启自动翻译策略的论文做自动预翻译。

2. 精读包生成
   - 将中文摘要、AI 评论、翻译 PDF、源码工程聚合成一个“论文包”。

3. 每周研究周报
   - 按分类、标签、用户收藏行为，自动汇总周报。

综合投入产出比来看，**第一优先级中的“arXiv 发现中心 + 收藏夹驱动的翻译闭环”最值得先做**。

## 3. 推荐方向

推荐将下一阶段主题定义为：

**Arxiv Intelligence Hub**

也就是把 LaTeXTrans 从“翻译任务系统”升级成“论文发现、筛选、翻译、归档的一体化工作台”。

一句话描述：

`将 ArxivArchive 的 crawl / judge / analyze 能力并入 LaTeXTrans backend，形成发现、筛选、收藏、翻译、归档一体化工作台。`

## 4. 为什么这是最好的下一步

### 4.1 与现有系统耦合自然

当前系统已经支持：

- `arxiv_id` 创建任务
- 历史任务按 `arxiv_id` 聚合
- 任务共享
- 翻译缓存

而 `ArxivArchive` 输出的核心对象也是围绕 `arxiv_id`。

这意味着集成不需要重新发明主键，也不需要强行改造当前任务链路。发现模块可以作为上游入口，翻译模块继续作为下游执行器。

### 4.2 会明显提升团队真实使用频率

现在的使用路径更像：

`用户先在外部看到一篇论文 -> 手工复制 arxiv_id -> 回到系统创建任务`

集成后会变成：

`用户打开系统 -> 直接看到今日值得看的论文 -> 加入某个收藏夹 -> 再决定自动翻译或手动翻译`

这个变化会把产品从“被动工具”变成“主动入口”。

### 4.3 可以放大已有缓存与归档价值

当前缓存和归档更偏底层能力，普通用户不一定感知明显。

接入发现流后，这些能力会变得直接可见：

- 某篇热门论文已经翻译过，用户可以直接查看历史结果。
- 某篇论文值得读，管理员可以直接共享给全员。
- 某个方向每天都有新论文进入系统，归档页会变成真正有内容积累的“内部论文库”。

## 5. 集成目标

目标是把 `ArxivArchive` 的核心能力并入当前 backend，并保留其最有价值的产品能力：

1. 每日按分类抓取新论文
2. 产出结构化 AI 粗筛结果
3. 将结果写入当前系统数据库
4. 在前端提供“发现流”页面
5. 允许用户把论文加入多个收藏夹
6. 由收藏夹策略决定自动翻译或手动翻译
7. 若已有历史翻译，则优先展示复用入口

## 6. 集成方案

当前决定采用：

**把 `ArxivArchive` 的核心模块直接并入当前 backend。**

集成方式：

- 将 `crawl`、`judge`、`analyze` 相关核心模块迁入 `backend/app` 或 `backend/src` 体系。
- 迁入源码的本地来源固定为 `/Users/hpcow/codes/ArxivArchive`。
- 由当前 backend 统一管理配置、日志、Redis worker、数据库落库和前端查询接口。
- 不再依赖“外部项目先产出 JSON 再导入”的双系统边界。

这样做的直接好处：

- 运行时只维护一个服务体系。
- `Huey + Redis` 可以直接调内部 discovery pipeline，不需要再走外部桥接层。
- 前端展示、任务创建、发现流落库、运行日志都在同一套 backend 边界里。
- 后续如果要给 discovery pipeline 增加状态页、运行历史、失败重试，会更自然。

需要接受的代价：

- 当前 backend 会变重。
- 配置和依赖会增多。
- 需要认真处理 discovery pipeline 与翻译 pipeline 的模块隔离，避免互相污染。

这条路线既然已经确认，就不再把“外部项目结构化导入”作为主路线，只保留为备选迁移思路。

## 7. 产品形态设计

## 7.1 新增页面

### `DiscoverPage`

用途：

- 展示今日 / 近几日新抓取论文。
- 支持按分类、worth_read、关键词、是否已翻译筛选。

推荐区块：

- 今日推荐
- 值得阅读
- 全部新论文
- 已有翻译结果
- 我的收藏夹入口

论文卡片建议字段：

- 英文标题
- 中文标题
- arXiv ID
- category
- authors
- 中文摘要
- worth_read badge
- AI comment
- 是否已有翻译结果
- 是否已收藏
- 可加入哪些收藏夹
- `Add to Collection`
- `View History`

论文卡片推荐交互：

- 默认不提供醒目的“立即翻译”主按钮。
- 主动作应该是 `Add to Collection`。
- 若用户已经把论文加入某个收藏夹，则展示该收藏夹的翻译策略：
  - `auto-translate`
  - `manual-translate`
- 若已有历史翻译结果，则提供 `View History` / `Reuse Existing Result`。

### `PaperDetailPage`

用途：

- 展示某篇论文的聚合详情。

建议内容：

- 原始元数据
- AI 粗筛结果
- 原文链接 / PDF 链接
- 已加入的收藏夹列表
- 每个收藏夹对应的翻译策略
- 历史翻译任务列表
- 最新可用翻译结果
- 共享情况
- `crawl -> judge -> analyze -> persist -> translate` 工作流可视化

工作流可视化建议：

- 前端使用 `React Flow` 当前官方包 `@xyflow/react`，不要再使用旧包名 `reactflow`。
- 在论文详情页放一个可折叠的 `Pipeline` 卡片，默认展示简化流程图。
- 节点建议至少包含：
  - `crawl`
  - `judge`
  - `analyze`
  - `persist`
  - `translate`
- 边的方向固定为从左到右，避免用户把它理解成可编辑工作流编排器。
- 这是“执行过程解释图”，不是 BPMN 设计器，所以前端应该只读，不开放拖拽保存。

每个节点建议展示的内容：

- `crawl`
  - 抓取分类
  - 抓取时间
  - 抓到的论文数

- `judge`
  - 使用模型
  - worth_read 判定
  - 简评摘要

- `analyze`
  - 是否成功抽取 Tex / figure
  - 中文标题
  - 中文摘要

- `persist`
  - 落库时间
  - 当前系统中的 `paper_id`
  - 是否已建立任务关联

- `translate`
  - 是否已被某个收藏夹纳入翻译范围
  - 当前采用自动翻译还是手动翻译
  - 是否已有历史任务
  - 是否命中缓存

推荐交互：

- 点击节点，右侧或下方展示节点详情面板。
- `judge` / `analyze` 节点可以展开查看结构化结果摘要。
- `translate` 节点可直接跳转任务详情页或触发新任务创建。
- 如果论文尚未进入任何收藏夹，`translate` 节点应展示“等待用户决策”而不是直接进入执行态。

推荐视觉语义：

- `crawl` 用信息采集色
- `judge` 用决策色
- `analyze` 用 AI 处理色
- `persist` 用系统同步色
- `translate` 用产出色

状态建议：

- `pending`
- `running`
- `succeeded`
- `failed`
- `skipped`

节点样式可以根据状态变化，但不建议一开始就做复杂动画；MVP 阶段先把结构和状态含义做清楚。

### `CollectionsPage`

MVP 阶段它就是 discovery 偏好和后续翻译策略的核心载体。

用途：

- 管理当前用户的多个收藏夹
- 为每个收藏夹设置用途和描述
- 为每个收藏夹设置关注的 arXiv 分类
- 为每个收藏夹设置 `prefer / not prefer` 关键词
- 为每个收藏夹设置翻译策略

收藏夹建议字段：

- 收藏夹名称
- 收藏夹描述
- 关注分类
- `prefer_keywords`
- `avoid_keywords`
- 文章数量
- 默认翻译策略：
  - `manual`
  - `auto`
- 当前偏好摘要

说明：

- 当前方案不再单独引入 `SubscriptionsPage` 或 `arxiv_collection_subscriptions`。
- discovery 偏好直接挂在 `arxiv_collections` 上，由每个收藏夹同时承载“发现入口”和“后续翻译策略”。

## 7.2 首页/任务页增强

即便不立刻做完整发现页，也建议先做两个轻量入口：

1. 在任务首页增加 `Today's arXiv Picks` 卡片
2. 在任务首页或发现页增加 “My Collections” 卡片
3. 在创建任务页增加 “从收藏夹中的待翻译论文快速创建” 区块

这样可以先验证真实使用行为，再决定要不要把发现页做成一级导航。

## 8. 后端能力设计

## 8.1 新增领域对象

建议新增以下逻辑实体。

### `arxiv_papers`

表示系统内收录的一篇论文主记录。

建议字段：

- `id`
- `arxiv_id`
- `primary_category`
- `published_at`
- `scraped_at`
- `title_en`
- `abstract_en`
- `authors_json`
- `pdf_url`
- `abs_url`
- `subjects_json`
- `comments`
- `source_run_date`
- `created_at`
- `updated_at`

约束建议：

- `arxiv_id` 唯一索引

### `arxiv_paper_reviews`

表示 AI 粗筛/分析结果，和论文主表分离，并且按 `collection` 维度存储，便于同一篇论文针对不同收藏夹生成不同判断结果。

建议字段：

- `id`
- `paper_id`
- `collection_id`
- `review_type`
- `model_name`
- `worth_read`
- `title_zh`
- `abstract_zh`
- `comment`
- `raw_result_json`
- `created_at`

说明：

- `review_type` 可以先只支持 `daily_judge`。
- 同一篇论文可以针对不同 `collection` 存在多条 review。
- `title_zh` / `abstract_zh` / `worth_read` / `comment` 在一期先都按 `collection` 视角落库，避免把个性化判断误建成全局唯一结果。
- 后续若做“精读总结”“周报摘要”，可以继续复用。

### `arxiv_collections`

表示用户自定义收藏夹，同时也是 discovery 偏好配置的承载对象。

建议字段：

- `id`
- `user_id`
- `name`
- `description`
- `categories_json`
- `prefer_keywords`
- `avoid_keywords`
- `translation_mode`
- `auto_translate_enabled`
- `created_at`
- `updated_at`

说明：

- 一个用户可以拥有多个收藏夹。
- `categories_json` 用于定义该收藏夹关心的 arXiv 分类。
- `prefer_keywords` / `avoid_keywords` 用于定义该收藏夹视角下的 AI 判断偏好。
- `translation_mode` 建议先支持：
  - `manual`
  - `auto`
- `auto_translate_enabled` 和 `translation_mode` 可以先保留，但一期后端只保存策略，不实际触发自动翻译任务。

### `arxiv_collection_items`

表示某篇论文被加入了哪个收藏夹。

建议字段：

- `id`
- `collection_id`
- `paper_id`
- `added_by_user_id`
- `note`
- `translate_decision`
- `created_at`
- `updated_at`

说明：

- 同一篇论文可以进入同一用户的多个收藏夹。
- `translate_decision` 建议先支持：
  - `pending`
  - `manual_requested`
  - `auto_queued`
  - `translated`

### `arxiv_paper_task_links`

表示论文与翻译任务的关联关系。

建议字段：

- `id`
- `paper_id`
- `task_id`
- `link_type`
- `created_by_user_id`
- `created_at`

说明：

- 理论上通过 `arxiv_id` 也能反查任务，但独立关系表更稳。
- 后续如果支持“不是 arXiv 原生任务，但人为关联这篇论文”，也更灵活。

## 8.2 新增服务边界

建议新增：

- `backend/app/services/arxiv_discovery_service.py`
- `backend/app/services/arxiv_pipeline_service.py`
- `backend/app/services/arxiv_persistence_service.py`
- `backend/app/services/arxiv_collection_service.py`
- `backend/app/repositories/arxiv_repository.py`
- `backend/app/api/routes/discovery.py`

职责建议：

- `arxiv_discovery_service`
  - 面向前端提供论文列表、详情、聚合状态。

- `arxiv_pipeline_service`
  - 负责编排 `crawl -> judge -> analyze` 主流程。

- `arxiv_persistence_service`
  - 负责将 discovery pipeline 结果落库，并维护论文与任务关联。

- `arxiv_collection_service`
  - 负责收藏夹、收藏动作、分类偏好、关键词偏好与翻译策略配置。

## 8.3 新增接口建议

### 发现相关

- `GET /api/discovery/papers`
- `GET /api/discovery/papers/{paper_id}`
- `GET /api/discovery/daily-digest`

### 收藏夹相关

- `GET /api/discovery/collections`
- `POST /api/discovery/collections`
- `PATCH /api/discovery/collections/{collection_id}`
- `POST /api/discovery/collections/{collection_id}/items`
- `DELETE /api/discovery/collections/{collection_id}/items/{paper_id}`

### 管理/同步相关

- `POST /api/admin/discovery/sync`
- `GET /api/admin/discovery/runs`

## 8.4 与现有任务系统的衔接

收藏夹触发的翻译请求不应该另起一条全新的翻译链路。

推荐做法：

- 用户先把论文加入某个收藏夹。
- 若收藏夹是 `manual` 模式，则由用户显式点击翻译。
- 若收藏夹是 `auto` 模式，则先只记录策略，不在一期直接触发后台翻译任务。
- 真正创建任务时，后端仍然根据 `paper_id` 取出 `arxiv_id`。
- 内部复用现有 `TaskService.create_task(...)`
- payload 仍然只传：
  - `source_type=arxiv`
  - `arxiv_id=<paper.arxiv_id>`

这样可以保留当前已经验证过的几项约束：

- 创建任务仍然是标准入口
- 缓存仍然正常命中
- 额度规则仍然一致
- 历史归档仍然走同一套
- 并且用户始终保有“是否真的翻译”的决策权

## 9. 数据同步设计

## 9.1 推荐的数据流

建议的数据流如下：

`Huey periodic task -> backend 内部 Arxiv crawl -> judge -> analyze -> persist -> 数据库存储 -> 前端发现流展示`

由于核心模块直接并入 backend，MVP 阶段不再把“外部 JSON 导入协议”作为主链路设计。

## 9.2 内部数据契约建议

虽然不再走跨项目导入，但 discovery pipeline 内部仍应保持稳定的结构化对象边界，至少包含：

- `run_date`
- `category`
- `articles[]`

每篇文章建议包含：

- `arxiv_id`
- `title`
- `abstract`
- `authors`
- `pdf_url`
- `abs_url`
- `subjects_primary`
- `subjects_other`
- `comments`
- `matched_collection_ids[]`
- `collection_reviews[]`

每个 `collection_reviews[]` 建议至少包含：

- `collection_id`
- `worth_read`
- `chinese_name`
- `chinese_abstract`
- `comment`

这比“每篇论文只存一份全局 worth_read/comment”的契约更符合当前方案，因为不同收藏夹可以配置不同分类和 `prefer / not prefer` 关键词。

## 9.3 定时执行方式

当前方案改为：

**使用 `Huey + Redis` 作为发现流同步与后续后台任务的统一执行基础。**

原因：

- 已经有现成 Redis 中间件可复用。
- 比 `Celery + Beat + RedBeat` 更轻，适合当前项目体量。
- 不只是能做定时执行，还能顺手承接后续独立 worker 化。
- 比单独把 scheduler 嵌进 API 进程更稳，也比外部 cron + 管理接口更容易演进成正式后台任务系统。

推荐落地方式：

1. API 进程只负责创建/查询/触发任务，不直接执行发现流同步。
2. 单独启动 `Huey consumer` 处理后台 job。
3. discovery 同步任务通过 `periodic_task(crontab(...))` 周期触发。
4. 同步任务内部串行执行：
   - `crawl`
   - `judge`
   - `analyze`
   - `persist`
5. 未来如果要把翻译任务从 `ThreadPoolExecutor` 迁出，也优先迁到同一套 Redis worker 体系。

MVP 阶段建议：

- 先只让 `Huey` 接 discovery sync 这条链路。
- 暂时不要在第一期同时迁移现有翻译任务执行器。
- 但目录设计和服务边界要预留后续统一迁移空间。

建议新增模块：

- `backend/app/worker/huey_app.py`
- `backend/app/worker/discovery_jobs.py`
- `backend/app/worker/discovery_schedule.py`

建议的第一条周期任务：

- 每天按固定时区运行一次 `sync_daily_arxiv_digest`
- 抓取范围不是来自环境变量，而是来自当前所有 `arxiv_collections.categories_json` 的分类并集
- 对命中的 `collection` 分别带入各自的 `prefer_keywords` / `avoid_keywords` 执行 judge / analyze

建议的第二类后台任务：

- `process_auto_translate_collections`
- 保留为后续阶段扩展点，一期先不实现

配置原则补充：

- discovery 运行时配置尽量收紧，一期只需要 `REDIS_URL` 和必要的时区开关。
- `judge` / `analyze` 默认复用现有 `OPENAI_MODEL`，不额外拆分新的 discovery model 环境变量。
- `MAX_FIGURE_NUM` 一期直接固定为 `20`，先不要暴露为环境变量。

配置原则：

- 时区必须显式配置，避免宿主机时区漂移。
- 运行频率先按“每日一次”做，不要一开始做高频拉取。
- 同步 job 要有幂等控制，避免重复落库同一批论文。

## 10. 分阶段落地建议

## Phase 1：最小可用发现流

目标：

- 把 `ArxivArchive` 核心能力并入当前 backend
- 先把后端 discovery 主链路做通
- 能按收藏夹视角生成个性化论文判断结果
- 能把论文加入用户自定义收藏夹
- 能在收藏夹中配置分类、`prefer / not prefer` 与翻译策略

范围：

- 新增 `arxiv_papers` / `arxiv_paper_reviews`
- 新增 `arxiv_collections` / `arxiv_collection_items`
- 新增 `Huey + Redis` discovery 同步任务
- 新增 backend 内部 discovery pipeline 服务边界
- 同步任务按所有 `collection` 的分类并集抓取
- review 结果按 `collection` 维度落库
- 新增 discovery 查询 API、收藏夹 API、管理员手动同步入口

不做：

- 不做独立订阅系统
- 不做消息推送
- 不做站外推送
- 不做自动翻译任务触发
- 不做复杂自动翻译规则引擎
- 不在一期同时要求前端页面全部完成

这是最推荐先落地的一期。

## Phase 2：前端发现页与团队推荐

目标：

- 从“后端能力可用”升级到“站内发现入口真正可用”

范围：

- `DiscoverPage`
- `CollectionsPage`
- `Pipeline` 可视化卡片
- 首页推荐卡片
- `worth_read` 过滤
- 团队推荐 / 收藏 / 稍后阅读
- 任务详情页增加“来自哪篇论文”的跳转入口

## Phase 3：主动内容生产

目标：

- 让系统不只是“展示论文”，还主动沉淀团队研究资产

范围：

- 自动翻译收藏夹中的选中论文
- 收藏夹自动翻译规则增强
- 每周周报
- 精读包
- 热门论文共享与复用统计

## 11. 风险与注意点

### 11.1 不要让发现模块反向污染翻译核心

`latex_trans_prod` 当前最稳定、最值钱的部分仍然是翻译任务链路。发现流应该作为上游域模块接入，而不是把翻译服务改造成“顺便做爬虫”的巨石。

### 11.2 不要先做推送，先做站内闭环

邮件、飞书、企业微信这些推送能力很诱人，但它们会显著增加配置、通知失败、权限、频控等问题。

在没有验证“站内发现页是否真的有人每天打开”之前，不建议优先投入。

### 11.3 先落结构化数据，再做 markdown 展示增强

`ArxivArchive` 当前 markdown 日报很适合人看，但在“核心模块已并入 backend”的前提下，产品集成优先级应该是：

1. 先拿结构化数据
2. 再做页面
3. 最后再考虑导出日报 markdown / HTML

### 11.4 worth_read 不能被误建成单一全局结论

建议前端支持三种视图：

- 全部论文
- 值得阅读
- 已翻译 / 有历史结果

另外，当前方案下 `worth_read` 是和 `collection` 绑定的判断结果，不应该在数据层被默认设计成“同一篇论文全局只有一个 worth_read 值”，否则会错误覆盖不同收藏夹的研究偏好。

### 11.5 不要把发现流默认等同于自动翻译

发现流的职责是“帮助用户发现和判断”，不是“替用户批量开翻译任务”。

默认原则应该是：

- 论文先进入待判断态
- 用户决定是否加入某个收藏夹
- 收藏夹决定后续采用手动翻译还是自动翻译

这样更符合真实研究流程，也更能控制算力消耗。

## 12. 最终建议

如果现在只选一个新方向，我建议：

**优先做 “ArxivArchive 核心模块并入 backend、并以收藏夹驱动翻译决策的发现流 MVP”**

具体落点是：

1. 新增发现域数据表与 API
2. 接入 `ArxivArchive` 的内部 pipeline 模块
3. 新增站内 `Discover` 页面和 `Collections` 页面
4. 每篇论文支持加入收藏夹
5. 由收藏夹决定自动翻译或手动翻译
6. 如果已有翻译结果，优先展示历史结果入口

这个方向的好处是：

- 复用现有 `arxiv_id` 任务入口
- 放大缓存、归档、共享的已有价值
- 让产品从“翻译工具”升级成“论文工作台”
- 对内部团队使用频率提升最直接

## 13. 建议的下一步文档

如果确认走这条路线，下一份应该写的不是代码，而是：

`docs/arxiv-discovery-mvp-spec-2026-05-28.md`

这份文档建议进一步细化：

- 具体数据表草案
- API request/response
- 页面原型
- `Huey` discovery job 时序
- 和现有权限/缓存/配额的交互规则

也就是说，当前这份文档用于“定方向”，下一份文档用于“能开工”。
