# ExperimentLens 后续阶段修改扩充实施方案

## 1. 文档目的

本文档以当前已经完成的“模块化基线与 Agent 基础骨架”为起点，规划 ExperimentLens 从规则驱动的 MVP 演进为有状态、受约束、可评测、可追溯的实验诊断 Agent。

后续改造继续遵守以下原则：

- 保留确定性统计、异常检测和证据校验内核。
- 大模型只负责选择工具、综合证据、比较假设和解释实验方案。
- Agent 不直接读取整个工作区，只能调用经过注册、校验和授权的工具。
- 每个阶段都包含后端、前端、测试和可运行演示。
- 每个提交都保持应用可启动，并包含对应测试。
- 旧 API、旧工作区和未配置模型时的本地能力继续可用。

## 2. 当前基线

当前版本已经具备：

- Flask Blueprint 和按用例拆分的 service。
- Repository 接口与兼容旧工作区的 LocalRepository。
- Detector Registry 和 EvidenceValidator。
- AgentRun、ToolCall、TraceSpan、EvaluationCase 领域模型。
- ToolRegistry 和离线 MockModelGateway。
- 六类实验 fixture 和三个原始样例的完整分析快照。
- IoU、MAE、RMSE、reward、latency、throughput、memory、cost 等指标推断。

当前尚未接入真实模型、Agent 编排、SSE、Trace 页面、评测运行器、MLflow 和 Proposal 回流。

## 3. 总体实施路径

```text
Schema V2 与多指标模型
    ↓
Agent Runtime 与受约束工具
    ↓
SSE 实时事件流与 Agent 面板
    ↓
Trace、Evaluation 与安全门禁
    ↓
ExperimentSource、MLflow 与曲线诊断
    ↓
Proposal 审批、实验回流与结果验证
    ↓
Worker、数据库、权限和生产部署
```

各阶段必须按依赖顺序推进。尤其不能在 Schema V2 和工具契约稳定前，让大模型直接访问原始实验数据。

## 4. 阶段一：Schema V2 与多指标分析

### 4.1 目标

解除 MVP 对单一 `primary_metric` 的依赖，使同一个项目可以同时分析质量、稳定性、延迟、成本和资源约束。

### 4.2 数据模型

新增 `MetricDefinition`：

```text
key
display_name
role: primary | secondary | constraint | resource
direction: maximize | minimize
unit
aggregation
valid_min
valid_max
constraint_operator
constraint_value
```

Project 增加：

```text
schema_version = 2
experiment_type
domain_tags[]
owner_id
metric_definitions[]
```

Run 增加：

```text
source_id
environment_id
started_at
ended_at
parent_run_id
proposal_id
```

### 4.3 数据迁移

- V1 的 `primary_metric` 转为 role 为 `primary` 的 MetricDefinition。
- `metric_direction` 转移到对应 MetricDefinition。
- `metric_columns` 转为多个版本化指标定义。
- 迁移实现为无副作用纯函数。
- 迁移前生成只读备份和 migration manifest。
- 在临时目录完成校验后原子替换。
- 重复执行迁移不得继续修改已迁移项目。
- 迁移失败时以只读方式打开 V1 项目并显示原因。

### 4.4 分析能力

- 主要结论继续围绕 primary 指标生成。
- 对 constraint 指标执行阈值检查。
- 支持质量、性能、稳定性、成本和资源的 Pareto 对比。
- 分析结果记录 analyzer 名称、版本、输入哈希和生成时间。
- 不同 experiment_type 加载不同 detector 集合。

### 4.5 前端

- 新建分析流程增加实验类型。
- 支持多个指标、角色、单位、方向和约束条件。
- Runs 页面支持指标切换和按方向排序。
- Overview 展示主指标、约束状态和资源权衡。
- 图表不再假设所有数据都是训练实验。

### 4.6 验收标准

- 原三个项目自动迁移且分析快照不变。
- 同一项目支持一个主指标、两个辅助指标和至少一个约束指标。
- 六类现有 fixture 全部可分析。
- V1 → V2 迁移可重复执行。

## 5. 阶段二：真正的 Agent Runtime

### 5.1 模型接入边界

Agent 只能执行以下流程：

1. 接收用户问题和有限上下文。
2. 从已注册工具中选择下一步操作。
3. 获取工具返回的结构化结果和 EvidenceRef。
4. 比较候选假设并决定是否继续调用工具。
5. 在预算内生成带有效证据的最终回答。

模型不得直接遍历工作区、拼接任意 SQL、访问未注册工具或绕过项目作用域。

