# WF-12 · yf 出牌决策链路分析

> **目的**：对 **yf1_v7 / yf2_v7 / yf1_m3 / yf2_m3** 某一出牌步做**可复现的决策链路还原**，定位「为何我方不胜 / 副级失误 / 浪费炸弹」的根因，并导向 **GUA 登记或最小修复**。  
> **与 WF-04 分工**：WF-04 = 批跑 KPI（局胜/副胜）；**WF-12 = 单步微观决策**（哪一层选了什么、为何）。  
> **与 WF-06 分工**：WF-06 = 回放工具 + `replay_word.md` 叙事；**WF-12 = 引擎日志 + `my_decisions` 的管线级证据**。

---

## 1. 触发

| 触发词 | 示例 |
|--------|------|
| 分析 yf 决策 / 决策链路 / 为何出这手 | 「分析 yf1 步 7 为何开炸」 |
| 我方不胜根因 / 典型败招 | 「这副为何 0 胜，看关键步」 |
| GUA 回放锚点 | ISSUES 中已写 `game_id` + 步号 |

**输入最少信息**（人类任选其一）：

```text
游戏: <game_records 文件名或 game_id>
<步号>/<总步>  <谁出牌>  <牌面>
```

示例：

```text
游戏: 20260628091707150272 [yf1_v7]-[opponent_1_3]-[16]-[2].json
6/73  对手@3  ♠6 ♥6 ♦6 ♥2 ♦2
7/73  yf1_v7  ♠8 ♠8 ♣8 ♦8
```

---

## 2. Agent 必做步骤（按序）

| 步 | 动作 | 真源 |
|----|------|------|
| **① 定位牌谱** | V7 → `game_records_v7/`；M3 → `game_records/`；按 `game_id` 或文件名 | 勿混目录 |
| **② 还原圈况** | 读 `actions[]` 该步前后 3～5 步：`cur_pos`、`greater_pos`、`greater_action`、PASS 链 | 平台 notify 流水 |
| **③ 读决策快照** | `my_decisions[]` 中 **同 timestamp 或最近** 的 `act` 条目：`action_index`、`handCards`、`card_mask`、`role`、`group_type_map` | JSON 内嵌 |
| **④ 对日志** | `logs/yf{1,2}_{v7,m3}_*.log` 搜同时刻 ±1s：`GUA-075`、`残局管线`、`组牌保护拦截`、`Guard`、`heuristic`、`actIndex=` | Layer 2，不进 Git |
| **⑤ 还原管线** | 按 §3 决策层顺序，写出**实际命中层**与**被跳过/拦截层** | 见下 |
| **⑥ 根因分类** | 归入 §4  taxonomy 之一（可多标签） | 导向 GUA |
| **⑦ 产出报告** | 格式见 [`工作流.md`](../工作流.md) §2.6 | 人类可读 |
| **⑧ 后续动作** | 可修 → 登记/更新 **GUA**（WF-10）+ pytest 构造态；仅观测 → 摘要写入 `replay_word.md` 或 analysis handoff | 禁止为单局写特例 |

**禁止**：

- 只凭 `actions[]` 猜意图、不读 `my_decisions` / 日志。
- 用 replay 逐步一致作为关单标准（ISSUES 头部「复盘发现 → 实现 → 验收」）。
- 篡改牌谱或日志。

---

## 3. V7 决策管线（`UltimateWinRateEngineV7.decide`）

自上而下，**先命中者先 return**（回退路径除外）：

| 层 | 模块 | 日志关键词 | 典型职责 |
|----|------|------------|----------|
| L0 | 组牌引擎 | `组牌引擎: role=` | `card_mask` / `group_type_map` |
| L0b | MemoryTracker + 信念 | `belief inject`（debug） | GUA-072 `_belief` |
| L1 | 残局管线 | `残局管线命中` / `Q0`～`Q3` | GUA-078；激活则常直接 return |
| L2 | **GUA-075 推荐** | `GUA-075 推荐:` → `主路径: … actIndex=` ✅ | 四场景：领出/跟上家/卡下家/让对家 |
| L2′ | 组牌保护 | `推荐被组牌保护拦截: … 拆 bomb` | 推荐有效但被 mask 挡 → **掉进回退** |
| L3 | Guard filter | `filter_action_list` | v7_guards 硬删 |
| L4 | 组牌前置过滤 | `前置过滤: role=` | `_group_consistency_filter` |
| L5 | 接风/投喂 | `接风` / `投喂` | 重排，不删 |
| L6 | NN | `模型决策` / 无 GUA-075 成功日志 | `_model_decision`（常 argmax 坍缩） |
| L7 | Heuristic 覆盖 | `heuristic top3`（debug） | 拆局 / 王滥用 → `_heuristic_select` |
| L8 | validate / fallback | `规则回退` | 最后兜底 |

