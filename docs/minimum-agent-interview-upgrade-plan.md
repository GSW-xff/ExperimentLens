# ExperimentLens 最小化 Agent 面试竞争力升级方案

> 文档状态：已实施
> 制定日期：2026-10-09  
> 完成日期：2026-10-09
> 预计工期：10～14 个工作日  
> 目标岗位：AI Agent 开发、Agent 平台、AI 应用后端、LLMOps 实习

## 1. 目标

本方案只保留能够显著提高 Agent 开发岗位面试竞争力的最小修改，不追求一次性把 ExperimentLens 改造成完整大厂生产平台。

改造完成后，项目必须能用代码、测试和演示回答四个问题：

1. Agent 是否真的通过工具完成任务，而不是只展示一段预制回答？
2. 如何证明模型、Prompt 或工具修改后，Agent 质量变好而不是变差？
3. Agent 执行中进程崩溃时，任务能否恢复且不重复执行工具？
4. 项目中关于可靠性、延迟和成功率的说法是否有可复现数据？

## 2. 当前基础

> 实施结果：真实 Evaluation Harness、数据库 Lease Worker、AgentStep 恢复、三个崩溃点测试、100 任务基线脚本、两篇 ADR 和一键演示均已落地。使用说明见 `docs/project-description-and-usage.md`，可复现证据见 `docs/evidence/`。

当前项目已经具备：

- FastAPI 控制面、React 工作台和 SQLAlchemy 持久化。
- AgentRun、AgentEvent、ToolCall、EvidenceRef、TraceSpan 和 EvaluationResult。
- 六个项目内只读诊断工具。
- 步骤预算、Token 预算、超时、取消、重试和证据校验。
- SSE 事件序号与断线续传。
- OpenTelemetry Trace 和 Prometheus 指标。
- 20 条 Golden Dataset。
- 75 个后端测试、24 个子测试、7 个前端测试和约 87% 后端覆盖率。

当前最影响面试说服力的不是功能数量，而是：

- 评测轨迹仍可由调用方直接提供，不能证明 Agent 被真实执行。
- Agent 长任务仍运行在 API 进程内线程池中。
- 进程恢复会重新执行，而不是从持久化步骤精确恢复。
- 还没有一份可复现的故障恢复和容量测试报告。

## 3. 最小修改范围

本轮只完成以下三个核心增量：

```text
真实 Evaluation Harness
        ↓
独立 Worker + 持久化步骤 + 幂等恢复
        ↓
故障实验 + 性能基线 + 面试演示材料
```

同时完成少量必要的工程收尾：CLI 安装、代码规范、文档和一键演示。

## 4. M0：工程基线全绿

预计时间：0.5～1 天。

### 4.1 修改内容

- 修复当前 Ruff import 格式问题。
- 重新执行 editable install，确认 `experimentlens-api` 和 `experimentlens-eval` 均可直接运行。
- 增加统一验证命令，例如 `make verify` 或 `scripts/verify.sh`。
- 验证命令必须依次执行后端测试、覆盖率、Ruff、前端测试、TypeScript 编译、前端构建和 Alembic 前滚/回滚。
- README 中只保留一套推荐启动方式。

### 4.2 验收标准

- 新环境按照 README 可以一次启动成功。
- `experimentlens-api`、`experimentlens-eval` 两个命令可用。
- 全部测试、Lint、构建和数据库迁移检查通过。
- Git 工作区无未提交文件。

## 5. M1：真实 Evaluation Harness

预计时间：4～5 天。优先级：最高。

### 5.1 目标

评测系统必须自己创建案例环境、运行 Agent、采集轨迹并评分，禁止调用方直接提交理想 trajectory。

目标链路：

```text
EvaluationCase
  → 创建隔离 Project/Fixture
  → 创建 AgentRun
  → 等待终态
  → 自动读取 ToolCall/Event/Evidence/Trace
  → 计算任务、安全、延迟和成本指标
  → 与 Baseline 比较
  → 输出 JSON + Markdown 报告
```

### 5.2 必须修改

- 新增 `EvaluationExecutor`，通过真实 Orchestrator 执行案例。
- Evaluation API 只接收数据集版本、候选模型和运行配置，不再接收完整 trajectory。
- 从数据库自动组装实际 trajectory。
- 每次评测记录以下版本信息：
  - Git commit；
  - 数据集 hash；
  - Prompt hash；
  - 模型名称；
  - 工具 Schema hash；
  - Detector 版本。
- 继续保留离线确定性模型作为 CI 基线。
- 支持可选真实模型评测，但真实模型失败不能影响离线 CI。
- 生成 baseline/candidate 差异报告。

### 5.3 最小评测指标

| 指标 | 门禁 |
|---|---:|
| Task pass rate | ≥ 95% |
| Invalid evidence rate | 0 |
| Cross-project access success | 0 |
| Unauthorized write success | 0 |
| Prompt injection success | 0 |
| Tool argument validity | 100% |
| Timeout recovery | 100% 进入明确终态 |

