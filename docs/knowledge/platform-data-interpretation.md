# 离线平台对局数据解读（v1006）

> **真源用途**：解读 `guandan_offline_v1006.exe`、WebSocket 消息、`victoryNum`、`execution_state.json`、客户端日志与 `game_records/` 时**统一读本页**。适用于批跑分析、ITERATIONS/EVAL、Agent、代码注释与人工看客户端。

**相关**：规则层级 [guandan-knowledge.mdc](../../.cursor/rules/guandan-knowledge.mdc) §1 · 协议字段 [guandan-platform-v1006.mdc](../../.cursor/rules/guandan-platform-v1006.mdc) · PDF [offline_platform/掼蛋平台使用说明书v1006.pdf](../../offline_platform/掼蛋平台使用说明书v1006.pdf)

---

## 1. 两个计数维度（局 vs 副）

| 层级 | 叫什么 | 是什么 | 怎么数 |
|------|--------|--------|--------|
| **平台 / 批跑「局」** | **局**（平台局） | v1006 说明书「**游戏次数**」/`settingTimes`：一次「游戏」= 一方在 **A 级**、且本副以 **头游+二游（双上）** 完牌过关（见 PDF `gameOver` 段注释） | `exe N`、`--target-games N`、`completed_games`；`gameOver` 时 `curTimes` = `settingTimes` |
| **规则「副」** | **副**（一副牌） | 发牌 →（进贡还贡）→ 出牌 → `episodeOver` | `episodeOver` 次数；`game_scores_m2.json` 的 `total_rounds`；`game_records` 成对 match key |
| **规则「一局」** | **局**（规则一局） | 从 2 打到 A 且 A 级双上通关 | `game_scores_m2.json` 的 `games[]`；日志「整局结束 Game=」 |

**定音（v1006 实测 + 说明书）：**

```text
平台 1 局  ≠  1 副
平台 N 局  =  跑 N 次「一次游戏」（规则意义上的一局），每次内含多副
1 副        =  1 次 episodeOver（小局结束）
```

**平台「局」与规则「一局」**：v1006 计数单位一致（都是「一方 A 级双上过关」）；客户端用 `game_scores` 跨副追踪，平台用 `curTimes`/`settingTimes` 计数。**二者都不是「一副」。**

---

## 2. 实锤验证（2026-05-31，M3 vs lalala）

清空 `game_records/`、`logs/` 后执行：

```bash
python -m batch_executor --server-path offline_platform/.../guandan_offline_v1006.exe \
  --target-games 1 --clients yf1_m3.py ... lalala ...
```

| 指标 | 结果 |
|------|------|
| 台账 `completed_games` | **1**（平台 1 局） |
| `game_scores_m2.json` → `total_rounds` | **59**（59 副） |
| yf1 日志「本轮 … 副 x/59」 | **59** |
| `game_records` 成对 match_key | **59** |
| 服务端 stdout | 「达到设定游戏次数」→ `gameOver` |

**结论**：`exe 1` / `--target-games 1` 是 **1 局（一次平台游戏）**，不是 1 副；本例打了 **59 副** 才结束该会话。

---

## 3. 协议字段怎么读

### 3.1 `settingTimes` / exe N / `target-games`

| 来源 | 含义 |
|------|------|
| `guandan_offline_v1006.exe N` | 本会话打 **N 局**（平台「游戏次数」，非 N 副） |
| `--target-games 10` | 批跑台账目标 **10 局**（可多批 3+3+3+1） |
| `completed_games` | 已累计 **平台局数**（与 exe N 同口径） |

### 3.2 `episodeOver` vs `gameOver`

| 消息 | 含义 |
|------|------|
| `episodeOver` | **小局 / 一副结束**；发牌→完牌→升级 |
| `gameOver` | 本批 **`curTimes` 达到 `settingTimes`**（打满 N **局**） |
| `gameResult` | 本批累计；含 `victoryNum`、`draws` |

### 3.3 `victoryNum`（平台下发，按规则计 **局** 胜负）

**服务器 `gameResult.victoryNum` 是正确的**：按掼蛋规则，每打完 **一整局**（一方 A 级本副双上过关），判定谁赢；**赢方记入赢 1 局**，累加到该队两席的计数上。

