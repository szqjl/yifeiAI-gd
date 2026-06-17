# M2 对战知识库

> **主文档**：请以 [docs/guandan-basic-knowledge.md](../guandan-basic-knowledge.md) 为准（README 已收录新手摘要）。  
> 重要：所有离线平台细节以 `offline_platform/掼蛋平台使用说明书v1006.pdf` 及 `offline_platform/guandan_offline_v1006/使用说明.pdf` 为准，本文档仅作简要梳理。

---

## 一、掼蛋基本规则（队际对战）

- **队伍**：4人对战，**0号位+2号位为一队，1号位+3号位为另一队**。连接顺序决定座位号。
- **一副牌**：108 张发完、每人 27 张 →（第二副起：进贡→还贡或抗贡）→ 多圈出牌 → 四人完牌顺序确定（`order` 四名；双上时可有 `restCards`）→ 按名次升级并决定下一副进贡关系。**一副 ≠ 一圈 ≠ 比赛一轮 ≠ 一局**。
- **一局**：从2打起，打到A并在A级取得**双上**（头游+二游），才算赢下一局。
- **完赛名次**：头游（第1名）→二游（第2名）→三游（第3名）→末游（第4名）。

### 升级规则

| 本队名次 | 本队升级级数 | 示例 |
|----------|-------------|------|
| 头游+二游（双上） | **升3级** | 2→5 |
| 头游+三游 | **升2级** | 2→4 |
| 头游+末游 | **升1级** | 2→3 |
| 无头游（对方双上/对方头游） | **不升级** | 保持当前级 |

- 对方同理：如果对方获得头游，对方按以上规则升级，本队不升级。
- **A级特殊规则**：打到A后，必须在A级这副拿到**双上**才算赢。若A级连续2副未胜（含被对方双上），则**降回2级重打**。A↔2循环满50次 → 平局。

---

## 二、离线平台（v1006）参数字义

详见 `offline_platform/掼蛋平台使用说明书v1006.pdf`

- **服务器参数**：`guandan_offline_v1006.exe N`
- 文档描述 N 为"游戏次数（一方从2打到A，并且双下）"
- **v1006 平台 N**：N = **局数**（「游戏次数」），一次「游戏」= 一方 A 级双上过关，**内含多副**；**N ≠ 副数**。见 [platform-data-interpretation.md](../../knowledge/platform-data-interpretation.md)（2026-05-31 实测 `target-games 1` → 59 副）。
- **关键协议字段**：
  - `episodeOver.order`：[头游, 二游, 三游, 末游] — 四位玩家的完赛座位号
  - `gameResult.victoryNum`：[P0胜场, P1胜场, P2胜场, P3胜场] — 累计胜场
  - `gameResult.draws`：[P0平局, P1平局, P2平局, P3平局] — 累计平局
  - `act.stage.play.curRank` — 当前打几
  - `act.stage.play.selfRank` — 我方等级
  - `act.stage.play.oppoRank` — 对方等级
- **需要跟踪升级过程才能知道一局何时结束**：客户端应记录每副 `curRank` 变化，当一方到A并双上时 = 一局结束。

---

## 三、胜负追踪架构

已在 `yf1_m2.py` / `yf2_m2.py` 中实现完整的"副级+局级"双重追踪，`yf1_m2.py` 负责写 `game_scores_m2.json`，`yf2_m2.py` 仅打日志（避免 race condition）。

### 关键逻辑

| 功能 | 函数/方法 | 所在文件 |
|------|----------|----------|
| 等级提取 | `_update_level_info()` | `yf1_m2.py` / `yf2_m2.py` |
| 副结果判定 | `_determine_round_result(order, partner_pos)` | `yf1_m2.py` / `yf2_m2.py` |
| 副存储 | `_save_round_result()` | `yf1_m2.py` |
| 局检测 | `_detect_game_end(curRank, order, partner_pos)` | `yf1_m2.py` / `yf2_m2.py` |
| 局存储 | `_save_game_end()` | `yf1_m2.py` |
| JSON读写 | `_load_scores()` / `_save_scores()` | `yf1_m2.py` |

### 等级提取

从 `handle_action_request`（`act.stage.play.curRank` / `selfRank` / `oppoRank`）、`_handle_tribute_action`、`_handle_back_action`、`_handle_game_start` 中捕获等级字段。服务端每副第一次 `act` 消息会携带 `curRank`。

### 副结果判定

`_determine_round_result(order, partner_pos)` 根据完赛名次数组判定：
- `order` 是 `[头游, 二游, 三游, 末游]`（座位号），0-indexed
- 如果本队两人在 `order` 中的索引之和 `<= 2`（即两人占据头游+二游或头游+三游）→ **win**
- 如果对方两人占据前两名 → **loss**
- 其他情况（本队一人头游但队友末游等平局情况）→ **draw**

### 局检测

`_detect_game_end(curRank, order, partner_pos)` ：
- 当 `curRank == "A"` 且本队获得**双上**（order中本队两人占前两名）→ 本队赢一局
- 当 `curRank == "A"` 且对方双上 → 本队输一局
- 当 `curRank == "2"` 且上一副 `curRank` 为 `"A"` → 对方在A级双上了（被降级），输一局

### 文件格式

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

### 相关脚本

| 脚本 | 作用 |
|------|------|
| `yf1_m2.py` (Player 0, 队长) | 负责所有持久化（写JSON），含等级追踪、副结果、局检测 |
| `yf2_m2.py` (Player 2, 队友) | 同步等级追踪、副结果判定，仅打日志不写文件 |
| `game_scores_m2.json` | 持久化文件，项目根目录，自动创建/更新 |
| `batch_executor/executor.py` | 用 `_count_new_paired_games()` 匹配 `yf1_` / `yf2_` 前缀统计场次 |

### 注意点

- 服务端 `rank` 字段取值：`2,3,4,5,6,7,8,9,T,J,Q,K,A`（T=10，字符格式）
- `curRank` 只在每副的第一次 `act` 消息中携带；`beginning` 通知**不包含**等级
- `selfRank` / `oppoRank` 可能为 `"X"`（未知），此时跳过不处理
- 完整局判定依赖客户端持续跟踪 `curRank` 跨副变化，而非单副消息

---

## 四、参考资料

- `offline_platform/掼蛋平台使用说明书v1006.pdf` — 离线平台协议、参数、数据结构
- `offline_platform/guandan_offline_v1006/使用说明.pdf` — 同一份文档的副本
- `docs/archive/skill/出炸弹要领.txt` — 掼蛋炸弹使用规范（76条经验规则）
- `docs/guandan-brain/M2_OPTIMIZATION.md` — M2优化日志、跑分记录、根因分析
