---
type: entity-module
title: "M2 双客户端胜负追踪模块"
sources:
  - docs/knowledge/platform-data-interpretation.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - m2
  - client-tracking
  - yf1
  - yf2
status: current
related_gua: []
date: 2026-06-18
---

# M2 双客户端胜负追踪模块

## 文件位置

- `yf1_m2.py` — 玩家 1 视角
- `yf2_m2.py` — 玩家 2 视角
- 关联数据：`game_scores_m2.json`

## 8 个关键方法

| 方法 | 职责 |
|------|------|
| `_update_level_info` | 更新等级/进贡信息 |
| `_determine_round_result` | 判定本副结果 |
| `_save_round_result` | 持久化副结果 |
| `_detect_game_end` | 检测局结束（A 级双上） |
| `_save_game_end` | 持久化局结果 |

（5 个核心方法，2 个客户端合计 10 个调用点；另有 3 个辅助方法）

## 局检测算法

### 赢局条件
```
curRank == A AND 本队双上
```

### 输局条件
```
curRank == 2 AND 上一副为 A
```

详见 concept-m2-game-detection

## 副结果判定

- 本队两人在 `order`（出牌顺序）中索引之和 **≤ 2** → **win**
- 索引之和 > 2 → **draw/loss**

## 历史地位

M2 引擎已实现，**Wiki 此前未显式收录**。本次补录以补齐 M2 → M3 演进链。

## 关联

- [[engine-m1]] — M2 演进链上游
- wiki-minimax/entities/engine-m3.md — M2 升级版
- concept-m2-game-detection — 局检测算法
- concept-round-vs-game-multi-level — 局/副口径
