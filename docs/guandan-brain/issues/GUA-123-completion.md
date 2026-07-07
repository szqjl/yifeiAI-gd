# GUA-123 完成定义：敌方炸弹冲刺须反炸 + core-filter 禁压豁免

> **状态**：implemented（2026-07-06）  
> **登记**：2026-07-06  
> **WF-12 锚点**：`game_records_v7/20260706084439722054 [yf1_v7]-[opponent_1_3]-[35]-[2].json` 步 **76/92**

---

## 1. 现象（可复现）

| 步 | 谁 | 动作 | 备注 |
|----|-----|------|------|
| 69–70 | @1 / yf2 | K 炸 → A 炸 | 炸权交换 |
| 72 | yf1 | PASS | 对队友 A 炸让道（合理） |
| 73 | @1 | **Bomb/6** 五张 6 | 打后 @1 **剩 5 张** |
| 74–75 | yf2 / @3 | PASS | |
| **76** | **yf1** | **PASS** | **应反炸** |

**步 76 决策证据**（`my_decisions` / trace）：

- `handCards`（14 张）：含四 J + 方块顺子组（`D5,D6,D8,D9,H9` 等）
- `actionList_size=2`：`PASS` + `Bomb/J=[SJ,SJ,HJ,DJ,H9]`
- `greaterPos=1`，`greaterAction=Bomb/6`
- `layer=GUA-075推荐`，`intent=mid_no_same_type_pass`，`stage=stage_2`
- `group_type_map`：`0=bomb`，`1=straight_flush`

**牌力**：J 五星炸 > 6 五星炸；同花顺亦 > 6 炸（本副平台未给 SF 候选，**不纳入本 GUA 实现范围**）。

---

## 2. 根因（三层）

### 2.1 残局 Q1：缺「跟压敌炸」专用通道

- `EndgamePreprocessor.is_active`：**已激活**（@1 rem=5 ≤ 10）。
- `endgame_rule[5]` 推荐：`Pair / Trips / 大单张`，**不含 Bomb**。
- `_q1_enemy_five_single_special` 仅处理 **greater=Single**，不覆盖 **greater=Bomb**。
- 步 72 同类局面 trace 曾走 `残局管线` 仍 PASS：Q1 选中炸后可能被 **core-filter** 打掉（见 2.2）。

### 2.2 `_group_consistency_filter`：反炸被静默删除

- `Bomb/J` 使用 `H9`（`gid1` 同花顺 core 的一部分），`_get_broken_core_type` → `StraightFlush`。
- 主攻 + 拆 bomb/SF core → **候选移除**（`永不放行` 分支）。
- 硬例外（我方 ≤5 张 / 敌 ≤2 张）**不满足**（我方 14 张、@1 剩 5 张）。

### 2.3 GUA-091 stage_2：敌炸无改压路径

- `_recommend_min_press_impl` / `_recommend_max_press_impl`：敌炸 → **直接 None**。
- `_r11_bomb_throttle_check`：敌炸 → **`can_bomb=False`**（注释「改压更高炸弹是另一回事」）。
- `_stage_mid_dispatch` 无 counter-bomb 回退 → **`mid_no_same_type_pass`**。

### 2.4 概念澄清（非缺陷）

| 概念 | 步 76 值 | 说明 |
|------|----------|------|
| GUA-089 `_current_stage` | `stage_2` | 看 **我方手牌** 14 张（11–20） |
| 残局 `is_active` | true | 看 **任意家** ≤10（@1=5） |
| trace `stage_3` | 仅后段 9→5 张领出 | 与步 76 无关 |

---

## 3. 5 问准入（[`V7-架构演进与新增规则准入治理.md`](../V7-架构演进与新增规则准入治理.md)）

| # | 结论 |
|---|------|
| ① 一类局面？ | **是** — 被动跟压敌方 bomb-like 控牌，且 `actionList` 存在 `_action_beats_greater` 为真的 bomb-like |
| ② 落点？ | **阶段 A hard safety**：Q1 专判 + stage_2 counter 回退 + filter 豁免；**非**牌例补丁 |
| ③ P0？ | **是** — 敌冲刺丢炸权，后续 @1 连出 TWT 等夺权 |
| ④ 验证？ | 构造态 pytest + WF-12 锚点步 76 + R-G080-4 零退化 |
| ⑤ 迁移？ | 统一评分器 `counter_bomb_min_cost`；intent `block_enemy_bomb_sprint` |

---

## 4. 最小修复方案（三补丁，按序实施）

### 补丁 A — Q1：`_q1_counter_enemy_bomb`（`endgame_decide.py`）

**插入点**：`_q1_block_enemy()` 内，在 `finish_now` 之后、`gua115` 之前（或 `gua115` 之后若需区分 rem=4）。

**逻辑**：

```text
IF 跟压敌方控牌（_is_q1_following_enemy_control）
AND greaterAction 为 bomb-like（平台声明优先）
AND 主敌 remaining <= 5（或与 sprint 相关的 endgame 阈值，可参数化 ≤5）
THEN:
  从 actionList 收集 bomb-like 候选 c，满足 _action_beats_greater(c, greaterAction, curRank)
  IF 非空:
    按 _sort_q1_block_candidates（GUA-103 最小足够成本）排序
    RETURN 最优候选
  ELIF 仅有 PASS:
    RETURN PASS   # 确实压不过
```

