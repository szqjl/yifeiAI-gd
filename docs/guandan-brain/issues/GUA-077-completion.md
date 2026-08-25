# GUA-077 完成定义：全局出牌序列 + 记忆门控的末段 TWT vs 单

> **状态**：open（P0–P4 **2026-08-25** 已编码；**仍缺**：GUA-238/273 领出 if 收敛、V8 批跑 KPI 护栏）  
> **优先级**：P1  
> **关联**：GUA-062、GUA-075、GUA-078、GUA-072（MEM-M01–M06）、GUA-125、GUA-110、GUA-168、GUA-238、GUA-273、GUA-260  
> **真源题库**：guandan.nullkit.com 残局 advanced_01（10 张两手 TWT 走完）、advanced_05（11 张三手连环 TWT）

---

## 0. 定音（人类 · 2026-08-25）

### 0.1 要解决什么

V8 已有 **单轮组牌**（`GroupingPlan`：炸弹/TWT/顺/散单静态拆分），也有 **残局 Q0–Q3** 与大量 GUA 特判（GUA-110/168/238/273…），但二者 **未用统一数据结构衔接**：

- 组牌不知道「第一手出完，第二手是什么」；
- 末段「先单还是先 TWT」散落在 `endgame_decide.py` 各函数，**重复推断**对手是否还有 TWT、单是否场上最大；
- 记忆模块（`RuleCardCounter` / `MemoryTracker`）已有 `can_opponent_form_type`、`_seat_may_hold_single_above`，但 **未作为 sprint 规划的唯一门控 API**。

### 0.2 职责三分（硬边界）

| 层 | 模块 | 只做什么 | **禁止**做什么 |
|----|------|----------|----------------|
| **结构规划** | `grouping_engine` | 从当前手牌导出 `play_sequence`（2–4 步 **理想出完序**，仅基于己方结构） | 读对手信念、决定先单还是先 TWT |
| **信念门控** | `rule_card_counter` / `MemoryTracker` | 回答「敌席是否还能压我的单/TWT/炸」「我的探单是否场上最大」 | 直接选 `actIndex` |
| **步序执行** | `EndgameDecider` Q0 / `_recommend_play` 领出 | 取 `play_sequence` **下一步**，经记忆门控 **确认或改序**，匹配 `actionList` | 在组牌里硬编码敌我剩张特判 |

**定音**：**末段 TWT vs 单的决策树 = 记忆模块供给信号 + Q0 步序选择器消费**；组牌只产出 **候选序列**，不嵌入敌情。

### 0.3 与现有 GUA 的关系（收敛，非废弃）

下列规则 **逻辑保留**，实施时 **迁入** `SprintStepPicker`，禁止再新增平行特判：

| 现有 GUA | 行为摘要 | GUA-077 落点 |
|----------|----------|--------------|
| GUA-112 / Q0.5 | 一手清最高优先 | `play_sequence[0]` 若 `steps_to_zero==1` → 直接执行 |
| GUA-110 | 两手冲刺先整牌（TWT）非散单 | 记忆门控：`enemy_can_beat_probe_single` → 否时仍可能先整 |
| GUA-168 | 炸弹+单、敌>1 → 先探单 | `play_sequence` 含 `[Single, Bomb]`；门控同上 |
| GUA-238 | 敌 TWT 弱点 → 先 TWT | `memory.enemy_twt_unlikely` 为 true → 提升 TWT 步优先级 |
| GUA-273 | 三头+配子+单：敌=1→TWT；敌>1→先单 | 写入决策树 **§4.2** 标准分支（非独立 if） |
| GUA-125 | 跟压 sprint-preserving | 仅 **跟压** 路径；领出步序仍走 `play_sequence` |

---

## 1. 数据结构

### 1.1 `PlayStep`（新建，`grouping_engine.py` 或 `play_plan_types.py`）

```python
@dataclass
class PlayStep:
    """平台对齐的一步出牌意图（非 actionList 下标）。"""
    action_type: str          # 平台名：Single / ThreeWithTwo / Bomb / …
    target_rank: str          # greaterAction 主 rank，如 ThreeWithTwo/K → "K"
    group_id: Optional[int]   # 对应 GroupingPlan.to_card_mask() 的 group_id
    cards_hint: Optional[List[str]] = None  # 可选：精确匹配 actionList 用
    step_role: str = "lead"   # lead | follow_same_type | bomb_recapture
```

### 1.2 `GroupingPlan.play_sequence`

```python
@dataclass
class GroupingPlan:
    ...
    play_sequence: List[PlayStep] = field(default_factory=list)
    plan_b_sequences: List[List[PlayStep]] = field(default_factory=list)  # 被炸后的备选序（Phase 4）
```

**语义**：

