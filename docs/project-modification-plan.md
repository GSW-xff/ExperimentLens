# ExperimentLens 项目修改方案

## 1. 方案目标

本方案把《ExperimentLens 面向大厂 AI Agent 岗位的扩充设计方案》转化为可以直接执行的代码修改计划。修改后的产品定位为：

> 面向机器学习、深度学习及其他可量化计算机与人工智能实验的通用实验诊断 Agent。

本方案不要求一次性重写当前 MVP。改造采用“小步迁移、兼容旧数据、每阶段可演示”的方式，在保留现有上传、统计、异常、假设、下一轮实验和报告功能的基础上，逐步增加真正的 Agent Runtime、评测、Trace、真实数据连接器和实验回流闭环。

最终需要证明五件事：

1. 产品可以诊断不同类型的结构化计算实验，而不只是一张机器学习结果表。
2. Agent 会调用经过约束的工具，并能恢复、超时、重试和控制预算。
3. 每个结论都可以追溯到真实 run、指标、配置、日志或 Trace。
4. Agent 的质量可以通过固定评测集和 CI 回归量化。
5. 系统可以接入真实实验平台并稳定运行，而不只是本地 Demo。

## 2. 修改原则

- **保留确定性内核**：统计量、异常检测和证据校验继续由代码完成。
- **Agent 只做综合决策**：LLM 负责选择工具、组织证据、比较假设和解释方案。
- **先抽象再接平台**：先建立 `ExperimentSource`，再实现 MLflow 等适配器。
- **先评测再换模型**：Agent Runtime 上线前先冻结黄金集和当前基线。
- **先只读再写入**：首阶段 Agent 工具、连接器和外部集成都保持只读。
- **兼容旧项目**：现有 `.experimentlens/workspace` 项目应自动迁移或保持可读。
- **按垂直切片交付**：每批修改都包含后端、前端、测试和可运行演示。
- **不进行一次性重写**：模块拆分与功能开发分开提交，降低回归风险。

## 3. 当前代码与目标变化

| 当前模块 | 当前职责 | 主要问题 | 目标变化 |
|---|---|---|---|
| `py-src/experimentlens/app.py` | Flask 创建、全部路由、静态页面 | 路由持续膨胀 | 拆成应用工厂和按领域划分的 Blueprint |
| `domain.py` | 所有 Pydantic 模型 | 模型数量增加后难维护 | 拆分 project、experiment、agent、evaluation、audit 模型 |
| `ingestion.py` | 文件解析、字段推断、标准化、日志关联 | Parser 和规则耦合 | 拆成 parser、mapping、normalization、lineage |
| `analysis.py` | 统计、异常、假设、建议、问答 | 确定性分析和自然语言回答耦合 | 拆成统计引擎、detector、evidence、规则基线 |
| `service.py` | 导入、分析、问答、报告、Demo | 单类承担全部用例 | 拆成用例级 service，并引入 repository/tool 接口 |
| `workspace.py` | 本地 JSON、Parquet 和文件目录 | 与本地存储强绑定 | 保留 LocalRepository，实现可替换存储接口 |
| `src/App.tsx` | 导航和全部页面 | 单文件过大、页面状态耦合 | 按 feature 拆分页面、组件和状态 |
| `src/api.ts` | 所有 HTTP 请求 | 不支持 SSE、任务和错误类型 | 增加 typed client、SSE client 和统一错误模型 |
| `src/store.ts` | 项目、runs、分析状态 | 无任务、Trace、评测、连接器状态 | 按 feature 拆成 slices |
| 本地规则问答 | 固定关键词返回回答 | 不是真正工具调用 Agent | 保留为离线回退，新增有状态 Agent Runtime |

## 4. 目标代码结构

建议最终形成以下结构。迁移期间允许旧模块作为兼容入口存在，但不能长期维护两套业务逻辑。

