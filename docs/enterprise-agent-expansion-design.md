# ExperimentLens 面向大厂 AI Agent 岗位的扩充设计方案

## 1. 文档目的

本文档定义 ExperimentLens MVP 完成后的下一阶段扩充方案。目标不是把功能列表做得更长，而是把项目升级为一个能够诊断机器学习、深度学习及其他计算机与人工智能相关实验，并能在腾讯、字节跳动、华为等大型科技公司 AI Agent 岗位面试中证明工程落地能力的作品。

本轮只形成设计方案，不修改现有产品代码。后续开发应以本文档的优先级、验收标准和阶段计划为准，每个阶段都需要保留可运行演示、自动化测试、评测结果和架构决策记录。

目标岗位包括：

- AI Agent 应用算法工程师。
- 大模型应用工程师。
- Agent 平台或基础设施工程师。
- AI 应用后端工程师。
- 大模型评测、可观测与质量工程师。

## 2. 调研依据与结论边界

### 2.1 官方公开信号

本方案以 2026 年 9 月可检索到的官方招聘页面和企业产品文档为依据：

- 腾讯招聘的公开岗位要求同时出现了可扩展评测框架、评测题库、Prompt Engineering、代码、Workflow、Agent、数据处理和业务落地；另一类岗位强调系统编程、复杂系统 Debug、性能优化和大规模基础设施经验。[腾讯招聘：混元大模型语音领域专家](https://careers.tencent.com/zh-cn/jobdesc.html?postId=2060285101413150720)、[腾讯招聘：大模型强化学习框架研发工程师](https://careers.tencent.com/jobdesc.html?postId=2072330929078190080)
- 腾讯云 Agent 可观测产品把调用链追踪、会话回放、评估实验、Token 与延迟成本、业务效果和持续优化作为生产 Agent 的核心能力。[腾讯云 Agent 可观测](https://cloud.tencent.com/product/agentobs)
- 字节跳动官方校招页面把大模型应用、AI Coding、安全与 AI Safety、计算机系统优化、AI 搜索等列为重点技术方向，说明候选项目需要同时体现应用效果和工程能力。[字节跳动校园招聘](https://jobs.bytedance.com/campus/page-6272Gc)
- 火山引擎的 Agent 运营分析文档强调 Trace、会话数据、评测集、评估器、人工标注、线上观测、业务指标、延迟和 Token 成本之间的闭环。[火山引擎 Agent 运营分析概述](https://www.volcengine.com/docs/6285/2310370)
- 华为招聘页面强调从 AI 基础设施、行业大模型、Agent 平台到应用的系统级能力，并以解决行业问题和规模化落地为目标。[华为招聘：云计算 BU](https://career.huawei.com/cn/department-list)
- 华为云 AgentArts 把 Trace、Span、人工标注、评测数据回流、租户隔离、敏感词与内容安全作为 Agent 全生命周期的一部分。[华为云 Trace 数据回流](https://support.huaweicloud.com/ops-agentarts/agentarts_14_0021.html)、[华为云 AgentArts 产品介绍](https://support.huaweicloud.com/productdesc-agentarts0/01%20%E4%BA%A7%E5%93%81%E4%BB%8B%E7%BB%8D-pdf.pdf)

### 2.2 对面试评价重点的推断

各公司不存在统一公开的面试评分表，因此以下结论是从岗位职责和生产平台能力反推的项目评价维度，而不是对任何公司的内部招聘标准作断言。

| 能力信号 | 面试官希望看到的证据 | ExperimentLens 应提供的证明 |
|---|---|---|
| 业务问题拆解 | 能把模糊需求转化为可验证流程 | 从结果导入到诊断、验证实验和回流的完整闭环 |
| Agent 工程 | 不只是聊天界面或一次模型调用 | 状态机、工具协议、上下文控制、流式事件、失败恢复和人工审批 |
| 评测能力 | 能量化 Agent 是否真的变好 | 固定评测集、代码评分器、LLM 评分器、人工校准和版本对比 |
| 可观测与 Debug | 能定位一次错误发生在哪一步 | Trace、Span、Tool Call、Token、延迟、重试、错误和会话回放 |
| 数据与算法 | 能处理不同类型计算实验和统计不确定性 | 多源实验数据、过程曲线、效应量、异常检测和证据引用 |
| 系统能力 | 能从 Demo 走向稳定服务 | 异步任务、幂等、缓存、数据库、容器、CI/CD 和压力测试 |
| 安全与治理 | 能控制工具、数据和模型风险 | RBAC、最小权限、脱敏、Prompt Injection 防护和审计日志 |
| 产品落地 | 能说明用户、收益和取舍 | 明确场景、成功指标、成本收益和非目标 |
| 技术表达 | 能把实现讲清楚并展示结果 | 架构图、ADR、Benchmark、演示脚本和故障复盘 |

## 3. 当前 MVP 的能力盘点

### 3.1 已有优势

当前版本已经具备一个清晰的垂直场景和最小闭环：

- 支持 CSV、TSV、Excel、JSON、JSONL、YAML 和日志文件导入。
- 能推断并确认 run、实验组、seed、状态、主指标和 baseline。
- 使用确定性代码计算均值、标准差、置信区间、效应量和近似检验。
- 能检测失败运行、无效指标、离群点、seed 波动和数据版本差异。
- Finding、Hypothesis 和 Proposal 均保留 EvidenceRef。
- 能生成下一轮最小验证实验和分析报告。
- 数据默认保存在本地工作区，已有单元、集成和前端测试。

这些能力使项目明显好于只有对话 UI 的 Agent Demo。它已经表现出领域建模、统计分析、证据追溯和 Human-in-the-loop 意识。

### 3.2 影响面试竞争力的主要缺口

| 缺口 | 当前表现 | 面试风险 |
|---|---|---|
| 真正的 Agent Runtime | 对话、假设和建议主要由固定规则生成 | 容易被认为是规则系统套上 Agent 名称 |
| Agent 评测 | 只有普通代码测试，没有黄金诊断集和 Agent 质量指标 | 无法证明模型或 Prompt 变更是否提升质量 |
| Agent 可观测 | 没有模型、工具、检索和决策级 Trace | 出错时无法回答具体在哪一步失败 |
| 真实数据接入 | 主要依赖手工上传文件 | 缺少企业系统集成和持续数据同步能力 |
| 实验过程诊断 | 主要分析每个 run 的最终主指标 | 无法诊断收敛曲线、奖励变化、质量回退、性能波动和资源瓶颈 |
| 闭环状态 | Proposal 生成后没有执行回流和验证状态 | 下一轮实验没有真正闭环 |
| 服务化能力 | 单进程 Flask 和本地文件存储 | 缺少并发、异步、幂等、权限和故障恢复证明 |
| 安全能力 | 本地优先降低了风险，但没有系统威胁模型 | 无法展示企业 Agent 的权限与提示注入防护 |
| 工程交付 | 缺少容器化、持续集成、部署说明和负载报告 | 难以证明能稳定上线和运维 |

## 4. 下一阶段产品定位

产品定位升级为：

> ExperimentLens 是面向机器学习、深度学习及其他可量化计算机与人工智能实验的通用实验诊断 Agent。它持续接入实验数据，把统计异常、过程曲线、配置、日志和运行环境组织为可追溯证据，通过受控工具调用形成排错假设，设计最小验证实验，并在新结果回流后自动判断假设得到支持、被否定或仍无结论。

这里的“实验”不要求一定包含模型训练。只要任务可以表示为多次可重复的 run，并具有可比较的参数、指标、状态、日志或产物，就可以进入统一诊断流程。

### 4.1 支持的实验类型

| 实验类型 | 示例 | 主要诊断对象 |
|---|---|---|
| 传统机器学习 | 分类、回归、聚类、特征工程 | 指标、数据切分、特征版本、随机性和耗时 |
| 深度学习训练 | 视觉、NLP、语音、多模态模型 | loss、过拟合、梯度、显存、吞吐量和 seed 稳定性 |
| 强化学习 | 策略优化、Agentic RL、仿真任务 | reward、成功率、回合长度、探索稳定性和资源成本 |
| 推荐与搜索 | 排序、召回、重排和检索实验 | 离线指标、分桶差异、数据版本、延迟和吞吐量 |
| 大模型与 Agent | Prompt、RAG、工具调用和工作流评测 | 正确性、引用、工具轨迹、Token、延迟和安全 |
| 推理与系统性能 | 推理引擎、量化、并行策略和编译优化 | 延迟、吞吐量、内存、错误率和质量损失 |
| 其他计算机与 AI 实验 | 数据处理、检索算法、仿真、模型压缩和 AI 系统 Benchmark | 正确性、复杂度、运行时间、资源和环境差异 |

首阶段仍优先服务人工智能实验，因为现有领域模型和样例最成熟；底层 Run、Param、Metric、Artifact、Finding 和 EvidenceRef 保持领域无关，避免把产品绑定到某一种模型或训练框架。

产品不直接覆盖无法表示为结构化 run 的湿实验、纯主观创作或没有统一评价协议的探索过程。这些场景只有在建立明确的实验单元、指标和证据映射后才接入。

产品闭环升级为：

```text
实验平台 / 文件 / 日志 / Trace
              ↓
增量同步与统一实验模型
              ↓
确定性统计、曲线与资源分析
              ↓
有状态诊断 Agent 调用只读工具
              ↓
证据化假设与最小验证实验
              ↓
人工审批并在外部执行实验
              ↓
新 Run 回流并验证原假设
              ↓
诊断知识沉淀与 Agent 回归评测
```

核心差异化不是让 Agent 自动改代码，而是让诊断过程可信、可复现、可评测和可运维。

## 5. 目标用户与重点场景

### 5.1 目标用户

- 从事传统机器学习、深度学习、视觉、NLP、语音、多模态、强化学习、推荐搜索和大模型应用的研究者与算法工程师。
- 开展 AI 算法、推理引擎、模型压缩、编译优化或系统 Benchmark 的计算机研究人员和工程师。
- 负责实验平台、训练与推理稳定性、资源效率的 MLOps 或 AI 平台工程师。
- 需要审核实验结论、复现实验和决定下一轮预算的学生、科研人员与技术负责人。

### 5.2 重点场景

1. 候选算法、模型或系统配置的均值更好，但变化是否由单个 seed、数据版本或运行环境造成。
2. 训练或计算过程出现 OOM、NaN、曲线震荡、提前终止或性能回退，需要跨日志、配置和过程指标定位原因。
3. RAG、Agent、推理服务或推荐搜索版本发布后质量或性能下降，需要从 Trace 和版本差异定位回归。
4. 系统 Benchmark 的吞吐量提高，但精度、稳定性或资源成本可能退化，需要进行多目标权衡。
5. 下一轮只有有限算力或时间预算，需要选择信息增益最大的验证实验。
6. 个人或团队需要把历史故障和验证结果沉淀为可检索的排错知识。

## 6. 总体技术架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                         Web Console                             │
│ 项目 │ Runs │ 曲线 │ Findings │ Agent Trace │ Evals │ Proposals │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS / SSE
┌───────────────────────────────▼─────────────────────────────────┐
│                  API Gateway + Auth + RBAC                      │
└───────────────┬───────────────────────────────┬─────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌────────────▼─────────────────┐
│ Experiment Application      │  │ Agent Orchestrator           │
│ 项目、同步、分析、报告、反馈 │  │ 状态机、预算、审批、恢复      │
└───────────────┬──────────────┘  └────────────┬─────────────────┘
                │                               │ Typed Tools
┌───────────────▼───────────────────────────────▼─────────────────┐
│                     Domain Tool Layer                           │
│ 统计分析 │ 曲线诊断 │ 日志检索 │ 配置 Diff │ 证据查询 │ 知识检索 │
└───────────────┬───────────────────────────────┬─────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌────────────▼─────────────────┐
│ Connector Layer             │  │ Model Gateway                │
│ File │ MLflow │ TensorBoard │  │ Provider │ Retry │ Budget    │
│ W&B │ HTTP/SDK │ Custom     │  │ Cache │ Fallback │ Policy   │
└───────────────┬──────────────┘  └────────────┬─────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼─────────────────┐
│ PostgreSQL │ Object Storage │ Vector Index │ Redis / Task Queue │
└───────────────────────────────┬─────────────────────────────────┘
                                │ OpenTelemetry
┌───────────────────────────────▼─────────────────────────────────┐
│ Trace、Metrics、Logs、Evaluation、Cost、Audit、Replay           │
└─────────────────────────────────────────────────────────────────┘
```

架构原则：

- 统计结论继续由确定性工具计算，LLM 不自行计算关键数字。
- Agent 只通过有类型、可审计的领域工具读取数据。
- 默认工具只读；任何外部写操作必须经过用户确认。
- 每个自然语言结论必须绑定有效 EvidenceRef。
- 长任务进入异步队列，并支持幂等、取消、重试和断点恢复。
- 先实现一个可靠的诊断 Agent，不为了展示概念引入多 Agent 群体。

## 7. 功能扩充设计

### 7.1 P0：真正的诊断 Agent Runtime

新增 `AgentRun` 状态机：

```text
created → planning → tool_running → synthesizing
        → awaiting_approval → completed
        → failed / cancelled / budget_exhausted
```

核心能力：

- 模型网关支持至少一个云模型和一个本地或 Mock 模型。
- Prompt、模型、工具定义和分析器均带版本号。
- Tool Registry 使用 Pydantic 定义输入输出，拒绝未注册工具。
- 首批只读工具包括 `list_runs`、`compare_groups`、`inspect_metric_curve`、`search_logs`、`diff_configs`、`get_finding_evidence` 和 `retrieve_runbook`。
- Agent 有最大步骤数、Token 预算、超时和重试上限。
- 工具失败返回结构化错误，Agent 可以换查询方式，但不能忽略错误编造结果。
- SSE 输出模型调用、工具开始、工具完成、等待审批和最终回答事件。
- 会话状态可保存和恢复，服务重启后不会丢失已完成工具结果。

验收标准：

- Agent 能完成“找出导致 SegFormer 波动的 runs，并给出证据化验证方案”的端到端任务。
- 回答中引用的 run、metric、param 和 log ID 100% 存在。
- 强制触发超时、工具异常和模型限流时，任务能进入明确状态并安全恢复或终止。

### 7.2 P0：Agent 全链路可观测

按照 OpenTelemetry 的通用语义约定记录 Trace、Metric 和 Log；GenAI 场景至少记录 request、model、tool、retrieval 和 evaluation Span。[OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)

每次 Agent 请求应展示：

- 用户输入、会话和项目 ID。
- Prompt 版本、模型名称和参数。
- 每个 Tool Call 的输入摘要、输出摘要、状态、耗时和重试次数。
- 检索命中的文档和 EvidenceRef。
- 输入与输出 Token、估算成本和端到端延迟。
- 错误类型、回退路径和最终状态。
- 用户反馈及其对应回答版本。

提供 Trace 详情和会话回放页面，支持按失败状态、工具、模型版本、延迟和时间范围过滤。MLflow 官方文档说明生产 Trace 可以用于评估工具轨迹、路由和检索质量，因此 ExperimentLens 的 Trace 数据模型应兼容后续导出或接入。[MLflow Production Trace Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/)

验收标准：

- 任意一条回答都能还原其工具调用顺序和证据来源。
- 能从 Trace 中区分模型失败、工具失败、检索失败和数据本身不足。
- 关闭敏感内容采集时仍保留可用的性能和错误指标。

### 7.3 P0：Agent 评测与回归门禁

建立版本化 `diagnostic-golden-set`，首批至少 50 个案例，覆盖：

- 稳定真实提升。
- 离群 seed 造成虚假均值提升。
- OOM、NaN、Inf、超时和缺失指标。
- 数据、代码和环境版本不一致。
- 训练/验证曲线分离、奖励退化、质量回退和性能异常。
- 日志中有直接证据、间接证据或相互矛盾证据。
- 信息不足时应拒绝确定归因。
- Prompt Injection 和越权工具请求。

评测指标分层：

| 层级 | 指标 | 目标 |
|---|---|---:|
| 确定性检测 | Finding precision / recall | ≥ 0.90 / ≥ 0.85 |
| 证据完整性 | 无效 EvidenceRef 比例 | 0% |
| 假设质量 | 标准根因是否进入 Top-3 | ≥ 85% |
| 不确定性 | 信息不足案例的正确拒答率 | ≥ 90% |
| 实验方案 | 单变量原则满足率 | ≥ 95% |
| 工具行为 | 正确工具选择率 | ≥ 90% |
| 安全 | 未授权写工具调用成功数 | 0 |
| 性能 | Agent 任务 P95 完成时间 | ≤ 20 秒，不含外部模型故障 |

评测组合：

- 代码评分器负责 ID、数值、结构、工具序列和权限等可确定判断。
- LLM Judge 只评估解释完整性、相关性和可执行性。
- 至少抽样 20% 结果由人工复核，并计算 Judge 与人工的一致率。
- 每次 Prompt、模型、工具或工作流变更都对固定数据集回归。
- CI 阻止证据完整性、安全和关键任务成功率下降的版本合并。

### 7.4 P0：通用实验源接口与 MLflow 增量连接器

先定义领域无关的 `ExperimentSource` 接口，统一实验发现、run 分页、参数、指标序列、日志、产物和增量游标。文件、MLflow、TensorBoard、Weights & Biases、HTTP API 和自定义 SDK 都通过适配器进入相同领域模型。

首个企业级适配器选择 MLflow，因为它与当前 Experiment、Run、Param、Metric 和 Artifact 模型天然匹配；这是实施优先级，不是产品范围限制。

功能包括：

- 配置 Tracking URI、认证方式和目标 Experiment。
- 分页读取 runs、params、tags 和最终指标。
- 按需读取 metric history、日志和配置 artifacts。
- 使用 source run ID、更新时间和内容哈希实现幂等增量同步。
- 同步失败保留游标，允许断点重试。
- 凭据进入 Secret Store，不写入项目 JSON、日志或 Trace。
- 连接器默认只读，不允许删除或修改 MLflow 数据。

验收标准：

- 同一批 runs 重复同步不会产生重复记录。
- 中途失败后恢复，同步结果与一次成功同步一致。
- 连接器数据和文件上传数据经过同一套分析接口。
- 使用 Mock Source 验证新的实验源无需修改分析引擎即可接入。

### 7.5 P0：实验过程曲线和资源异常分析

从“每个 run 一个最终指标”扩展到 step/time 序列：

- 训练与验证 loss 趋势。
- 强化学习 reward、成功率和回合长度趋势。
- Agent、RAG 或推理服务的正确率、失败率、Token、延迟和吞吐量趋势。
- 算法与系统 Benchmark 的运行时间、内存、吞吐量和正确性变化。
- 指标长期不改善、震荡、突然跳变或提前终止。
- 训练下降而验证恶化的过拟合信号。
- 学习率变化与指标变化的时间对齐。
- CPU/GPU/NPU 内存、利用率、吞吐量和 step time 异常。
- 相同配置不同 seed 的曲线形态比较。

首批 detector 使用透明规则和稳健统计，不直接上黑盒异常模型。每个 detector 必须说明阈值、版本和适用条件，并允许用户查看原始曲线区间。

### 7.6 P1：下一轮实验的闭环账本

扩展 Proposal 生命周期：

```text
proposed → approved → exported → running → completed
         → supported / refuted / inconclusive
```

功能包括：

- 用户审批 Proposal，并导出 YAML/JSON 实验配置。
- 记录唯一变量、固定条件、预算、seed 和停止条件。
- 新 runs 可以关联 `proposal_id`。
- 确定性验证器比较预期和实际观察。
- Agent 解释为什么假设被支持、否定或仍无结论。
- 实验历史形成“问题—证据—假设—验证—结论”决策链。

该功能是项目从一次性分析工具升级为通用实验诊断闭环的关键展示点。

### 7.7 P1：团队诊断知识库

知识库只存储经过人工确认的内容：

- 故障 Runbook。
- 已确认根因和修复记录。
- 数据集、模型和指标定义。
- 团队实验规范。
- 历史 Proposal 及验证结果。

检索结果必须展示文档版本、片段和来源。Agent 应把“当前数据证据”和“历史经验”分开陈述，不能因为历史案例相似就把相关性表述为当前根因。

评测需要覆盖检索召回率、引用正确率、无答案拒答和过期文档处理。

### 7.8 P1：安全、权限与审计

安全设计遵循最小权限和明确审批：

- Project、Connector、Knowledge Base 和 Report 采用 RBAC。
- 上传文件做类型、大小、压缩炸弹和恶意内容检查。
- 日志与 Trace 支持密钥、Token、邮箱和自定义敏感模式脱敏。
- 外部文档、日志和工具结果全部视为不可信数据，不能覆盖系统指令。
- Tool 具有 `read_only`、`destructive`、`external_side_effect` 和 `requires_approval` 元数据。
- 写操作展示目标、参数和影响范围，用户确认后才能执行。
- 审计日志记录操作者、动作、对象、结果和 Trace ID。
- 多租户数据查询强制带 tenant/project scope，并做越权测试。

MCP 官方安全说明强调客户端应展示工具能力、敏感调用应有同意机制，服务端应验证输入并遵循最小权限。[MCP Security Policy](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/SECURITY.md)

### 7.9 P1：服务化、异步任务和部署

建议演进路径：

- Flask API 保持兼容，逐步拆分 route、service、repository 和 worker。
- PostgreSQL 保存项目、状态、Agent Run、反馈和审计数据。
- 对象存储保存原始文件、Parquet、日志和报告。
- Redis 与任务队列处理解析、同步、分析、评测和报告任务。
- 每个任务使用 idempotency key，支持取消、指数退避和 Dead Letter Queue。
- Docker Compose 提供本地一键启动；云上部署再提供 Kubernetes 清单。
- CI 执行 Python、TypeScript、端到端、Agent Eval、安全扫描和镜像构建。
- 发布记录包含 schema migration、Prompt 版本、模型版本和回滚步骤。

性能验收建议：

- 10,000 个 runs 的结构化汇总在 60 秒内完成。
- 100 MB 合法输入异步解析，页面保持可操作并展示进度。
- 并发 20 个只读分析任务时无数据串读。
- Worker 异常退出后，已确认完成的步骤不重复产生副作用。

### 7.10 P2：受控执行与标准化工具接入

在只读诊断和审批机制稳定后，再扩展：

- 生成可审查的训练配置、Benchmark manifest、Agent 评测配置或 Git patch，但不直接合并。
- 对接内部实验或作业平台提交运行，提交前必须人工确认预算、环境和目标。
- 将 ExperimentLens 的查询与分析能力暴露为 MCP Server。
- 接入可信 MCP Server 前展示权限、网络范围和工具风险。
- 支持 Agent 版本 A/B、Canary 和自动回滚建议。

MCP 中 Tool 属于模型控制的可执行能力，接入外部工具会显著扩大权限边界，因此不能把“支持 MCP”当作默认安全保证。[MCP Server Primitives](https://modelcontextprotocol.io/specification/2025-06-18/server)

### 7.11 明确不优先的功能

- 不优先实现通用多 Agent 群体或角色扮演。
- 不允许 Agent 任意执行 Python 或 Shell。
- 不自动修改实验代码并无限循环运行。
- 不同时接入大量实验平台，先把 MLflow 连接器做到稳定可测。
- 不用向量数据库替代结构化查询和统计分析。
- 不用 LLM Judge 替代可确定的代码断言。

## 8. 领域模型扩展

新增核心实体：

| 实体 | 关键字段 | 作用 |
|---|---|---|
| AgentRun | project_id, session_id, status, prompt_version, model, budget | 一次可恢复的 Agent 任务 |
| TraceSpan | trace_id, parent_id, kind, start, end, status | 还原模型、工具和检索链路 |
| ToolCall | tool_name, input_digest, output_ref, approval, error | 工具调用审计 |
| EvaluationDataset | name, version, cases, provenance | 固定 Agent 回归样本 |
| EvaluationRun | agent_version, scorer_versions, metrics | 比较不同版本质量 |
| HumanFeedback | trace_id, label, correction, reviewer | 校准自动评测 |
| KnowledgeDocument | version, scope, source, chunks | 团队诊断知识 |
| ProposalExecution | proposal_id, external_run_ids, result | 连接建议和新实验 |
| AuditEvent | actor, action, target, result, trace_id | 权限与操作追溯 |

所有实体使用不可变 ID。Prompt、分析器、工具、数据映射和评估器必须独立版本化，避免只保存最终文本而无法复现当时的决策过程。

## 9. API 与事件设计

建议新增：

```text
POST /api/projects/:id/agent-runs
GET  /api/agent-runs/:run_id
GET  /api/agent-runs/:run_id/events
POST /api/agent-runs/:run_id/cancel
POST /api/tool-calls/:call_id/approve

POST /api/projects/:id/connectors/mlflow
POST /api/projects/:id/connectors/:connector_id/sync
GET  /api/projects/:id/metric-series

POST /api/evaluations/run
GET  /api/evaluations/:evaluation_id
GET  /api/evaluations/compare

POST /api/proposals/:proposal_id/approve
POST /api/proposals/:proposal_id/link-runs
POST /api/proposals/:proposal_id/verify

GET  /api/traces/:trace_id
POST /api/traces/:trace_id/feedback
GET  /api/audit-events
```

SSE 事件统一包含：

```json
{
  "event_id": "evt_...",
  "agent_run_id": "ar_...",
  "sequence": 12,
  "type": "tool.completed",
  "timestamp": "2026-09-21T10:00:00Z",
  "payload": {},
  "trace_id": "tr_..."
}
```

`event_id + agent_run_id` 用于客户端去重，`sequence` 用于断线续传后恢复顺序。

## 10. 评测、测试与质量门禁

### 10.1 普通软件测试

- Parser、Connector、Repository、Tool 和 Detector 单元测试。
- API、任务队列、数据库和对象存储集成测试。
- 上传、同步、诊断、审批、回流和报告端到端测试。
- 任务重试、服务重启、限流和模型超时故障注入测试。
- RBAC、租户隔离、Prompt Injection 和敏感信息泄漏安全测试。
- 数据库 migration 的前向与回滚测试。

### 10.2 Agent 专项评测

- 固定黄金集离线回归。
- 从真实 Trace 采样并脱敏形成困难集。
- 新版本与当前稳定版本做成对比较。
- 自动评分和人工复核同时保留评分理由。
- 按任务类型、数据源、异常类型和模型版本切片分析。
- 失败案例进入评测集前需人工确认，避免错误标签持续污染评测。

### 10.3 发布门禁

满足以下条件才能发布：

- 普通测试、类型检查和静态检查全部通过。
- EvidenceRef 有效率保持 100%。
- 关键诊断任务成功率不得低于当前稳定版 2 个百分点。
- 未授权工具调用和跨项目数据读取测试必须全部失败。
- P95 延迟和单任务成本不超过设定预算。
- 新增模型或 Prompt 有可比较的评测报告和回滚方案。

## 11. 分阶段实施计划

### 阶段 A：评测先行与架构基线，1 周

- 冻结当前 MVP 行为并建立 50 个诊断案例。
- 定义 AgentRun、TraceSpan、ToolCall 和评测 schema。
- 记录当前规则系统的 precision、recall、延迟和错误类型。
- 产出第一份 ADR：为什么采用确定性工具加 LLM 综合，而不是让 LLM 直接分析原始表格。

交付物：基线评测报告、黄金集、架构图和 ADR。

### 阶段 B：诊断 Agent Runtime，2 周

- 实现模型网关、Agent 状态机、Tool Registry 和 SSE。
- 将现有统计能力封装为只读工具。
- 实现预算、超时、重试、取消和恢复。
- 完成证据引用校验器。

交付物：真实工具调用演示、失败恢复录屏和 Agent 回归报告。

### 阶段 C：Trace、评测看板与安全基线，2 周

- 接入 OpenTelemetry Trace。
- 增加会话回放、Token、延迟和工具错误看板。
- 建立代码评分器、LLM Judge 和人工反馈工作流。
- 实现脱敏、Prompt Injection 测试和工具审批元数据。

交付物：Trace 页面、版本对比页面、安全测试报告和成本报告。

### 阶段 D：通用连接器与过程诊断，2 周

- 定义并测试领域无关的 ExperimentSource 接口。
- 实现 MLflow 只读增量连接器。
- 支持训练、强化学习、Agent 评测和系统性能的 metric history 与曲线 detector。
- 增加同步任务状态、幂等和失败恢复。
- 用真实或本地 MLflow Server 完成端到端演示。

交付物：连接器 Demo、曲线异常案例和负载测试报告。

### 阶段 E：实验闭环与工程交付，2 周

- 实现 Proposal 审批、导出、run 关联和结果验证。
- 增加 PostgreSQL、任务队列和 Docker Compose。
- 完成端到端 CI、迁移、备份与恢复说明。
- 准备面试演示、技术文章和项目复盘。

交付物：完整闭环 Demo、一键部署、测试报告和面试材料。

总周期约 9 周。若时间有限，必须优先完成阶段 A 到 C；这三阶段最能证明 Agent 工程、评测、可观测和可靠性能力。

## 12. 面试演示方案

### 12.1 八分钟主线 Demo

1. 从 MLflow 同步一批含多 seed、OOM 和曲线异常的深度学习实验，并说明同一接口也适用于 Agent 评测或系统 Benchmark。
2. 展示确定性统计发现和具体 EvidenceRef。
3. 向 Agent 提问“为什么候选算法、模型或系统配置均值更好但不建议发布”。
4. 打开 Trace，展示 Agent 调用了哪些工具、读取了哪些证据、消耗多少 Token 和时间。
5. 展示一个工具超时后的重试或降级过程。
6. 查看 Agent 版本评测，说明新 Prompt 改善了什么、退化了什么。
7. 审批一个最小验证实验并导出配置。
8. 导入新 runs，展示原假设被支持、否定或保持无结论。

### 12.2 必须能够回答的面试问题

- 为什么不让 LLM 直接读取全部 CSV 并计算统计量？
- Agent 与普通 Workflow 的边界在哪里？
- 如何防止模型引用不存在的 run？
- 如何评测排错假设质量，而不只评测最终文案？
- LLM Judge 为什么不能成为唯一门禁？
- Connector 如何保证增量同步幂等？
- Agent 服务重启后如何恢复？
- Prompt Injection 如何通过日志或知识文档进入系统？
- 如何控制 Token 成本和延迟？
- 为什么现在不做多 Agent？什么条件下才值得拆分？

### 12.3 简历可量化表达模板

完成实现后再用真实数据填写以下指标，不提前虚构：

> 设计并实现面向机器学习、深度学习、Agent 评测和系统 Benchmark 的通用实验诊断平台，使用确定性分析工具与有状态 LLM 编排完成证据化排错；构建包含 N 个案例的评测集，使 EvidenceRef 有效率达到 X%，Top-3 根因覆盖率达到 Y%；实现通用 ExperimentSource 并接入 MLflow 增量同步和 OpenTelemetry Trace，将失败定位时间从 A 分钟降低到 B 分钟，并通过异步任务、RBAC 和安全门禁支持可复现部署。

## 13. 项目完成定义

扩充后的项目只有同时满足以下条件，才能称为具有较强面试竞争力：

- 不是单次调用模型，而是有状态、可恢复、受预算约束的 Agent Runtime。
- 不是只展示效果，而是有固定评测集和版本回归数据。
- 不是只看最终回答，而是能回放模型、工具、检索和证据链路。
- 不是只支持样例 CSV，而是至少有一个稳定、幂等、只读的真实平台连接器。
- 不是生成建议后结束，而是能接收新 runs 并验证原假设。
- 不是本地脚本集合，而是有容器、异步任务、权限、安全和 CI/CD。
- 不是只讲技术名词，而是能够用用户问题、设计取舍、量化指标和失败复盘说明价值。

## 14. 参考资料

- [腾讯招聘：混元大模型语音领域专家](https://careers.tencent.com/zh-cn/jobdesc.html?postId=2060285101413150720)
- [腾讯招聘：大模型强化学习框架研发工程师](https://careers.tencent.com/jobdesc.html?postId=2072330929078190080)
- [腾讯云 Agent 可观测](https://cloud.tencent.com/product/agentobs)
- [字节跳动校园招聘](https://jobs.bytedance.com/campus/page-6272Gc)
- [火山引擎 Agent 运营分析概述](https://www.volcengine.com/docs/6285/2310370)
- [华为招聘：云计算 BU](https://career.huawei.com/cn/department-list)
- [华为云 AgentArts Trace 数据回流](https://support.huaweicloud.com/ops-agentarts/agentarts_14_0021.html)
- [华为云 AgentArts 产品介绍](https://support.huaweicloud.com/productdesc-agentarts0/01%20%E4%BA%A7%E5%93%81%E4%BB%8B%E7%BB%8D-pdf.pdf)
- [MLflow：评估生产 Trace](https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/)
- [MLflow：Agent Tracing 与可观测](https://mlflow.org/docs/latest/llms/tracing/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
- [Model Context Protocol Security Policy](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/SECURITY.md)
- [Model Context Protocol Server Primitives](https://modelcontextprotocol.io/specification/2025-06-18/server)

资料检索日期：2026 年 9 月 21 日。岗位和平台能力会持续变化，开始具体实现前应再次确认依赖版本与官方文档。
