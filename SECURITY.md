# Security Policy

## Supported version

Security fixes are applied to the latest commit on `main`. This project is currently pre-1.0 and does not maintain security patches for older snapshots.

## Reporting a vulnerability

Please do not disclose a suspected vulnerability in a public issue. Use GitHub's **Security > Report a vulnerability** private reporting flow after the repository is published. If private vulnerability reporting is unavailable, contact the repository owner privately and include:

- affected version or commit;
- reproduction steps or a minimal proof of concept;
- expected impact and required preconditions;
- any suggested mitigation.

Do not include real API keys, personal data, or proprietary experiment data in a report. Maintainers should acknowledge a report within seven days and coordinate disclosure after a fix is available.

## Deployment note

Credentials in `compose.yaml` are local-development defaults only. Public or shared deployments must replace them with secret-managed values, terminate TLS at a trusted proxy, restrict network access, and review uploaded experiment data before enabling external model providers.

---

## 中文说明

安全修复仅针对 `main` 分支最新版本。请不要在公开 Issue 中披露疑似漏洞；仓库发布后应使用 GitHub **Security > Report a vulnerability** 的私密报告流程。报告中不得包含真实 API Key、个人数据或专有实验数据。`compose.yaml` 中的凭据仅供本地开发，公开部署前必须替换。
