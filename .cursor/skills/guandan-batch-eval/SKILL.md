---
name: guandan-batch-eval
description: >-
  掼蛋 V7/M3 批跑与胜率解读：run_v7_vs_lalala 或 M3 批跑、victoryNum 对账、局/副口径、
  analyze_v7_rounds、L2 日志 Shell 定位、更新 v7-win-rate-history 与 ITERATIONS。Use when 批跑, 胜率,
  victoryNum, 局胜, 副胜, game_records, WF-04, logs, 找不到日志, or 解读批跑结果.
---

# 批跑与数据分析（WF-04）

## 动手前

读 [`docs/knowledge/platform-data-interpretation.md`](../../docs/knowledge/platform-data-interpretation.md) 与 [`docs/guandan-brain/工作流.md`](../../docs/guandan-brain/工作流.md) §2.3（**Step 4a L2** + **一步到位清单**）。

## 口径定音

| 指标 | 来源 | 禁止 |
|------|------|------|
| **局胜** | 批末 `victoryNum[0]` vs `[1]`（[0]=[2]、[1]=[3]） | 四席相加 |
| **副数** | `game_records_v7` 文件数 / `total_rounds` | 当局数 |
| **批跑 N 局** | `--target-games` 为 **3 的倍数** | 用 10 |
| 对账 L1 | `<repo_root>/batch_executor/latest_victory_num.json` | 裸信异常 vn |
| 对账 L3 | `<repo_root>/v7_vs_lalala_scores.json` | **`batch_executor/` 下无此文件** |

## 一步到位（批跑已结束）

```powershell
cd <repo_root>
Get-ChildItem logs -Force | Sort-Object LastWriteTime -Descending
python scripts/analysis/analyze_v7_rounds.py --all
python scripts/tools/analyze_v7_round_levels.py   # 可选；路径在 tools/ 非 analysis/
# 读根目录 latest_victory_num.json / v7_vs_lalala_scores.json / v7_vs_lalala_state.json
rg "_run_grouping_engine\s*失败|_basic_classify\s*也失败" logs/yf*_v7_*.log logs/v7_vs_lalala_*.log
```

- **L2**：仅 `<repo_root>/logs/`；`.cursorignore` → **必须 Shell**，禁止 IDE Grep 报「无日志」。
- **KPI**：以 `analyze_v7_rounds.py --all` 输出为真源，勿手写 Python 数副胜。

## 命令

```bash
# V7（v7-dev）
python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3

# M3 队 KPI
python scripts/launchers/m/run_m3_vs_lalala_games.py --games 12
```

## 产出

- 汇报含：局胜、副胜/副数、口径声明、`vn_source`、**本批 L2 日志文件名**、R-G080-4 结论。
- 结论写入 `docs/guandan-brain/v7-win-rate-history.md` 与 `ITERATIONS.md`（若本轮迭代相关）。

## 脚本索引

[`docs/guandan-brain/SCRIPT_INDEX.md`](../../docs/guandan-brain/SCRIPT_INDEX.md) §三 WF-04 行
