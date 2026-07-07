# GUA-131 完成定义：C1 队友协作冲刺 + bomb family 判别接口

> **状态**：draft（2026-07-07 待登记）  
> **WF-12 锚点**：game_records_v7/20260706222548831117 [yf1_v7]-[opponent_1_3]-[10]-[2].json 步 **51/89**  
> **关联**：[GUA-125-completion.md §0.5.1](GUA-125-completion.md) C1 决策树；GUA-065（R07-R09 队友保护）；GUA-123（敌方冲刺）

---

## 1. 现象（可复现）

| 步 | 谁 | 动作 | 备注 |
|----|-----|------|------|
| 50 | @1 | 333+22（5 张 TWT）| @1 余 finish 5 张 = 更大 TWT（点 > 7）|
| **51** | **yf2** | **JJJJJJ 6J（bomb family）** | **败招**：应跟 777+22 / 888+22 形成冲刺能力 |
| 52–54 | yf1 / @3 / @1 | PASS / 同型压回 | @1 finish 同型压 yf2 777+22 路径未触发 |
| ... | ... | ... | 队友 yf1 未拦截 @1 finish，yf 队丢头游 |

**步 51 决策证据**（my_decisions / trace）：

- handCards（14 张）：JJJJJJ + 777 + 888 + 22
- ctionList_size=N：含 PASS + JJJJJJ + 777+22 + 888+22 + ...
- greaterPos=@1，greaterAction=ThreeWithTwo/3
- layer=GUA-075推荐，intent=block_with_bomb_like，stage=stage_2
- group_type_map：omb / three_with_two / pair / trips

**应做**：跟 777+22 或 888+22 形成冲刺能力（剩 2 手 = 炸弹 + 单手），由队友 yf1 接力拦截 @1 finish。

---

## 2. 根因（三层）

### 2.1 C1 决策缺失队友视角

- **当前**：ndgame_decide._q1_block_enemy 走 _filter_by_recommended_types → 通用排序 → lock_with 命中 omb-like → 出 6J。
- **缺失**：没有「队友视角」决策树——yf2 没有评估 yf1 拦截 @1 finish 的能力。
- **理论**：C1 中 yf2 单独不能闭合冲刺；闭合必须由 yf 队（yf1+yf2）联合完成（见 GUA-125 §0.5.1）。

### 2.2 _select_two_turn_sprint_structure 只看自己 sprint

- 当前实现（ndgame_decide.py 行 1661-1720）：
  `python
  def _select_two_turn_sprint_structure(self, structured, candidates, game_state, ec):
      """仅剩两手时，优先选择能先手冲刺的整牌型。"""
      # 1. 自己手牌校验
      # 2. residue 整牌型判定（第二手是否能闭合）
  `
- **缺失**：
  - 不校验「圈 1 跟 TWT 后剩 2 手 = 冲刺能力」（仅看自己手牌剩 2 手）
  - 不评估 yf1 是否有拦截 @1 finish 的能力
  - 不返回「跟 TWT 形成冲刺能力 + 队友接力闭合」的复合动作

### 2.3 bomb family 判别缺失

- 当前 _is_bomb_like_action 只判别 Bomb（4+ 张同点炸），不含：
  - StraightFlush（同花顺 = bomb family 一员，§4.1）
  - 王炸（最大炸弹家族）
- **缺失**：_is_bomb_family() 统一判别 bomb 家族（含 Bomb + StraightFlush + 王炸），用于：
  - yf1 拦截 @1 finish 时的「bomb family 跨型压杂牌 TWT」判定
  - @3 是否能压 yf2 6J 的判定

---

## 3. 接口定义

### 3.1 _is_bomb_family(action: List) -> bool

**作用**：判别一手牌型是否属于 bomb family（含 Bomb / StraightFlush / 王炸）

**实现要点**：

`python
def _is_bomb_family(action: List) -> bool:
    """
    判别 action 是否属于 bomb family
    bomb family = Bomb (4+ 同点) + StraightFlush (同花顺) + 王炸
    见 GUA-125-completion §0.0 / §4.1
    """
    if not action or len(action) < 2:
        return False
    atype = get_action_type(action)
    if atype == ACTION_TYPE_BOMB:
        return True
    if atype == ACTION_TYPE_STRAIGHT_FLUSH:
        return True
    # 王炸：两个王
    cards = _get_cards(action)
    if len(cards) == 2 and set(cards) == {"SJ", "BJ"}:  # 大小王
        return True
    return False
`

