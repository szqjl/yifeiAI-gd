# Git 设置指南（已过时）

> **分支与远程策略请以以下文档为准**（2026-05-29 起生效）：
>
> - [main-branch-policy.md](./main-branch-policy.md) — `m-dev` 主开发线、`main` 冻结
> - [M-V-Series-治理方案.md](./M-V-Series-治理方案.md) §4 — 远程与分支对照
>
> ## 已废弃
>
> | 旧约定 | 现行 |
> |--------|------|
> | `develop` 日常开发 | **`m-dev`**（Gitee `origin` 默认分支） |
> | `git push origin develop` | `git push origin m-dev` |
> | GitHub 与 Gitee 双写 | **Gitee 为唯一真相源**；GitHub 仅按需镜像 |
>
> ## GitHub 镜像同步（可选）
>
> 本机网络可达 GitHub 时：
>
> ```powershell
> powershell -ExecutionPolicy Bypass -File scripts/tools/sync_github_mirror.ps1
> ```
>
> 脚本会：`fetch --prune`、删除远程 `develop`（若存在）、推送 `m-dev`。
>
> ---
>
> 下文为历史正文（编码损坏 + 策略过时），**勿再按此操作**。完整历史见 Git 旧版本 `docs/governance/git-setup-guide.md`。