```text
Experimentlens/
├── py-src/experimentlens/
│   ├── app.py
│   ├── config.py
│   ├── api/
│   │   ├── errors.py
│   │   ├── projects.py
│   │   ├── sources.py
│   │   ├── analysis.py
│   │   ├── agent_runs.py
│   │   ├── evaluations.py
│   │   ├── traces.py
│   │   └── proposals.py
│   ├── domain/
│   │   ├── project.py
│   │   ├── experiment.py
│   │   ├── evidence.py
│   │   ├── agent.py
│   │   ├── evaluation.py
│   │   └── audit.py
│   ├── ingestion/
│   │   ├── parsers/
│   │   ├── mapping.py
│   │   ├── normalization.py
│   │   └── lineage.py
│   ├── analysis/
│   │   ├── summary.py
│   │   ├── baseline.py
│   │   ├── curves.py
│   │   ├── resources.py
│   │   ├── detectors/
│   │   └── evidence_validator.py
│   ├── agent/
│   │   ├── orchestrator.py
│   │   ├── state.py
│   │   ├── model_gateway.py
│   │   ├── prompts/
│   │   ├── tools/
│   │   └── fallback.py
│   ├── connectors/
│   │   ├── base.py
│   │   ├── files.py
│   │   └── mlflow.py
│   ├── evaluation/
│   │   ├── runner.py
│   │   ├── datasets.py
│   │   └── scorers/
│   ├── observability/
│   │   ├── tracing.py
│   │   ├── redaction.py
│   │   └── metrics.py
│   ├── repositories/
│   │   ├── interfaces.py
│   │   ├── local.py
│   │   └── postgres.py
│   ├── services/
│   ├── workers/
│   └── reports/
├── src/
│   ├── app/
│   ├── features/projects/
│   ├── features/import/
│   ├── features/overview/
│   ├── features/runs/
│   ├── features/findings/
│   ├── features/agent/
│   ├── features/traces/
│   ├── features/evaluations/
│   ├── features/connectors/
│   ├── features/proposals/
│   ├── features/reports/
│   └── shared/
├── evals/
│   ├── cases/
│   ├── fixtures/
│   └── baselines/
├── migrations/
├── tests/
├── docker-compose.yml
└── docs/adr/
```

## 5. 阶段 0：冻结基线并拆分模块

### 5.1 修改内容

这一阶段不改变用户可见行为，只降低后续修改风险。

- 为当前三个实验样例保存完整分析快照，包括 summary、findings、hypotheses 和 proposals。
- 为 `analysis.py` 中每个 detector 增加阳性、阴性和边界测试。
- 为字段推断补充 IoU、MAE、RMSE、reward、latency、throughput 等通用指标别名测试。
- 把 `app.py` 路由迁移到 Blueprint，但保留原 URL。
- 把 `service.py` 拆成 ingestion、analysis、project 和 report service。
- 把前端页面从 `App.tsx` 移到各 feature 目录，保持 UI 不变。
- 建立 ADR 模板，记录关键架构选择及其替代方案。

### 5.2 兼容策略

- 原有 import 暂时通过 `__init__.py` 重新导出，避免一次修改所有调用点。
- API 返回结构不变。
- 工作区目录和 JSON/Parquet 文件不变。
- 每次只拆一个模块，拆分提交中不加入新功能。

### 5.3 验收标准

- 当前所有测试继续通过。
- 三个样例的结构化分析快照完全一致。
- 前端关键页面截图和交互不发生非预期变化。
- `app.py`、`service.py` 和 `App.tsx` 不再承载全部业务逻辑。

## 6. 阶段 1：通用实验模型与多指标分析

### 6.1 数据模型修改

给 Project 增加：

```text
schema_version
experiment_type
domain_tags[]
owner_id
```

给 Run 增加：

```text
source_id
environment_id
started_at
ended_at
parent_run_id
proposal_id
```

把 `primary_metric + metric_direction` 扩展为版本化指标定义：

```text
MetricDefinition:
key, display_name, role, direction, unit,
aggregation, valid_min, valid_max
```

其中 `role` 支持 `primary`、`secondary`、`constraint` 和 `resource`。例如一个推理实验可以同时要求 Accuracy 最大化、P95 latency 小于阈值、显存最小化。