**调用点**：

- _rule_r07_teammate_yield：判断队友出的「炸」是否跨型可压
- _q1_hold_teammate_max_control：队友控牌时 yf2 不压除非残局冲刺
- GUA-131 _c1_decision：yf1 拦截能力评估（是否有 bomb family）
- GUA-123 _q1_counter_enemy_bomb：敌方冲刺反炸阈值评估

### 3.2 _c1_decision(game_state, action_list, ec) -> Optional[Tuple[int, List]]

**作用**：C1 情形下 yf2 圈 1 决策（队友视角）

**输入**：

- game_state：当前牌局状态（含 handCards / curRank / greaterPos 等）
- ction_list：候选动作列表（含 PASS / TWT / bomb family / 杂牌等）
- c：决策上下文（含 my_pos / numofplayers / enemies 等）

**输出**：最优动作 (idx, action) 或 None

**决策树**（见 GUA-125 §0.5.1）：

`python
def _c1_decision(self, game_state, action_list, ec):
    """
    C1 决策（队友视角）：
    @1 出 333+22（5 张 TWT）→ yf2 整手 14 张 = JJJJJJ+777+888+22
    阵营：@1+@3 (lalala队) vs yf1+yf2 (v7队)

    返回：
    - 'follow_twt_sprint_capability'：圈 1 跟 777/888+22，剩 2 手 = 冲刺能力，等 yf1 拦截
    - 'play_6j_self_rescue'：圈 1 出 6J，圈 2/3 三手清空（yf2 自救）
    - 'pass_lose'：圈 1 PASS 必败（@1 finish 必出头游）
    """
    # 1. 判定 C1 场景
    if not self._is_c1_scenario(game_state, ec):
        return None

    my_pos = ec.get('my_pos', 0)
    teammate = (my_pos + 2) % 4  # 队友位置
    numofplayers = ec.get('numofplayers', [])

    # 2. 校验 yf1 拦截 @1 finish 的能力
    @1_finish = self._extract_enemy_finish(game_state, ec)
    yf1_hand_estimate = self._estimate_teammate_hand(ec, teammate)
    yf1_can_intercept = (
        self._has_bomb_family_in_hand(yf1_hand_estimate) or
        self._has_bigger_twt(yf1_hand_estimate, @1_finish)
    )

    # 3. 校验 @3 是否能压 yf2 6J（bomb family）
    @3_hand_estimate = self._estimate_enemy_hand(ec, ...)
    @3_can_press_6j = self._has_bigger_bomb_family(@3_hand_estimate, 'JJJJJJ')

    # 4. 决策
    if yf1_can_intercept:
        # 路径 A：yf2 跟 TWT 形成冲刺能力，等 yf1 拦截
        twt_action = self._find_twt_with_min_remaining(action_list)
        if twt_action:
            return twt_action  # 'follow_twt_sprint_capability'
    elif @3_can_press_6j:
        # 路径 B 退化：yf1 不行，但 @3 也不能压 6J
        six_joker = self._find_six_joker_bomb(action_list)
        if six_joker:
            return six_joker  # 'play_6j_self_rescue'

    # 路径 C：PASS（必败）
    return self._find_pass_action(action_list)
`

**调用点**：

- _q1_block_enemy ⑤ lock_with 命中 bomb-like 前插入
- 仅在 C1 场景触发（@1 rem ≤ 8 + finish 是杂牌 TWT + yf2 整手 ≥ 10 张）

### 3.3 _has_bigger_twt(hand_estimate, finish) -> bool

**作用**：判断手牌估计中是否有 ≥finish 点 的杂牌 TWT

**实现要点**：

`python
def _has_bigger_twt(self, hand_estimate, finish):
    """
    判断 hand_estimate 中是否有 ≥finish 点 的杂牌 TWT
    用于 yf1 拦截 @1 finish（同型互压 §4.4）
    """
    if not finish or finish.get('type') != 'ThreeWithTwo':
        return False
    finish_rank = finish.get('rank_value', 0)
    for twt in hand_estimate.get('three_with_twos', []):
        if twt.get('rank_value', 0) >= finish_rank:
            return True
    return False
`

