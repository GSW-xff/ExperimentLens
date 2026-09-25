# ExperimentLens 大厂 AI Agent 实习竞争力升级方案

> 文档状态：待实施  
> 基线版本：`2a8dcac`  
> 更新日期：2026-09-25  
> 目标岗位：AI Agent 平台、AI Infra、LLMOps、机器学习平台与 AI 应用工程实习

## 1. 文档目的

本文档基于 ExperimentLens 当前代码、测试、运行链路和基础设施配置，对项目的真实完成度进行审计，并给出面向腾讯、字节跳动等互联网公司的后续修改方案。

本文档遵循三个约束：

- 严格区分“已实现”“部分实现”和“规划中”，不以 Docker Compose 中存在组件代表主链路已经接入。
- 优先补齐能够通过测试、故障实验和性能数据证明的能力，而不是继续增加概念或页面。
- 每个阶段必须包含实现、测试、验收证据和独立 Git commit，保证可追踪、可回滚。

## 2. 项目定位与结论

### 2.1 推荐定位

ExperimentLens 应定位为：

> 一个可恢复、可评测、可观测、以证据为约束的实验诊断 Agent 平台。

它的核心价值不是替代实验管理平台，而是在 MLflow、文件工作区或 CI Benchmark 等数据源之上，通过受约束工具完成实验诊断，并把结论、证据、修改建议和后续实验结果连接成闭环。

### 2.2 当前竞争力判断

| 目标岗位 | 当前适配度 | 主要依据 | 下一步重点 |
|---|---|---|---|
| AI Agent 平台/后端 | 较强 | 已有控制面、Agent 状态、工具、证据和 SSE | 独立 Worker、持久化工作流、事件链路 |
| LLMOps / AI Infra | 中等偏上 | 已有模型网关、Trace、评测和指标雏形 | 真实评测执行、故障恢复、容量与成本数据 |
| AI 应用工程 | 较强 | 已有完整产品界面和领域场景 | 接入真实数据源，形成可复现演示 |
| Agent 算法 | 一般 | 当前强项是工程编排而非模型优化 | 长程 Benchmark、检索、轨迹数据和小规模后训练 |
| 大模型训练/RL Infra | 偏弱 | 缺少分布式训练和后训练实践 | 独立算法支线，不在主平台中伪造大规模能力 |

当前项目已经明显强于普通的“聊天界面 + Prompt + 向量库”演示，但仍属于完成度较高的工程原型，还不能宣称是生产级分布式 Agent 平台。

### 2.3 面试叙事主线

后续所有修改应服务于以下五个问题：

1. 为什么实验诊断需要 Agent，而不是一个长 Prompt？
2. 如何保证模型只通过授权工具访问项目数据？
3. Worker、API 或事件通道发生故障时，任务如何恢复且不重复产生副作用？
4. 如何证明 Prompt、模型、工具或分析算法升级后质量真的提高？
5. 如何让一条诊断结论回溯到具体 Run、Metric、Step、配置和日志证据？

## 3. 当前版本实际情况

### 3.1 已实现能力

- React 管理界面与 FastAPI 控制面。
- 旧 Flask API 通过适配层继续兼容。
- 基于 SQLAlchemy 的 AgentRun、AgentEvent、ToolCall、EvidenceRef、TraceSpan、EvaluationRun、EvaluationResult 和 Transactional Outbox。
- SQLite 开发模式、PostgreSQL 连接配置和 Alembic 数据库迁移。
- Provider-neutral ModelGateway、OpenAI Responses API 网关和确定性离线网关。
- 六个项目作用域内的只读工具：Run 列表、组间比较、日志检索、配置差异、指标序列检查和 Finding 证据读取。
- 步骤预算、Token 预算、超时、取消、重试、重复工具调用检测和最终证据门禁。
- 带事件序号和 `Last-Event-ID` 的 SSE 断线续传。
- OpenTelemetry Span、Prometheus 指标和 Grafana 基础设施。
- 20 条 JSONL Golden Dataset、确定性轨迹评分器和评测界面。
- Docker、Compose、CI、依赖安全审计、后端与前端自动化测试。

### 3.2 部分实现能力

