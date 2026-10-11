# ExperimentLens

[English](README_EN.md) | 简体中文

ExperimentLens 是面向机器学习与数据科学实验的证据驱动诊断平台。它把结果表、配置和日志统一为 runs，使用确定性统计生成 baseline 对比和异常 findings，再由受约束 Agent 组合只读工具形成带证据的诊断、下一轮最小实验方案与可分享报告。

2.0 控制面采用 FastAPI，并通过兼容层保留现有 Flask API；AgentRun、AgentStep、事件、ToolCall、EvidenceRef、Trace 与评测结果持久化到 SQLAlchemy 支持的数据库。API 只入队，独立 Worker 通过 Lease、heartbeat 和 fencing token 执行并恢复任务；工具调用用步骤级幂等键去重。SSE 支持事件序号和断线续传，30 条评测案例由真实 AgentRun 生成轨迹。

面向最终用户的文件准备、操作流程和结果解读说明，参见 [ExperimentLens 使用说明书](docs/user-guide.md)。

后续 Agent Runtime、SSE、Trace、评测、MLflow 和实验回流的实施顺序，参见 [后续阶段修改扩充实施方案](docs/next-stage-implementation-plan.md)。

面向腾讯、字节跳动等大厂面试的服务化、持久化工作流、可观测性、评测、安全、压测和部署升级路线，参见 [ExperimentLens 修改扩充 2.0 项目方案](docs/experimentlens-2.0-expansion-plan.md)。

基于当前代码真实完成度的岗位适配分析、关键缺口、实施优先级、量化验收标准与面试交付物，参见 [ExperimentLens 大厂 AI Agent 实习竞争力升级方案](docs/interview-competitive-modification-roadmap.md)。

若以最少改动优先获得 Agent 开发岗位的面试竞争力，参见 [ExperimentLens 最小化 Agent 面试竞争力升级方案](docs/minimum-agent-interview-upgrade-plan.md)。

## 推荐启动方式

需要 Python 3.11+ 与 Node.js 20+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pnpm install
./scripts/start_local.sh
```

该命令会构建前端、升级数据库，同时启动 FastAPI 控制面和独立 Agent Worker。打开 `http://127.0.0.1:5050`。开发界面可另行运行 `pnpm dev`。

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

固定评测集位于 `evals/cases/golden-v2.jsonl`，共 30 条诊断、安全和可靠性案例。评测器自动创建隔离 fixture、执行真实 AgentRun，再从数据库采集 ToolCall、Event、Evidence 和 Trace；API 不接受调用方构造的 trajectory。

```bash
experimentlens-eval \
  --output evals/reports/latest.json \
  --markdown-output evals/reports/latest.md
```

用 `--baseline evals/reports/baseline.json` 生成 baseline/candidate 差异。无效证据、跨项目访问、越权写入和 Prompt Injection 成功数均为零容忍；任务通过率低于 95% 时 CLI 返回非零状态。

## 支持的数据

- 结果表：CSV、TSV、Excel、JSON、JSONL
- 配置：JSON、YAML
- 日志：TXT、LOG、JSONL

仓库中的样例同时覆盖图像分割、文本分类、时序预测、强化学习、Agent 评测和推理 Benchmark。确定性检测器通过 registry 运行，所有分析证据在输出前都会校验是否指向真实 run、指标、参数或日志。

## 架构边界

Flask API 按项目/导入、分析/报告和 AgentRun 拆为 Blueprint 并作为兼容层挂载在 FastAPI 下。业务用例位于 `py-src/experimentlens/services/`，只依赖 Repository 接口。Agent Runtime 通过强类型只读工具访问当前项目；API 写入任务后立即返回，Worker 通过数据库 Lease 领取，从已完成 AgentStep 恢复上下文。最终回答必须通过 Evidence Validator。

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

## 统一验证

```bash
make verify
```

该命令依次检查 CLI、后端测试与覆盖率、Ruff、前端测试、TypeScript、前端构建和 Alembic 前滚/回滚/再前滚。

完整项目说明、命令和故障排查见 [项目说明与使用文档](docs/project-description-and-usage.md)；8 分钟演示流程见 [面试演示说明](docs/interview-demo.md)。

面向 AI Agent 初学者的原理、技术栈、代码地图、学习路线和面试问答，见 [从零学习与面试讲解手册](docs/onboarding-and-interview-study-guide.md)。

当前已完成的 2.0 边界、尚未宣称完成的生产能力与演进顺序，参见 [2.0 架构实现说明](docs/architecture-2.0.md)。
