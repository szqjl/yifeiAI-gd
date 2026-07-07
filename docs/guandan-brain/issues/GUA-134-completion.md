# GUA-134 完成定义：C3 / C5 / C6 yf2 自闭合（高闭合率三手清空）

> **状态**：draft（2026-07-07 待登记）  
> **WF-12 锚点**：game_records_v7/20260706222548831117 [yf1_v7]-[opponent_1_3]-[10]-[2].json 步 **51/89**  
> **关联**：[GUA-125-completion.md §0.5.2](GUA-125-completion.md) C3/C5/C6 行；GUA-131（C1）；GUA-132（C2）；GUA-133（C4）

---

## 1. 牌理基础

| 情形 | @1 finish 牌型 | @1 圈 1 反应 | yf2 圈 1 必选 |
|------|----------------|--------------|--------------|
| **C3** | 顺子（杂牌）| 顺子杂牌通道**不能跨型压 TWT** §4.4 → @1 必 PASS | **跟 777+22 夺权** |
| **C5** | 更小 TWT（finish 点 < 7）| 同型互压，finish 点 < yf2 TWT 点 → @1 必 PASS | **跟 777+22 夺权** |
| **C6** | 5 张散（非整牌型）| 散牌不能压整牌 TWT → @1 必 PASS | **跟 min TWT 夺权** |

**共同特征**：
- @1 finish **不能跨型 / 不能同型** 压 yf2 跟的 TWT（§4.4 杂牌同型）
- yf2 圈 1 跟 min TWT → @1 必 PASS → yf2 圈 2 必领出
- 闭合路径 = **yf2 自闭合三手清空**（高闭合率，不依赖 yf1 记忆）

---

## 2. yf2 自闭合路径（终版）

```
C3/C5/C6：@1 出 5 张 TWT + finish = 杂牌（顺子 / 更小 TWT / 5 张散）
yf2 圈 1：跟 min TWT（777+22 或 888+22）

圈 1 闭环：
  @1 (TWT) → yf2 (TWT) → @3 PASS → yf1 PASS → @1 PASS（finish 不能压 TWT）

圈 2：yf2 领出（@1 圈 1 末没出牌）
  yf2 6J → @3 PASS → yf1 PASS → @1 PASS（不能跨型压 bomb family 杂牌通道 §4.4）

圈 3：yf2 继续领出（@3 圈 2 末没出牌）
  yf2 777+888 三连对 → @3 PASS → yf1 PASS → @1 PASS

圈 4：yf2 继续领出
  yf2 22 对 → @3 PASS → yf1 PASS → @1 PASS

yf2 头游（三手清空 + 一手对 = 4 圈清空）✓
```

**闭合条件**：
- yf2 圈 2 出 6J 后 @3 / yf1 / @1 不能压 6J（无更大 bomb family）
- yf2 圈 3 出 777+888 三连对后三家不能压（同型更大三连对 / 钢板 / bomb family）
- yf2 圈 4 出 22 对后三家不能压（无更大对 / bomb family）

---

## 3. C3 / C5 / C6 真实决策树

### 3.1 共同 yf2 圈 1 动作 = 跟 min TWT

```
yf2 圈 1 决策：
├─ 跟 min TWT（777+22 或 888+22）★ ★ ★
│   ├─ @1 PASS（finish 不能跨型 / 不能同型压 TWT §4.4）
│   ├─ @3 PASS（保护队友，但 @1 已 PASS）
│   ├─ yf1 PASS（队友不接力）
│   └─ 圈 2 yf2 领出 6J → 三手清空闭合
│
├─ 出 6J bomb family
│   ├─ @1 不能压 6J（无 bomb family，杂牌 finish）→ @1 PASS
│   ├─ 但 @1 圈 2 必出 finish → yf2 失去出牌权（接力失败）❌
│   └─ @1 finish = 杂牌 → @1 圈 2 一手清 → @1 头游
│
└─ PASS 蓄力
    └─ @1 圈 2 领出 finish → @1 一手清 → @1 头游 ❌
```

**C3/C5/C6 闭合路径统一**：
- 必出 **min TWT**（777+22 或 888+22）
- 闭合路径明确：**yf2 自闭合三手清空**，不依赖 yf1
- 闭合率**高**（仅当 yf2 没有 6J / 三连对 / 对 时才退化）

---

## 4. 关键判定函数

### 4.1 _c3_c5_c6_decision(game_state, action_list, ec, ctx)

