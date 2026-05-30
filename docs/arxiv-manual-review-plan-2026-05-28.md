# LaTeXTrans arXiv 单篇论文手动 AI Review 方案

更新时间：2026-05-28

关联文档：

- `docs/arxiv-discovery-integration-plan-2026-05-28.md`
- `docs/arxiv-discovery-frontend-handoff-2026-05-28.md`
- `docs/backend-api-reference-2026-05-26.md`
- `docs/productization-auth-sharing-cache-plan-2026-05-27.md`

## 1. 这次要补的能力

当前系统已经具备两类和论文相关的能力：

- discovery 流会在每日同步时批量生成 `arxiv_paper_reviews`
- 用户可以从论文详情页直接 `Translate now`，把论文送入翻译任务系统

但现在还缺一个很自然的中间动作：

`用户在发现页/论文详情页看到一篇论文 -> 不想立刻翻译 -> 先手动触发一次 AI review -> 再决定值不值得读/值不值得翻译`

这次文档要确定的就是这条能力链路。

## 2. 当前实现约束与设计结论

先基于当前代码现实做判断，而不是重新发明一套新域模型。

### 2.1 当前 review 的真实归属

当前 `arxiv_paper_reviews` 不是“全局公共评论”，而是：

- 通过 `collection_id` 绑定到某个收藏夹
- prompt 依赖该收藏夹的 `categories_json`、`prefer_keywords`、`avoid_keywords`
- 前端展示时也只看“当前用户自己的 collection 下可见 review”

也就是说，现有 review 实际上是 **collection-scoped AI opinion**，不是 paper-global opinion。

### 2.2 本期结论

本期手动 AI review 不做“全局 paper review”，而是明确采用：

**collection-scoped manual review**

具体含义：

- 用户手动 review 一篇论文时，必须明确选择一个自己的 collection
- review 结果仍然落在 `arxiv_paper_reviews`
- 但 `review_type` 不再只有 `daily_judge`，新增 `manual_judge`
- 不新增“无 collection 的 review”形态
- 不新增单独的 review task / review artifact / review quota 系统

这样做的原因：

1. 和现有数据模型最一致，不需要为“review owner”额外补一层权限字段
2. prompt 仍然能复用“按收藏夹偏好判断是否值得读”的现有产品语义
3. 前端能直接在现有 `DiscoverPage` / `PaperDetailPage` 上加入口，不需要新页面
4. 后端改动集中在 discovery 域，不会污染翻译任务域

## 3. 本期产品规则

### 3.1 用户触发规则

- 用户只能对自己的 collection 触发 manual review
- 一次 manual review 只能针对一个 `paper + collection`
- 如果论文尚未加入任何 collection，前端先引导用户 `Add to collection`
- `Translate now` 和 `AI Review` 是并列动作，不互相包含

### 3.2 review 结果规则

- `daily_judge` 代表系统日同步阶段产出的粗筛结果
- `manual_judge` 代表用户在页面上主动触发的单篇精细 review
- 同一 `paper + collection + review_type` 只保留一条最新记录
- 默认允许重复触发 manual review，但通过 `force_refresh` 控制是否覆盖旧结果

### 3.3 配额与计费规则

本期建议：

- manual review 不接入现有 translation quota
- 不创建 `translation_tasks`
- 不写入 `task_events` / `task_artifacts`

原因不是它永远不需要成本控制，而是当前仓库里的 quota 体系明确面向翻译任务。若本期把 review 也并进去，会把需求从“补一个 discovery 能力”放大成“重做一套通用 AI 调用计费层”。

后续如果 review 使用频率很高，再单独设计 `review_quota` 或统一 AI usage ledger。

## 4. 推荐交互流程

## 4.1 DiscoverPage

推荐新增次级动作：

- `AI Review`

点击后行为：

- 若论文未加入任何 collection，弹窗提示先加入 collection
- 若已加入一个 collection，默认选中该 collection
- 若已加入多个 collection，用户选择以哪个 collection 视角发起 review
- 可选填写一段 `focus_prompt`
  - 例如：`重点看 novelty 和实验是否扎实`

