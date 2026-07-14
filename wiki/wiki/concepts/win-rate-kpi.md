---
type: concept
title: "V7 队胜率 KPI"
sources:
  - docs/guandan-brain/v7-win-rate-history.md
  - docs/governance/M-V-Series-治理方案.md
tags:
  - kpi
  - win-rate
  - evaluation
  - v7
status: current
related_gua:
  - GUA-037a
  - GUA-037b
  - GUA-038
  - GUA-039b
date: 2026-07-03
---

# V7 队胜率 KPI

## 定义

**V7 队胜率** = `[0] + [1]` 出现次数 / 总局数

其中：
- `[0]` = V7 队内头游玩家所在位次出现次数
- `[1]` = V7 队内次游玩家所在位次出现次数

> ⚠️ **不是** "V7 玩家名出现次数"，是**位次**统计

## 副数计算

- 副数 = mtime 窗内 `game_records/*.json` 文件数 / 2
- 每条 JSON 包含 yf1 + yf2 两个人的记录
- 副 ≠ 局：1 局 = 2 副（详见 [[recursion-game-round]]）

## 阈值

| 阈值 | 含义 | 来源 |
|------|------|------|
| ≥ 30% | V7 批跑通过的最低标准 | GUA-039b（30 局 vs lalala）|
| ≥ 40% | V 冒烟 ON 模式（50 局）| `v7-win-rate-history.md` |
| > 0% | GUA-038（哪怕只赢 1 局）| GUA-038 |
| 不退化 | GUA-037b | GUA-037b |

## 必跑下限

任何策略变更（GUA / Guard / 启发式 / BC 模型）必须跑 ≥ 3 局（GUA-037a/b, GUA-038）。

## 易错点

1. **局 ≠ 副**：队胜率分母是"局"，副胜率分母是"副"
2. **位次 ≠ 玩家名**：`[0]+[1]` 是位次数组，不是姓名
3. **训练指标 ≠ 实战 KPI**：BC v3 val_acc=80.88% 不能用来辩解 0/12 队胜

## 关联

- [[recursion-game-round]] — 局 ⊃ 副 定音
- [[v7-win-rate-history-summary]] — 战 KPI 真源
- [[batch-evaluation]] — 批跑评测体系