### 5.2 ModelGateway

统一接口：

```python
class ModelGateway(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...
```

实现顺序：

1. `MockModelGateway`：离线、确定性、用于 CI。
2. `OpenAIModelGateway`：真实模型调用。
3. `FallbackModelGateway`：未配置模型时使用现有规则回答。

ModelGateway 统一处理：

- 连接和读取超时。
- 指数退避重试和最大重试次数。
- 限流和并发控制。
- 输入、输出和缓存 Token 统计。
- 结构化输出验证。
- 模型错误分类。
- 模型、Prompt 和工具版本记录。
- API Key 仅从环境变量或 Secret Store 读取。

建议环境变量：

```text
EXPERIMENTLENS_MODEL_PROVIDER
EXPERIMENTLENS_MODEL
OPENAI_API_KEY
EXPERIMENTLENS_AGENT_MAX_STEPS
EXPERIMENTLENS_AGENT_TOKEN_BUDGET
EXPERIMENTLENS_AGENT_TIMEOUT_SECONDS
```

### 5.3 首批只读工具

| 工具 | 主要输入 | 输出 |
|---|---|---|
| `list_runs` | 筛选、排序、分页 | run 摘要和有效 ID |
| `compare_groups` | metric、baseline、groups | 结构化统计比较 |
| `inspect_metric_series` | run_ids、metric、range | 曲线片段和趋势特征 |
| `search_logs` | query、run_ids、limit | 日志片段和 EvidenceRef |
| `diff_configs` | run_ids 或 groups | 参数、模型、数据和环境差异 |
| `get_finding_evidence` | finding_id | 原始证据和 detector 信息 |
| `retrieve_runbook` | query、scope | 已确认知识片段和版本 |

每个工具必须具备：

- Pydantic 输入和输出模型。
- 强制 project scope。
- 参数长度、分页和路径限制。
- 只读、副作用和审批声明。
- 单工具超时。
- 结构化错误类型。
- EvidenceRef 输出。

### 5.4 AgentOrchestrator

状态机：

```text
pending
  → running
  → waiting_for_tool
  → running
  → validating_evidence
  → completed

异常或人工分支：
  → failed
  → cancelled
  → budget_exhausted
  → awaiting_approval
```

Orchestrator 必须控制：

- 最大步骤数。
- Token 总预算。
- AgentRun 总超时。
- 单次模型调用超时。
- 单工具调用超时。
- 重复工具调用检测。
- 用户取消。
- 模型调用重试。
- 失败恢复。
- 最终 EvidenceValidator。

### 5.5 本地持久化

第一版继续保持本地优先：

```text
.experimentlens/workspace/<project_id>/agent-runs/<agent_run_id>/
├── run.json
├── events.jsonl
└── tool-calls.jsonl
```

所有事件必须先持久化再发送给前端，确保页面刷新、SSE 重连或服务重启后仍可恢复。

### 5.6 验收标准

- Mock 模型下的 Agent 流程完全离线且结果可重复。
- Agent 能通过多个工具完成跨 runs、配置和日志诊断。
- 未注册工具和额外参数全部被拒绝。
- 回答中的 EvidenceRef 100% 有效。
- 未配置真实模型时仍能使用现有确定性回答。

## 6. 阶段三：SSE 实时事件流与 Agent 面板

### 6.1 API

```text
POST /api/projects/:project_id/agent-runs
GET  /api/agent-runs/:agent_run_id
GET  /api/agent-runs/:agent_run_id/events
GET  /api/agent-runs/:agent_run_id/stream
POST /api/agent-runs/:agent_run_id/cancel
POST /api/agent-runs/:agent_run_id/retry
POST /api/tool-calls/:tool_call_id/approve
```

创建请求示例：

```json
{
  "question": "为什么候选组延迟下降但准确率也下降？",
  "max_steps": 8,
  "token_budget": 8000
}
```

### 6.2 SSE 事件协议

统一 envelope：

```json
{
  "id": 17,
  "agent_run_id": "ar_xxx",
  "type": "tool.completed",
  "created_at": "2026-09-21T10:00:00Z",
  "payload": {}
}
```

首批事件类型：

```text
agent.created
agent.started
model.started
model.completed
tool.requested
tool.started
tool.completed
tool.failed
approval.required
evidence.validated
agent.completed
agent.failed
agent.cancelled
heartbeat
```

协议要求：