| 能力 | 已有基础 | 当前限制 |
|---|---|---|
| 故障恢复 | 启动时扫描未完成 AgentRun 并重新入队 | 重新入队不等于从精确检查点恢复，内存中的消息和工具轨迹不能完整重放 |
| Transactional Outbox | 状态与 Outbox 可在同一事务写入 | 缺少 Publisher、Redis Streams Consumer 和多实例事件网关 |
| Trace | TraceSpan 可持久化，也可导出 OTLP | Span 粒度较粗，缺少完整 Trace 查询、比较和故障聚类 |
| Evaluation | 有数据集、评分器、API 和页面 | 评分器接收外部 trajectory，尚未自动真实运行 Agent |
| 生产基础设施 | Compose 中提供 PostgreSQL、OTel、Prometheus、Grafana，并可选 Redis、MinIO、Temporal | Redis、MinIO 和 Temporal 尚未进入核心请求链路 |
| 多租户模型 | 数据结构可以保存组织或项目范围 | 缺少 OIDC、RBAC、成员校验、租户隔离中间件和负向测试 |

### 3.3 尚未实现的关键能力

- 独立于 API 进程的 Agent Worker。
- Temporal Activity 或等价的持久化任务执行语义。
- Outbox Publisher、Redis Streams 和独立 SSE Gateway。
- MLflow、TensorBoard 或 CI Benchmark 的真实 Source Adapter。
- MinIO/S3 Artifact 内容寻址和生命周期管理。
- Proposal 审批、导出、执行、结果回收和效果判定闭环。
- 真实的认证、授权、租户隔离、审计和敏感信息脱敏。
- 自动执行 Agent 的 Evaluation Harness 和版本间回归报告。
- 多模型路由、成本核算、限流、熔断、缓存和首 Token 延迟统计。
- 长程任务 Benchmark、Runbook 检索、记忆、反思或训练数据闭环。
- Locust/k6 压测、故障注入、SLO 和容量分析报告。
- Kubernetes/Helm/Kind 部署验证。
- 浏览器端 E2E 测试和完整 Trace Explorer。

## 4. 当前最影响项目含金量的问题

### 4.1 评测结果不能证明 Agent 真实能力

当前评测器可以对传入的 trajectory 评分，但 trajectory 不是由评测框架实际执行 Agent 后自动采集。调用方可以构造理想工具轨迹，因此高分不能证明真实系统表现。

这是最高优先级问题。大厂面试更关心“如何证明修改有效”，而不是是否存在一个 Evaluation 页面。

### 4.2 API 进程仍承担长任务执行

Agent 仍使用进程内 `ThreadPoolExecutor`。服务重启后可以重新调度未完成任务，但模型上下文、已收集证据和已执行工具集合不能从精确步骤恢复。

当前工具均为只读，因此风险暂时可控；一旦引入 Proposal 写回或外部执行工具，重复执行将成为数据一致性问题。

### 4.3 事件模型没有形成跨实例链路

Outbox 已经写入数据库，但没有发布者和消费者。当前 SSE 依赖 API 进程内通知机制，不适合作为多实例部署的事件通道。

### 4.4 缺少真实数据源和真实规模证明

本地工作区适合演示，但不能证明增量同步、幂等导入、分页、游标、大数据量查询和外部平台兼容性。

### 4.5 缺少安全边界验证

仅在工具参数中携带 `project_id` 不等于已经实现项目隔离。系统必须通过身份、成员关系、资源归属和事件订阅校验共同完成授权。

### 4.6 缺少算法差异化

当前 Agent 主要体现平台工程能力。如果应聘 Agent 算法岗，还需要长程、多工具、检索、反思、轨迹数据和后训练实验；否则应明确以 Agent 平台和 AI Infra 为主赛道。

## 5. 修改路线图

### 5.1 阶段 P0：冻结真实基线

预计时间：2～3 天。

修改内容：

- 记录当前 Agent、工具、Prompt、数据集和数据库 Schema 版本。
- 为现有 20 个案例生成不可手工修改的基线结果。
- 在 EvaluationResult 中记录 Git commit、模型、Prompt hash、工具版本和数据集版本。
- 统一“已实现、实验性、规划中”的页面及文档标识。
- 修正文档中与当前代码不一致的描述。