成功后：

- toast 提示 review 完成
- 刷新 `discovery-paper`、`discovery-papers`、`discovery-daily-digest`
- 卡片上更新 `worth_read` / `comment` / `title_zh` / `abstract_zh`

### 4.2 PaperDetailPage

推荐在当前按钮组中形成三件事：

- `Add to collection`
- `AI Review`
- `Translate now`

其中：

- `AI Review` 是这次新增主能力
- `Translate now` 保持现有能力不变
- `Review history` 区块里要能区分 `daily_judge` 和 `manual_judge`

## 5. 新接口设计

本期新增一个接口即可，不单独拆查询接口。

### 5.1 `POST /api/discovery/papers/{paper_id}/reviews`

用途：

- 手动触发某篇论文在某个 collection 视角下的 AI review

认证：

- 复用当前 discovery 域的登录态认证
- 与现有实现一致，继续使用 cookie session
- 本期不引入新的 JWT-only 接入方式

请求体：

```json
{
  "collection_id": 12,
  "force_refresh": true,
  "model_name": "gpt-4.1-mini",
  "focus_prompt": "重点看方法创新性、实验可信度和是否值得投入翻译",
  "source": "paper_detail"
}
```

字段说明：

- `collection_id`: 必填，只允许当前用户自己的 collection
- `force_refresh`: 可选，默认 `false`
- `model_name`: 可选，默认沿用当前 discovery judge 模型配置
- `focus_prompt`: 可选，给这次手动 review 增加一次性关注点
- `source`: 可选，仅用于埋点/调试，推荐值 `discover_card` / `paper_detail`

响应体：

```json
{
  "review": {
    "id": 101,
    "collection_id": 12,
    "collection_name": "LLM Agents",
    "review_type": "manual_judge",
    "model_name": "gpt-4.1-mini",
    "worth_read": true,
    "title_zh": "......",
    "abstract_zh": "......",
    "comment": "......",
    "raw_result_json": {
      "judge": {},
      "analysis": {},
      "request": {
        "focus_prompt": "重点看方法创新性、实验可信度和是否值得投入翻译",
        "source": "paper_detail",
        "trigger_mode": "manual"
      }
    },
    "created_at": "2026-05-28T14:00:00Z",
    "updated_at": "2026-05-28T14:00:00Z"
  },
  "paper": {
    "...DiscoveryPaperDetailResponse": "..."
  },
  "reused_existing": false,
  "message": "Manual review completed."
}
```

行为约束：

- 当 `force_refresh=false` 且该 `paper + collection + manual_judge` 已存在时：
  - 直接返回现有 review
  - `reused_existing=true`
- 当 `force_refresh=true` 时：
  - 覆盖旧的 manual review 内容
  - `updated_at` 刷新
- 该接口只写 discovery review，不创建翻译任务

### 5.2 为什么不新加 `GET /reviews`

因为当前 `GET /api/discovery/papers/{paper_id}` 已经返回：

- `reviews[]`
- `tasks[]`
- `latest_task`

只要把 `manual_judge` 一并纳入 `reviews[]`，前端不需要额外补查询接口。

## 6. 后端改造方案

## 6.1 数据模型

目标文件：

- `backend/app/models/discovery.py`

改造点：

1. 扩展 `ArxivPaperReviewType`

新增：

- `MANUAL_JUDGE = "manual_judge"`

2. 保持 `collection_id` 非空

结论：

- 本期不把 `collection_id` 改成 nullable
- 不引入 global review owner 字段

3. 保留当前唯一性语义，但实现层要改

当前索引已经是：

- `(paper_id, collection_id, review_type)` 唯一

这正好支持 `daily_judge` 和 `manual_judge` 并存。

## 6.2 repository 层

目标文件：

- `backend/app/repositories/arxiv_repository.py`

改造点：

1. `get_review(...)` 需要改成带 `review_type`

建议签名：

```python
def get_review(
    self,
    *,
    paper_id: int,
    collection_id: int,
    review_type: ArxivPaperReviewType,
) -> ArxivPaperReview | None:
```