- 每个 AgentRun 的 event ID 单调递增。
- 支持 `Last-Event-ID` 断线续传。
- 客户端按 event ID 去重。
- 空闲期间发送 heartbeat。
- Agent 完成后发送最终事件并关闭连接。
- 用户取消后停止模型和工具任务。
- SSE 断线不取消 AgentRun。

### 6.3 前端 Agent 面板

用 Agent Run 面板替换当前问答抽屉，展示：

- 当前执行阶段。
- 工具调用时间线。
- 工具输入和输出摘要。
- 已用步骤和最大步骤。
- Token 使用量和预算。
- 总耗时。
- 取消按钮。
- 失败恢复和重试入口。
- EvidenceRef 跳转。
- 审批目标和影响范围。

旧 `/api/projects/:id/chat` 暂时保留：

- 未配置模型时走规则回答。
- 配置模型后内部创建 AgentRun 并等待最终结果。
- 前端稳定切换到 SSE 后再标记为废弃。

### 6.4 验收标准

- 页面刷新后可恢复 AgentRun 状态。
- SSE 重连不会丢失或重复展示事件。
- 取消操作在限定时间内停止任务。
- 工具失败能够显示可操作的重试信息。

## 7. 阶段四：Trace、Evaluation 与安全门禁

### 7.1 Trace

为以下操作创建 Span：

- HTTP 请求。
- AgentRun。
- 模型调用。
- 工具调用。
- Repository 查询。
- 检索。
- Evidence 校验。
- Evaluation。

记录字段：

```text
trace_id
span_id
parent_span_id
name
status
duration_ms
retry_count
input_digest
output_digest
token_usage
error_category
```

默认只保存输入输出摘要和哈希，不保存完整 Prompt、日志和模型响应。

### 7.2 脱敏

写入 Trace 和普通日志前处理：

- API Key 和 Bearer Token。
- 邮箱。
- URL 中的凭据。
- 自定义敏感字段。
- 日志中的 Secret。
- Prompt 中的敏感配置。

### 7.3 Agent Evaluation

目录：

```text
evals/
├── cases/
├── fixtures/
├── baselines/
└── reports/
```

第一批先建立 20 个高质量案例，再扩展到至少 50 个，覆盖：

- OOM。
- 数值异常。
- seed 不稳定。
- 数据版本漂移。
- 均值提升但统计证据不足。
- 准确率、延迟和成本权衡。
- reward 坍塌。
- Agent 工具调用失败。
- Prompt Injection。
- 跨项目访问。

代码评分指标：

- EvidenceRef 有效率。
- 数值准确率。
- 工具选择准确率。
- 工具参数准确率。
- Top-3 假设覆盖率。
- 未授权调用数。
- 任务完成率。
- P95 延迟。
- Token 和成本。

零容忍指标：

- 无效 EvidenceRef 数量必须为 0。
- 跨项目读取成功数必须为 0。
- 未审批写操作成功数必须为 0。
- Secret 泄漏数量必须为 0。
- 外部内容改变系统规则的成功数必须为 0。

### 7.4 前端

- Agent Trace 页面展示 Span 树。
- Evaluation 页面比较模型、Prompt、Agent 和工具版本。
- 展示整体与实验类型切片指标。
- 支持用户标记正确、部分正确或错误并填写原因。

### 7.5 验收标准

- 任意 Agent 回答都可打开完整 Trace。
- 固定评测集可以在 CI 中离线运行。
- CI 能对比当前结果和稳定基线。
- 安全零容忍指标全部满足。

## 8. 阶段五：ExperimentSource、MLflow 与曲线诊断

### 8.1 ExperimentSource

```python
class ExperimentSource(Protocol):
    def list_experiments(self, cursor=None): ...
    def list_runs(self, experiment_id, cursor=None, updated_after=None): ...
    def get_run(self, run_id): ...
    def get_metric_series(self, run_id, metric_key): ...
    def list_artifacts(self, run_id): ...
    def read_artifact(self, run_id, path): ...
```

实现顺序：

1. MockSource。
2. FileSource。
3. MLflowSource。

所有 Source 返回统一 DTO，分析层不能依赖 MLflow 原始对象。

### 8.2 MLflow 只读连接器

- experiments 和 runs 分页。
- params、tags 和 metrics 同步。
- metric history 和 artifacts 按需读取。
- 增量同步游标。
- source ID、更新时间和内容哈希保证幂等。
- 失败重试和断点恢复。
- 同步进度和取消。
- 凭据不进入 Project、Trace 或普通日志。

### 8.3 过程曲线 Detector