- `play_sequence`：从 **当前完整手牌** 到 0 张的 **最短可靠路径**（优先 2–3 手残局；开局可只填前 2 步或空）。
- 每步必须能由 `group_id` 在 `card_mask` 中找到对应牌组；出完一步后 **重算** 余牌 `play_sequence`（滚动规划，非整副锁死）。

### 1.3 `SprintBelief`（记忆模块输出，`game_state["_sprint_belief"]`）

```python
@dataclass
class SprintBelief:
  # 单张
  my_single_is_field_max: Dict[str, bool]      # rank -> 任一敌均不能压
  enemy_can_beat_single: Dict[int, Dict[str, bool]]  # seat -> rank -> bool
  probe_single_rank: Optional[str]             # 建议探路的最小非核散单

  # 三带二
  enemy_can_beat_twt: Dict[int, Dict[str, bool]]     # seat -> trip_rank
  any_enemy_can_beat_twt: Dict[str, bool]              # trip_rank -> bool
  enemy_twt_unlikely: Dict[int, bool]                  # 牌路弱点 + MEM-M04 三头耗尽

  # 炸
  enemy_bomb_risk_on_lead: float                       # 领出被炸综合概率
  my_bomb_beats_field: bool                            # 我最大炸是否场上顶

  # 残局张数
  enemy_min_remaining: int
  enemy_any_remaining_eq_1: bool
```

**实现落点**：`RuleCardCounter.get_sprint_belief(game_state, my_hand, active_plan)` — 聚合现有 API，不重复算牌：

- `can_opponent_form_type(seat, "Single", rank)` → `enemy_can_beat_single`
- `can_opponent_form_type(seat, "ThreeWithTwo", trip_rank)` → `enemy_can_beat_twt`
- `get_type_route_signal()` + `seat_unlikely_form_type(seat, "ThreeWithTwo")` → `enemy_twt_unlikely`
- `get_head_bomb_signal()["twt_trip_ranks_depleted"]` → TWT 主三张上限
- `EndgameDecider._seat_may_hold_single_above` **逐步迁出** 到 `RuleCardCounter`（避免双真源）

---

## 2. 组牌层：`_plan_play_order()`

### 2.1 输入 / 输出

- **输入**：`GroupingPlan`（已枚举的 bombs/TWT/straights/singles…）、`cur_rank`
- **输出**：`List[PlayStep]`，长度 = `num_rounds()` 或残局截断为 `min(num_rounds, 4)`

### 2.2 排序启发（仅结构，不看敌情）

**优先级（残局 ≤10 张时启用完整序；中局可只生成前 2 步）**：

1. **连环 TWT**（advanced_05）：按 trip 点数从大到小，pair 配子优先小对 → `[TWT/K, TWT/A, …]`
2. **钢板 / 三连对**（GUA-174：两手 sprint 时优先于 TWT）
3. **顺子 / 同花顺**
4. **独立 TWT**（非连环）
5. **三张 / 对子**
6. **散单**（从小到大，**标记** `step_role=probe`）

**衔接规则**（手数间牌型衔接，ISSUES 原 §②）：

- 若 plan 含 `trip_T + pair_KK` 与 `trip_AAA + pair_66`，序列为先 `ThreeWithTwo/T` 再 `ThreeWithTwo/A`（advanced_01/05）。
- 配子（wild）不单独成步；归入 TWT 的 `pair` 子组（与 GUA-273 adapter 一致）。

### 2.3 与评分的关系

- `_plan_play_order` **不改变** `GroupingPlan.score`；仅在 **同分或近似同分** 方案间，优先 `play_sequence` 更短、`recovery_score` 更高的方案（可选 Phase 2）。
- **GUA-080 冻结**：不为此调 `grouping_engine` 四维权重。

---

## 3. 记忆层：MEM-M07「冲刺门控」

### 3.1 新增技能映射

在 `PRINCIPLES_MAPPING.md` §十五 追加（实施时登记）：

| ID | 人类技能 | 引擎信号 |
|----|----------|----------|
| **MEM-M07** | 残局冲刺前：外面还有没有更大的单 / 三带二 / 炸 | `SprintBelief` 全字段 |

对应 `docs/knowledge/skills/04_common_skills/05_memory_skills.md` §三记炸弹 + §残局：推定外面无炸再冲刺 → `enemy_bomb_risk_on_lead`。

### 3.2 API 草案

```python
# rule_card_counter.py
def get_sprint_belief(
    self,
    game_state: dict,
    *,
    probe_single_candidates: List[str],
    twt_trip_ranks: List[str],
) -> SprintBelief: ...
```

**调用时机**：`decide()` 内组牌完成后、残局 Q0 之前；`actions` 每步更新后 **失效重算**。

### 3.3 关键判定（须 pytest 单测）

