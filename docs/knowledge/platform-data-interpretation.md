# 掼蛋规则与离线平台数据解读（v1006）

> **真源用途**：掼蛋**基本规则**（队际、升级、局/副）、解读 `guandan_offline_v1006.exe`、WebSocket 消息、`victoryNum`、`execution_state.json`、客户端日志与 `game_records/` 时**统一读本页**。适用于批跑分析、ITERATIONS/EVAL、Agent、代码注释与人工看客户端。  
> **新手摘要**亦见 [README.md § 掼蛋与平台基础知识](../../README.md#掼蛋与平台基础知识新手必读)。

**相关**：完整规则 [guandan-knowledge.mdc](../../.cursor/rules/guandan-knowledge.mdc) · 协议字段 [guandan-platform-v1006.mdc](../../.cursor/rules/guandan-platform-v1006.mdc) · PDF [offline_platform/掼蛋平台使用说明书v1006.pdf](../../offline_platform/掼蛋平台使用说明书v1006.pdf)

---

## 0. 掼蛋基本规则（队际对战）

- **队伍**：4 人对战，**0 号位 + 2 号位为一队，1 号位 + 3 号位为另一队**。连接顺序决定座位号。
- **一副牌（副）**：108 张发完、每人 27 张 →（第二副起：进贡 → 还贡或抗贡）→ 多圈出牌 → 四人完牌顺序确定（`order` 四名；双上时可有 `restCards`）→ 按名次升级并决定下一副进贡关系。**一副 ≠ 一圈 ≠ 比赛一轮 ≠ 一局**。
- **一局（平台局 / 规则一局）**：从 2 打起，打到 A 并在 A 级取得**双上**（头游 + 二游），才算赢下一局。
- **完赛名次**：头游（第 1 名）→ 二游（第 2 名）→ 三游（第 3 名）→ 末游（第 4 名）。

### 0.1 升级规则

| 本队名次 | 本队升级级数 | 示例 |
|----------|-------------|------|
| 头游 + 二游（双上） | **升 3 级** | 2→5 |
| 头游 + 三游 | **升 2 级** | 2→4 |
| 头游 + 末游 | **升 1 级** | 2→3 |
| 无头游（对方双上 / 对方头游） | **不升级** | 保持当前级 |

- 对方同理：若对方获得头游，对方按上表升级，本队不升级。
- **A 级特殊规则**：打到 A 后，须在 A 级这副拿到**双上**才算赢一局。若 A 级连续 2 副未胜（含被对方双上），则**降回 2 级重打**。A↔2 循环满 50 次 → 平局。

> 牌型、逢人配、进贡细则 → [guandan-knowledge.mdc](../../.cursor/rules/guandan-knowledge.mdc)。

---

## 1. 两个计数维度（局 vs 副）

| 层级 | 叫什么 | 是什么 | 怎么数 |
|------|--------|--------|--------|
| **平台 / 批跑「局」** | **局**（平台局） | v1006 说明书「**游戏次数**」/`settingTimes`：一次「游戏」= 一方在 **A 级**、且本副以 **头游+二游（双上）** 完牌过关（见 PDF `gameOver` 段注释） | `exe N`、`--target-games N`、`completed_games`；`gameOver` 时 `curTimes` = `settingTimes`。**例外**：本包 exe argv 实测见 **§2**（单次会话固定 3 局） |
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

## 2. v1006 exe argv 实测（定音，2026-05-31）

> **与 PDF 说明书不一致**：说明书约定 `guandan_offline_v1006.exe N` → `settingTimes=N`；**本仓库所附 v1006 离线 exe 在本机实测未按 argv 执行**。

### 2.1 探测方法

- **环境**：`offline_platform/guandan_offline_v1006/windows/` **仅含 exe**，无 `config.ini` / `config.json` 等覆盖 argv 的配置。
- **启动 stdout**：`exe 1` / `3` / `10` / 无参均只打印 `Ready for connect.`，**不 echo N**。
- **WebSocket 抓包**：`scripts/tools/probe_exe_argv_ws.py`（4 客户端连入，记录 `gameOver` / `gameResult`）。

```bash
python scripts/tools/probe_exe_argv_ws.py --compare -o data/eval/exe_argv_compare.json
python scripts/tools/probe_exe_argv_ws.py --n 10 -o data/eval/exe_argv_10.json
```

### 2.2 实测矩阵（同机、同 exe）

| exe argv | WebSocket `settingTimes` | `curTimes` 序列 | 本会话实际平台局数 | 批末 `victoryNum` `[0]+[1]` |
|----------|--------------------------|-----------------|--------------------|-----------------------------|
| **1** | **3** | 1 → 2 → 3 | **3 局**（非 1） | **3**（例 `[0,3,0,3]`） |
| **3** | **3** | 1 → 2 → 3 | **3 局** | **3**（例 `[2,1,2,1]`） |
| **10** | **3** | 1 → 2 → 3 | **仍只 3 局**（非 10） | **3** |

**定音**：

1. **单次 exe 会话固定跑满 3 个平台局**（`curTimes` 必到 3），与 argv **1 / 3 / 10 无关**（至少在本包 build 上 **N≠3 时 argv 无效或被忽略**）。
2. WebSocket **`settingTimes` 恒为 3**；**不是**「字段陈旧」，而是 exe 内部会话上限为 3。
3. **`gameResult.victoryNum` 按 3 局累计**，故 `batch_games=1` 时常出现 `[3,0,3,0]`、`[2,1,2,1]` 等 **`[0]+[1]=3≠1`**——须 GUA-033 校验 + fallback，**禁止裸信**。
4. **`batch_executor` 的 `single_run_limit=3`** 是对该 exe 行为的适配，**不是** exe 听脚本的话。

### 2.3 与批跑脚本的关系

| 层 | 行为 |
|----|------|
| `restart_manager` | 正确执行 `[exe, str(batch_games)]`；日志「游戏场数: N」= **意图 N** |
| 离线 exe | **实测忽略 argv**（或 N&lt;3 / N&gt;3 均钳制为 **3 局/会话**） |
| `completed_games` | 按 **一次会话结束 +1**（与 `batch_games` 台账同口径），**不等于** WebSocket 内实际打的平台局数 |
| 队胜 / 回填 | 以 **`current_batch.json` → `batch_games`** 为准，交叉校验 `victoryNum` |

**满 12 局平台局**：须 **多批重启**（3+3+3+3），不能指望 `exe 12` 一次跑完。**勿设 `--target-games 10`** 等非 3 倍数（末批 1 局 → GUA-033 fallback）。

### 2.4 关键协议字段（速查）

| 字段 | 含义 |
|------|------|
| `episodeOver.order` | [头游, 二游, 三游, 末游] — **一副**结束 |
| `gameResult.victoryNum` | 批末各队 **赢几局**（`[0]` vs `[1]`，不是副数） |
| `gameResult.draws` | [P0, P1, P2, P3] 累计平局 |
| `act.stage.play.curRank` / `selfRank` / `oppoRank` | 当前级 / 我方级 / 对方级 |

**需要跟踪升级过程才能知道一局何时结束**：客户端应记录每副 `curRank` 变化，当一方到 A 并双上时 = 一局结束。客户端实现见 **§8**。

---

## 3. 批跑侧观测（2026-05-31，M3 vs lalala）

净盘 `--target-games 1`、`batch_games=1` 的一次批跑（修复前客户端仍可能误信服务器 vn）：

| 指标 | 结果 | 解读 |
|------|------|------|
| 台账 `completed_games` | **1/1** | 批跑 **意图 1 批**；见 §2.3 |
| WebSocket | `settingTimes=3`，`curTimes=1→3` | **实际平台 3 局**（§2.2） |
| `game_records` 成对 match_key | **45**（例） | **副数**，≠ 局数 |
| 服务端 stdout | 一次「达到设定游戏次数」 | 一次 **exe 会话**结束 |

**结论**：`--target-games 1` 表示批跑 **台账 +1**，**不是**「平台只打 1 个平台局」；本包 exe 该会话内仍会打 **3 局、数十副**。

---

## 4. 协议字段怎么读

### 4.1 `settingTimes` / exe N / `target-games` — **谁为准**

| 优先级 | 来源 | 含义 | 可靠性 |
|--------|------|------|--------|
| **1（批级真源）** | `batch_executor/current_batch.json` → `batch_games` | 本批 **意图 N**（`restart_manager` 写入） | **高** — 校验 vn、回填、队胜口径 |
| **2** | 环境变量 `BATCH_GAMES` | 与上同源 | **高** |
| **3** | 日志「游戏场数: N」/ argv | **传给 exe 的意图 N** | **高（意图）** — **≠ exe 实际局数**（§2.2） |
| **4（勿裸信）** | WebSocket `gameOver.settingTimes` | 协议字段 | **低** — 本包实测 **恒 3** |
| **5（台账）** | `--target-games` / `execution_state.completed_games` | 多批 **会话完成次数**累计 | **高**（进度）；单批 N 仍看 `batch_games` |

**结论**：批末校验、回填、胜率 **`batch_games` 为准**；**不得**用 `gameOver.settingTimes` 或裸信 `gameResult.victoryNum` 定本批 N。

| 来源 | 含义 |
|------|------|
| `guandan_offline_v1006.exe N` | **意图** N 局；**本包 exe 实测单次会话固定 3 局**（§2） |
| `--target-games 10` | 批跑台账目标 **10**（通常 3+3+3+1 四批） |
| `completed_games` | 已完成 **批次数/会话数**（与 `batch_games` 累加同口径） |

### 4.2 `episodeOver` vs `gameOver`

| 消息 | 含义 |
|------|------|
| `episodeOver` | **小局 / 一副结束**；发牌→完牌→升级 |
| `gameOver` | 本批 **`curTimes` 达到 `settingTimes`**（打满 N **局**） |
| `gameResult` | 本批累计；含 `victoryNum`、`draws` |

### 4.3 `victoryNum`（批末队胜 — **须校验，禁止裸信 WebSocket**）

> **GUA-033（2026-05-31）**：根因见 **§2**——exe 会话固定 3 局，`gameResult.victoryNum` 按 **3 局**累计；当 `batch_games=1` 时常为 `[3,0,3,0]` 等 **`[0]+[1]≠batch_games`**。**不得**未校验就落盘/回填/计胜率。

| 优先级 | 来源 | 用法 |
|--------|------|------|
| **1** | 校验通过的 `gameResult.final` 或 `victoryNum` | `[0]+[1]==batch_games` 且 `[0]=[2]`、`[1]=[3]` |
| **2** | 客户端本批 **`gameOver` 计数**（`curTimes≤batch_games`） | 服务器 vn 无效时的 fallback（`yf1_m3`/`yf2_m3`） |
| **3** | `batch_executor/latest_victory_num.json` | executor 批末交叉验证；含 **`server_vn_raw`** / **`vn_source`** 对账（§4.3.1） |

**语义**（校验通过后）：各队在本批会话内累计 **赢了几局**（不是副数）。

| 项 | 说明 |
|----|------|
| **含义** | 本批会话内，各座位所属队累计 **赢了几局**（不是副数） |
| **同队** | 0 与 2 一队、1 与 3 一队；同队两席数值相同 |
| **队级读法** | 只取 **`[0]` vs `[1]`**（或 `[2]` vs `[3]`，等价）；**禁止四席相加**（会重复计同一队） |
| **与批跑** | 本批 `batch_games=3` → 批末 **`[0]+[1]=3`**；`batch_games=1` → **`[0]+[1]=1`** |
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

批内 3 局也可能拆成例如 `[2,1,2,1]`（M3 赢 2 局、lalala 赢 1 局）；**`[0]` + `[1]` 应等于本批 `batch_games`（非裸信 `settingTimes`）**。

**与 `completed_games`**：台账记录本批跑了几个 **局**；`victoryNum` 记录这些局里 **各队赢了几个**。

#### 4.3.1 fallback 语义：`batch_games=1` 只认领 `curTimes=1`

本包 exe **单次会话固定 3 平台局**（§2），但第 4 批等场景 **`batch_games=1`**（10 局跑法的最后一个台账槽位）。此时：

| 字段 / 行为 | 含义 |
|-------------|------|
| 服务器 `gameResult.victoryNum` | 本会话 **3 局合计**（例 `[3,0,3,0]`，`[0]+[1]=3`） |
| 校验 | **拒绝**（`3 ≠ batch_games=1`），**禁止**回填到本批 JSON |
| fallback | `gameOver` 仅在 **`curTimes ≤ batch_games`** 时计胜 → **`curTimes=1` 那一局** |
| 落盘 `victoryNum` | 例 `[1,0,1,0]`：**台账口径下本批认领 1 局队胜**，不是会话 3 局合计 |
| `latest_victory_num.json` | `victoryNum` = 采用值；**`server_vn_raw`** = WebSocket 原文；**`vn_source`** = `server` \| `fallback` |

```text
batch_games=1 的一批：
  平台实际：gameOver curTimes 1 → 2 → 3（3 局、多副）
  台账队胜：只取 curTimes=1 对应那一局的胜负 → [0]+[1]=1
  对账：server_vn_raw 仍保留 [3,0,3,0] 等，便于与平台 RAW 对照
```

**勿混读**：fallback 后的 `[1,0,1,0]` **不是**「平台只打了 1 局」；**是**「在 `--target-games` 台账里这一批只计 1 个队胜槽位」。分析「本会话真实 3 局谁赢几局」请看 **`server_vn_raw`** 或 §2 矩阵，**不要**用 fallback 后的 `victoryNum` 当会话合计。

**代码位置**：`yf1_m3` / `yf2_m3` 的 `_handle_game_over`（`curTimes <= expected`）；共享文件由 **`yf1_m3`** 写入 `batch_executor/latest_victory_num.json`。

### 4.4 `game_records/`（每条 = 一副，不是一局）

- **一条 JSON = 一副**（单座视角；平台 **小局** / `episodeOver` 后落盘）。
- **文件数 / match_key 数 = 副数**（成对 yf1+yf2 去重），**≠ 局数**，**≠ `victoryNum`**。
- 落盘可能膨胀（pending 回填等）；数副优先 `total_rounds` 或成对 match key。

---

## 5. 批跑台账 vs 牌谱分析

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

## 6. 常见误读

| 误读 | 正确 |
|------|------|
| `exe 1` = 平台只打 1 局 | **本包 exe 实测单次会话固定 3 局**（§2）；`batch_games=1` 是批跑 **意图** |
| `exe 1` = 打 1 副 | **1 平台局 ≠ 1 副**；3 局会话可打 **数十副** |
| `episodeOver` 次数 = 平台局数 | `episodeOver` = **副数**；平台局看 §2 / `batch_games`，勿裸信 `settingTimes` |
| `victoryNum` 相加 = 局数 | 四席相加会重复计队；用 **`[0]` vs `[1]`** = 各队 **赢局数** |
| 裸信 `gameResult.victoryNum` | 须 **`[0]+[1]==batch_games`**；失败则用 gameOver 计数 fallback（GUA-033） |
| 裸信 `gameOver.settingTimes` | 本包实测 **恒 3**；批级 N 以 **`current_batch.json`** 为准 |
| argv 传给 exe 就等于平台局数 | argv **可能无效**；以 WebSocket `curTimes` 序列 + §2 矩阵为准 |
| `victoryNum` = 副数 | **局**胜负累计；**副**看 `game_records` / match_key |
| 10 平台局 = 10 副 | 10 局 = 10 次「一次游戏」，副数通常 **远大于** 10 |
| 1 个 JSON = 1 平台局 | **1 JSON = 1 副（单座）** |

---

## 7. 工作示例（M3 vs lalala，2026-05-31，10 局批跑）

| 批次 | 平台局数 | M3 胜 | lalala 胜 | 批内胜率 |
|------|----------|-------|-----------|----------|
| 1 | 3 | 2 | 1 | 66.7% |
| 2 | 3 | 3 | 0 | 100% |
| 3 | 3 | 2 | 1 | 66.7% |
| 4 | 1 | 1 | 0 | 100% |
| **合计** | **10** | **8** | **2** | **80%** |

胜率按批末 `victoryNum[0]` vs `[1]`。**各批实际副数未在此表统计**（需另读 `total_rounds` / match_key）。

---

## 8. M2 胜负追踪架构

已在 `yf1_m2.py` / `yf2_m2.py` 中实现完整的「副级 + 局级」双重追踪；`yf1_m2.py` 负责写 `game_scores_m2.json`，`yf2_m2.py` 仅打日志（避免 race condition）。

### 8.1 关键逻辑

| 功能 | 函数/方法 | 所在文件 |
|------|----------|----------|
| 等级提取 | `_update_level_info()` | `yf1_m2.py` / `yf2_m2.py` |
| 副结果判定 | `_determine_round_result(order, partner_pos)` | `yf1_m2.py` / `yf2_m2.py` |
| 副存储 | `_save_round_result()` | `yf1_m2.py` |
| 局检测 | `_detect_game_end(curRank, order, partner_pos)` | `yf1_m2.py` / `yf2_m2.py` |
| 局存储 | `_save_game_end()` | `yf1_m2.py` |
| JSON 读写 | `_load_scores()` / `_save_scores()` | `yf1_m2.py` |

### 8.2 等级提取

从 `handle_action_request`（`act.stage.play.curRank` / `selfRank` / `oppoRank`）、`_handle_tribute_action`、`_handle_back_action`、`_handle_game_start` 中捕获等级字段。服务端每副第一次 `act` 消息会携带 `curRank`。

### 8.3 副结果判定

`_determine_round_result(order, partner_pos)` 根据完赛名次数组判定：

- `order` 是 `[头游, 二游, 三游, 末游]`（座位号），0-indexed
- 本队两人在 `order` 中的索引之和 `<= 2`（头游 + 二游或头游 + 三游）→ **win**
- 对方两人占据前两名 → **loss**
- 其他（本队一人头游但队友末游等）→ **draw**

### 8.4 局检测

`_detect_game_end(curRank, order, partner_pos)`：

- `curRank == "A"` 且本队**双上** → 本队赢一局
- `curRank == "A"` 且对方双上 → 本队输一局
- `curRank == "2"` 且上一副 `curRank` 为 `"A"` → 对方在 A 级双上（被降级），输一局

### 8.5 `game_scores_m2.json` 格式

```json
{
  "rounds": [
    {
      "round": 1,
      "order": [1, 0, 2, 3],
      "curRank": "2",
      "selfRank": "2",
      "oppoRank": "2",
      "result": "draw"
    }
  ],
  "games": [
    {
      "game": 1,
      "start_round": 1,
      "end_round": 7,
      "result": "loss"
    }
  ],
  "total_rounds": 21,
  "round_wins": 1,
  "round_draws": 4,
  "round_losses": 16,
  "total_games": 3,
  "game_wins": 0,
  "game_draws": 0,
  "game_losses": 3,
  "current_game_start_round": 22,
  "current_level_self": "2",
  "current_level_oppo": "A"
}
```

### 8.6 相关脚本与注意点

| 脚本 | 作用 |
|------|------|
| `yf1_m2.py` (Player 0) | 持久化（写 JSON），含等级追踪、副结果、局检测 |
| `yf2_m2.py` (Player 2) | 同步等级追踪、副结果判定，仅打日志不写文件 |
| `game_scores_m2.json` | 项目根目录，自动创建/更新 |
| `batch_executor/executor.py` | `_count_new_paired_games()` 匹配 `yf1_` / `yf2_` 前缀统计场次 |

- 服务端 `rank`：`2,3,4,5,6,7,8,9,T,J,Q,K,A`（T=10）
- `curRank` 只在每副第一次 `act` 携带；`beginning` **不包含**等级
- `selfRank` / `oppoRank` 可能为 `"X"`（未知），跳过不处理
- 完整局判定依赖客户端跨副跟踪 `curRank`，而非单副消息

---

## 9. 维护与参考资料

改批跑台账、`game_recorder` 或客户端胜负逻辑时同步更新本文。Agent 分析 lalala 数据前先读本文 + [EVAL.md](../guandan-brain/EVAL.md)。

复测 exe argv：`python scripts/tools/probe_exe_argv_ws.py --compare`。

| 资料 | 说明 |
|------|------|
| `offline_platform/掼蛋平台使用说明书v1006.pdf` | 离线平台协议、参数、数据结构 |
| `docs/archive/skill/出炸弹要领.txt` | 炸弹使用规范（经验规则） |
| `docs/guandan-brain/M2_OPTIMIZATION.md` | M2 优化日志、跑分记录、根因分析 |

**版本**：2026-06-05（合并 `guandan-basic-knowledge.md`：§0 基本规则、§8 M2 追踪；原 `platform-data-interpretation` §1～§7 保留）
