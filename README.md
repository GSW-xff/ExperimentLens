# ExperimentLens

ExperimentLens 是面向机器学习与数据科学实验的本地优先分析工作台。它把结果表、配置和日志统一为 runs，使用确定性统计生成 baseline 对比和异常 findings，再据此形成带证据的排错假设、下一轮最小实验方案与可分享报告。

面向最终用户的文件准备、操作流程和结果解读说明，参见 [ExperimentLens 使用说明书](docs/user-guide.md)。

后续 Agent Runtime、SSE、Trace、评测、MLflow 和实验回流的实施顺序，参见 [后续阶段修改扩充实施方案](docs/next-stage-implementation-plan.md)。

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
pytest
pnpm test
pnpm build
ruff check .
```