**与 GUA-115 边界**：主敌 `remaining==4` 且火不打四场景 → **GUA-115 优先**，本补丁不得覆盖 `_q1_gua115_fire_no_bomb_four_pass`。

**与 GUA-104 边界**：`greaterPos==队友` → 已有 `_q1_hold_teammate_max_control`，本补丁不触发。

### 补丁 B — stage_2：敌炸 counter 回退（`ultimate_win_rate_engine_v7.py`）

**插入点**：`_stage_mid_dispatch()` 的 `is_lower` / `is_upper` 分支，在 `mid_no_same_type_pass` 之前。

**新增辅助**：`_recommend_counter_bomb_from_action_list(game_state, action_list, cur_rank)`：

- 输入：当前 `greaterAction`（敌炸）、平台 `actionList`（非 card_mask 臆造）
- 筛选：bomb-like 且 `_action_beats_greater`
- 排序：与 GUA-103 一致（张数少、少 wild、牌点小）
- 返回推荐 dict 或 None

**触发**：`_recommend_min_press_impl` 因敌炸返回 None **且** 主敌 `remaining<=5`（或 `sprint_fire_ready` 且敌控炸）时，走 counter 而非 R11「不跟炸」。

**不改**：R11 对「敌出非炸、我方无同型」的让道语义。

### 补丁 C — core-filter：反炸豁免（`ultimate_win_rate_engine_v7.py`）

**插入点**：`_group_consistency_filter` 硬例外块（紧接 R16 之后）或 bomb/SF 拆 core 分支前。

**条件（同时满足）**：

1. `greaterAction` 为 bomb-like 敌方控牌；
2. 候选 `action` 为 bomb-like 且 `_action_beats_greater(action, greaterAction, cur_rank)`；
3. 主敌 `numofplayers[enemy] <= 5`（或与 Q1 补丁同一阈值）；
4. **可选收紧**：该候选是 actionList 中**唯一**可压过的 bomb-like（避免滥用拆 core）。

**效果**：步 76 的 `Bomb/J` 虽拆 SF core，仍进入合法候选并最终被 Q1/stage_2 选中。

**与 GUA-112 关系**：finish-now 仍最高优先；本豁免仅针对 **跟压敌炸**。

---

## 5. 测试计划（`tests/test_gua123_counter_enemy_bomb.py`）

| ID | 场景 | 期望 |
|----|------|------|
| 123-1 | 敌 `Bomb/6` 五星，我 `Bomb/J` 五星 + PASS，`curRank=9`，敌 rem=5 | 选 `Bomb/J`，非 PASS |
| 123-2 | WF-12 锚点 multiset：`handCards` 14 张简化构造 + `actionList` 两步 | 与 123-1 一致 |
| 123-3 | 敌 rem=4、仅炸可压 | **PASS**（GUA-115 回归） |
| 123-4 | 队友 A 炸控牌，我方可压 | **PASS**（GUA-104 回归） |
| 123-5 | 敌 `Bomb/K` 四星，我仅 `Bomb/6` 五星 | **PASS**（压不过） |
| 123-6 | core-filter：反炸拆 SF core，满足豁免条件 | filter_map 不为 -1 |

**回归 bundle**：

```bash
python -m pytest tests/test_gua123_counter_enemy_bomb.py \
  tests/test_gua115_fire_no_bomb_four.py \
  tests/test_gua078_endgame_tracker_decide_entry.py \
  tests/test_gua091_stage_mid_dispatch.py -q
```

---

## 6. 关单条件

- [x] 补丁 A+B+C 落地
- [x] 123-1～123-6 全绿（含 latent SF 诊断 123-8）
- [x] WF-12 锚点步 76 构造态：必须 `Bomb/J`
- [x] GUA-115 / GUA-104 / GUA-091 回归无退化
- [ ] 净盘批跑 R-G080-4 零退化（用户触发后登记 ITERATIONS）

---

**牌力**：J 五星炸 > 6 五星炸；同花顺亦 > 6 炸（本副平台未给 SF 候选 → **GUA-124 观测**，见 §8）。

---

## 8. 平台 actionList 缺 SF（GUA-124，观测项）

**结论（步 76）**：非客户端过滤；`actionList_size=2` 即平台全量。

| 项 | 说明 |
|----|------|
| 根因 | 逢人配 `H9` 被平台编入 `Bomb/J` 五星炸；**未同时枚举**「方片 5–9 同花顺 + H9」变体 |
| 组牌 | `enumerate_groupings` 可见 SF `D5,D6,H9,D8,D9` 且可压 `Bomb/6` |
| 约束 | `actIndex` 必须对应平台列表；**客户端不得臆造 SF 出牌** |
| 诊断 | `find_latent_bomb_like_beaters_not_in_action_list` + trace 警告 `GUA-124` |
| 本 GUA 修复 | 在仅有 `Bomb/J` 时 **必须反炸**；`action_list_item_to_feed_recommendation` 优先平台声明牌型（避免逢人配炸被 `get_action_type` 误判为 Free→PASS） |

---

## 7. 明确不做（本 GUA 范围外）

- 客户端补 SF 进 actionList 并出牌（需平台/exe 枚举支持）
- 修改 GUA-089 阶段边界（我方 14 张保持 `stage_2` 为设计如此）
- M3 引擎同步（V7-only）