| 问题 | 记忆回答 | 数据来源 |
|------|----------|----------|
| 我出 `Single/T` 会不会被压？ | `not my_single_is_field_max["T"]` | `can_opponent_form_type` × 4 席 |
| 敌是否还可能 `ThreeWithTwo` 压我的 `ThreeWithTwo/K`？ | `any_enemy_can_beat_twt["K"]` | 三头 copy 计数 + 牌路弱项 |
| 敌是否「接不住 TWT」？ | `any(enemy_twt_unlikely.values())` | GUA-238 弱点 + `unlikely_form_types` |
| 敌是否报单？ | `enemy_any_remaining_eq_1` | `numofplayers` / `publicInfo.rest` |

---

## 4. 决策层：`SprintStepPicker`（末段 TWT vs 单）

### 4.1 挂载点

```
EndgameDecider._q0_self_sprint()
  └─ SprintStepPicker.pick_lead_step(game_state, play_sequence, sprint_belief, action_list)
       → Optional[Tuple[idx, action]]  # 命中则 Q0 return
```

中局（`num_rounds<=3` 且非残局激活）可选：`stage_main_attack_lead` 领出前读 `play_sequence[0]` 作 **软引导**（Phase 3，非硬覆盖 GUA-116）。

### 4.2 领出决策树（定音）

```text
输入: play_sequence[], sprint_belief, hand_cards, enemies[]

① 若 len(play_sequence)==1 或 Q0.5 一手清成立
   → 出 play_sequence[0]（类型不限）

② 若 len(play_sequence)>=2 且两手 sprint
   令 A = play_sequence[0], B = play_sequence[1]
   若 A 为整牌 (TWT/钢板/三连对/顺/炸) 且 B 为收尾
      2a. 若 enemy_any_remaining_eq_1
          → 优先 A 为整牌（GUA-110；禁先小单送敌报单）
      2b. 若 A 为 TWT 且 any_enemy_twt_unlikely
          → 出 A（GUA-238）
      2c. 若 A 为 Single(probe) 且 my_single_is_field_max[rank]
          → 出 A（探路成功预期；GUA-168 炸弹+单）
      2d. 若 A 为 Single 且 NOT my_single_is_field_max[rank]
          且 B 为 TWT 且 NOT any_enemy_can_beat_twt[trip]
          → 改序：先 B（TWT）后 A（单）   # 避免先单被压后 TWT 卡死
      2e. 若 A 为 Single 且 NOT my_single_is_field_max
          且 enemy_bomb_risk_on_lead 低
          → 仍出 A（探路）；跟压路径由 GUA-125 保 sprint
      2f. 若 trips_wild_single 五张模式（GUA-273）
          若 enemy_min_remaining==1 → B=TWT 一手清
          若 enemy_min_remaining>1 → A=非三头最小散单，再 Bomb/TWT

③ 若 play_sequence 为空或门控全失败
   → return None（交现有 Q0 启发 / GUA-273 等兜底，逐步删除）

④ 跟压（greaterPos 有效）
   → 不跑此树；走 Q1 + GUA-125 sprint-preserving
```

### 4.3 滚动重规划

每执行一步后：

1. 更新 `handCards` / `numofplayers` / `MemoryTracker`
2. 若 `play_sequence[0]` 已打出 → `pop(0)` 或 **全量重跑** `_plan_play_order`（推荐后者，防结构变化）
3. 若敌 **炸弹截胡** 且 `plan_b_sequences` 非空 → 切 Plan B（Phase 4）

---

## 5. 消费链（`decide()` 改造摘要）

```text
_run_grouping_engine()
  → best_plan.play_sequence = _plan_play_order(best_plan)
  → game_state["_active_play_sequence"] = play_sequence
  → game_state["_sprint_belief"] = rule_counter.get_sprint_belief(...)

EndgamePreprocessor → should_sprint
EndgameDecider Q0
  → SprintStepPicker.pick_lead_step(...)   # 新增
  → 未命中则现有 _q0_* 链（逐步瘦身）

_recommend_play() 领出
  → 若 _active_play_sequence 且 stage in (stage_2, stage_3)
     软匹配 play_sequence[0]（_match_actionList）
```

**trace 字段**（GUA-098 对齐）：`play_sequence_head`、`sprint_belief_summary`、`sprint_picker_branch`（2a–2f）。

---

## 6. 分阶段实施（建议顺序）

| 阶段 | 内容 | 关单局部 |
|------|------|----------|
| **P0** | `PlayStep` + `SprintBelief` + `get_sprint_belief()` + pytest 记忆门控 ≥8 case | 记忆 API 单测绿 |
| **P1** | `_plan_play_order()` + `GroupingPlan.play_sequence` + advanced_01/05 结构用例 ≥6 | 组牌序列单测绿 |
| **P2** | `SprintStepPicker` 接入 Q0 + 收敛 GUA-238/273/168 领出分支 | 残局构造 pytest ≥10 |
| **P3** | `_recommend_play` 领出软消费 `play_sequence[0]` | stage_2 冒烟 |
| **P4** | `plan_b_sequences`（被炸后重规划） | 可选，不挡 P2 关单 |