测试与验收：

- 同一离线模型和固定输入重复运行，结果完全一致。
- 数据集、Prompt 或工具版本变化时，评测结果能够定位到对应版本。
- 所有 README、架构文档和 API 描述不再把可选 Compose 组件写成已接入能力。

### 5.2 阶段 P1：真实 Evaluation Harness

预计时间：1 周。优先级：最高。

目标链路：

```text
EvaluationCase
  → 创建隔离测试项目
  → 导入 fixture
  → 实际启动 AgentRun
  → 自动采集模型与工具轨迹
  → 验证 EvidenceRef
  → 计算质量、延迟与成本
  → 与基线版本比较
  → 生成回归报告
```

修改内容：

- Evaluation Runner 不再接受调用方提供的理想 trajectory。
- 测试案例必须通过正常 Agent API 或内部用例入口执行。
- 扩充至至少 50 个案例，覆盖正常、边界、失败和安全场景。
- 增加任务成功率、工具选择准确率、参数正确率、证据有效率、拒答正确率、延迟和成本指标。
- 生成 JSON 与 Markdown 两种回归报告。
- CI 支持 baseline/candidate 比较和质量门禁。

验收标准：

- 所有评分轨迹均来自真实执行。
- 不存在证据和跨项目证据的通过率均为 0。
- 同一确定性模型重复运行评分一致。
- Candidate 低于质量阈值时 CI 失败，并展示具体退化案例。

### 5.3 阶段 P2：控制面与执行面分离

预计时间：1～2 周。

修改内容：

- API 只负责创建任务、查询状态、取消和订阅事件。
- 新增独立 Agent Worker 进程。
- 使用 Temporal Workflow/Activity；若先做过渡版本，则使用数据库 Lease、heartbeat 和 fencing token。
- 把模型输入、工具调用参数、结果、EvidenceRef 和步骤状态持久化为检查点。
- ToolCall 增加稳定的 idempotency key 和唯一约束。
- 实现 heartbeat、取消传播、超时和可配置重试策略。
- 将不可重试错误与暂时性错误分类。

故障测试：

- 在模型调用前杀死 Worker。
- 在工具执行中杀死 Worker。
- 在工具结果写入后、步骤完成前杀死 Worker。
- 在最终答案写入时杀死 Worker。
- API 与 Worker 分别重启。

验收标准：

- 四个故障点均能恢复到终态。
- 不重复写入 ToolCall、EvidenceRef 和最终答案。
- 多 Worker 不会同时执行同一个业务步骤。
- API 重启不影响 Worker 中正在执行的任务。

### 5.4 阶段 P3：Outbox 与实时事件闭环

预计时间：1 周。

修改内容：

- 实现 Outbox Publisher。
- 接入 Redis Streams Consumer Group。
- SSE Gateway 从 Stream 消费事件，PostgreSQL 作为权威回放来源。
- 增加幂等消费、消费者心跳、Pending Entry 恢复和死信策略。
- 支持慢消费者、客户端重连和事件保留策略。

验收标准：

- 浏览器断开 60 秒后能够从最后 Event ID 继续，无丢失、无重复展示。
- Publisher 在发送前后任一位置崩溃均不会永久丢失事件。
- 两个 API 实例与两个事件消费者下状态一致。
- Redis 不可用时可以降级为数据库回放，并暴露降级指标。

### 5.5 阶段 P4：真实 MLflow 数据源与曲线诊断

预计时间：1 周。

修改内容：

- 定义 `ExperimentSource` SPI 和 Source capability。
- 实现 MLflow 只读 Connector。
- 支持 Experiment、Run、Metric、Parameter、Tag 和 Artifact 元数据映射。
- 使用 cursor/watermark 进行增量同步。
- 为同步批次保存 lineage、源版本和错误信息。
- 接入 MinIO/S3 Artifact 索引和内容哈希。
- 增加平台期、振荡、过拟合、突变点和早停建议等确定性曲线工具。

验收标准：