**M3**：管线不同，读 `m3_decision_engine` + `TrickSequenceTracker`；WF-12 同样适用「牌谱 + my_decisions + 客户端 log」，层名换为 M3 guard Rxx。

---

## 4. 根因 taxonomy（导向 GUA）

| 标签 | 含义 | 常见修复方向 |
|------|------|--------------|
| **R-D01 推荐被 mask 挡** | GUA-075 选对型但拆 core → 回退出炸/NN | 下一档同型（GUA-081） |
| **R-D02 推荐缺失** | 无同型、R11 让道 PASS，局面需压 | R11 阈值 / 三带二 builder |
| **R-D03 残局未命中** | `numofplayers` 假 / Q 未触发 | GUA-078 / publicInfo.rest |
| **R-D04 组牌锁死** | 对子/三张 is_core 导致无法合法压牌 | grouping to_card_mask / 借调 API |
| **R-D05 启发式/NN 劣选** | 有合法小压却选炸/王/拆对 | GUA-071 规则、GUA-079 最小压制 |
| **R-D06 场态误读** | greaterPos/curPos/队友识别错 | GUA-027 类、greaterAction |
| **R-D07 记录/贡还** | initial_hand 与出牌不一致 | GUA-067/081 recorder |
| **R-D08 知识未接入** | 人类常识有、代码无 | GUA-073 映射 → guard/heuristic |

分析结论须标 **至少一个 R-Dxx** + **证据行**（日志或 JSON 字段）。

---

## 5. 命令与文件速查

```bash
# 牌谱目录
# V7: game_records_v7/<game_id> [yf1_v7]-....json
# M3: game_records/<game_id> [yf1_m3]-....json

# 客户端日志（与牌谱 start_time 同批）
# logs/yf1_v7_YYYYMMDD_HHMMSS.log

# 批跑总日志（vn / batch_games）
# logs/v7_vs_lalala_YYYYMMDD_HHMMSS.log

# PowerShell：按 game_id 搜决策日志
rg "GUA-075|残局管线|组牌保护|actIndex=" logs/yf1_v7_*.log
```

| 文件 | 用途 |
|------|------|
| `src/v/nn/ultimate_win_rate_engine_v7.py` | V7 `decide()` / `_heuristic_select` / GUA-075 |
| `src/v/nn/guards/v7_guards.py` | Guard R01～R12 |
| `src/v/nn/endgame/` | 残局 Q0～Q3 |
| `src/communication/v7_game_recorder.py` | `my_decisions`、贡还 `initial_hand` |
| `docs/guandan-brain/ISSUES.md` | 登记 GUA |
| `replay_word.md`（仓根） | 典型步人类可读摘要 |

---

## 6. 报告模板（复制使用）

```markdown
## WF-12 决策链路：<game_id> 步 <N>/<M>

### 圈况
- 级牌 / 角色 / 手牌数：
- 上家控牌 / 队友 / 对手出牌：
- greaterPos / greaterAction：

### 实际出牌
- 动作 / actIndex：
- 决策层：**L?**（证据：日志一行或 my_decisions）

### 管线还原（按序）
1. GUA-075：…
2. mask 拦截：…
3. 回退：Guard → … → NN/heuristic → 最终 actIndex=

### 根因
- **R-D0?**：…
- 人类可优解：…（非关单标准）

### 建议
- [ ] 登记 GUA-xxx / 更新 GUA-081
- [ ] pytest 构造态：tests/test_gua0xx_….
- [ ] 批跑：**R-G080-4 零退化**（`v7-win-rate-history.md`）；**禁止**以「再跑同副 replay 逐步一致」为 pass
```

---

## 7. 范例（GUA-081 锚点）

**牌谱**：`20260628091707150272`，步 7，yf1 四炸 8888 压对手三带二 666+22。

| 层 | 结果 |
|----|------|
| GUA-075 | 推荐 `ThreeWithTwo/8`（888+22） |
| L2′ | **组牌保护拦截**（拆 8 炸） |
| 回退 | 无二次三带二 fallback → **actIndex=116 Bomb/8** |
| 根因 | **R-D01** + 缺 fallback（→ GUA-081） |

完整日志行见批跑 `logs/v7_vs_lalala_20260628_091551.log` 同秒 `GUA-075 推荐被组牌保护拦截`。

---

## 8. 维护

- 新增决策层或改 `decide()` 顺序 → 更新 §3 表 + Skill。
- 新 taxonomy → §4 追加 R-Dxx，并在 ISSUES 交叉引用。
- 关单 GUA 若方法论可复用 → **WF-11** Playbook（如 PB-001 拆炸时序）。
