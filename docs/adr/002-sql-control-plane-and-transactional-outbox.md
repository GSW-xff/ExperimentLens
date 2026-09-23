# ADR-002：FastAPI SQL 控制面与 Transactional Outbox

- 状态：Accepted
- 日期：2026-09-23

## 背景

本地 JSON/JSONL 能保证单机可追溯，但无法提供跨进程并发控制、原子事件序号、查询索引和标准迁移。一次性重写既有分析 API 会扩大回归面。

## 决策

新增 FastAPI 控制面，以 ASGI 兼容层挂载旧 Flask API。2.0 Agent、Trace 与 Evaluation 元数据进入 SQLAlchemy 仓储，开发使用 SQLite WAL，部署使用 PostgreSQL。AgentEvent 与 Outbox 记录在同一事务中写入，实时分发层只能消费 Outbox，不能成为权威状态源。

## 结果

- 新旧 API 可以在同一进程渐进迁移。
- 数据库迁移、唯一索引和事务语义可以自动验证。
- Redis 不可用时仍能从数据库事件表回放。
- 代价是迁移期存在两套 Repository；项目/实验数据仍在文件工作区，后续按用例逐步迁移。