2. 如需要更清晰，也可以补一个：

```python
def list_reviews_for_paper(self, *, paper_id: int, current_user: User) -> list[ArxivPaperReview]:
```

不过这不是必须项，因为当前 `get_paper_by_id()` 已经 eager load 了 reviews。

## 6.3 persistence 层

目标文件：

- `backend/app/services/arxiv_persistence_service.py`

改造点：

1. `upsert_review(...)` 增加 `review_type`

建议签名：

```python
def upsert_review(
    self,
    *,
    paper: ArxivPaper,
    collection: ArxivCollection,
    review_type: ArxivPaperReviewType,
    model_name: str,
    worth_read: bool,
    title_zh: str | None,
    abstract_zh: str | None,
    comment: str | None,
    raw_result_json: dict[str, Any] | None,
) -> ArxivPaperReview:
```

2. 每日同步路径显式写 `DAILY_JUDGE`

3. 手动 review 路径显式写 `MANUAL_JUDGE`

## 6.4 review service 抽取

当前 review 逻辑散在：

- `backend/app/services/arxiv_pipeline_service.py`
  - `_build_review`
  - `_judge_article`
  - `_get_judge_agent`
  - `_build_judger_prompt`
  - `_fallback_judge`
  - `_analyze_source_metadata`

本期不建议继续把 manual review 逻辑也堆进 pipeline service。推荐抽一个共享服务：

- `backend/app/services/arxiv_review_service.py`

建议职责：

1. 根据 `paper + collection + focus_prompt` 组装 prompt
2. 调用 OpenAI / fallback judge
3. 生成统一的 review payload
4. 复用给：
   - discovery 每日同步
   - 手动 review 接口

建议接口形态：

```python
class ArxivReviewService:
    def build_review_for_article(...)
    def build_review_for_paper(...)
```

其中：

- `build_review_for_article(...)` 给每日同步时使用
- `build_review_for_paper(...)` 给单篇手动 review 使用

这样可以避免手动 review 为了拿 prompt 和 model 调用逻辑，又反向依赖整个抓取 pipeline。

## 6.5 discovery service

目标文件：

- `backend/app/services/arxiv_discovery_service.py`

新增方法建议：

```python
def create_manual_review(
    self,
    paper_id: int,
    payload: DiscoveryPaperManualReviewRequest,
    *,
    current_user: User,
) -> DiscoveryPaperManualReviewResponse:
```

核心行为：

1. 校验 paper 存在
2. 校验 collection 属于当前用户
3. 可选校验 paper 是否已在该 collection 中
   - 推荐要校验
   - 这样页面语义更一致，也避免“一个 collection 从没收过这篇论文却先有 review”
4. 查询是否已有 `manual_judge`
5. 若已有且 `force_refresh=false`，直接返回
6. 若需要刷新，则调用 `ArxivReviewService`
7. 用 `ArxivPersistenceService.upsert_review(...)` 写回
8. 返回更新后的 `paper detail`

### 6.6 schema 与 route

目标文件：

- `backend/app/schemas/discovery.py`
- `backend/app/api/routes/discovery.py`

建议新增 schema：

```python
class DiscoveryPaperManualReviewRequest(APIModel):
    collection_id: int
    force_refresh: bool = False
    model_name: str | None = Field(default=None, max_length=128)
    focus_prompt: str | None = Field(default=None, max_length=2000)
    source: str | None = Field(default=None, max_length=64)


class DiscoveryPaperManualReviewResponse(APIModel):
    review: DiscoveryPaperReviewResponse
    paper: DiscoveryPaperDetailResponse
    reused_existing: bool = False
    message: str
```

route：

```python
@router.post(
    "/papers/{paper_id}/reviews",
    response_model=DiscoveryPaperManualReviewResponse,
    status_code=status.HTTP_200_OK,
)
def create_manual_review(...):
    ...
```

### 6.7 summary 选择策略

当前 `_pick_review(...)` 优先逻辑是：

