---
name: guandan-batch-eval
description: >-
  掼蛋 V7/M3 批跑与胜率解读：run_v7_vs_lalala 或 M3 批跑、victoryNum 对账、局/副口径、
  analyze_v7_rounds、更新 v7-win-rate-history 与 ITERATIONS。Use when 批跑, 胜率,
  victoryNum, 局胜, 副胜, game_records, WF-04, or 解读批跑结果.
---

# 批跑与数据分析（WF-04）

## 动手前

读 [`docs/knowledge/platform-data-interpretation.md`](../../docs/knowledge/platform-data-interpretation.md) 与 [`docs/guandan-brain/工作流.md`](../../docs/guandan-brain/工作流.md) §2.3。

## 口径定音

| 指标 | 来源 | 禁止 |
|------|------|------|
| **局胜** | 批末 `victoryNum[0]` vs `[1]`（[0]=[2]、[1]=[3]） | 四席相加 |
| **副数** | `game_records` 文件数 / `total_rounds` | 当局数 |
| **批跑 N 局** | `--target-games` 为 **3 的倍数** | 用 10 |
| 对账 | `batch_executor/latest_victory_num.json` | 裸信异常 vn |

## 命令

```bash
# V7（v7-dev）
python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3

# 分析
python scripts/analysis/analyze_v7_rounds.py

# M3 队 KPI
python scripts/launchers/m/run_m3_vs_lalala_games.py --games 12
```

## 产出

- 汇报含：局胜、副胜/副数、口径声明、`vn_source`。
- 结论写入 `docs/guandan-brain/v7-win-rate-history.md` 与 `ITERATIONS.md`（若本轮迭代相关）。

## 脚本索引

[`docs/guandan-brain/SCRIPT_INDEX.md`](../../docs/guandan-brain/SCRIPT_INDEX.md)
