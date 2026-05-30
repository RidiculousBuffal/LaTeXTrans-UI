# LaTeXTrans arXiv Discovery 全局 Enrichment 与 Collection Judgment 解耦重构方案

更新时间：2026-05-30

关联文档：

- `docs/arxiv-discovery-integration-plan-2026-05-28.md`
- `docs/arxiv-manual-review-plan-2026-05-28.md`
- `docs/arxiv-discovery-frontend-handoff-2026-05-28.md`
- `docs/backend-api-reference-2026-05-26.md`

## 1. 这份文档要解决什么问题

当前 discovery 实现里，`title_zh`、`abstract_zh`、`worth_read`、`comment` 被一起写入 `arxiv_paper_reviews`。

这在第一期能快速跑通，但从产品语义和数据边界看已经出现了明显耦合：

- `title_zh` / `abstract_zh` 本质上是 **paper-global enrichment**
- `worth_read` / `comment` 本质上是 **collection-scoped judgment**
- 两者现在由同一个 judge prompt 一次性生成，并落在同一张 review 表里

这会导致：

1. 同一篇论文在不同 collection 下重复存储中文标题和中文摘要。
2. 全局公共字段被错误地建模成“某个 collection 的 opinion”。
3. 后续引入 `manual_judge`、不同模型、重新翻译、review history 后，字段语义会继续混乱。
4. 前端容易把“已有中文标题摘要”误认为“已有 review”或“甚至已翻译”。

这份文档的目标，就是把 discovery 域重构成：

`paper metadata -> global enrichment -> collection-scoped judgment -> translate decision`

而不是继续把这些职责堆进 `arxiv_paper_reviews`。

## 2. 当前实现的真实状态

当前落地状态可以概括为：

1. `arxiv_papers`
   - 保存原始论文元信息
2. `arxiv_paper_reviews`
   - 绑定 `collection_id`
   - 目前同时保存：
     - `title_zh`
     - `abstract_zh`
     - `worth_read`
     - `comment`
3. `arxiv_collection_items`
   - 表示论文被加入哪个 collection
   - `translate_decision` 表示后续翻译动作
4. `arxiv_paper_task_links`
   - 负责 discovery paper 与 translation task 的关联

当前 judge 流程实际是：

`crawl article -> match collection -> judge(article, collection) -> write review`

而 judge 输出里同时包含：

- `chinese_name`
- `chinese_abstract`
- `worth_read`
- `comment`

这说明“翻译标题/摘要”和“按偏好判断 worth_read”现在确实被实现成了一个 agent 的单次输出。

## 3. 为什么现在这套架构不合理

## 3.1 数据归属错位

`title_zh` 和 `abstract_zh` 不依赖某个用户、某个 collection，也不应该因为 collection 偏好不同而变化。

因此它们不应该放在：

- `arxiv_paper_reviews`
- 任何带 `collection_id` 的表
- 任何默认被理解成 opinion / judgment 的记录里

它们应该属于：

- `arxiv_papers` 的扩展信息
- 或独立的 `paper enrichment` 表

## 3.2 存储冗余会越来越严重

如果一篇论文命中 10 个 collection，当前设计就会写 10 份：

- `title_zh`
- `abstract_zh`

这不仅浪费存储，更重要的是会把后续“重跑翻译”“切模型”“保留历史版本”的问题变得更难处理。

## 3.3 运行职责混杂

现在一个 agent 同时做两类性质完全不同的工作：

1. 语义翻译 / 规范化
2. 偏好判断 / 推荐判断

这会让 prompt 和输出都不稳定：

- 如果强调忠实翻译，`worth_read` 判断可能变弱
- 如果强调 collection preference，`title_zh` / `abstract_zh` 可能带入过多“解释性改写”

## 3.4 产品语义容易误导

在当前返回模型里，前端经常会看到：

- `title_zh`
- `abstract_zh`
- `worth_read`
- `has_translation`

如果这些字段都来自同一个 review 聚合，用户很容易误解成：

- “有中文摘要 = 已经翻译过”
- “worth_read = 全局结论”
- “我看到了 title_zh，但为什么 review 是 null”