- 重复同步同一 MLflow Run 不产生重复数据。
- 中途失败后可以从游标恢复。
- 每个诊断数值可以追溯到源 Run、Metric、Step 和同步批次。
- 使用至少一个真实训练项目完成端到端演示。

### 5.6 阶段 P5：Proposal 审批与结果回流

预计时间：1 周。

目标链路：

```text
Finding
  → Agent 生成 Proposal 草稿
  → 人工审核
  → 导出配置 Diff
  → 外部执行实验
  → 回收新 Run
  → 应用决策规则
  → 标记 Proposal 有效或无效
  → 将反馈加入评测数据
```

修改内容：

- Proposal 状态机：draft、pending_approval、approved、rejected、exported、running、verified、failed。
- 保存审批人、审批意见、时间和审计记录。
- 生成 YAML/JSON 配置 Diff。
- 对参数范围、资源需求和危险配置进行策略校验。
- 将新 Run 与 Proposal、基线 Run 和 AgentRun 关联。
- 用确定性决策规则判断质量提升、约束满足和成本变化。

验收标准：

- 未审批 Proposal 不能进入导出或执行状态。
- 重复审批和重复结果回传保持幂等。
- Proposal 结论包含指标变化、置信信息和原始证据。
- 人工反馈可以进入下一版 Evaluation Dataset。

### 5.7 阶段 P6：身份、权限与审计

预计时间：1 周。

修改内容：

- 接入 OIDC/OAuth2 和 JWT 校验。
- 实现 Organization、Project、Member、Role 和 Scope。
- 在 API、Repository、Tool、SSE 和 Artifact 五个边界进行授权。
- 实现审计事件、敏感字段脱敏和 Secret 管理。
- 增加 Prompt injection、路径穿越、越权订阅和跨租户读取测试。

验收标准：

- A 组织用户不能读取、猜测或订阅 B 组织的任何资源。
- Viewer、Operator、Approver 和 Admin 权限满足最小授权原则。
- 拒绝操作同样生成审计事件，但不泄露目标资源是否存在。
- API Key、Token 和敏感日志不会进入模型上下文或 Trace。

### 5.8 阶段 P7：性能、可靠性与交付证明

预计时间：1 周。

修改内容：

- 使用 Locust 或 k6 编写 API、SSE 和 Worker 压测。
- 注入 PostgreSQL、Redis、模型网关和 Worker 故障。
- 建立请求、任务、模型、工具、队列和数据库六类 Dashboard。
- 定义并测量可用性、任务成功率、队列延迟、首事件时间和恢复时间 SLO。
- 输出固定硬件、数据规模和负载条件下的容量报告。
- 增加 Playwright 端到端测试。

验收标准：

- 报告包含机器配置、数据量、并发、p50/p95/p99、错误率和资源占用。
- 给出优化前后对照和瓶颈解释，不使用未经测量的“高并发”表述。
- 核心用户路径在浏览器 E2E 中可重复运行。
- 故障发生时告警、Trace 和日志能够定位同一个 AgentRun。

## 6. Agent 算法增强支线

本支线只在 P1～P4 完成后实施，避免同时扩散平台和算法范围。

### 6.1 长程诊断 Benchmark

- 构造需要连续调用 4～10 次工具的诊断任务。
- 覆盖信息不足、证据冲突、工具失败和必须拒答的任务。
- 分别衡量规划、工具选择、参数、证据和最终结论。

### 6.2 Runbook 检索

- 建立版本化的实验故障知识库。
- 实现 project、organization 和 global 三层检索范围。
- 测量 Recall@K、证据正确率和最终任务成功率。
- 检索内容必须以 EvidenceRef 形式进入最终回答。

### 6.3 轨迹数据与小规模后训练

- 自动保存成功和失败轨迹，进行隐私过滤和去重。
- 生成工具选择、参数修复和证据引用训练样本。
- 选择一个开源小模型完成 LoRA/SFT。
- 在冻结的 Benchmark 上比较训练前后效果。
- 资源允许时再进行小规模 DPO/GRPO，不宣称具备大规模 RL 训练能力。

## 7. 推荐提交拆分

每一项必须是能够独立通过测试的垂直切片，禁止将全部改造压缩为一个提交。

