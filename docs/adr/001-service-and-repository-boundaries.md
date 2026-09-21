# ADR-001：以用例服务和 Repository 接口拆分 MVP 单体

- 状态：accepted
- 日期：2026-09-21
- 决策者：ExperimentLens maintainers
- 关联问题：`docs/project-modification-plan.md` 阶段 0

## 背景与约束

原 `ExperimentService` 同时负责项目、导入、分析和报告，且直接依赖本地 `Workspace`。后续 Agent、连接器与异步任务需要稳定的用例边界，但现有 API 和工作区必须保持兼容。

## 决策

保留 `ExperimentService` 作为兼容 facade，将实现拆到 `ProjectService`、`IngestionService`、`AnalysisService` 和 `ReportService`。服务只依赖 `ExperimentRepository` Protocol；`LocalRepository` 继承现有 `Workspace`，保持目录和文件格式不变。Flask 路由迁入按领域划分的 Blueprint。

## 备选方案

- 一次性删除 `Workspace` 并迁移数据库：会扩大迁移范围，破坏本地优先和旧项目兼容。
- 继续扩充单个 service：短期简单，但会让 Agent 工具复用、测试隔离和存储替换变得困难。

## 后果

API 和已有 import 保持不变，后续可以按用例注入 Mock Repository。当前存在一层 facade 转发；待外部调用全部迁移后可单独评估是否删除。
