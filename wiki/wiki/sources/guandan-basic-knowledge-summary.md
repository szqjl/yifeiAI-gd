---
type: source-summary
title: "M2 知识库对话分析摘要"
sources:
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
tags:
  - M2
  - 知识库
  - 规则引擎
  - source-summary
status: current
related_gua: []
date: 2026-06-21
---

# M2 知识库对话分析摘要

## 来源
`docs/analysis/agent-sessions/guandan-basic-knowledge.md`（4093 字符）—— Agent 会话中对掼蛋基本规则、M2 引擎架构、v1006 平台协议的提问与梳理。

## 核心要点

### 1. 掼蛋基本规则
- **队际对战**：4 人两队，0+2 vs 1+3（按连接顺序决定座位号）
- **一副**：108 张发完到四人完牌，order 确定 → 升级 + 决定下副进贡关系
- **一局**：从 2 打到 A 并在 A 级双上过关（A↔2 循环 50 次 → 平局）
- **升级规则表**：双上 +3 / 头游+三游 +2 / 头游+末游 +1 / 无头游 +0

### 2. A 级特殊规则
- A 级必须双上才算赢局
- 连续 2 副未胜降回 2
- A↔2 循环满 50 次 → 平局

### 3. v1006 平台协议
- `N` 参数 = **局数**（不是副数），实测 N=1 对应 59 副
- 关键字段：`order`、`curRank`、`selfRank`、`oppoRank`
- 与 [[platform-data-interpretation]] 中的实测结论一致

### 4. M2 胜负追踪架构
- `yf1_m2.py` 写 JSON（持久化）
- `yf2_m2.py` 仅打日志（**避免 race condition**）
- 副结果判定：`order` 索引和 ≤2 → win；对方占前两名 → loss；其他 → draw
- 局检测：curRank==A 且本队双上 → 赢局；curRank==A 且对方双上 → 输局；curRank==2 且上副为 A → 输局
- 客户端需**跨副跟踪** curRank 变化判定局结束（单副消息无法判定）

## 涉及实体
- 引擎：[[engine-m2]]
- 模块：`yf1_m2.py`、`yf2_m2.py`、`game_scores_m2.json`、`batch_executor/executor.py`
- 平台：`offline_platform/guandan_offline_v1006.exe`、`掼蛋平台使用说明书v1006.pdf`
- 知识文档：`docs/guandan-basic-knowledge.md`、`docs/analysis/platform-data-interpretation.md`、`docs/guandan-brain/M2_OPTIMIZATION.md`

## 关键脚本函数
- `_update_level_info()`、`_determine_round_result()`、`_save_round_result()`
- `_detect_game_end()`、`_save_game_end()`
- `_load_scores()`、`_save_scores()`
- `_count_new_paired_games()`

## 关键张力（待 Wiki 化解决）
1. yf1_m2 / yf2_m2 在 V7 时代是否仍存在？（历史资产 vs 持续维护）
2. 是否需要将 `docs/archive/skill/出炸弹要领.txt`（76 条炸弹规则）纳入 Wiki？
3. M2 与 M3/V7 的胜负追踪架构是同源演化还是各自独立？

## 关联页面
- [[guandan-basic-rules]]（将创建）
- [[offline-platform-v1006]]（将创建）
- [[game-scoring-tracking]]（将创建）
- [[engine-m2]]（将创建）
- [[局不等于副]]（需更新）
- [[batch-evaluation]]（需更新）