这已经在当前 case 里暴露出来了。

## 4. 重构目标

本次重构建议围绕 5 个目标收敛：

1. 全局 enrichment 与 collection judgment 明确分层。
2. `title_zh` / `abstract_zh` 只生成一次，供所有用户复用。
3. `worth_read` / `comment` 保持 collection-scoped，不把它们错误升级成全局结论。
4. 让 discovery 列表、详情、manual review、translate decision 的字段来源更清晰。
5. 尽量兼容现有 discovery 与 translation 主链路，不推翻整套系统。

## 5. 推荐的新架构

## 5.1 核心原则

把 discovery 拆成 4 层：

1. `Paper`
   - 客观原始元数据
2. `Paper Enrichment`
   - 面向所有用户共享的 AI 加工结果
3. `Collection Judgment`
   - 某个 collection 视角下的 worth_read 判断
4. `Translation Decision / Task`
   - 是否进入翻译，以及翻译任务执行与复用

推荐流水线：

`crawl -> persist paper -> enrich globally -> match collections -> judge per collection -> add to collection / decide translate -> create or reuse translation task`

## 5.2 Agent 角色拆分

建议明确拆成两个逻辑 agent，而不是继续一个 agent 同时负责全部字段。

### A. Global Enrichment Agent

职责：

- 翻译 `title_en -> title_zh`
- 翻译 `abstract_en -> abstract_zh`
- 可选生成：
  - `summary_zh`
  - `keywords_zh`
  - `domain_tags`

特点：

- 不依赖 collection
- 不依赖用户偏好
- 结果对所有用户共享
- 更偏“忠实翻译 / 规范表达”

### B. Collection Judgment Agent

职责：

- 判断该 paper 在某个 collection 视角下是否 `worth_read`
- 生成 `comment`
- 可选生成：
  - `reason_tags`
  - `confidence`
  - `matched_preferences`
  - `matched_avoid_terms`

特点：

- 显式依赖 `collection`
- 输入包含：
  - `categories_json`
  - `prefer_keywords`
  - `avoid_keywords`
  - 可选 `focus_prompt`
- 更偏“推荐判断 / 研究偏好匹配”

这里更准确的说法不是“每个 category 一个 agent”，而是：

**一个 global enrichment agent + 一个 collection/policy-scoped judgment agent**

因为最终真正影响 `worth_read` 的不只是 category，还有 collection 偏好配置。

## 6. 推荐的数据模型调整

## 6.1 总体建议

我不建议把 `title_zh` / `abstract_zh` 直接继续塞回 `arxiv_papers` 主表。

最小改动当然可以这么做，但从可维护性看，更推荐单独新增一张 enrichment 表。

推荐新增：

- `arxiv_paper_enrichments`

保留：

- `arxiv_papers`
- `arxiv_paper_reviews`
- `arxiv_collection_items`
- `arxiv_paper_task_links`

## 6.2 推荐新表：`arxiv_paper_enrichments`

建议字段：

- `id`
- `paper_id`
- `enrichment_type`
  - 初期可先只有 `global_summary`
- `model_name`
- `title_zh`
- `abstract_zh`
- `summary_zh`
- `keywords_json`
- `raw_result_json`
- `created_at`
- `updated_at`

建议唯一性：

- `(paper_id, enrichment_type)` 唯一

如果后续要支持多版本，也可以改成：

- `(paper_id, enrichment_type, version)` 唯一
- 再加 `is_active`

但本期建议先保持简单。

## 6.3 `arxiv_paper_reviews` 重定义

重构后，`arxiv_paper_reviews` 不再承载标题摘要翻译，只承载 judgment。

建议保留字段：

- `id`
- `paper_id`
- `collection_id`
- `review_type`
- `model_name`
- `worth_read`
- `comment`
- `raw_result_json`
- `created_at`
- `updated_at`

建议新增可选字段：

- `reason_tags_json`
- `confidence_score`

建议移除字段：

- `title_zh`
- `abstract_zh`

注意：

这里的“移除”是目标态，不建议第一步就直接 drop column。

