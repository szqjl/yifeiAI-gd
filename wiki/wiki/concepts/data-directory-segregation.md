---
type: concept
title: "数据目录分离（game_records vs game_records_v7）"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
tags:
  - data-segregation
  - bc-training
  - v7
  - m3
status: current
related_gua: []
date: 2026-06-17
---

# 数据目录分离

> M3 与 V7 的训练/评测数据**物理隔离**，避免 BC（行为克隆）训练污染。

## 1. 目录对照

| 引擎 | 评测输出 | 训练输入 |
|---|---|---|
| M3 | `game_records/` | — |
| V7 | `game_records_v7/` | ✅ BC 训练只读此目录 |

## 2. 隔离目的

- V7 训练数据应**纯净**来自 V7 引擎的对局
- M3 旧数据混入会导致 BC 模型学习到错误策略
- 副级等级分析（`analyze_v7_round_levels.py`）只处理 V7 目录

## 3. 配套脚本

- `scripts/tools/yf_replay.py` — 回放工具
- `scripts/tools/analyze_v7_round_levels.py` — 副级分析
- `train_bc_v7.py` — BC 训练入口（**只读 `game_records_v7/`**）

## 4. 与 Layer 2 禁入 Git 的关系

两个目录均属 Layer 2，详见 [[agent-protocol]] §4。

## 关联页面

- [[agent-protocol]]
- [[victorynum-data-recovery]]
- wiki/entities/engine-v7.md
- [[module-v7-engine]]
```

---
