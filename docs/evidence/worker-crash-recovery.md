# Worker 故障恢复记录

验证日期：2026-10-09  
对应实现 commit：`b202a7fdc44283ee1992e1fe08a1d95a71f52109`

## 自动化故障点

`tests/integration/test_worker_recovery.py` 使用真实 SQLite 数据库、AgentRun、Worker Lease 和确定性工具循环，分别在以下位置抛出不被 Agent 异常处理捕获的硬崩溃：

1. 模型调用结果写入 AgentStep 后、进入工具阶段前。
2. 工具已执行、ToolCall 完成结果提交前。
3. Evidence 已校验、最终回答提交前。

每次都等待原 Lease 过期，再使用不同 owner 的 Worker 领取。另一个并发测试在 Lease 未过期时尝试用第二个 Worker 领取同一任务，领取被拒绝，错误 fencing token 也无法通过 ownership 检查。

## 结果

- 3/3 崩溃点最终恢复为 `completed`。
- 模型 Token 计费保持 72，已持久化的模型步骤未重复计费。
- 每个 run 仅 2 条唯一 ToolCall，幂等键无重复。
- EvidenceRef 数量与最终 AgentRun 一致，数据库唯一约束无冲突。
- AgentEvent 序号从 1 连续增长，`agent.completed` 仅出现一次。
- 完整 100-run 故障注入数据见 `reliability-baseline.md`。

## 复现

```bash
pytest -q tests/integration/test_worker_recovery.py
experimentlens-benchmark --runs 100 --workers 2
```
