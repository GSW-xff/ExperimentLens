# ExperimentLens

ExperimentLens 是面向机器学习与数据科学实验的本地优先分析工作台。它把结果表、配置和日志统一为 runs，使用确定性统计生成 baseline 对比和异常 findings，再据此形成带证据的排错假设、下一轮最小实验方案与可分享报告。

面向最终用户的文件准备、操作流程和结果解读说明，参见 [ExperimentLens 使用说明书](docs/user-guide.md)。

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

原始文件保存在 `.experimentlens/workspace/<project_id>/sources/original`，标准化表保存为 Parquet，分析结果和报告保存为结构化 JSON/Markdown。默认不上传外部服务，也不会修改或启动用户实验。

## 验证

```bash
pytest
pnpm test
pnpm build
ruff check .
```