- plateau。
- 震荡。
- 突变。
- 提前终止。
- 训练改善但验证退化。
- reward 坍塌或方差突增。
- 延迟、吞吐量或内存回退。
- 版本变化与指标异常的时间对齐。

### 8.4 前端

- 数据源和同步状态页面。
- 曲线叠加和区间选择。
- 同 seed 配对。
- 曲线异常标记。
- EvidenceRef 定位到具体曲线区间。
- 可操作的重试和重新认证提示。

### 8.5 验收标准

- Mock、File 和 MLflow Source 通过同一契约测试。
- 重复同步不产生重复 run 或 metric point。
- 中途失败恢复后与一次成功同步的数据完全一致。

## 9. 阶段六：Proposal 审批、回流与验证

### 9.1 状态模型

```text
proposed
→ approved
→ exported
→ running
→ completed
→ supported | refuted | inconclusive
```

新增字段：

```text
budget
stop_conditions
expected_outcomes[]
decision_rules[]
external_run_ids[]
reviewer_id
approved_at
```

### 9.2 功能

- 用户编辑 Proposal。
- 人工审批后才能导出或执行后续操作。
- 按实验类型导出 YAML、JSON、Benchmark manifest 或 Agent eval config。
- 新 run 手动或自动关联 proposal_id。
- 按预先保存的 decision rule 自动判断结果。
- Agent 解释 supported、refuted 或 inconclusive 的原因。
- 报告串联 Finding、Hypothesis、Proposal、新 Run 和验证结论。

Decision rule 必须在新结果产生前保存。Agent 不得根据结果事后修改规则。

### 9.3 验收标准

- OOM 假设可完成生成、审批、导出、关联 run 和得出结论的完整流程。
- 重复关联和重复验证保持幂等。
- 所有状态转换保留审计记录。

## 10. 阶段七：服务化与生产交付

在 Agent、Trace 和 Evaluation 稳定后再引入：

- PostgreSQL Repository。
- 原始文件和 artifact 对象存储。
- Redis 与 Worker 队列。
- 导入、同步、分析、Agent、评测和报告异步任务。
- idempotency key、进度、重试和 Dead Letter 状态。
- User、Organization、Membership 和 Role。
- Project、Connector、Trace 和 Report 租户隔离。
- OpenTelemetry exporter。
- Docker Compose。
- 健康检查和 readiness。
- 备份、恢复和 migration 脚本。

不建议在 Agent Runtime 第一版同时引入全部基础设施，否则模型、编排、任务和存储问题会相互干扰。

## 11. 推荐提交顺序

1. `feat: add schema v2 models and idempotent migration`
2. `feat: support multi-metric analysis and constraints`
3. `feat: add read-only diagnostic agent tools`
4. `feat: implement model gateway and agent orchestrator`
5. `feat: persist agent runs and event logs`
6. `feat: stream agent events over resumable sse`
7. `feat: replace chat drawer with agent run panel`
8. `feat: add trace recording and redaction`
9. `feat: add agent evaluation runner and security cases`
10. `feat: add experiment source contract and file source`
11. `feat: add mlflow incremental connector`
12. `feat: diagnose metric series and curve anomalies`
13. `feat: implement proposal approval and result validation`
14. `feat: add worker queue postgres and docker deployment`

每个提交必须增加或更新相关测试，并确保 Python、TypeScript、前端测试和生产构建全部通过。

## 12. 下一批建议交付范围

下一批建议作为一个完整的垂直切片交付：

- Schema V2 和可重复迁移。
- 多指标及约束分析。
- `list_runs`、`compare_groups`、`search_logs`、`diff_configs` 四个只读工具。
- OpenAIModelGateway。
- AgentOrchestrator。
- AgentRun 本地持久化。
- 支持断线续传的 SSE。
- 前端 Agent Run 面板。
- Mock 模型下的完整离线集成测试。

完成后，ExperimentLens 将从规则分析工作台升级为具备真实模型调用、确定性工具执行、实时过程展示、预算控制和证据校验的实验诊断 Agent。

## 13. 下一批完成定义

下一批只有同时满足以下条件才算完成：

- 旧项目和现有 API 继续可用。
- 未配置模型时规则回答继续工作。
- 配置模型后可以创建 AgentRun。
- Agent 至少连续调用两个工具完成一次诊断。
- 工具只能访问当前 project。
- 所有最终 EvidenceRef 通过校验。
- SSE 支持重连、去重和取消。
- 页面可以查看工具事件、预算、耗时和最终回答。
- Mock 模型测试完全离线且可重复。
- Python、TypeScript、前端测试和生产构建全部通过。
