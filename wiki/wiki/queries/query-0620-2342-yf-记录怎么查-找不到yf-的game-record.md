---
type: query-answer
title: "yf2记录怎么查 找不到yf2的game record"
date: 2026-06-20
sources:
  - entities/gua-008.md
  - sources/GAME_RECORD_SAVE_FIX-summary.md
  - concepts/data-directory-segregation.md
  - concepts/fix-reports-cluster.md
  - sources/fixes-cluster-overview.md
  - sources/GAME_RECORD_VICTORYNUM_CHECK-summary.md
  - concepts/branch-isolation.md
  - concepts/dual-data-channel.md
  - entities/module-v7-engine.md
  - queries/query-0619-0828-analyze-v-rounds-批跑局级副级分析脚本-末级分布-victory.md
---

# yf2记录怎么查 找不到yf2的game record

# 查 yf2 的 game record — 完整指南

## ⚠️ 关键先确认：你要找的是哪个分支的 yf2？

Wiki 中 **`yf2`** 出现在 **M3** 和 **V7** 两个引擎分支，对应**不同的目录、客户端和分支** [{7}][{3}][{9}]：

| 分支 | 客户端 | 数据目录 | 启动脚本 |
|---|---|---|---|
| `m-dev` | `yf2_m3.py` | `game_records/` | `scripts/launchers/m/run_m3_vs_lalala_games.py` |
| `v7-dev` | `yf2_v7.py` | `game_records_v7/` | `scripts/launchers/v7/run_v7_vs_lalala_games.py` |

> 找不到 yf2 的 record，**90% 的情况是分支与目录不匹配** —— 比如在 `m-dev` 分支跑出来的 yf2，对应 record 在 `game_records/`；切到 `v7-dev` 看不到是正常的。

---

## 一、最快的排查路径

### 1. 先确认你当前在哪条分支、跑的哪个 yf2

```bash
# 1. 看分支
git branch --show-current    # 应该是 m-dev 或 v7-dev

# 2. 看实际加载的客户端
ps aux | grep -E "yf[12]_(m3|v7)" 
# 或日志里 grep "loading player"
```

### 2. 按分支到对应目录找 record

```bash
# M3 引擎 yf2 的 record（M3 规则引擎，m-dev 分支）
ls game_records/ | head
# 或 grep yf2
grep -l "yf2_m3" game_records/*.json | head

# V7 引擎 yf2 的 record（V7 NN 引擎，v7-dev 分支）
ls game_records_v7/ | head
grep -l "yf2_v7" game_records_v7/*.json | head
```

### 3. 用回放工具直接看 yf2 视角

```bash
# 通用回放
python scripts/tools/yf_replay.py game_records_v7/<record>.json --player yf2
```

---

## 二、为什么"找不到"的 5 个常见原因

| # | 症状 | 原因 | 解决 |
|---|------|------|------|
| 1 | `game_records_v7/` 是空的 | 当前在 `m-dev` 分支跑 | 切到 `v7-dev` 重跑 |
| 2 | `game_records/` 是空的 | 当前在 `v7-dev` 分支跑 | 切到 `m-dev` 重跑 |
| 3 | record 文件在但 grep 无结果 | 玩家名不是 `yf2_m3/v7`，是 `player_2` 等代号 | 看 [[module-v7-engine]] 中的字段命名 |
| 4 | record 没保存 | GUA-008 已知缺陷 —— 保存路径/文件锁问题 [{1}] | 见 `docs/fixes/GAME_RECORD_SAVE_FIX.md` |
| 5 | record 在但 victoryNum 异常 | GUA-033 + GAME_RECORD_VICTORYNUM_CHECK 范畴 [{6}] | 用双重数据通道 [[dual-data-channel]] 三步恢复法 |

---

## 三、如果你要找 V7 的 yf2 record（最常见场景）

按 [[data-directory-segregation]] 的硬规则，**V7 的 yf2 record 一定在 `game_records_v7/`** [{3}]：

```bash
# 1. 确认分支
git branch --show-current   # 必须 v7-dev

# 2. 列目录
ls -lt game_records_v7/ | head -20

# 3. 在最近一份 record 里找 yf2_v7
grep -l "yf2_v7" game_records_v7/*.json | tail -5

# 4. 副级分析（必走，V7 不能只看局级）
python scripts/tools/analyze_v7_round_levels.py \
  --records game_records_v7/ \
  --output reports/yf2_v7_rounds.csv
```

> **关键提醒**：V7 必须同时跑局级 (`analyze_v7_rounds.py`) + 副级 (`analyze_v7_round_levels.py`)，避免「局 ≠ 副」统计陷阱 [{10}]。

---

## 四、记录结构里 yf2 的字段位置

参考 [[module-v7-engine]] 的对局记录器 `v7_game_recorder.py` 输出 schema：

```json
{
  "game_id": "...",
  "players": [
    {"seat": 0, "client": "yf1_v7.py"},
    {"seat": 1, "client": "yf2_v7.py"},   // ← 你要找的在这里
    {"seat": 2, "client": "lalala"},
    {"seat": 3, "client": "lalala"}
  ],
  "rounds": [
    {
      "round_idx": 1,
      "actions": [
        {"player": 1, "type": "play", "cards": [...]}   // seat=1 即 yf2
      ],
      "victory_num": [2, 1, 2, 1]
    }
  ]
}
```

**`seat=1` 对应 yf2**（队内分工：yf1/yf2 为同队对家，lalala 为对手）[{9}][{10}]。

---

## 五、信息缺口（Wiki 未覆盖）

| 缺口 | 建议 |
|------|------|
| `v7_game_recorder.py` 实际写入的玩家字段名（`player` vs `seat`） | 直接 grep 一份 record 看 |
| yf2 视角的决策日志（NN 输出 vs 规则兜底） | 需要进 `v7-dev` 分支看 `yf2_v7.py` |
| 历史批跑中 yf2 的胜率明细 | 不在 Wiki 中，需要跑 `analyze_v7_rounds.py` |

---

## 六、关联页面

- [{3}] 数据目录分离（最关键：物理隔离规则）
- [{7}] V7-dev / m-dev 分支隔离策略
- [{9}] V7 引擎模块（含 `yf2_v7.py` 模块结构）
- [{1}] GUA-008 — game record 保存缺陷（找不到的原因之一）
- [{10}] analyze_v7_rounds 批跑局级副级分析脚本（统计方式）
- [[module-v7-engine]] — V7 模块结构

---

## TL;DR

**找不到 yf2 的 record，第一步先回答两个问题：**
1. 你在哪条分支（`v7-dev` 还是 `m-dev`）？
2. 你找的是哪个目录（`game_records/` 还是 `game_records_v7/`）？

分支和目录对不上是 90% 找不到的原因。如果对上了还是空的，看 GUA-008（保存缺陷）和 GAME_RECORD_VICTORYNUM_CHECK（字段校验）[{1}][{6}]。