### 6.2 导入与字段映射修改

- Schema 确认页面支持选择实验类型，但允许“通用计算实验”。
- 支持多个指标及各自方向、单位和角色。
- 自动识别常见质量、损失、奖励、延迟、吞吐量、内存和成本指标。
- 保存原始列到标准字段的 lineage。
- 缺失、空字符串、零和不适用值必须明确区分。
- 版本字段扩展为数据、代码、模型、环境和评估协议版本。

### 6.3 分析修改

- 主要结论继续围绕主指标生成。
- 对 constraint 指标执行阈值检查。
- 增加性能、质量、稳定性和成本的 Pareto 对比。
- 不同实验类型加载不同 detector 集合，但复用统一 Finding 接口。
- 所有计算结果记录 analyzer 名称、版本、输入哈希和生成时间。

### 6.4 前端修改

- 新建分析时增加实验类型和指标定义步骤。
- 总览页展示主指标、约束是否满足和资源权衡。
- Runs 页面支持选择指标、单位和排序方向。
- 图表不再假定所有实验都是训练任务。

### 6.5 验收标准

- 息肉分割、情感分类和负荷预测旧样例继续可用。
- 新增强化学习 reward、Agent 评测、推理 Benchmark 三类 fixture。
- 同一个项目可以比较一个主指标、两个辅助指标和至少一个约束指标。
- 旧 `project.json` 可以自动升级到新 schema，且升级可重复执行。

## 7. 阶段 2：实现真正的 Agent Runtime

### 7.1 新增后端组件

`ModelGateway`：

- 统一模型请求、超时、重试、限流、Token 统计和错误类型。
- 支持真实模型、测试 Mock 和规则回退。
- 密钥只从环境变量或 Secret Store 读取。

`ToolRegistry`：

- 使用 Pydantic 定义工具输入和输出。
- 工具声明只读、是否有外部副作用、是否需要审批。
- 拒绝未注册工具和额外参数。

`AgentOrchestrator`：

- 保存 AgentRun 状态和每一步事件。
- 控制最大步骤、Token 预算、总超时和单工具超时。
- 支持取消、失败恢复和预算耗尽状态。
- 最终输出前运行 EvidenceValidator。

### 7.2 首批 Agent 工具

| 工具 | 输入 | 输出 |
|---|---|---|
| `list_runs` | 筛选条件、分页 | run 摘要和有效 ID |
| `compare_groups` | metric、baseline、groups | 结构化统计比较 |
| `inspect_metric_series` | run_ids、metric、range | 曲线片段和趋势特征 |
| `search_logs` | query、run_ids、limit | 日志证据引用 |
| `diff_configs` | run_ids 或 groups | 参数差异和版本差异 |
| `get_finding_evidence` | finding_id | 原始证据与 detector 信息 |
| `retrieve_runbook` | query、scope | 已确认知识片段和版本 |

### 7.3 API 修改

新增异步接口：

```text
POST /api/projects/:id/agent-runs
GET  /api/agent-runs/:agent_run_id
GET  /api/agent-runs/:agent_run_id/events
POST /api/agent-runs/:agent_run_id/cancel
POST /api/tool-calls/:tool_call_id/approve
```

旧 `/api/projects/:id/chat` 暂时保留：

- 未配置模型时使用现有确定性回答。
- 配置 Agent Runtime 后，内部创建 AgentRun 并等待最终结果。
- 前端稳定切换到 SSE 后再标记旧接口废弃。

### 7.4 前端修改

- 将 ChatDrawer 改为 Agent Run 面板。
- 实时展示“正在比较分组”“正在查询日志”等可理解的工具事件。
- 展示预算、耗时、取消按钮和失败恢复入口。
- 回答中的 EvidenceRef 可跳转到对应 run、日志或图表。
- 需要审批的工具调用必须展示目标和影响范围。

### 7.5 验收标准

