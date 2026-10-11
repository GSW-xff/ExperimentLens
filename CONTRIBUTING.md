# Contributing to ExperimentLens

[English](#english) | [简体中文](#简体中文)

## English

Thank you for improving ExperimentLens. Please keep changes focused, evidence-backed, and easy to review.

### Development setup

Requirements: Python 3.11+, Node.js 20.19+, and pnpm 11. The repository pins the CI versions in `.python-version`, `.nvmrc`, and `package.json`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pnpm install --frozen-lockfile
```

Copy `.env.example` to `.env` only when you need custom local settings. Never commit API keys, experiment data, generated workspaces, or local databases.

### Change workflow

1. Create a short-lived branch from `main`.
2. Add or update tests with every behavior or documentation change.
3. Run `make verify` from the activated virtual environment.
4. Use a descriptive commit message, preferably following Conventional Commits.
5. Open a pull request that explains the motivation, behavior change, verification, and any security or migration impact.

The full verification gate includes backend coverage, Ruff, frontend tests, TypeScript compilation, a production build, and an Alembic round trip.

## 简体中文

感谢你参与改进 ExperimentLens。请让每次变更保持聚焦、可验证且易于审阅。

### 开发环境

需要 Python 3.11+、Node.js 20.19+ 和 pnpm 11。CI 使用的版本已写入 `.python-version`、`.nvmrc` 和 `package.json`。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pnpm install --frozen-lockfile
```

只在需要自定义本地配置时复制 `.env.example` 为 `.env`。请勿提交 API Key、实验数据、生成的 workspace 或本地数据库。

### 变更流程

1. 从 `main` 创建短期分支。
2. 每次行为或文档变更都必须新增或更新测试。
3. 在已激活的虚拟环境中运行 `make verify`。
4. 使用清晰的提交信息，建议遵循 Conventional Commits。
5. 提交 Pull Request，说明动机、行为变化、验证方式，以及安全或迁移影响。

完整验证包括后端覆盖率、Ruff、前端测试、TypeScript 编译、生产构建和 Alembic 前滚/回滚/再前滚。
