# ADR 0002：评测必须执行真实 AgentRun

- 状态：Accepted
- 日期：2026-10-09

## 决策

Evaluation API 只接收数据集版本、候选模型和运行预算。EvaluationExecutor 为每条案例创建隔离 fixture、入队 AgentRun、由 Worker 执行，然后从持久化 ToolCall、Event、EvidenceRef 和 Trace 组装 trajectory。

## 原因

允许调用方上传 trajectory 只能测试打分器，不能证明工具选择、租户隔离、证据验证和超时终态在真实执行中有效。真实执行让 Prompt、工具 Schema 和模型变化可通过版本 hash 与 baseline 对比。

## 后果

评测更慢，但输出能定位到具体 case、AgentRun、步骤和工具调用。默认确定性离线模型保证 CI 可重复；真实模型作为显式可选的候选运行，不影响离线门禁。
