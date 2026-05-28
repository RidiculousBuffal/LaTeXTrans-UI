# Python Scheduler / Redis 方案调研

更新时间：2026-05-28

## 1. 当前项目语境

先结合当前 `latex_trans_prod` 的现状看这个问题：

- 当前后端没有正式的分布式队列框架。
- 现有翻译任务执行依赖 `backend/app/workers/translation_runner.py` 里的 `ThreadPoolExecutor(max_workers=2)`。
- 这意味着当前的“后台任务”本质上仍然是 API 进程内的本地线程池，而不是独立 worker 系统。

所以这次选型其实不是单纯挑一个“定时器”，而是在回答两个问题：

1. 我们只是想给 `ArxivArchive` 同步加一个定时触发器吗？
2. 还是想顺手把未来的翻译任务、同步任务都迁移到 Redis 驱动的 worker 架构里？

如果只是第 1 个问题，方案可以很轻。
如果是第 2 个问题，最好直接选一个能承接未来后台任务体系的框架。

## 2. 候选方案

## 2.1 APScheduler

定位：

- 经典 Python scheduler。
- 更像“调度器”，不是完整任务队列。

优点：

- 上手快，API 清晰。
- 支持 cron / interval / date 三类调度。
- 适合做单独 scheduler 进程，定时调用本地函数或 HTTP 接口。
- 和 FastAPI 集成资料很多。

风险点：

- 它本身不是 Redis worker 队列。
- 如果嵌进 API 进程里跑，仍然会回到你文档里已经担心过的问题：API 进程承担后台调度职责。
- 当前稳定版是 `3.11.2`，但 4.x 还处于迁移阶段；4.x 架构变化较大，不适合一边上生产一边赌迁移。
- 新版文档里 Redis 更偏 event broker；如果你期待“纯 Redis 持久调度中心”，路线没有 Celery/Redis 那么直给。

适合你们的场景：

- 想保留“独立 scheduler 进程 + 调管理接口”这一模式。
- 想要一个比系统 cron 更 Python-native 的调度进程。
- 暂时不想把翻译任务执行层重构成 Redis worker。

一句话判断：

**适合做独立调度层，不适合单独承担未来整个后台任务体系。**

## 2.2 Celery + Beat

定位：

- 经典分布式任务队列。
- `celery beat` 负责定时投递，worker 负责执行。

优点：

- 功能最全，生态最成熟。
- Redis 可直接做 broker。
- 未来如果你想把当前 `ThreadPoolExecutor` 翻译任务迁到独立 worker，Celery 是一条正路。
- 支持任务路由、重试、超时、结果后端、独立 worker 扩缩容。

风险点：

- 复杂度最高。
- 引入后通常意味着：
  - 一个 API 进程
  - 一个或多个 worker
  - 一个 beat 进程
  - Redis broker
- 对当前这个仓库来说，属于一次体系升级，不只是“补个 scheduler”。

适合你们的场景：

- 后续不只想调 arXiv 同步，还想把翻译执行也迁到真正的后台队列。
- 任务会越来越多，或者想做更强的失败重试、并发隔离、队列拆分。

一句话判断：

**如果你想顺手把后台任务架构做正，这个最强；但它明显偏重。**

## 2.3 Celery + RedBeat

定位：

- `celery beat` 的 Redis 持久化调度器。
- 调度定义和元数据放在 Redis，不用默认的本地文件。

优点：

- 比 Celery 默认 beat 更适合多机/容器化部署。
- 调度状态放 Redis，更符合你们现在已经有 Redis 中间件的条件。
- 自带分布式锁思路，能减少多 beat 重复调度问题。
- 后续做动态 schedule 管理会更顺。

风险点：

- 这是 Celery 体系下的增强件，不是独立方案。
- 你一旦用它，基本也默认接纳 Celery 的整体复杂度。

适合你们的场景：

- 你已经接受 Celery。
- 你不想把 beat 的 schedule 落到本地文件。
- 你预计会有多个环境/容器/实例。

一句话判断：

**如果选 Celery，几乎应该一起考虑 RedBeat。**

## 2.4 RQ

定位：

- Redis Queue，轻量级 Redis 任务队列。

优点：

- 比 Celery 简单很多。
- 非常贴近 Redis 思维模型。
- 很适合把当前 API 中的长任务投递到独立 worker。

风险点：

- 它的 recurring cron 调度能力是新加的。
- 官方 `CronScheduler` 文档明确写了 beta。
- 如果你的核心诉求是“生产级周期任务调度”，我不会把 beta cron 当第一选择。

适合你们的场景：

- 你更在乎“把后台执行移出 API 进程”，而不是立即拿到最成熟的定时系统。
- 短期 recurring schedule 仍可先用外部 cron，RQ 先只接后台 worker。

一句话判断：

**队列层不错，但就今天的 recurring scheduler 成熟度来看，我会保守一点。**

## 2.5 Huey

定位：

- 轻量任务队列 + 定时任务框架。
- Redis 是它的天然强项之一。

优点：

- 明显比 Celery 轻。
- 自带 `task()`、`periodic_task()`、crontab 风格周期任务。
- Redis 集成自然。
- 很适合内部工具、管理后台、轻中量任务系统。
- 对“每天同步 arXiv + 触发一些后台作业”这种需求很对味。

风险点：

