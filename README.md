# ExperimentLens

ExperimentLens 是面向机器学习与数据科学实验的证据驱动诊断平台。它把结果表、配置和日志统一为 runs，使用确定性统计生成 baseline 对比和异常 findings，再由受约束 Agent 组合只读工具形成带证据的诊断、下一轮最小实验方案与可分享报告。

2.0 控制面采用 FastAPI，并通过兼容层保留现有 Flask API；AgentRun、事件、ToolCall、EvidenceRef、Trace 与评测结果可持久化到 SQLAlchemy 支持的数据库。AgentEvent 与 Transactional Outbox 在同一事务写入，SSE 支持事件序号和断线续传。Prometheus 指标、OpenTelemetry Trace、20 条版本化 Golden Dataset 与确定性发布门禁均已纳入测试。

面向最终用户的文件准备、操作流程和结果解读说明，参见 [ExperimentLens 使用说明书](docs/user-guide.md)。

后续 Agent Runtime、SSE、Trace、评测、MLflow 和实验回流的实施顺序，参见 [后续阶段修改扩充实施方案](docs/next-stage-implementation-plan.md)。

面向腾讯、字节跳动等大厂面试的服务化、持久化工作流、可观测性、评测、安全、压测和部署升级路线，参见 [ExperimentLens 修改扩充 2.0 项目方案](docs/experimentlens-2.0-expansion-plan.md)。

基于当前代码真实完成度的岗位适配分析、关键缺口、实施优先级、量化验收标准与面试交付物，参见 [ExperimentLens 大厂 AI Agent 实习竞争力升级方案](docs/interview-competitive-modification-roadmap.md)。

## 本地运行

需要 Python 3.11+ 与 Node.js 20+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pnpm install
pnpm build
experimentlens
```

打开 `http://127.0.0.1:5050`。开发界面可另行运行 `pnpm dev`，它会把 `/api` 代理到 Flask。

推荐运行 2.0 FastAPI 控制面（本地默认使用 SQLite，并挂载旧 API）：

```bash
alembic upgrade head
experimentlens-api
```

API 文档位于 `http://127.0.0.1:5050/docs`，健康检查、就绪检查与 Prometheus 指标分别位于 `/api/v2/health/live`、`/api/v2/health/ready` 和 `/api/v2/metrics`。

## 一键基础设施

```bash
docker compose up --build
```

默认启动 Web/API、PostgreSQL、OpenTelemetry Collector、Prometheus 和 Grafana。Redis Streams、MinIO 与 Temporal 已作为明确的后续执行面边界放入可选 profile，避免默认环境启动尚未接入主链路的组件：

```bash
docker compose --profile events --profile artifacts --profile workflow up --build
```

本地示例密码只用于开发环境，部署时必须通过 Secret Manager 或编排平台 Secret 覆盖。

## Agent 评测门禁

固定评测集位于 `evals/cases/golden-v2.jsonl`，覆盖数值异常、OOM、Seed 波动、多目标权衡、越权访问、Prompt Injection、重复消息和超时。记录候选版本轨迹后执行：

```bash
experimentlens-eval --trajectories /path/to/candidate-trajectories.json \
  --output evals/reports/latest.json
```

无效证据、跨项目访问、越权写入和 Prompt Injection 成功数均为零容忍；任务通过率低于 95% 时命令返回非零状态。前端“质量与评测”页展示数据集覆盖和最新门禁结果。

## 支持的数据

- 结果表：CSV、TSV、Excel、JSON、JSONL
- 配置：JSON、YAML
- 日志：TXT、LOG、JSONL

仓库中的样例同时覆盖图像分割、文本分类、时序预测、强化学习、Agent 评测和推理 Benchmark。确定性检测器通过 registry 运行，所有分析证据在输出前都会校验是否指向真实 run、指标、参数或日志。

## 架构边界

Flask API 按项目/导入、分析/报告和 AgentRun 拆为 Blueprint。业务用例位于 `py-src/experimentlens/services/`，只依赖 Repository 接口；默认 `LocalRepository` 完全兼容原 `.experimentlens/workspace`。Agent Runtime 通过强类型只读工具访问当前项目，运行过程先持久化为 JSONL，再通过可续传 SSE 展示给前端，最终回答必须通过 Evidence Validator。

默认使用确定性离线网关，不会访问外部模型。配置以下环境变量后，Agent 使用 OpenAI Responses API；用户问题和必要的结构化工具结果会发送给模型服务：

```bash
export OPENAI_API_KEY="..."
export EXPERIMENTLENS_MODEL="gpt-5.6-luna"
export EXPERIMENTLENS_AGENT_MAX_STEPS="8"
export EXPERIMENTLENS_AGENT_TOKEN_BUDGET="8000"
export EXPERIMENTLENS_AGENT_TIMEOUT_SECONDS="60"
export EXPERIMENTLENS_AGENT_TOOL_TIMEOUT_SECONDS="10"
experimentlens
```

Agent 面板会显示当前模型提供方、模型名称、已注册工具、实时步骤和累计 Token，并允许在每次运行前调整最大步骤数和 Token 预算。`GET /api/projects/:project_id/agent/runtime` 只返回非敏感运行配置，不会返回 API Key。

当前 Agent 工具为 `list_runs`、`compare_groups`、`search_logs`、`diff_configs`、`inspect_metric_series` 和 `get_finding_evidence`，全部强制限定到当前 project 且没有外部副作用。最终回答没有工具证据或包含无效 EvidenceRef 时会被拒绝。

原始文件保存在 `.experimentlens/workspace/<project_id>/sources/original`，标准化表保存为 Parquet，分析结果和报告保存为结构化 JSON/Markdown。默认不上传外部服务，也不会修改或启动用户实验。

## 验证

```bash
pytest --cov=experimentlens --cov-report=term-missing
ruff check .
pnpm test
pnpm build
alembic upgrade head
alembic downgrade base
```

当前已完成的 2.0 边界、尚未宣称完成的生产能力与演进顺序，参见 [2.0 架构实现说明](docs/architecture-2.0.md)。