延迟和 Token 只做对比指标，第一版不设置绝对生产 SLO。

### 5.4 数据集范围

保留现有 20 条案例，新增 10 条真实执行案例，重点覆盖：

- 多工具顺序错误；
- 重复工具调用；
- 证据不足时拒答；
- 工具超时；
- 伪造 Run ID；
- 跨项目读取；
- 日志中的 Prompt Injection；
- Token 预算耗尽；
- 候选组均值提升但置信区间跨 0；
- OOM Run 不应进入有效指标均值。

总量控制在 30 条，优先保证每条都能真实运行和稳定复现，不追求案例数量。

### 5.5 验收测试

- 测试不能通过手工构造高分 trajectory 绕过真实运行。
- 相同 fixture 和确定性模型重复评测两次，结果一致。
- 修改 Prompt 或工具 Schema 后，报告能显示版本变化。
- Candidate 低于门禁时 CLI 和 CI 返回非零状态。
- 失败报告能够定位到具体 case、步骤、工具调用和 EvidenceRef。

## 6. M2：独立可恢复 Agent Worker

预计时间：4～5 天。

### 6.1 目标

将 Agent 执行从 API 进程内的 `ThreadPoolExecutor` 移到独立 Worker，同时不引入 Temporal、Redis 或 Kubernetes。

第一版采用 PostgreSQL/SQLite 支持的数据库任务表、Lease 和持久化步骤，展示核心可靠性能力即可。

### 6.2 最小架构

```text
Browser
  → FastAPI Control Plane
      → PostgreSQL/SQLite AgentRun + AgentStep
              ↑                ↓
          SSE Query        Agent Worker
```

### 6.3 必须修改

- 新增独立命令 `experimentlens-worker`。
- API 创建 AgentRun 后只写数据库，不直接提交线程任务。
- Worker 轮询并领取待执行任务。
- 新增持久化 `AgentStep`：
  - step index；
  - step type；
  - input hash；
  - output hash；
  - status；
  - attempt；
  - started/finished time；
  - error category。
- 任务领取使用 lease owner、lease expiry 和 fencing token。
- ToolCall idempotency key 由 `agent_run_id + step_index + tool_name + arguments_hash` 生成。
- Worker 定期 heartbeat；Lease 过期后其他 Worker 可以恢复任务。
- 恢复时从已完成 AgentStep 重建 messages、证据和已执行工具集合。
- 取消信号通过数据库状态传播。
- API 不再负责恢复和执行任务。

### 6.4 暂不引入的组件

- Temporal；
- Redis Streams；
- Kafka；
- Celery；
- Kubernetes；
- 分布式锁服务。

面试中可以说明这些是规模扩大后的演进选项；当前实现重点证明任务状态、Lease、幂等和恢复语义。

### 6.5 故障测试

必须自动化覆盖三个崩溃点：

1. 模型调用完成后、结果保存前；
2. 工具执行完成后、ToolCall 提交前；
3. Evidence 校验完成后、最终答案提交前。

每个测试都需要杀死 Worker 进程、等待 Lease 过期、启动新 Worker，并验证：

- AgentRun 最终完成或明确失败；
- 已完成步骤不会重复计费；
- ToolCall 不重复；
- EvidenceRef 不重复；
- AgentEvent 序号连续；
- 最终答案只写入一次。

### 6.6 验收标准

- API 重启不影响 Worker 中的任务。
- Worker 重启后可以从持久化步骤恢复。
- 两个 Worker 不会同时提交同一任务步骤。
- 相同幂等键最多存在一个 ToolCall。
- 取消操作在下一次 heartbeat 或步骤边界生效。
- 前端 Agent 面板无需改变使用方式。

## 7. M3：面试级可靠性证据和演示

预计时间：2～3 天。

### 7.1 最小性能实验

使用确定性离线模型，固定测试机器和数据规模，运行：

- 100 个 AgentRun；
- 2 个 Worker；
- 每个 Run 2～4 次工具调用；
- 执行过程中随机终止 1 个 Worker；
- 随机断开并恢复 SSE 客户端。

记录：

- 完成率；
- 重复 ToolCall 数；
- 丢失事件数；
- 队列等待时间 p50/p95；
- Agent 执行时间 p50/p95；
- 崩溃恢复时间；
- 数据库 CPU、内存和连接数。

本阶段不承诺互联网生产流量，只建立可复现基线。

### 7.2 演示脚本

增加 `scripts/interview_demo.sh` 或等价命令，完成：

1. 初始化数据库；
2. 启动 API 和 Worker；
3. 导入息肉分割示例；
4. 创建 AgentRun；
5. 展示实时工具事件；
6. 中途杀死 Worker；
7. 启动新 Worker并恢复任务；
8. 打开 Trace；
9. 运行 30 条 Evaluation；
10. 输出 baseline/candidate 报告。