```python
def _c3_c5_c6_decision(self, game_state, action_list, ec, ctx):
    """
    C3/C5/C6 决策：yf2 圈 1 跟 min TWT 形成冲刺能力，等 yf2 圈 2 领出自闭合。

    @1 finish ∈ {Straight(杂牌), 更小 TWT, 5 张散}
    yf2 圈 1 必跟 min TWT → @1 必 PASS → yf2 圈 2 必领出 → 三手清空闭合。
    """
    if not ctx:
        return None
    cur_rank = str(game_state.get("curRank", "2"))
    twt = self._find_twt_min_point(action_list, cur_rank)
    if twt is not None:
        logger.info("GUA-134 C3/C5/C6: 跟 min TWT 夺权，三手清空闭合")
        return twt
    # 兜底：无可跟 TWT → PASS（@1 必头游）
    return self._find_pass_action(action_list)
```

**调用点**：
- `_q1_block_enemy` ④ 与 ⑤ 之间，**与 GUA-131/132/133 同位**
- 仅在 C3/C5/C6 上下文触发（@1 finish 是杂牌 / 更小 TWT / 散牌）

### 4.2 _is_c3_c5_c6_scenario(game_state, ec) -> Optional[Dict]

```python
def _is_c3_c5_c6_scenario(self, game_state, ec):
    """
    探测 yf2 当前是否落在 C3/C5/C6。

    触发条件：
      - 当前 greaterAction 是 5 张 TWT
      - greaterPos 是 yf2 上家/下家（@1）
      - @1 remaining ∈ {5, 6}（5 张 = @1 报 5 张 finish 含 5 张；6 张残局）
      - yf2 整手 ≥ 10 张
      - yf2 属于跟压（greaterPos != my_pos）
    返回 ctx dict 或 None
    """
```

**与 C1/C2/C4 探测的区别**：
- C1/C2/C4：@1 finish 是 bomb family（更大 TWT / SF / 5+ 炸）
- **C3/C5/C6：@1 finish 是杂牌 / 更小 TWT / 散牌**

判别逻辑：finish_kind == "twt" 且 greater_action_rank < yf2_twt_rank → C5
         finish_kind == "straight" → C3
         finish_kind == "scatter" → C6

---

## 5. 调用流程（C3/C5/C6 锚点步 51/89 修复路径）

```
@1 出 333+22（5 张 TWT）
  ↓
_q1_block_enemy 触发
  ├─ ① _q1_hold_teammate_max_control（队友控牌才走）
  ├─ ② _q1_finish_now_candidate（自己能清才走）
  ├─ ③ _q1_gua115_fire_no_bomb_four_pass
  ├─ ④ _q1_counter_enemy_bomb（GUA-123）
  ├─ ④.5a _q1_c1_c2_c4_dispatch（GUA-131/132/133） — C1/C2/C4 命中即返回
  ├─ ④.5b _q1_c3_c5_c6_dispatch（GUA-134）        — C3/C5/C6 命中即返回 ★新增
  ├─ ⑤ _q1_enemy_five_single_special
  └─ ⑥ 推荐类型过滤 → 通用排序 → 选炸
```

---

## 6. 停手条件 / 完成定义

**GUA-134 关单须满足**：

1. ✅ `_q1_c3_c5_c6_dispatch` + `_c3_c5_c6_decision` + `_is_c3_c5_c6_scenario` 在 `endgame_decide.py` 实现
2. ✅ 挂载在 `_q1_block_enemy` ④ 与 ⑤ 之间（与 GUA-131/132/133 并联）
3. ✅ pytest：`tests/test_gua134_c3_c5_c6.py` 全绿
4. ✅ 回归：GUA-131/132/133 + GUA-123 + GUA-122 仍绿
5. ✅ ITERATIONS 末追加：`v7-gua134-c3c5c6-implemented`

**关联 GUA**：
- GUA-125：sprint preserving（同型 min 压 + 残局整牌冲刺）
- GUA-131/132/133：C1/C2/C4 决策
- GUA-110/111：残局 Q1 整牌冲刺 / 同型通道
- WF-12：决策溯源

---

## 7. 不做 / 后续

**本 GUA 不做**：
- C3/C5/C6 各自的微调（C3 顺子 finish 还需校验 @1 是否真有顺子）
- yf2 圈 2 领出 6J 后 @3 / yf1 拦截能力评估（C1 路径 A 的镜像问题，留 GUA-135）
- 双进优先级判定（C2/C4 接受 @1 头游后的 yf 队整体策略，留 GUA-135）

**后续 GUA**：
- **GUA-135**：`_q1_double_second_priority` 双进优先级判定（C2/C4 接受 @1 头游 + C3/C5/C6 闭合后队整体策略）
- **GUA-136**：`_estimate_teammate_hand` 队友手牌估计增强（yf1 接力闭合 C1/C4 依赖）