### 3.4 _sprint_capability_after_twt(hand, action) -> bool

**作用**：校验出完 action 后手牌是否具备冲刺能力（剩 2 手 = 炸弹 + 单手）

**实现要点**：

`python
def _sprint_capability_after_twt(self, hand, action):
    """
    校验出完 action 后手牌是否具备冲刺能力
    冲刺能力 = 剩 2 个整牌型 = 炸弹 + 单手（单/对/三张/三连对/三带二/钢板/顺子/同花顺/炸弹/王炸）
    见 GUA-125 §0.0b「冲刺能力」
    """
    # 1. 计算出完 action 后的剩余手牌
    remaining = self._hand_after_action(hand, action)

    # 2. 枚举所有可能的整牌型组合
    groupings = self._enumerate_valid_groupings(remaining)

    # 3. 判定：剩 2 个整牌型 = 冲刺能力
    return len(groupings) == 2 and any(
        self._is_bomb_family(g) for g in groupings
    )
`

---

## 4. 调用流程（C1 锚点步 51/89 修复路径）

`
@1 出 333+22（5 张 TWT）
  ↓
_q1_block_enemy 触发
  ├─ ① _q1_hold_teammate_max_control（队友控牌才走）
  ├─ ② _q1_finish_now_candidate（自己能清才走）
  ├─ ③ _q1_gua115_fire_no_bomb_four_pass
  ├─ ④ _q1_counter_enemy_bomb（GUA-123）
  ├─ **新增 ④.5 _c1_decision**（C1 场景触发）
  │     ├─ 校验 yf1 拦截能力
  │     ├─ 选 yf2 圈 1 动作（跟 TWT 形成冲刺能力 / 出 6J 自救 / PASS 必败）
  │     └─ 走 _is_bomb_family + _sprint_capability_after_twt 校验
  ├─ ⑤ _q1_enemy_five_single_special
  └─ ⑥ 推荐类型过滤 → 通用排序 → 选炸（**当前错误路径**）
`

---

## 5. 停手条件 / 完成定义

**GUA-131 关单须满足**：

1. ✅ 接口 _is_bomb_family / _c1_decision / _has_bigger_twt / _sprint_capability_after_twt 在 ndgame_decide.py 实现
2. ✅ _c1_decision 在 _q1_block_enemy ④ 与 ⑤ 之间调用（**不是替代**④）
3. ✅ pytest：	ests/test_gua131_c1_decision.py 全绿（含 _is_bomb_family 单元 + _c1_decision 集成）
4. ✅ 锚点回归：game_records_v7/20260706222548831117 ... 步 51/89 改为 777+22 或 888+22，**不出 6J**
5. ✅ 同 seed 同 12 局回归：净盘批跑（WF-04）后 vn 改善（队胜率或副胜率 +1pp 以上）
6. ✅ ITERATIONS 末追加：7-gua131-c1-decision-implemented

**关联 GUA**：

- GUA-065：队友识别与保护（R07-R09 已落地，但只覆盖 yf2 让道 / 送队友）
- GUA-125：sprint preserving（同型 min 压 + 残局整牌冲刺，本 GUA 是其延展）
- GUA-123：敌方冲刺反炸（已 closed，本 GUA 复用其 _is_bomb_like_action 思路但补 SF/王炸）
- GUA-110/111：残局 Q1 整牌冲刺 / 同型通道
- WF-12：决策溯源

---

## 6. 不做 / 后续

**本 GUA 不做**：

- GUA-065 队友保护的进一步强化（M3 评估"极弱"，但 V7 R07-R09 已落地）
- yf1 拦截能力的记忆模块实现（依赖 _estimate_teammate_hand 增强，留作 GUA-132 跟进）
- C2-C6 决策树扩展（每个 finish 牌型独立 GUA）

**后续 GUA**：

- **GUA-132**：_estimate_teammate_hand 队友手牌估计（基于圈序出牌历史 + 记忆模块）
- **GUA-133**：C2（同花顺 finish）决策树
- **GUA-134**：C3（顺子 finish）决策树
- **GUA-135**：C4（5 星炸 finish）决策树
- **GUA-136**：C5/C6（小 TWT / 散牌 finish）决策树