- 先 preferred collection
- 再 worth_read=true 的最新 review
- 再最新 review

手动 review 加进来后，建议改成：

1. 若指定 `preferred_collection_id`
   - 先取该 collection 下最新的 `manual_judge`
   - 再取该 collection 下最新的 `daily_judge`
2. 若未指定 collection
   - 先取所有可见 `manual_judge` 中最新的 worth_read=true
   - 再取所有可见 `manual_judge` 中最新的
   - 再退回 `daily_judge`

这样用户刚刚手动触发的结果能立刻体现在列表摘要上，不会被旧的 daily review 抢掉。

## 7. 前端改造方案

## 7.1 类型与 API 封装

目标文件：

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`

改造点：

1. 扩展 `DiscoveryPaperReview.review_type`

从：

- `"daily_judge"`

改成：

- `"daily_judge" | "manual_judge"`

2. 新增 payload / response type

建议新增：

- `DiscoveryPaperManualReviewPayload`
- `DiscoveryPaperManualReviewResponse`

3. 新增 API 方法

```ts
export function createManualReviewForDiscoveryPaper(
  paperId: number,
  payload: DiscoveryPaperManualReviewPayload
) {
  return withApiError(
    api.post<DiscoveryPaperManualReviewResponse>(`/discovery/papers/${paperId}/reviews`, payload)
  )
}
```

## 7.2 DiscoverPage

目标文件：

- `frontend/src/pages/discover-page.tsx`

改造点：

1. 论文卡片增加 `AI Review` 次级入口
2. 复用类似 `Add to collection` 的 dialog 交互
3. 弹窗字段建议：
   - `collection`
   - `focus_prompt`
   - `force_refresh`
4. 提交时按钮文案：
   - idle: `Run AI review`
   - pending: `Reviewing...`
5. 成功后 invalidate：
   - `["discovery-papers"]`
   - `["discovery-paper", paper.id]`
   - `["discovery-daily-digest"]`
   - `["discovery-collections"]`

## 7.3 PaperDetailPage

目标文件：

- `frontend/src/pages/paper-detail-page.tsx`

改造点：

1. 当前顶栏按钮从两项改成三项

- `Add to collection`
- `AI Review`
- `Translate now`

2. review dialog 交互建议

- 若 `paper.collections.length === 0`：
  - 禁用 `AI Review`
  - 或点击后提示 `Add this paper to a collection first.`
- 若只有一个 collection：
  - 默认选中
- 若多个 collection：
  - 让用户显式选择

3. `Review history` 区块增加来源标签

建议 badge：

- `Daily review`
- `Manual review`

4. 摘要卡片中的主 comment / title_zh / abstract_zh 应跟随后端新的 summary 选择策略，无需前端自己排优先级

## 8. 实施顺序

推荐按下面顺序落地，避免边改边散：

1. 抽 `ArxivReviewService`
2. 扩展 `ArxivPaperReviewType` 与 persistence/repository 签名
3. 新增 `POST /api/discovery/papers/{paper_id}/reviews`
4. 调整 `DiscoveryPaperDetailResponse` / summary 取值逻辑
5. 前端补 type + api client
6. 前端先改 `PaperDetailPage`
7. 再补 `DiscoverPage` 卡片入口
8. 最后回写 `docs/backend-api-reference-2026-05-26.md`

## 9. 本期不做

这次先明确不做以下内容：

- 不做“无 collection 的全局 manual review”
- 不做单独的 review 任务表 / review 运行历史页
- 不做 review artifact 存储
- 不做 review 配额或 token 计费
- 不做批量勾选多篇论文后一起 manual review
- 不做 admin 替别人触发 review

## 10. 最终落地方向

本期推荐的最终方案可以概括成一句话：

**在现有 discovery 域内新增一个 collection-scoped 的单篇 manual review 接口，把它做成 `Translate now` 之前的人工判断动作，而不是新建一套独立 review 系统。**

这样能以最小改动补上真正缺失的产品动作，同时保持当前 discovery、collection、translation 三层边界仍然清晰。