更稳妥的迁移顺序应该是：

1. 先新增 enrichment 表
2. 双写一段时间
3. 前后端切读
4. 再清理 review 表里的冗余字段

## 6.4 `arxiv_papers` 是否要加冗余快照字段

如果前端 discovery 列表对性能非常敏感，可以考虑在 `arxiv_papers` 上增加只读快照字段：

- `current_title_zh`
- `current_abstract_zh`

但我不建议第一步就这样做。

更好的顺序是：

1. 先用 enrichment 表保证语义正确
2. 观察查询性能
3. 如果确实需要，再加冗余快照或物化视图

## 7. 推荐的服务层拆分

## 7.1 新服务建议

### `backend/app/services/arxiv_enrichment_service.py`

职责：

- 基于 paper 元信息生成全局 enrichment
- 支持：
  - `build_global_enrichment_for_article(...)`
  - `build_global_enrichment_for_paper(...)`
  - `upsert_global_enrichment(...)`

### `backend/app/services/arxiv_judgment_service.py`

职责：

- 基于 collection 偏好生成 judgment
- 支持：
  - `build_judgment_for_article(...)`
  - `build_judgment_for_paper(...)`
  - `upsert_review(...)`

### `backend/app/services/arxiv_projection_service.py`

可选职责：

- 统一拼装 discovery summary/detail 的读模型
- 明确字段来源：
  - 标题摘要来自 enrichment
  - worth_read/comment 来自 selected review
  - has_translation 来自 task links

## 7.2 为什么不建议继续把逻辑堆在 `arxiv_pipeline_service.py`

当前 `arxiv_pipeline_service.py` 已经同时承担：

- crawl
- parse
- analyze source
- judge
- persistence

如果再把全局 enrichment、manual review、不同 review_type、不同模型切换都继续往里堆，后续维护成本会越来越高。

所以这次重构最好顺手把职责拆清：

- pipeline 负责 orchestrate
- enrichment service 负责全局翻译
- judgment service 负责 collection 判断
- persistence service 负责统一落库

## 8. 接口层怎么改

## 8.1 discovery summary/detail 返回模型

重构后建议明确字段来源：

- `title_zh`
- `abstract_zh`
  - 来自 `paper_enrichment`
- `worth_read`
- `comment`
  - 来自 `selected_review`
- `has_translation`
- `translation_task_count`
  - 来自 `task_links + access filter`

也就是说，summary/detail 不应该再把 `title_zh` / `abstract_zh` 绑定到“有没有 review”。

这样即使：

- 当前用户没有任何 review
- 但系统已经有全局 enrichment

前端仍然可以看到中文标题和中文摘要。

## 8.2 manual review 接口语义

`POST /api/discovery/papers/{paper_id}/reviews`

重构后建议语义变成：

- 只创建或更新 judgment
- 不负责生成 `title_zh` / `abstract_zh`

若该 paper 尚无全局 enrichment，可由后端：

1. 先懒生成 enrichment
2. 再执行 judgment

但返回结构里要明确区分：

- `enrichment`
- `review`

而不是仍旧只返回一份混合 review payload。

## 8.3 可选新增接口

如果后续要支持独立重跑全局摘要，可考虑新增：

- `POST /api/discovery/papers/{paper_id}/enrichment`

本期不是必须，但它能让“重跑标题摘要翻译”和“重跑 worth_read 判断”彻底分开。

## 9. 前端展示建议

## 9.1 Discovery 列表页

卡片字段建议分组显示：

### Global

- `title_zh`
- `abstract_zh`

### My Judgment

- `worth_read`
- `comment`
- `judged_by_collection`

### Translation

- `has_translation`
- `translation_task_count`
- `collections`

这样可以明显减少“这些字段是不是同一层语义”的误解。

## 9.2 Paper Detail 页

建议把详情页拆成 3 个可见区块：

1. `Global Enrichment`
   - 中文标题
   - 中文摘要
   - 可选 summary
2. `Review History`
   - 当前用户可见 judgments
   - 区分 `daily_judge` / `manual_judge`