- Agent 能通过工具完成跨 runs、指标、日志和配置的诊断。
- 回答中的 EvidenceRef 100% 有效。
- 模型限流、工具超时、服务重启和用户取消均有自动化测试。
- Mock 模型下 Agent 测试完全离线且结果可重复。
- 未配置模型时，现有本地功能仍然可用。

## 8. 阶段 3：Trace、评测与安全门禁

### 8.1 Trace 修改

- 为 HTTP 请求、AgentRun、模型调用、工具调用、检索和评测创建 Span。
- 保存 trace_id、parent_span_id、状态、耗时、Token、重试和错误类别。
- 默认只保存输入输出摘要和哈希；完整内容采集必须显式开启。
- 在写 Trace 前执行密钥、Token、邮箱和自定义规则脱敏。
- 支持 OpenTelemetry exporter，未配置时写本地 JSONL。

### 8.2 评测修改

新增 `evals/`：

- `cases/*.jsonl` 保存输入、期望 finding、允许假设、禁止行为和标签。
- `fixtures/` 保存脱敏后的 runs、配置、日志和 metric series。
- `baselines/` 保存稳定版本的聚合指标，不保存不可复现的自由文本快照。

评分器分为：

- 代码评分器：EvidenceRef、数值、工具选择、参数、状态和权限。
- LLM Judge：解释相关性、假设覆盖和实验方案可执行性。
- 人工反馈：确认根因、纠正评分和标记难例。

### 8.3 前端修改

- 新增 Agent Trace 页面，按 Session 展开 Span。
- 新增 Evaluation 页面，对比 Agent、Prompt 和模型版本。
- 展示任务成功率、证据有效率、Top-3 根因覆盖、P95 延迟和成本。
- 支持用户对回答标记“正确、部分正确、错误”并填写纠正原因。

### 8.4 安全修改

- 外部日志、文档和 Tool Output 全部作为不可信内容处理。
- System Prompt 与外部文本使用不同字段传递，禁止拼接覆盖。
- 所有 repository 查询强制带 project scope。
- 工具输入执行 schema、长度、路径和权限检查。
- 审计用户、工具、连接器、审批和导出操作。
- 建立 Prompt Injection、跨项目访问和敏感信息泄漏测试集。

### 8.5 验收标准

- 任意 Agent 回答均能打开完整 Trace。
- 固定评测集至少 50 个案例。
- 无效 EvidenceRef 比例为 0%。
- 未授权写工具调用成功数为 0。
- CI 可以对比当前版本和稳定基线，并阻止关键指标回退。

## 9. 阶段 4：实验连接器与过程诊断

### 9.1 ExperimentSource 接口

```python
class ExperimentSource(Protocol):
    def list_experiments(self, cursor=None): ...
    def list_runs(self, experiment_id, cursor=None, updated_after=None): ...
    def get_run(self, run_id): ...
    def get_metric_series(self, run_id, metric_key): ...
    def list_artifacts(self, run_id): ...
    def read_artifact(self, run_id, path): ...
```

所有 source 返回统一 DTO，不直接向分析层暴露 MLflow 或其他平台对象。

### 9.2 MLflow 适配器

- 只读连接 Tracking Server。
- 分页和增量读取 experiments、runs、params、tags 和 metrics。
- 按需同步 metric history 与 artifacts。
- 使用 source ID、更新时间和内容哈希保证幂等。
- 凭据不进入 Project、Trace 或普通日志。
- 同步任务支持进度、取消、重试和断点恢复。

### 9.3 通用过程分析

支持以下时间序列：

- 训练/验证 loss 和质量指标。
- 强化学习 reward、成功率和回合长度。
- Agent/RAG 的正确率、工具成功率、Token、延迟和成本。
- 推理或系统 Benchmark 的延迟、吞吐量、内存和错误率。

首批 detector：

- plateau、震荡、突变和提前终止。
- 训练改善但验证退化。
- reward 坍塌或方差突然增大。
- 延迟、吞吐量或内存回退。
- 指标变化与版本、参数或环境变化的时间对齐。

### 9.4 前端修改

