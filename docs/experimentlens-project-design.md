# ExperimentLens 项目设计方案

## 1. 文档目的

本文档描述 ExperimentLens 的整体技术方案、核心模块、项目搭建顺序，以及以下三个开源项目在系统中的复用位置：

- **主要复用**：[Microsoft Data Formulator](https://github.com/microsoft/data-formulator)
- **辅助设计参考**：[karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- **未来实验数据接入**：[MLflow](https://github.com/mlflow/mlflow)

本文档以 MVP 产品设计为前提。第一阶段聚焦“导入已有实验数据—分析结果—发现异常—提出排错假设—建议下一轮实验—生成报告”，不自动修改用户代码，也不直接启动实验。

## 2. 设计目标

ExperimentLens 需要提供一条可信、可追溯的实验分析链路：

```text
结果文件 / 配置 / 日志
          ↓
数据解析与实验结构确认
          ↓
统一实验数据模型
          ↓
确定性统计分析与异常检测
          ↓
基于证据的 Agent 解释与排错
          ↓
下一轮最小验证实验
          ↓
可追溯分析报告
```

核心设计原则：

- **统计计算确定化**：均值、置信区间、效应量和异常检测由经过测试的代码执行，不由 LLM 凭文本推断。
- **Agent 负责综合判断**：LLM 负责解释、组织证据、生成候选假设和下一步方案。
- **结论必须可追溯**：重要结论引用具体 run、指标、配置项或日志行。
- **用户保留控制权**：实验字段、baseline、异常判断和排错假设都允许用户确认或修正。
- **先支持文件，再支持平台**：MVP 使用文件上传，后续通过连接器接入 MLflow。

## 3. 三个参考项目的职责边界

| 项目 | 在 ExperimentLens 中的角色 | 复用方式 | 明确不复用的部分 |
|---|---|---|---|
| Microsoft Data Formulator | 应用底座 | Fork 后复用前端、文件解析、工作区、Agent Shell、沙箱、图表和报告能力 | 通用数据探索的产品定位和完全自由的数据分析流程 |
| karpathy/autoresearch | 实验决策循环参考 | 借鉴受约束目标、实验账本、keep/discard/crash 状态和基于历史结果规划下一步的思路 | 自动修改代码、自动运行实验、Git reset 和无限循环 |
| MLflow | 后续实验数据源 | 通过 Python Client 或 REST API 读取 experiment、run、param、metric、tag 和 artifact | 第一阶段不把 MLflow 作为系统数据库，也不要求用户预先使用 MLflow |

选择该组合的原因是三者互补：Data Formulator 解决“产品怎么搭起来”，autoresearch 提供“实验决策如何形成闭环”的简洁范式，MLflow 解决“真实团队的实验数据如何持续接入”。

## 4. 总体架构

```text
┌──────────────────────────────────────────────────────────────┐
│                     ExperimentLens Web                       │
│  项目概览 │ Runs │ Baseline 对比 │ 异常 │ 假设 │ 下一步 │ 报告 │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP + NDJSON/SSE
┌──────────────────────────────▼───────────────────────────────┐
│                    Application API                           │
│ 项目管理 │ 文件上传 │ Schema 确认 │ 分析任务 │ 对话 │ 报告生成 │
└──────────────┬──────────────────────┬────────────────────────┘
               │                      │
┌──────────────▼─────────────┐  ┌─────▼────────────────────────┐
│ Deterministic Analysis     │  │ Experiment Analyst Agent     │
│ 统计 │ 对比 │ 异常 │ 趋势 │  │ 证据组织 │ 假设 │ 实验建议 │
└──────────────┬─────────────┘  └─────┬────────────────────────┘
               │                      │ 工具调用
┌──────────────▼──────────────────────▼────────────────────────┐
│                   Experiment Domain                          │
│ Run │ Param │ Metric │ Artifact │ Finding │ Evidence │ Hypothesis │
└──────────────┬──────────────────────────────┬────────────────┘
               │                              │
┌──────────────▼─────────────┐       ┌────────▼─────────────────┐
│ Local Workspace            │       │ Connector Layer          │
│ Parquet │ JSON/JSONL │ 文件 │       │ File MVP │ MLflow Future │
└────────────────────────────┘       └──────────────────────────┘
```

系统划分为五层：

1. **交互层**：上传、确认、查看分析结果、对话和编辑报告。
2. **应用层**：协调项目、数据源、分析任务、Agent 会话和报告。
3. **分析层**：以确定性代码完成统计和异常检测。
4. **Agent 层**：读取结构化分析结果，生成解释、假设与下一步实验建议。
5. **数据层**：用统一领域模型屏蔽文件和 MLflow 等不同来源。

## 5. 技术栈

### 5.1 前端

沿用 Data Formulator 的前端技术栈，减少底层重写：

| 技术 | 用途 |
|---|---|
| React 18 + TypeScript | Web 应用与类型安全的交互逻辑 |
| Vite | 开发服务器和前端构建 |
| Material UI | 基础组件与界面布局 |
| Redux Toolkit | 项目、数据表、分析任务和会话状态 |
| Vega-Lite / ECharts / Flint Chart | 指标曲线、分布、对比和资源消耗图表 |
| TipTap | 分析报告编辑器 |
| Vitest + Testing Library | 前端单元与组件测试 |
| Playwright | 核心用户流程的端到端测试 |

MVP 的主要页面：

- 项目与数据源页面。
- 实验字段确认页面。
- 实验概览 Dashboard。
- Runs 和配置对比页面。
- 异常与证据页面。
- 排错假设与下一轮实验页面。
- Agent 对话面板。
- 报告编辑与导出页面。

### 5.2 后端

| 技术 | 用途 |
|---|---|
| Python 3.11+ | 主要后端和分析语言 |
| Flask | 沿用 Data Formulator 的 API 和流式响应框架 |
| Pydantic | 领域对象、工具输入和分析输出校验 |
| Pandas | 中小规模实验表处理 |
| DuckDB | 多表关联、聚合和较大 CSV/Parquet 查询 |
| PyArrow + Parquet | 统一的本地列式数据存储 |
| NumPy + SciPy | 描述统计、bootstrap、显著性检验和数值计算 |
| statsmodels | 效应量、统计模型和多重检验校正 |
| scikit-learn | 可选的离群点与异常模式检测 |
| PyYAML + openpyxl | YAML 配置和 Excel 文件解析 |
| LiteLLM | OpenAI、Azure、Anthropic、Ollama 等模型适配 |
| pytest | 后端单元、集成和统计回归测试 |

### 5.3 运行与交付

| 技术 | 用途 |
|---|---|
| uv | Python 依赖与虚拟环境管理 |
| Yarn | 前端依赖管理 |
| Docker / Docker Compose | 本地部署与代码执行隔离 |
| GitHub Actions | 测试、静态检查、构建和安全扫描 |
| Ruff | Python lint 与格式检查 |
| ESLint | TypeScript lint |

MVP 默认采用单机、本地优先部署。多用户服务化时再增加 PostgreSQL、对象存储、统一认证和任务队列，避免首版过度设计。

## 6. 核心领域模型

所有输入源必须转换为统一的数据模型，后续分析不直接依赖 CSV 列名或 MLflow 字段。

### 6.1 核心实体

| 实体 | 说明 |
|---|---|
| Project | 一项研究或一组相关实验的工作区 |
| DataSource | 上传文件或外部平台连接信息 |
| Experiment | 围绕同一目标组织的一组 runs |
| Run | 一次实际实验执行 |
| Param | run 的配置和超参数 |
| Metric | 单点指标或随 step/time 变化的指标序列 |
| Artifact | 日志、图像、模型、配置和其他输出文件 |
| BaselineDefinition | 用户指定的对照组及主指标方向 |
| Finding | 确定性分析产生的事实性发现 |
| EvidenceRef | 指向 run、指标、配置、文件或日志行的证据引用 |
| Hypothesis | Agent 基于 findings 提出的候选原因 |
| ExperimentProposal | 用于验证假设的下一轮最小实验方案 |

### 6.2 本地标准化存储

```text
workspace/<project_id>/
├── project.json
├── sources/
│   ├── original/                 # 用户原始文件，只读保留
│   └── manifests.jsonl           # 文件哈希、解析器和来源信息
├── normalized/
│   ├── runs.parquet
│   ├── params.parquet
│   ├── metrics.parquet
│   └── artifacts.jsonl
├── analysis/
│   ├── findings.jsonl
│   ├── hypotheses.jsonl
│   └── proposals.jsonl
├── reports/
└── scratch/                      # 沙箱临时文件
```

推荐的标准表：

```text
runs:
run_id, experiment_id, group, seed, status, start_time,
end_time, duration_seconds, source_type, source_run_id

params:
run_id, key, value, value_type

metrics:
run_id, key, value, step, timestamp, split
```

这种长表结构既适合 DuckDB 聚合，也可以直接映射 MLflow 的 Run、Param 和 Metric。

## 7. 核心模块设计

### 7.1 数据导入与结构识别

职责：

- 读取 CSV、TSV、Excel、JSON、YAML、TXT 和 JSONL。
- 计算文件哈希并保留原始文件。
- 推断 run ID、实验组、seed、参数、指标和状态字段。
- 从文件名、目录结构和公共字段关联结果、配置与日志。
- 生成字段映射建议，由用户确认后写入标准化表。
- 对格式错误、重复 run、单位不一致和缺失主键给出明确提示。

实现原则：

- 文件解析使用确定性 parser。
- LLM 只协助解释模糊列名和提出字段映射候选。
- 映射结果必须经过 schema 校验和用户确认。
- 原始数据不被覆盖，所有转换记录 lineage。

### 7.2 实验总览与 Baseline 分析

职责：

- 汇总成功、失败和未完成的 runs。
- 计算指标均值、中位数、标准差和置信区间。
- 比较实验组与 baseline 的绝对变化和相对变化。
- 分析不同 seed 的波动与稳定性。
- 计算效应量和适用的显著性检验。
- 展示性能、运行时间和资源消耗之间的权衡。

统计工具必须返回结构化结果，例如：

```json
{
  "analysis_type": "baseline_comparison",
  "metric": "accuracy",
  "baseline_group": "A",
  "candidate_group": "B",
  "mean_delta": 0.018,
  "confidence_interval": [0.004, 0.031],
  "effect_size": 0.42,
  "sample_size": {"A": 5, "B": 5},
  "warnings": ["sample_size_small"],
  "evidence_refs": ["run:A-1", "run:B-1"]
}
```

Agent 只能基于这些结构化结果生成自然语言解释。

### 7.3 异常检测

首版采用规则与统计方法组合：

- 缺失值、NaN、Inf 和非法指标。
- 重复 run、缺失 seed、配置字段不完整。
- 同组 runs 的离群点。
- seed 方差明显增大。
- loss 不下降、震荡、突然跳变或训练/验证曲线分离。
- 状态失败、OOM、超时和日志中的异常栈。
- 运行时间、显存和吞吐量异常。
- 数据集版本、代码版本或环境字段不一致。

每个 detector 输出统一的 `Finding`：

```text
id, type, severity, title, description,
evidence_refs, detector, detector_version, confidence
```

LLM 不负责决定基础异常是否存在，但可以对多个 findings 进行组合解释。

### 7.4 排错假设 Agent

沿用 Data Formulator 的 AnalystAgent 工具调用框架，新增实验领域 Skills：

| Skill | 作用 |
|---|---|
| `experiment-inspection` | 查询 runs、配置、指标和日志摘要 |
| `baseline-analysis` | 调用确定性 baseline 分析工具 |
| `anomaly-diagnosis` | 读取 findings 并形成候选原因 |
| `evidence-review` | 检查支持证据、反对证据和信息缺口 |
| `next-experiment` | 生成用于区分候选假设的最小实验 |
| `experiment-report` | 汇总分析过程并生成报告 |

每个 Hypothesis 必须包含：

```text
description
supporting_evidence[]
contradicting_evidence[]
uncertainties[]
confidence
verification_plan
```

如果没有足够证据，Agent 应输出“尚不能判断”以及缺少的数据，而不是补全一个确定性解释。

### 7.5 下一轮实验建议

本模块借鉴 autoresearch 的约束思路，但保持 human-in-the-loop：

- 一次 proposal 尽量只改变一个主要变量。
- 明确固定条件、主指标和判断标准。
- 指定建议 seed 数量和停止条件。
- 估计实验成本与信息增益。
- 说明不同可能结果分别支持或反对哪个假设。
- 生成 proposal，但不自动执行。

建议状态沿用简化的实验账本语义：

```text
proposed → accepted/rejected → completed → supported/refuted/inconclusive
```

当用户导入下一批实验时，可将新 runs 关联到 proposal，形成可追溯的研究决策链。

### 7.6 对话与报告

对话层保留当前项目、baseline、筛选条件、findings 和 hypotheses 上下文。用户追问时，Agent 通过查询工具读取数据，而不是把全部原始表格塞入 prompt。

报告包含：

- 实验目标和数据来源。
- 字段映射和 baseline 定义。
- 结果总览与关键图表。
- 统计比较和限制条件。
- 异常 findings。
- 排错 hypotheses 及证据。
- 下一轮 experiment proposals。
- 数据文件、run ID、分析器版本和生成时间。

## 8. Microsoft Data Formulator 的具体复用方案

### 8.1 复用方式

建议 Fork 一个经过验证的 Data Formulator tag 或 commit，保留 `upstream` remote，并在 ExperimentLens 仓库中直接演进。由于产品领域会明显分叉，不把它当作普通依赖包使用；安全修复和重要更新通过人工审查后选择性同步。

MIT 许可证允许复制、修改和商业使用，但必须保留原始版权和许可证声明，同时避免使用 Microsoft 商标造成官方背书的误解。

### 8.2 可直接复用的模块

| Data Formulator 能力 | ExperimentLens 用途 |
|---|---|
| React/TypeScript 应用外壳 | 项目工作区和主要页面框架 |
| 上传与数据源 UI | 上传结果表、配置和日志 |
| CSV/TSV/XLSX 解析 | 实验结果表导入 |
| Workspace / Datalake | 项目隔离、文件持久化和 Parquet 管理 |
| AnalystAgent | 实验分析 Agent 的主循环 |
| Skill Registry | 按需加载实验分析、排错和报告能力 |
| Python Sandbox | 执行受控分析工具和生成图表 |
| NDJSON 流式协议 | 返回 Agent 进度、工具事件和报告内容 |
| Data Thread | 保存分析路径和对话上下文 |
| 图表引擎 | 指标曲线、分布、baseline 对比和资源图表 |
| TipTap Report Editor | 编辑、保存和导出实验报告 |
| 模型适配层 | 切换云端或本地 LLM |
| 知识与推理日志 | 记录研究规则、排错经验和 Agent 运行轨迹 |

### 8.3 需要领域化改造的部分

- 将“任意数据表”升级为 Project、Experiment、Run 等实验实体。
- 将通用字段推荐改为实验字段映射确认。
- 在 Data Thread 中增加 run、finding、hypothesis 和 proposal 引用。
- 将通用 chart recommendation 替换为实验分析图表模板。
- 增加 JSON/YAML 配置和 TXT/JSONL 日志解析。
- 将报告模板替换为实验诊断报告。
- 限制 Agent 自由执行任意分析代码，优先暴露经过测试的领域工具。
- 将 Data Formulator 名称、Logo 和介绍替换为 ExperimentLens，同时保留许可证文件。

### 8.4 不建议直接复用的方式

- 不建议只复制若干 React 组件，容易丢失工作区、流式协议和 Agent 状态之间的配合。
- 不建议直接依赖 PyPI 包并在外部覆盖 UI，因为需要修改的产品流程过多。
- 不建议长期追随 `main` 自动合并，应固定基线并选择性吸收上游修复。

## 9. karpathy/autoresearch 的辅助设计复用

autoresearch 的关键价值不是代码量，而是清晰的实验契约。ExperimentLens 借鉴以下设计：

| autoresearch 设计 | ExperimentLens 中的转化 |
|---|---|
| 固定评估指标 | 用户确认 primary metric 及方向 |
| 固定时间/资源预算 | proposal 中记录预算、seed 数和停止条件 |
| `results.tsv` 实验账本 | 标准化 Run、Finding 和 Proposal 历史 |
| `keep/discard/crash` | `supported/refuted/inconclusive/failed` 结论状态 |
| 每轮只修改有限范围 | 推荐最小验证实验，减少混杂变量 |
| 根据历史实验决定下一步 | Agent 查询已尝试方案，避免重复建议 |
| 保留成功、回退失败 | 不修改代码，只说明是否支持假设以及下一步决策 |

ExperimentLens 不复用它的训练脚本或自主执行流程，因为这与 MVP 的安全边界冲突。真正可复用的是“受约束、可记录、可比较”的实验决策范式。

## 10. MLflow 的未来接入方案

### 10.1 接入原则

领域层定义统一 `ExperimentSource` 接口，文件上传和 MLflow 都只是适配器：

```python
class ExperimentSource:
    def list_experiments(self): ...
    def list_runs(self, experiment_id, filters=None): ...
    def get_run(self, run_id): ...
    def get_metric_history(self, run_id, metric_key): ...
    def list_artifacts(self, run_id): ...
    def download_artifact(self, run_id, path): ...
```

MVP 实现 `FileExperimentSource`。后续实现 `MLflowExperimentSource`，而分析层始终只读取统一领域模型。

### 10.2 MLflow 字段映射

| MLflow | ExperimentLens |
|---|---|
| Experiment | Experiment |
| Run | Run |
| Param | Param |
| Metric / Metric History | Metric |
| Tag | Run 元数据、group、seed 或版本信息 |
| Artifact | Artifact |
| Run status / timestamps | Run 状态和耗时 |

接入步骤：

1. 用户配置 Tracking URI 和认证信息。
2. 获取 experiments，用户选择需要分析的实验。
3. 分页读取 runs、params、metrics 和 tags。
4. 按需读取 metric history，避免一次下载全部曲线。
5. 只在分析需要时下载日志、配置或图像 artifacts。
6. 转换为本地标准化表，并记录 `source_type=mlflow` 和原始 run ID。
7. 保存同步游标，后续执行增量刷新。

首版 MLflow 连接器只读，避免误修改用户的 Tracking Server。

## 11. 建议的代码结构

项目初期保留 Data Formulator 的单仓库结构，并逐步形成清晰领域边界：

```text
ExperimentLens/
├── src/                                # React/TypeScript 前端
│   ├── features/projects/
│   ├── features/import/
│   ├── features/overview/
│   ├── features/runs/
│   ├── features/findings/
│   ├── features/hypotheses/
│   ├── features/proposals/
│   └── features/reports/
├── py-src/experimentlens/
│   ├── app.py
│   ├── routes/
│   ├── domain/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── repositories.py
│   ├── ingestion/
│   │   ├── parsers/
│   │   ├── mapping.py
│   │   └── normalization.py
│   ├── analysis/
│   │   ├── summary.py
│   │   ├── baseline.py
│   │   ├── stability.py
│   │   ├── significance.py
│   │   └── anomalies/
│   ├── agent/
│   │   ├── analyst.py
│   │   ├── tools/
│   │   └── skills/
│   ├── evidence/
│   ├── proposals/
│   ├── reports/
│   ├── connectors/
│   │   ├── base.py
│   │   ├── files.py
│   │   └── mlflow.py                 # 后续阶段
│   ├── workspace/
│   └── sandbox/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── e2e/
├── docs/
├── pyproject.toml
├── package.json
└── docker-compose.yml
```

Fork 初期可以保留原有包名和目录，先添加领域模块；当核心流程跑通后再完成包名迁移，避免“一开始只做重命名却没有产品功能”。

## 12. 主要 API 设计

MVP 可以围绕以下资源设计接口：

```text
POST /api/projects
GET  /api/projects/:id

POST /api/projects/:id/sources/upload
POST /api/projects/:id/schema/infer
POST /api/projects/:id/schema/confirm

POST /api/projects/:id/analysis/run
GET  /api/projects/:id/analysis/summary
GET  /api/projects/:id/findings

POST /api/projects/:id/chat/stream
GET  /api/projects/:id/hypotheses
POST /api/projects/:id/proposals

POST /api/projects/:id/reports/generate
GET  /api/projects/:id/reports/:report_id

# 后续
POST /api/projects/:id/connectors/mlflow
POST /api/projects/:id/connectors/mlflow/sync
```

耗时分析和 Agent 对话沿用 Data Formulator 的流式事件协议，普通查询使用 JSON API。

## 13. 项目搭建顺序

### 阶段 0：建立复用基线

- Fork 并固定 Data Formulator 的稳定 tag 或审核后的 commit。
- 保留 MIT 许可证和上游来源说明。
- 配置 `upstream` remote，但禁止自动合并。
- 跑通原项目的 Python、前端和端到端测试。
- 完成 ExperimentLens 品牌和最小导航调整。

完成标准：原有上传、对话、图表和报告链路可运行，测试保持通过。

### 阶段 1：实验数据模型与文件导入

- 建立 Project、Experiment、Run、Param、Metric 和 Artifact 模型。
- 增加 JSON、YAML、TXT 和 JSONL parser。
- 实现字段推断、用户确认和标准化存储。
- 准备多配置、多 seed、含失败日志的固定测试数据集。

完成标准：用户可以上传一批混合文件并得到正确的标准化 runs。

### 阶段 2：确定性分析引擎

- 实现实验总览和 baseline 对比。
- 实现 seed 稳定性、置信区间和效应量。
- 实现首批规则型异常 detector。
- 为统计边界条件编写回归测试。

完成标准：无需调用 LLM 也能生成完整的结构化 findings。

### 阶段 3：排错 Agent

- 基于 AnalystAgent 增加实验领域 Skills 和工具。
- 强制 Hypothesis 引用 Finding 和 EvidenceRef。
- 增加反对证据、不确定性和缺失数据检查。
- 实现对话追问和分析状态恢复。

完成标准：Agent 能针对已知故障样例提出可解释、可验证的候选原因。

### 阶段 4：下一轮实验与报告

- 引入 autoresearch 风格的受约束 proposal 模型。
- 实现 proposal 状态和新 runs 关联。
- 完成实验诊断报告模板和导出。

完成标准：用户可以从异常进入假设，再生成并保存下一轮实验方案。

### 阶段 5：MLflow 只读连接器

- 实现 Tracking Server 配置和连通性测试。
- 分页同步 experiments 和 runs。
- 按需同步 metric history 和 artifacts。
- 增加增量同步、错误恢复和权限测试。

完成标准：同一分析流程可以无差别分析上传文件或 MLflow runs。

## 14. 测试策略

### 14.1 单元测试

- 每种文件 parser 的正常、缺失和错误输入。
- 字段映射和标准化规则。
- 每个统计方法的已知结果和边界条件。
- 每个异常 detector 的阳性与阴性样例。
- EvidenceRef 不允许引用不存在的 run 或日志行。
- Hypothesis 和 Proposal 的 schema 校验。

### 14.2 集成测试

- 混合文件上传到标准化数据的完整链路。
- 标准化数据到 findings 的完整链路。
- Agent 工具只能读取授权项目的数据。
- Agent 输出必须引用有效 evidence。
- 报告可以从保存的分析结果重新生成。
- MLflow 连接器使用 mock server 验证分页和失败恢复。

### 14.3 端到端测试

固定三组代表性场景：

1. 候选配置真实优于 baseline，多个 seed 表现稳定。
2. 平均值提升来自单个离群 seed，不应得出稳定提升结论。
3. loss 震荡且日志包含 OOM/数值异常，Agent 应提出对应验证方案。

端到端测试验证上传、字段确认、异常展示、对话、proposal 和报告流程。

### 14.4 Agent 评测

建立一组带标准答案的诊断案例，评估：

- 异常召回率和误报率。
- 假设是否得到证据支持。
- 是否明确表达不确定性。
- 是否建议了能区分候选原因的实验。
- 是否产生不存在的 run、指标或日志引用。

## 15. 安全与隐私

- 原始实验数据默认保存在本地 workspace。
- 上传文件执行类型、大小、扩展名和内容校验。
- 日志显示前脱敏 token、密码、连接串和个人信息。
- LLM 默认只接收 schema、聚合结果和必要证据，不上传整份原始数据。
- 所有 Python 执行设置超时、内存限制、路径限制和网络限制。
- 本地开发可使用进程隔离，面向外部用户时必须使用 Docker 或更强沙箱。
- MLflow 凭证存储在凭证保险库中，不写入项目文件或 Agent prompt。
- MLflow 连接器首版严格只读。

## 16. 关键技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 应用基座 | Fork Data Formulator | 产品能力重合度高，能明显减少 UI、Agent 和数据基础设施工作 |
| 后端框架 | MVP 继续 Flask | 避免为了框架迁移延迟核心价值验证 |
| 数据格式 | Parquet + JSON/JSONL | 适合本地分析、可追溯且容易与 DuckDB 配合 |
| 分析方式 | 确定性工具优先 | 提高统计正确性、可测试性和结果可解释性 |
| Agent 模式 | 单 AnalystAgent + Skills | 比多 Agent 更简单，符合 MVP，并能按需扩展能力 |
| 实验建议 | 人工确认，不自动执行 | 与 MVP 安全边界一致 |
| MLflow 接入 | 领域接口 + 只读适配器 | 避免分析逻辑依赖具体实验平台 |
| 部署方式 | 本地优先 | 研究数据敏感，且最适合早期用户验证 |

## 17. MVP 完成定义

首版达到以下条件即可进入真实用户试用：

- 能导入结果表、配置和日志，并正确形成 runs。
- 用户可以确认字段和 baseline。
- 能生成统计总览、稳定性分析和异常 findings。
- 每个重要结论都能定位到具体证据。
- Agent 能提出包含支持证据、反对证据和置信度的假设。
- Agent 能生成不自动执行的下一轮最小实验方案。
- 能生成并保存一份完整分析报告。
- 固定测试数据上的统计、异常检测和端到端测试全部通过。

## 18. 参考资料

- [ExperimentLens MVP 产品设计](./mvp-product-design.md)
- [Microsoft Data Formulator](https://github.com/microsoft/data-formulator)
- [Data Formulator Development Guide](https://github.com/microsoft/data-formulator/blob/main/DEVELOPMENT.md)
- [Data Formulator Python Dependencies](https://github.com/microsoft/data-formulator/blob/main/pyproject.toml)
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- [autoresearch Experiment Program](https://github.com/karpathy/autoresearch/blob/master/program.md)
- [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking)
- [MLflow REST API](https://mlflow.org/docs/latest/api_reference/rest-api.html)
- [MLflow Artifact Store Architecture](https://github.com/mlflow/mlflow/blob/master/docs/docs/self-hosting/architecture/artifact-store.mdx)