3. `Translation History`
   - 任务列表
   - 最新结果

## 10. 迁移方案

## 10.1 目标

避免一次性硬切，尽量保证 discovery 列表、详情、manual review、已有数据都不被打断。

## 10.2 推荐分阶段迁移

### Phase 1. 新增 enrichment 表，不改旧读路径

工作：

- 新增 `arxiv_paper_enrichments`
- 新增 ORM / repository / schema
- discovery pipeline 在跑 review 前先生成 enrichment
- 开始双写：
  - `title_zh` / `abstract_zh` 写 enrichment
  - 旧字段暂时仍写 review

收益：

- 不影响当前前端
- 可以先把新增数据积累起来

### Phase 2. 切后端读路径

工作：

- `DiscoveryPaperSummaryResponse`
- `DiscoveryPaperDetailResponse`

改为：

- `title_zh` / `abstract_zh` 从 enrichment 读
- `worth_read` / `comment` 从 selected review 读

收益：

- 语义开始真正解耦

### Phase 3. 回填历史数据

工作：

- 从现有 `arxiv_paper_reviews` 按 `paper_id` 聚合出一份 enrichment
- 规则建议：
  - 优先取最新非空 `title_zh`
  - 优先取最新非空 `abstract_zh`
  - 若多个 review 内容不同，记录到 `raw_result_json.migration_candidates`

注意：

- 这一步要接受历史 review 里可能有轻微不一致
- 迁移目标是“恢复全局 enrichment”，不是追求历史完全可逆

### Phase 4. manual review 只写 judgment

工作：

- manual review 接口停止写 `title_zh` / `abstract_zh` 到 review
- review payload 聚焦 judgment 字段

### Phase 5. 清理 review 冗余字段

工作：

- 确认前后端、脚本、报表都不再依赖 review 里的 `title_zh` / `abstract_zh`
- 再发 migration drop column

## 11. 对现有代码的建议改动点

建议优先改这些文件：

1. `backend/app/models/discovery.py`
   - 新增 `ArxivPaperEnrichment`
   - 为 `ArxivPaper` 增加 enrichment relationship
2. `backend/app/services/arxiv_pipeline_service.py`
   - 拆出 global enrichment 与 collection judgment 两段
3. `backend/app/services/arxiv_persistence_service.py`
   - 新增 `upsert_enrichment(...)`
   - 收窄 `upsert_review(...)` 的职责
4. `backend/app/services/arxiv_discovery_service.py`
   - summary/detail 改从 enrichment 读 `title_zh` / `abstract_zh`
5. `backend/app/repositories/arxiv_repository.py`
   - eager load enrichment
6. `backend/app/schemas/discovery.py`
   - 明确 enrichment 字段与 review 字段边界

## 12. 本期不建议做的事

为了避免重构范围失控，本期不建议同时做：

1. 不把 review 提升成“全局 paper opinion”
2. 不引入新的 review task 系统
3. 不把 translation quota 和 review quota 强行统一
4. 不在第一步就支持 enrichment 多版本回溯
5. 不在第一步就支持“每个 category 一套独立 agent 编排”

## 13. 推荐结论

本次架构调整建议明确采用：

**全局 enrichment 和 collection-scoped judgment 解耦**

其中：

- `title_zh` / `abstract_zh` 属于全局共享 enrichment
- `worth_read` / `comment` 属于 collection judgment
- `Translate now` 与 translation task 继续保持下游执行层语义

一句话总结：

**先把“这篇论文中文是什么”与“这个 collection 觉得值不值得读”分开，再谈后续的 manual review、auto translate、cache reuse 和知识页聚合。**

## 14. 建议的下一步实施顺序

1. 先补 Alembic 迁移与 `ArxivPaperEnrichment` ORM。
2. 再改 pipeline 为 `enrich -> judge` 两段式。
3. 再切 discovery summary/detail 的读路径。
4. 最后处理历史数据回填和 review 冗余字段下线。

如果只允许先做一件事，优先级最高的是：

**先把 `title_zh` / `abstract_zh` 从 review 的逻辑归属里拿出来。**
