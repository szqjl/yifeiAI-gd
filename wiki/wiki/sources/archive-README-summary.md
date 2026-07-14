---
type: source-summary
title: "analysis/archive 归档说明"
sources:
  - docs/analysis/archive/README.md
tags:
  - archive
  - meta
status: current
date: 2026-06-28
---

# analysis/archive 归档说明

## 来源

- `docs/analysis/archive/README.md` (915 chars)

## 用途

`docs/analysis/archive/` 存放**已结案或已勘误**的分析报告，包括：
- 已 closed 的 GUA 批跑报告
- 已自标 ⚠️ 已勘误的观测报告
- 历史 handoff 文档

## 重要归档项

| 文件 | 状态 | 说明 |
|------|------|------|
| `2026-06-18-gua062-batch-eval.md` | closed | GUA-062 批跑 0/9 局胜 |
| `level2-root-cause.md` | closed | 卡2级 80.5% Single 决策根因 |
| `2026-06-21-cardmask-dict-collision.md` | in-progress | card_mask multiset 修复 |
| `南邮离线平台-actionList候选缺失观测报告.md` | ⚠️ 已勘误 | 平台 bug 主张未复现 |

## ⚠️ 勘误警示

**南邮离线平台 actionList 候选缺失观测报告** 已自标 ⚠️：
- 初稿主张平台漏算合法候选（44 例）
- 2026-06-28 独立复现（`verify_actionlist_pass_only.py`）0 例站住
- 案例 1 实为 curRank=J 而 J 为级牌 > A
- 案例 5 误以为四炸压 SF

**结论**：
- ~26% PASS-only 比例为**描述性统计**，非 platform bug
- 复盘 PASS 必须按该步 curRank 比较牌力
- 区分 PASS-only 与漏候选

## 关联页面

- [[offline-platform-v1006]] — 平台协议（需引用此勘误）
- [[gua062-batch-eval-summary]] — GUA-062 归档
- [[cardmask-multiset-fix]] — cardmask 归档
```

下面更新现有页面。
