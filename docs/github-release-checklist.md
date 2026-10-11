# GitHub 发布清单

本仓库已包含双语 README、开源许可证、贡献与安全说明、Issue/PR 模板、Dependabot、CI、Docker 部署和环境变量示例。首次发布时按以下顺序检查。

## 上传前

1. 在已激活的 `.venv` 中运行 `make verify`。
2. 运行 `git status --short` 并确认没有 `.env`、API Key、本地数据库、生成的 workspace 或私有实验数据。
3. 核对 `LICENSE` 是否符合你期望的开源方式。当前为 MIT License。

## 首次上传

在 GitHub 创建一个空仓库，不要勾选生成 README、`.gitignore` 或 License，然后在本地执行：

```bash
git remote add origin git@github.com:OWNER/REPOSITORY.git
git push -u origin main
```

如果使用 HTTPS，把远端地址替换为 `https://github.com/OWNER/REPOSITORY.git`。

## GitHub 仓库设置

- 添加简短描述与 Topics，建议包含 `ai-agent`、`experiment-tracking`、`fastapi`、`react`。
- 开启 Private vulnerability reporting、Dependabot alerts 和 Secret scanning（平台与仓库类型支持时）。
- 为 `main` 配置 branch protection/ruleset，要求 Pull Request 和 CI 的 `python`、`web`、`container`、`security` 检查通过。
- 确认 Actions 首次运行全部通过后再对外分享仓库。
- 如果部署公网服务，替换 `compose.yaml` 中的本地凭据，使用 Secret Manager，并在受信任代理层终止 TLS。