- 生态和团队熟悉度通常不如 Celery。
- 多消费者部署时，周期任务通常要明确只让一个 consumer 负责 enqueue。
- 如果未来要做到非常复杂的分布式任务编排，天花板不如 Celery。

适合你们的场景：

- 想用 Redis。
- 想有 worker 和 periodic tasks。
- 又不想一下子把系统复杂度拉到 Celery 那个量级。

一句话判断：

**这是当前项目最像“刚刚好”的方案。**

## 2.6 ARQ

定位：

- asyncio + Redis 的任务队列。

优点：

- 和 FastAPI / async 语境表面上很搭。
- 自带 cron jobs 能力。

风险点：

- 当前 PyPI 明确写了 `maintenance only mode`。

一句话判断：

**不建议作为你们现在的新选型。**

## 2.7 Dramatiq

定位：

- 现代化任务队列，支持 Redis broker。

优点：

- 任务执行层不错。
- Redis 支持没问题。

风险点：

- 官方文档对 cron-like scheduling 的建议是配合 APScheduler 或第三方包。
- 也就是说，它本身不是一个“拿来就很好用的 Redis 周期调度方案”。

一句话判断：

**如果核心问题是 scheduler，这个不是最顺手的第一选择。**

## 3. 结合你们项目的推荐

我把建议分成三个层级：

## 3.1 如果只解决 arXiv 每日同步

推荐顺序：

1. 外部 cron 调管理接口
2. 独立 APScheduler 进程

原因：

- 实现最简单。
- 风险最低。
- 不会误伤当前翻译链路。

这仍然是你之前在 `9.3` 里写的方向，我现在看完生态后，依然认为这是很稳的 MVP 选择。

## 3.2 如果你想顺手把后台执行体系也做起来

推荐顺序：

1. `Huey + Redis`
2. `Celery + Redis + RedBeat`

我的判断依据是：

- 当前项目规模和复杂度，还没到非 Celery 不可。
- 但当前 `ThreadPoolExecutor` 又确实已经有点像临时方案了。
- 所以如果你希望“这次不是只加一个定时器，而是开始把后台任务正规化”，`Huey` 会是很平衡的一步。

## 3.3 如果你想直接为后续大规模后台化铺路

推荐：

- `Celery + Redis + RedBeat`

适用前提：

- 你接受更复杂的部署。
- 你准备把翻译任务、同步任务、后续周报生成、缓存预热都统一到 worker 系统。

## 4. 当前采用结论

当前文档结论已经收敛为：

**采用 `Huey + Redis`。**

原因：

- 你们已经有现成 Redis 中间件。
- 它足够轻，适合当前项目体量。
- 它不只是 scheduler，还能承接 worker 化改造。
- 对当前仓库来说，它比 `Celery + RedBeat` 更容易以较低成本接入。
- 它比“继续堆 API 进程内 scheduler”更稳，也比“长期停留在外部 cron 调接口”更可演进。

当前推荐落地顺序：

1. 先让 `Huey` 承接 discovery sync
2. 保持现有翻译任务执行器不动
3. 等 discovery 跑稳后，再评估是否把翻译任务迁到 `Huey`

### 什么时候改选 Celery

如果后续出现这些信号，再考虑切到 `Celery + RedBeat`：

- 多类 worker 队列拆分已经很明显
- 更复杂的失败重试 / 路由 / 优先级开始成为核心诉求
- 多实例部署下需要更重型的后台任务体系
- 希望把翻译任务、发现流任务、周报生成、缓存预热统一纳入更成熟的分布式生态

## 5. 不推荐项

当前不建议作为主方案的有：

- `ARQ`
  - 原因：维护模式已转为 maintenance only。

- `RQ CronScheduler`
  - 原因：官方 cron scheduler 仍标注 beta，做生产主调度我会保守。

- `Dramatiq` 作为 scheduler 主方案
  - 原因：它更像任务队列，不是最顺手的周期调度选择。

## 6. 我建议的下一步

既然方案已经确定，最合理的后续不是继续选型，而是补实施规格：

1. `docs/arxiv-discovery-mvp-spec-2026-05-28.md`
   - 细化 discovery 数据模型、API、页面、`@xyflow/react` 可视化和 `Huey` job contract。

2. `docs/huey-redis-integration-plan-2026-05-28.md`
   - 细化当前仓库如何引入 `Huey`、启动 consumer、配置 Redis、注册 periodic task、处理幂等和日志。

## 7. 主要参考

- APScheduler 官方文档
  - https://apscheduler.readthedocs.io/
- APScheduler PyPI
  - https://pypi.org/project/APScheduler/
- Celery 官方文档
  - https://docs.celeryq.dev/
- Celery PyPI
  - https://pypi.org/project/celery/
- Celery RedBeat 文档
  - https://redbeat.readthedocs.io/
- Celery RedBeat PyPI
  - https://pypi.org/project/celery-redbeat/
- RQ 官方文档
  - https://python-rq.org/docs/
- RQ PyPI
  - https://pypi.org/project/rq/
- Huey 官方文档
  - https://huey.readthedocs.io/
- Huey PyPI
  - https://pypi.org/project/huey/
- ARQ 文档 / PyPI
  - https://arq-docs.helpmanual.io/
  - https://pypi.org/project/arq/
- Dramatiq 官方文档 / PyPI
  - https://dramatiq.io/
  - https://pypi.org/project/dramatiq/
