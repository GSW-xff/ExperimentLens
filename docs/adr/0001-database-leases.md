# ADR 0001：先使用数据库 Lease Worker

- 状态：Accepted
- 日期：2026-10-09

## 决策

AgentRun 由 API 持久化后入队，独立 Worker 使用数据库 Lease、heartbeat 和单调 fencing token 领取。模型、工具和证据边界保存 AgentStep，工具以确定性幂等键提交。

## 原因

当前目标是用最小系统证明状态机、幂等和恢复语义。SQLite/PostgreSQL 已经是项目的真实依赖，这一方案不需要额外运维 Temporal、Redis 或 Kafka，也能用故障测试覆盖脑裂与过期接管。

## 后果

优点是部署简单、事务边界清晰、可在 CI 中完整复现。代价是数据库同时承担队列轮询和业务持久化；如果队列等待、写竞争或跨区恢复成为瓶颈，再迁移到专用工作流引擎。