| 顺序 | 推荐提交主题 | 必须同步增加的测试 |
|---:|---|---|
| 1 | `test: freeze agent evaluation baseline` | 版本、确定性和基线快照测试 |
| 2 | `feat: execute real agent evaluation cases` | Evaluation Harness、失败案例和回归门禁 |
| 3 | `feat: separate agent worker from control plane` | 领取、租约、并发和取消测试 |
| 4 | `feat: persist resumable agent checkpoints` | 四个崩溃点恢复和幂等测试 |
| 5 | `feat: publish outbox events through redis streams` | 重复投递、重连和多消费者测试 |
| 6 | `feat: ingest mlflow experiments incrementally` | Cursor、幂等、恢复和 lineage 测试 |
| 7 | `feat: close the proposal feedback loop` | 状态机、审批、回传和决策规则测试 |
| 8 | `feat: enforce tenant authorization and audit` | 跨租户负向测试和脱敏测试 |
| 9 | `perf: establish load and failure baselines` | k6/Locust 场景、故障注入和报告校验 |
| 10 | `docs: package interview architecture evidence` | 文档链接、演示脚本和能力声明检查 |

## 8. 统一完成定义

一个阶段只有同时满足以下条件才算完成：

- 主链路代码已实现，不仅存在接口、表结构或 Compose 配置。
- 单元、集成、契约、迁移或 E2E 测试已按风险补充。
- 全量测试、构建和安全审计通过。
- 正常路径、失败路径和恢复路径都有可复现证据。
- 指标、Trace 和日志能够关联到同一个业务 ID。
- README、架构图、API 和用户文档与真实实现一致。
- 创建对应 Git commit，提交说明能够表达用户价值。

## 9. 面试交付物

### 9.1 必须准备

- 一张区分控制面、执行面、状态存储和事件通道的架构图。
- 一份真实 Agent baseline/candidate 回归报告。
- 一份 Worker 崩溃恢复和事件不丢失的故障实验记录。
- 一个真实 MLflow 项目的端到端诊断案例。
- 一份包含测试环境和优化对照的性能报告。
- 三篇 ADR：持久化工作流选择、事件通道选择、Evaluation 设计。

### 9.2 推荐演示流程

演示总时长控制在 8～10 分钟：

1. 从 MLflow 同步一组真实实验。
2. 创建 AgentRun 并查看实时步骤。
3. 展示工具输入、输出和原始证据。
4. 在执行中杀死 Worker，并展示任务恢复。
5. 生成 Proposal 并完成审批。
6. 导入后续实验结果并判断 Proposal 是否有效。
7. 展示版本回归评测和 Grafana 指标。

## 10. 不建议优先投入的方向

- 继续增加没有后端闭环的 Dashboard 页面。
- 为了数量引入多个职责模糊的 Agent Persona。
- 仅接入向量数据库，却没有检索 Benchmark。
- 仅把 Redis、Temporal 或 MinIO 加入 Compose，却不接入主链路。
- 频繁更换模型，但没有固定数据集和基线。
- 在没有训练实验和测量结果时声称具备 RL 或大规模分布式能力。
- 在核心可靠性尚未完成前投入 Kubernetes 和复杂微服务拆分。

## 11. 参考岗位方向

- 字节跳动校园招聘中的大模型应用、AI PaaS、Agent、AI 搜索、AI Coding 和机器学习系统方向：<https://jobs.bytedance.com/campus/page-6272Gc>
- 腾讯大模型强化学习框架岗位对分布式训练、PPO、GRPO、DPO 和 Agentic RL Infra 的要求：<https://careers.tencent.com/jobdesc.html?postId=2072330929078190080>
- 上海人工智能实验室 Agent 岗位对轨迹、Benchmark、长程多工具任务和后训练闭环的要求：<https://www.shlab.org.cn/joinus/detail/7688979700371507519>

这些岗位信息用于确定能力方向，不代表项目必须同时覆盖所有岗位。ExperimentLens 的主路线应优先完成 Agent 平台、AI Infra 和 LLMOps 能力，再根据目标岗位选择是否投入算法增强支线。