- 新增数据源与同步状态页面。
- 曲线页面支持 run 叠加、区间选择、同 seed 配对和异常标记。
- Finding 的证据可以定位到具体曲线区间。
- 连接器错误显示可操作的重试或重新认证提示。

### 9.5 验收标准

- Mock Source、File Source 和 MLflow Source 通过同一连接器契约测试。
- 重复同步不产生重复 run 或 metric point。
- 中途失败恢复后的数据与一次成功同步一致。
- 至少覆盖深度学习、强化学习、Agent 评测和系统性能四类曲线 fixture。

## 10. 阶段 5：下一轮实验回流闭环

### 10.1 Proposal 修改

扩展状态：

```text
proposed → approved → exported → running → completed
         → supported / refuted / inconclusive
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

### 10.2 功能修改

- 用户可以修改并审批 Proposal。
- 按实验类型导出 YAML、JSON、Benchmark manifest 或 Agent eval config。
- 新 runs 可以手动或自动关联 proposal_id。
- 验证器根据预先保存的 decision rule 判断支持、否定或无结论。
- Agent 只能解释验证结果，不能事后修改判断标准迎合结果。
- 已确认案例可以沉淀为诊断知识，但必须保留来源和版本。

### 10.3 前端修改

- Proposal 卡片增加编辑、审批、导出和状态时间线。
- 显示预算、固定条件、停止条件和不同结果的解释规则。
- 新 runs 回流后展示预期与实际对照。
- 项目总览增加已解决、未解决和仍需验证的问题。

### 10.4 验收标准

- 一个 OOM 假设可以完成“生成方案—审批—导出—关联新 run—得出结论”的完整流程。
- 判断规则在结果产生前保存，并保留审计记录。
- 重复关联和重复验证保持幂等。
- 报告能够引用原始异常、Proposal 和验证结果。

## 11. 阶段 6：服务化与交付

### 11.1 存储和任务

- 引入 Repository 接口后再增加 PostgreSQL，不让业务层直接写 SQL。
- 原始文件、Parquet、日志和报告进入对象存储接口；本地文件实现继续保留。
- Redis 与任务队列处理导入、同步、分析、Agent、评测和报告任务。
- 每个任务具有 idempotency key、进度、重试策略和 Dead Letter 状态。
- 数据库 migration 包含前向升级、备份和回滚说明。

### 11.2 身份与权限

- 增加 User、Organization、Membership 和 Role。
- Project、Connector、Knowledge Base、Trace 和 Report 按租户隔离。
- 默认角色为 viewer、analyst 和 admin。
- Agent 不继承创建者的全部权限，只获得任务需要的临时能力。

### 11.3 部署

- Docker Compose 启动 Web、API、Worker、PostgreSQL、Redis 和可选的 MLflow。
- 增加健康检查、readiness、日志格式和环境变量说明。
- CI 执行 Python、TypeScript、E2E、Agent Eval、安全扫描和镜像构建。
- 提供初始化 Demo、备份、恢复和版本回滚脚本。

### 11.4 性能目标

- 10,000 个 runs 的结构化汇总在 60 秒内完成。
- 100 MB 合法文件使用异步任务处理，页面持续显示进度。
- 并发 20 个只读分析任务时不存在跨项目数据读取。
- Agent 任务 P95 完成时间不超过 20 秒，不含外部模型不可用时间。
- Worker 异常退出后，已经完成的幂等步骤不会重复产生副作用。

## 12. 前端页面修改总表

| 页面 | 保留内容 | 新增内容 |
|---|---|---|
| 新建分析 | 名称、目标、上传、字段映射 | 实验类型、多指标、单位、方向、约束 |
| 实验总览 | 运行数、最佳 run、baseline 对比 | 多目标权衡、约束状态、同步和任务状态 |
| Runs | 搜索、状态、主指标、参数 | 指标选择、环境、source、proposal 和版本 diff |
| 异常与证据 | Finding、严重度、EvidenceRef | 曲线区间、detector 版本、确认和误报反馈 |
| 排错 Agent | 当前问答面板 | AgentRun、工具事件、预算、取消和恢复 |
| Trace | 无 | Span 树、模型、工具、检索、错误、Token 和延迟 |
| Evaluations | 无 | 版本比较、切片指标、失败案例和人工复核 |
| 数据源 | 文件列表 | Connector、同步游标、进度、认证和错误恢复 |
| 下一轮实验 | Proposal 卡片 | 编辑、审批、导出、状态、run 回流和验证 |
| 报告 | 编辑和下载 | Agent/分析器版本、Trace、Proposal 验证链 |

## 13. 数据迁移方案

### 13.1 Schema 版本

- 当前项目视为 `schema_version=1`。
- 新项目使用 `schema_version=2`。
- 读取项目时先检测版本，再执行纯函数迁移。
- 每次迁移写入临时目录，校验完成后原子替换。
- 原目录先生成只读备份和 migration manifest。

### 13.2 V1 到 V2 映射

| V1 字段 | V2 目标 |
|---|---|
| `primary_metric` | role 为 primary 的 MetricDefinition |
| `metric_direction` | MetricDefinition.direction |
| `metric_columns` | 多个 MetricDefinition |
| `parameter_columns` | ParamDefinition 或动态 Param |
| `sources[]` | DataSource + SourceManifest |
| `analysis/*.json` | 带 analyzer_version 和 input_digest 的 AnalysisRun |

### 13.3 回滚

- migration 不删除原始上传文件。
- migration 失败时继续以只读方式打开 V1 项目，并显示错误原因。
- V2 写入开始后不再让旧版本应用修改该项目。
- 提供导出兼容包，而不是尝试把所有 V2 能力无损降级到 V1。

## 14. 测试修改方案

### 14.1 单元测试

- 领域模型验证和 V1/V2 migration。
- 每个 Parser、Mapping 规则和 ExperimentSource 契约。
- 每个统计方法和 detector 的阳性、阴性、缺失和边界输入。
- Agent 状态转换、预算、超时、取消和恢复。
- Tool schema、权限和 EvidenceValidator。
- Trace 脱敏和审计事件。
- Proposal decision rule 和幂等验证。

### 14.2 集成测试

- 文件或 MLflow 到统一实验模型。
- Agent 调用多个工具后生成有效证据回答。
- PostgreSQL、对象存储和任务队列故障恢复。
- SSE 断线续传和事件去重。
- 跨项目、跨租户和未授权工具访问失败。
- Prompt Injection 不改变工具权限和系统规则。

### 14.3 前端和 E2E

- 多指标字段确认。
- Agent 事件流、取消和重试。
- Trace 展开和 EvidenceRef 跳转。
- Evaluation 版本比较。
- Connector 同步失败恢复。
- Proposal 审批、导出、回流和报告。

### 14.4 Agent Eval

- 首批至少 50 个版本化案例。
- 评测结果按实验类型、异常类型、模型和 Prompt 版本切片。
- 无效 EvidenceRef 和越权调用是零容忍指标。
- LLM Judge 结果至少抽样 20% 进行人工校准。
- CI 保存与稳定版本的差异报告。

## 15. 九周实施顺序

| 周期 | 核心修改 | 可演示交付物 |
|---|---|---|
| 第 1 周 | 冻结基线、模块拆分、Schema V2 设计 | 不改变行为的模块化版本和基线报告 |
| 第 2–3 周 | 通用实验模型、多指标、Agent Runtime | Agent 工具调用和通用实验导入演示 |
| 第 4–5 周 | Trace、评测、安全门禁 | Trace 回放、版本对比和攻击测试报告 |
| 第 6–7 周 | ExperimentSource、MLflow、过程曲线 | 增量同步和多类型曲线诊断演示 |
| 第 8–9 周 | Proposal 回流、异步任务、部署 | 完整诊断闭环和 Docker Compose |

如果时间不足，最低可交付范围是第 1–5 周。该范围已经可以证明模块化设计、真实 Agent 编排、评测、可观测和安全意识，比继续增加静态分析规则更有面试区分度。

## 16. 推荐提交批次

为了让 Git 历史能够展示工程演进，建议按以下顺序提交，而不是一个超大提交：

1. 固定当前分析快照与 detector 回归测试。
2. 拆分 Flask Blueprint 和后端 services，不改变行为。
3. 拆分前端 feature 页面和 slices，不改变 UI。
4. 增加 Schema V2、migration 和通用指标定义。
5. 增加强化学习、Agent 评测和系统 Benchmark fixtures。
6. 增加 ModelGateway、ToolRegistry 和 Mock 模型。
7. 增加 AgentOrchestrator、SSE 和 EvidenceValidator。
8. 增加 OpenTelemetry Trace、脱敏和回放页面。
9. 增加黄金评测集、scorers 和 CI 门禁。
10. 增加 ExperimentSource 和契约测试。
11. 增加 MLflow 增量连接器和曲线 detector。
12. 增加 Proposal 审批、回流和验证。
13. 增加 PostgreSQL、任务队列和 Docker Compose。
14. 增加 RBAC、安全测试、压力测试和最终演示材料。

每个提交都必须包含相应测试，并保持应用可以启动。

## 17. 风险与控制措施

| 风险 | 影响 | 控制措施 |
|---|---|---|
| 过早大规模重构 | 功能长期不可用 | 先锁定快照，模块拆分和功能开发分离 |
| 产品范围过宽 | detector 质量下降 | 统一模型保持通用，首批只做四类高质量 fixture |
| LLM 输出不稳定 | 回归和演示失败 | Mock、固定黄金集、结构化输出和规则回退 |
| Trace 泄露敏感数据 | 安全风险 | 默认摘要、脱敏、采样和显式内容开关 |
| 连接器产生重复数据 | 分析结果失真 | source ID、游标、内容哈希和幂等测试 |
| LLM Judge 自身不稳定 | 错误发布决策 | 代码指标优先、人工校准、Judge 版本化 |
| 引入基础设施过多 | 本地运行复杂 | LocalRepository 保留，Docker Compose 提供可选服务 |
| Agent 工具越权 | 外部数据或系统受损 | 默认只读、最小权限、审批和审计 |
| 旧工作区无法读取 | 用户数据不可用 | Schema 版本、备份、纯函数迁移和只读降级 |

## 18. 修改完成定义

项目修改完成需要同时满足：

- 支持至少四种不同类型的人工智能或计算实验 fixture。
- 现有三个 CSV 样例和旧工作区继续可用。
- Agent 通过有类型工具完成诊断，不直接读取全部原始数据自由推断。
- 每条关键结论都有有效 EvidenceRef 和完整 Trace。
- 至少 50 个 Agent Eval 案例进入 CI。
- MLflow 增量同步通过幂等和故障恢复测试。
- Proposal 可以关联新 runs 并得出 supported、refuted 或 inconclusive。
- 未授权写操作、跨项目读取和 Prompt Injection 测试全部被阻止。
- Python、TypeScript、E2E、Agent Eval 和生产构建全部通过。
- Docker Compose 可以一条命令启动可演示环境。
- 项目包含架构图、ADR、评测报告、性能报告、安全报告和演示脚本。

## 19. 建议立即开始的第一批修改

第一批只做“基线和模块边界”，不接真实模型：

1. 为三个现有样例保存结构化分析快照。
2. 增加强化学习、Agent 评测和推理 Benchmark 三个 fixture 设计。
3. 拆分 `analysis.py`，建立 detector registry 和 EvidenceValidator。
4. 拆分 `service.py`，引入 Repository 接口但继续使用本地文件。
5. 定义 AgentRun、ToolCall、TraceSpan 和 EvaluationCase 模型。
6. 实现 Mock ModelGateway 与 ToolRegistry 的最小骨架。

完成这一批后，再开始真实 Agent 编排。这样可以先获得稳定评测基线和清晰模块边界，避免在单体文件上直接叠加模型、Trace、连接器和异步任务。
