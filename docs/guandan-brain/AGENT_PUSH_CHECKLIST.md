# Agent 提交 / 推送 · 检查清单（复制即用）

> **人类派「提交推送」任务时**，把下面 **默认第一句** 粘贴给 Agent；Agent 须逐项勾选后再动 `git`。

---

## 默认第一句（推送任务）

```text
提交推送前先完成 docs/guandan-brain/AGENT_PUSH_CHECKLIST.md 全部勾选：必读 docs/governance/M-V-Series-治理方案.md §4/§6/§8 与 main-branch-policy.md，跑 pre_push_check.bat，按 §8.1 前缀 commit，最后 git push origin m-dev。
```

---

## Agent 勾选表（完成后再 commit/push）

### A. 必读文档

- [ ] `docs/governance/M-V-Series-治理方案.md` — §4 远程/分支、§6 产物、§8 Commit、§7 门禁
- [ ] `docs/governance/main-branch-policy.md` — **只推 m-dev，禁止推 main**

### B. 环境与范围

- [ ] 当前分支：`git branch -vv` → **`m-dev`**（非 main）
- [ ] 已 `git status` / `git diff --stat`，**未** `git add .` 盲加
- [ ] 未纳入 Layer 2：`game_scores_m2.json`、`game_records/`、`models/*.pth`、`logs/`、大 replay

### C. 推送前脚本

- [ ] 已运行 **`pre_push_check.bat`** 或 `python scripts/hooks/pre_push_validate.py`（无 >1MB 进暂存区）

### D. 测试（按改动类型）

- [ ] 文档 only：相关 pytest 通过（若有）
- [ ] 改 M 行为：治理 §7.3 M 冒烟；行为变更 §7.1 30 局 regression（或说明本机未跑原因）

### E. Commit 与推送

- [ ] Commit 标题含治理 §8.1 前缀：`[docs]` / `[M-m2]` / `[M-m3]` …
- [ ] `git push origin m-dev`（**非** `origin main`）
- [ ] GitHub 镜像（可选）：`scripts/tools/sync_github_mirror.ps1`，失败只报告、不 force

### F. 向人类回报

- [ ] 每个 commit：`hash` + 标题
- [ ] `pre_push` / pytest 结果
- [ ] 未提交文件及理由
- [ ] 确认：**未推 main**

---

## 与「新开 Agent 第一句」的分工

| 场景 | 用哪个文件 |
|------|------------|
| 新开会话、接开发/分析任务 | [`AGENT_FIRST_MESSAGE.md`](./AGENT_FIRST_MESSAGE.md) |
| **提交、推送、开 PR** | **本文件** |

---

## 延伸阅读

- [M-V-Series-治理方案.md](../governance/M-V-Series-治理方案.md)
- [推送前检查指南.md](../development/推送前检查指南.md)
- 安装 Git 钩子：`scripts/hooks/install-hooks.bat`（阻止推 main、Layer 2 大文件）