### 7.3 面试材料

只准备以下材料：

- 一张当前真实架构图；
- 一份 Agent Evaluation 报告；
- 一份 Worker 故障恢复记录；
- 一份 100 个任务的性能基线；
- 一个 8 分钟演示视频或演示脚本；
- 两篇 ADR：为什么先用数据库 Lease、为什么评测必须真实执行 Agent。

## 8. 明确不做的功能

以下能力不属于本轮最小方案：

- 多 Agent 协作和 Agent Persona；
- 长期记忆；
- 通用 RAG 或向量数据库；
- MLflow、TensorBoard、Weights & Biases 在线连接；
- Temporal、Redis、Kafka、MinIO；
- Kubernetes、Helm 和自动扩缩容；
- OIDC 完整账号系统；
- 自动修改代码或自动启动训练；
- SFT、DPO、GRPO 或大模型训练；
- 复杂 Proposal 审批流程；
- 第二个前端管理后台。

这些功能可以在明确目标岗位或真实需求出现后继续补充，不应阻塞本轮完成。

## 9. 推荐提交拆分

每个提交必须同时包含实现和对应测试。

| 顺序 | Commit | 交付内容 |
|---:|---|---|
| 1 | `chore: make all project quality gates reproducible` | CLI、统一验证命令、Lint 和 README |
| 2 | `feat: execute evaluation cases through the real agent runtime` | EvaluationExecutor 和真实轨迹采集 |
| 3 | `feat: compare agent evaluation baselines and candidates` | 版本记录、报告和 CI 门禁 |
| 4 | `feat: move agent execution into a database-backed worker` | Worker、任务领取和命令入口 |
| 5 | `feat: persist resumable agent steps` | AgentStep、上下文恢复和迁移 |
| 6 | `test: verify worker crash recovery and idempotency` | 三个崩溃点故障测试 |
| 7 | `perf: publish the first agent reliability baseline` | 100 任务实验和报告 |
| 8 | `docs: add the interview demo and architecture evidence` | ADR、演示脚本和简历说明 |

## 10. 统一完成标准

本轮升级只有同时满足以下条件才算完成：

- 全部测试、Ruff、TypeScript、前端构建和数据库迁移验证通过。
- Evaluation 的 trajectory 全部来自真实 AgentRun。
- 30 条 Evaluation 可以离线重复执行。
- Worker 与 API 已分离为两个进程。
- 三个崩溃点恢复测试全部通过。
- 100 个 AgentRun 实验没有重复 ToolCall 和丢失事件。
- 所有性能数字都能通过仓库脚本重新生成。
- README、架构图和简历描述只声明已经完成的能力。
- 所有改动按独立 Git commit 提交，工作区保持干净。

## 11. 完成后的简历写法

项目名称：

> ExperimentLens：可评测、可恢复的实验诊断 Agent 平台

推荐描述：

- 基于 FastAPI、React 和 SQLAlchemy 构建证据驱动的实验诊断 Agent，通过 6 个项目级只读工具分析 Runs、指标、配置和日志，并使用 EvidenceRef 门禁防止无依据结论与跨项目访问。
- 设计真实 Agent Evaluation Harness，自动执行 30 条诊断、安全和可靠性案例，采集 ToolCall、Event、Evidence 和 Trace，支持模型、Prompt 与工具版本的 baseline/candidate 回归比较。
- 将 Agent 执行从 API 线程池拆分为数据库 Lease Worker，持久化步骤与幂等键；通过三个进程崩溃点测试验证任务恢复、工具调用不重复和事件连续性。
- 建立 OpenTelemetry、Prometheus 和 SSE 可观测链路，并使用 100 个 AgentRun 的可复现实验记录任务完成率、p95 延迟和故障恢复时间。

简历中的具体百分比和延迟数字必须在 M3 实验完成后再填写，禁止预估或编造。

## 12. 面试重点准备

完成本方案后，重点准备以下问题：

1. 为什么 Agent 只能访问 Tool Registry，不能直接读取整个工作区？
2. 为什么确定性统计不能全部交给大模型？
3. Evaluation 如何避免调用方伪造理想 trajectory？
4. 数据库 Lease 如何处理 Worker 脑裂和过期任务？
5. ToolCall 为什么需要幂等键？
6. 崩溃发生在工具执行后、结果提交前时如何处理？
7. SSE 至少一次事件投递如何在前端去重？
8. 为什么当前选择数据库 Worker，而不是直接使用 Temporal？
9. 项目从单机扩展到多实例时，下一步最先替换什么？
10. 当前系统最诚实的能力边界是什么？

能够用真实代码、测试、Trace 和实验报告回答这些问题，比继续增加页面、Agent 数量或基础设施名词更有面试价值。
