---
name: guandan-git-push
description: >-
  掼蛋仓库 git commit 与 push：AGENT_PUSH_CHECKLIST、M-V-Series 治理 §4/§6/§8、
  pre_push_validate、v7-dev 或 m-dev 禁止 push main。Use when commit, push,
  提交, 推送, 开 PR, WF-08.
---

# Git 提交与推送（WF-08）

## 动手前（不可跳过）

1. [`docs/guandan-brain/AGENT_PUSH_CHECKLIST.md`](../../docs/guandan-brain/AGENT_PUSH_CHECKLIST.md) 逐项勾选
2. [`docs/governance/M-V-Series-治理方案.md`](../../docs/governance/M-V-Series-治理方案.md) §4/§6/§8
3. [`docs/governance/main-branch-policy.md`](../../docs/governance/main-branch-policy.md) — **禁止 push main**

## 分支

| 线 | 推送 |
|----|------|
| V7 | `git push origin v7-dev` |
| M3 日常 | `git push origin m-dev` |

## 推送前

```bash
python scripts/hooks/pre_push_validate.py
# 或 pre_push_check.bat
```

## Layer 2 禁止提交

`game_records/`、`models/*.pth`、`logs/`、大 replay、`game_scores_m2.json`

## Commit 前缀（治理 §8.1）

`[V-nn-v7]`、`[M-m3]`、`[docs]` 等

## 向用户确认

推送前一句话：已读治理、pre_push 通过、目标分支 `origin/v7-dev` 或 `origin/m-dev`。
