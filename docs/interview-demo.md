# ExperimentLens 8 分钟面试演示

## 一键执行

```bash
./scripts/interview_demo.sh
```

脚本会升级数据库，启动 API/Worker，导入 Transformer 示例，创建 AgentRun，终止第一个 Worker 并用第二个 Worker 恢复，导出 Event/Trace，运行 30 条真实评测和 100 任务可靠性基线。产物位于 `.experimentlens/interview-demo/`。

## 讲解节奏

1. 0:00–1:00：打开工作台，说明数据输入、确定性检测和六个只读工具。
2. 1:00–2:30：创建 AgentRun，展示 `model.*`、`tool.*` 和 `evidence.validated` 事件。
3. 2:30–4:00：终止 Worker，展示 Lease 过期、fencing token 变化与 AgentStep 恢复；对比 ToolCall 幂等键。
4. 4:00–5:00：打开 Trace，串起 agent/model/tool/evidence span。
5. 5:00–6:30：打开评测报告，说明 trajectory 为何不能由调用方上传，以及六项版本来源。
6. 6:30–8:00：展示 100 任务报告、边界与下一步演进。

## 诚实的能力边界

性能数字是本地 SQLite 和离线模型基线，不代表互联网生产 SLO。当前工具全部只读，没有多 Agent、长期记忆、Temporal 或 Kubernetes。