**P3/P4 落地（2026-08-25）**：`try_soft_lead_from_play_sequence`（`num_rounds≤3` 且 `len(hand)>10`）接 `stage_main_attack_lead`；`_build_plan_b_sequences` + `_maybe_switch_play_sequence_plan_b` 敌 Bomb/SF 截胡后切 plan_b。pytest `test_gua077_p3_p4.py` **5/5**；GUA-077 合计 **26/26** ✅。

**依赖**：GUA-075 主路径稳定（已具备）；**不依赖** NN 重训。

---

## 7. pytest 清单（最低）

### 7.1 组牌 `tests/test_gua077_global_planning.py`

| Case | 手牌要点 | 期望 `play_sequence` |
|------|----------|----------------------|
| advanced_01 | 10 张，两手 TWT 走完 | `[TWT/x, TWT/y]` 长度 2 |
| advanced_05 | 11 张，三手连环 TWT | 长度 3，trip 降序 |
| steel+sprint | 钢板+单（GUA-174） | 钢板在 TWT 前 |
| bomb+single | 炸+单（GUA-168 结构） | `[Single, Bomb]` 序 |
| trips_wild_single | 444+H2+DT（GUA-273） | `[Single/DT, TWT/4]` 或 `[Bomb/4]` 视结构 |
| one_hand | 5 张 TWT | 长度 1 |

### 7.2 记忆 `tests/test_gua077_sprint_belief.py`

| Case | 设定 | 期望 |
|------|------|------|
| field_max_single | 敌 A/K 已出尽 | `my_single_is_field_max["T"]==True` |
| enemy_has_twt | 敌未出 T、外剩 ≥3 张 T | `any_enemy_can_beat_twt["K"]` 视牌池 |
| twt_weakness | 敌对 TWT PASS×2 | `enemy_twt_unlikely[seat]==True` |
| head_bomb_depleted | 4 张 A 已出 | trip A 不可作敌 TWT 主三张 |

### 7.3 集成 `tests/test_gua077_sprint_step_picker.py`

| Case | 信念 | 期望首出 |
|------|------|----------|
| 2b GUA-238 | twt_unlikely | ThreeWithTwo |
| 2c GUA-168 | 单最大 | Single |
| 2d 先单被压 | 单不最大、TWT 安全 | ThreeWithTwo |
| GUA-273 敌=1 | `enemy_min_remaining==1` | ThreeWithTwo |
| GUA-273 敌>1 | `enemy_min_remaining>1` | Single（非三头点） |

---

## 8. 关单条件（GUA-077 整体）

| # | 条件 |
|---|------|
| 1 | `GroupingPlan.play_sequence` 上线，advanced_01/05 pytest ≥6 pass |
| 2 | `get_sprint_belief()` + `SprintStepPicker` 上线，§7.2+7.3 ≥18 pass |
| 3 | Q0 领出命中 `sprint_picker_branch` 可追溯（日志或 GUA-098） |
| 4 | GUA-238/273/168 **领出** 路径无重复特判（grep 仅保留 picker 内） |
| 5 | V8 Botzone 9 局 KPI **环比不下降**（与 GUA-234 阶段 F 同护栏） |

**不作关单**：整副 27 张开局全程按 `play_sequence` 机械执行；中局完整 MCTS。

---

## 9. 非目标（本 GUA 不做）

- 对手完整手牌贝叶斯推断（V5+ / BC 训练）
- 开局 27 张一次性排完 10+ 步剧本
- 修改 `grouping_engine` 评分权重（GUA-080 冻结）
- 用 `play_sequence` 绕过 `actionList` / Guard / 组牌一致性过滤

---

## 10. 复现与调试

```bash
# 组牌序列（实施后）
python scripts/checks/check_grouping_engine.py --hand "<cards>" --rank 2 --show-play-sequence

# 残局步序 + 信念 trace（实施后扩展）
python scripts/checks/check_endgame_agent.py --hand "<cards>" --rest 3,8,5,7 --trace-sprint-belief
```

---

## 11. 关联文档

- `docs/knowledge/skills/04_common_skills/05_memory_skills.md` — MEM-M07 残局冲刺信念
- `docs/guandan-brain/issues/GUA-125-completion.md` — sprint 定义与跟压 preserving
- `docs/guandan-brain/issues/GUA-080-completion.md` — 组牌参数冻结
- `docs/guandan-brain/PRINCIPLES_MAPPING.md` §十五 — 记牌技能索引