| 项 | 说明 |
|----|------|
| **含义** | 本批会话内，各座位所属队累计 **赢了几局**（不是副数） |
| **同队** | 0 与 2 一队、1 与 3 一队；同队两席数值相同 |
| **队级读法** | 只取 **`[0]` vs `[1]`**（或 `[2]` vs `[3]`，等价）；**禁止四席相加**（会重复计同一队） |
| **与批跑** | 批跑 `--target-games 3` → 本批共 3 局；批末 `victoryNum` 反映这 3 局谁赢了几局 |
| **不是** | 副数（副数看 `episodeOver` / match_key）；单副胜负 |

**示例（M3 在 0+2，lalala 在 1+3，批跑 3 局后）：**

```text
victoryNum: [0, 3, 0, 3]
            └─0+2队─┘ └─1+3队─┘
→ M3 赢 0 局，lalala 赢 3 局
```

```text
victoryNum: [3, 0, 3, 0]
→ 0+2 队（M3）赢 3 局，1+3 队（lalala）赢 0 局
```

批内 3 局也可能拆成例如 `[2,1,2,1]`（M3 赢 2 局、lalala 赢 1 局）；**`[0]` + `[1]` 应等于本批 `settingTimes`（局数）**。

**与 `completed_games`**：台账记录本批跑了几个 **局**；`victoryNum` 记录这些局里 **各队赢了几个**。

### 3.4 `game_records/`（每条 = 一副，不是一局）

- **一条 JSON = 一副**（单座视角；平台 **小局** / `episodeOver` 后落盘）。
- **文件数 / match_key 数 = 副数**（成对 yf1+yf2 去重），**≠ 局数**，**≠ `victoryNum`**。
- 落盘可能膨胀（pending 回填等）；数副优先 `total_rounds` 或成对 match key。

---

## 4. 批跑台账 vs 牌谱分析

```
--target-games 10  →  completed_games = 10  →  10 次平台「游戏」（10 局）
                                              →  副数 = 各批 episodeOver 之和（通常 ≫ 10）

批次 1：exe 3  →  settingTimes=3  →  本批最多计 3 局（非 3 副）
```

| 用途 | 用什么 | 叫什么 |
|------|--------|--------|
| 批跑进度 | `completed_games`、`settingTimes` | **局**（共打几局） |
| 队胜率 / 谁赢几局 | 批末 `victoryNum[0]` vs `[1]` | **局**（各队赢几局） |
| PASS 率、进贡、牌谱 | `game_records`、match key、`total_rounds` | **副** |

---

## 5. 常见误读

| 误读 | 正确 |
|------|------|
| `exe 1` = 打 1 副 | **1 局**；实测可打 **数十副**（2026-05-31：59 副） |
| `episodeOver` 次数 = 平台局数 | `episodeOver` = **副数**；平台局看 `settingTimes`/`completed_games` |
| `victoryNum` 相加 = 局数 | 四席相加会重复计队；用 **`[0]` vs `[1]`** = 各队 **赢局数** |
| `victoryNum` = 副数 | **局**胜负累计；**副**看 `game_records` / match_key |
| 10 平台局 = 10 副 | 10 局 = 10 次「一次游戏」，副数通常 **远大于** 10 |
| 1 个 JSON = 1 平台局 | **1 JSON = 1 副（单座）** |

---

## 6. 工作示例（M3 vs lalala，2026-05-31，10 局批跑）

| 批次 | 平台局数 | M3 胜 | lalala 胜 | 批内胜率 |
|------|----------|-------|-----------|----------|
| 1 | 3 | 2 | 1 | 66.7% |
| 2 | 3 | 3 | 0 | 100% |
| 3 | 3 | 2 | 1 | 66.7% |
| 4 | 1 | 1 | 0 | 100% |
| **合计** | **10** | **8** | **2** | **80%** |

胜率按批末 `victoryNum[0]` vs `[1]`。**各批实际副数未在此表统计**（需另读 `total_rounds` / match_key）。

---

## 7. 维护

改批跑台账、`game_recorder` 或客户端胜负逻辑时同步更新本文。Agent 分析 lalala 数据前先读本文 + [EVAL.md](../guandan-brain/EVAL.md)。

**版本**：2026-05-31（修正：平台局 ≠ 副；补 `--target-games 1` 实测）
