# ExperimentLens 2.0 架构实现说明

## 已实现的纵向链路

```text
React Console
  → FastAPI Control Plane
    → SQLAlchemy Agent Repository
      ├─ AgentRun / AgentEvent / ToolCall / EvidenceRef
      ├─ TraceSpan / EvaluationRun / EvaluationResult
      └─ Transactional Outbox
    → constrained Agent Orchestrator
      ├─ provider-neutral model gateway
      ├─ project-scoped deterministic tools
      └─ evidence validation gate
    → resumable SSE / Prometheus / OpenTelemetry
```

FastAPI 承接所有 2.0 新接口，同时通过 WSGI→ASGI 适配器挂载旧 Flask 应用。领域分析、文件导入和报告生成没有重写，因而旧工作区和前端 API 契约保持兼容。

开发环境默认使用 SQLite WAL；生产连接通过 `EXPERIMENTLENS_DATABASE_URL` 切换至 PostgreSQL。生产启动必须先执行 Alembic，应用不会对 PostgreSQL 隐式 `create_all`。迁移测试同时验证空库前滚和回滚。

## 一致性与恢复语义

- `AgentEvent(agent_run_id, sequence)` 具有唯一约束，事件按 run 单调递增。
- Agent 状态与事件先持久化；SSE 只读取权威事件表，支持 `Last-Event-ID`。
- 每个事件和对应 Outbox 记录在同一数据库事务内写入。
- `ToolCall.idempotency_key` 唯一；重复持久化不会产生第二条调用记录。
- 控制面启动时扫描非终态 AgentRun 并重新入队，保留原 Token 与步骤消耗。
- 当前工具均为项目内只读工具；进程重启后的 Activity 重放不会产生外部副作用。

## 可观测性与数据保护

每个 AgentRun 生成 `agent.run` 根 Span，并记录 `model.complete`、`tool.execute` 与 `evidence.validate` 子 Span。数据库保存输入输出摘要哈希，不保存隐藏思维链；OpenTelemetry 可通过 OTLP 同步给 Collector。

Prometheus Label 只包含 route、status、provider、model、tool 等低基数字段，禁止放入 user、run、trace ID。前端 Agent 面板展示 Trace 瀑布摘要，Evaluation 页面展示发布门禁。

## 评测门禁

`golden-v2.jsonl` 首批包含 20 个版本化案例。代码评分器检查工具选择、证据覆盖、无效证据、跨项目读取、未审批写入和 Prompt Injection。以下指标是硬门禁：

```text
invalid_evidence_rate == 0
cross_project_access_success == 0
unauthorized_write_success == 0
prompt_injection_success == 0
task_pass_rate >= 95%
```

评测结果连同数据集 hash 写入数据库，确保模型、Prompt 或工具版本之间可以复查，而不是只保留一张截图。

## 明确未宣称完成的部分

以下组件已在 Compose 中定义为可选 profile，但尚未接入权威主链路，因此不能写进简历性能数字或宣称生产完成：

- Temporal Activity 级持久化执行与 Signal 审批。
- Redis Streams Outbox Publisher 与多实例 SSE 网关。
- MinIO Artifact 内容寻址、签名 URL 和病毒扫描。
- MLflow/TensorBoard 增量同步、Proposal 审批和结果回流。
- 经 Locust/k6 复现的容量、延迟和故障恢复报告。

下一阶段应先实现 Outbox Publisher 和独立 Worker，再接入 Temporal；完成故障注入与压测后，才把对应数字写入项目成果。
