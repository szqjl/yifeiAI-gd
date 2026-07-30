# GUA-188 完成定义

> **GUA-188**：`_q1_counter_enemy_bomb` 硬阈值 >5 导致对手剩 6 张时不反压；组牌 8 张时选 Bomb/A 而非 Clubs SF
> **登记**：2026-07-30
> **严重级别**：P1
> **关联**：GUA-078（残局管线）、GUA-142（Q1 封锁）、GUA-115（火不打四）、`src/v/nn/endgame/endgame_decide.py` L1881 `_q1_counter_enemy_bomb`、`src/v/nn/features/grouping_engine.py` `_score_power`

---

## 1. 问题描述

WF-12 复盘 `20260730125841692070 [yf1_v8]-[opponent_1_3]-[2]-[2].json` 发现两处问题：

### 1.1 `_q1_counter_enemy_bomb` 硬阈值跳过

step 33 对手@3 出 `Bomb/Q [HQ,SQ,CQ,HQ]` 剩 6 张，yf1 手牌 `[C7, CJ, CT, DA, H4, H4, HA, SA]` 可组：
- **Bomb/A** `[H4,H4,HA,SA,DA]`（反压 Bomb/Q）
- **Clubs SF** `[C7, H4→8♣, H4→9♣, CT, CJ]`

但 `_q1_counter_enemy_bomb`（`endgame_decide.py:1881`）首行：
```python
if main_enemy.get("remaining", 99) > 5:
    return None  # ← 敌剩 6 > 5 → 直接跳过
```
硬阈值让整条反压路径不可达，即使有合法 Bomb/SF 可压也不出。

### 1.2 组牌引擎 8 张选 Bomb/A 而非 Clubs SF

同一 8 张手牌，组牌引擎产两组竞争方案——Bomb/A（+2 分）vs Clubs SF（+3 分），引擎选前者。后续 3 张 Ace 都锁定在 Bomb 核心组，单张 Ace 被 `_group_consistency_filter` 保护过滤，导致 step 37（敌剩 5）→ step 47（敌剩 3）持续 PASS。

### 1.3 Q3 炸只在敌剩 2 张才触发

step 49 对手剩 2 张才落到 Q3 `_should_bomb(5)` 判定 `True`。敌 4 张时 `_q1_gua115_fire_no_bomb_four_pass` 有非炸候选跳过；敌 3 张时 `_will_lose(rem=3)=True` 但 `_should_bomb=can_clear AND will_lose` 已满足，被 Q1 推荐型路径抢先拦截未落 Q3。

### 1.4 炸后无 SF 冲刺（属预期行为）

Bomb/A 消耗 5 张后手剩 `[C7, CT, CJ]`（3 杂花单），不可能组 SF。初始 Hearts SF 组件在步骤 13/17 的 Straight 推荐中被拆散使用。

---

## 2. 修复方案

### 2.1 删除 `_q1_counter_enemy_bomb` 硬跳过

`endgame_decide.py:1880` 去除 `remaining > 5` 门：

```python
# 删前：if main_enemy.get("remaining", 99) > 5: return None
# 删后：直接进入 _is_q1_following_enemy_control 继续执行
```

### 2.2 删除 `should_allow_counter_bomb_core_exempt` 硬跳过

`endgame_decide.py:636` 去除 `>5` 门（两处同频修复）：

```python
# 删前：if enemy_rem is None or enemy_rem > 5 or enemy_rem < 1: return False
# 删后：if enemy_rem is None or enemy_rem < 1: return False
```

### 2.3 `_bomb_min_sufficient_key` SF 延后键

`endgame_decide.py:793-808` 新增 `has_non_sf_bomb` 检测 + SF 延后键排序首项：

```python
has_non_sf_bomb = any(
    _get_declared_action_type(item) not in ("StraightFlush", "STRAIGHT_FLUSH")
    for item in bomb_items
)

def _bomb_min_sufficient_key(item):
    ...
    is_sf = act_type in ("StraightFlush", "STRAIGHT_FLUSH")
    return (
        1 if (is_sf and has_non_sf_bomb) else 0,  # ← 有非SF替代时SF垫底
        1 if split_orphan else 0,
        len(cards),
        wild_count,
        _max_card_value(act, cur_rank),
    )
```

**效果**：actionList 同时有普通炸弹和 SF 都可反压时，普通炸弹排前（省 SF）；只有 SF 可反压时 SF 正常排前（不延后）。

---

## 3. 验收

### 3.1 pytest

| # | 用例 | 期望 |
|---|------|------|
| ① | `_q1_counter_enemy_bomb` 敌剩 6 + actionList 有 Bomb/SF | 返回非 None（推荐 Bomb/SF） |
| ② | `_q1_counter_enemy_bomb` 敌剩 6 + actionList 无 Bomb/SF | 返回 None（同原行为） |
| ③ | `_q1_counter_enemy_bomb` 敌剩 5 + actionList 有 Bomb/SF | 返回非 None（原行为不变）|
| ④ | 组牌 8 张含 Clubs SF 候选 | SF 优先级 > Bomb（同分或更高分） |

### 3.2 端到端

- yf1 step 33 不再 PASS → 出 Bomb/A 或 Clubs SF 反压 Bomb/Q
- yf1 step 37-47 不再持续 PASS

### 3.3 回归

- `test_gua142_q1_block_enemy.py` 全 pass（Q1 封锁逻辑不受影响）
- `test_gua078_endgame_preprocessor` 全 pass
- V8 批跑队胜率不退化

---

## 4. 进度

- [ ] `_q1_counter_enemy_bomb` 阈值调整
- [ ] `grouping_engine.py` SmallHand SF 加分
- [ ] Q1→Q3 兜底加固
- [ ] pytest 用例
- [ ] 净盘 V8 批跑队胜率验收

---

## 5. KPI 锚点（修前后对照预期）

| 指标 | 修前 | 修后预期 |
|------|------|---------|
| yf1 step 33（敌 6 张 Bomb/Q） | PASS | Bomb/A 或 SF 反压 |
| yf1 step 37-47（敌 5→3 单走） | 持续 PASS | 至少 1 次拦截 |
| 队胜率 | 基线 | ≥ 修前 |
| `_q1_counter_enemy_bomb` 命中率 | 6+ 张跳过 | 所有剩余张数均可评估 |
