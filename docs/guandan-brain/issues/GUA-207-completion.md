# GUA-207 被动跟压保留炸弹，先用散牌（含级牌）压制 — 细案

> 登记：2026-08-06 · 状态：修复已实现，待 commit/重启监听/实局验证
> 对局：match `6a74236927e7bf01db12f002`（2026-08-06 14:02:57）
> 日志：`logs/v8_vs_botzone_20260806_134921.log` L493-500

## 一、场景复现

残局 V8 手牌 6 张：

```
[D5, H5, H5, C5]  ← 四星炸 5
[D2]              ← 级牌（curRank=2）
[SJ]              ← 单 J
```

2 号（player1）出 `Single/Q ['HQ']`，actionList 仅 3 项：

```
{PASS:1, Single:1, Bomb:1}   ← Single 即 D2，能压 Q
```

## 二、决策链（修复前）

`endgame_decider` → `Q0 自己冲刺`，出牌权不在我手 → 被动分支：

```
_q0_passive_sprint_vs_enemy_control
  └─ _select_two_turn_sprint_structure
       手牌 = 炸(4张) + D2 + SJ = 3 份，非「两手」 → 返回 None
        ↓
   if bombs:
       return self._select_best_bomb(bombs, action_list)   ← 盲目出最大炸
        ↓
   决策：Bomb/5 ['D5','H5','H5','C5']
```

结果：3 号用 `Bomb/J` 反压，V8 剩 `D2、SJ` 两张散单彻底失去控制权。

## 三、根因

`_q0_self_sprint` 被动分支在两手冲刺规划失败后**无条件 `_select_best_bomb`**，
缺少「用散牌先压、保留炸弹回手」的护栏。

仓库已有**领出侧**同类修复（GUA-168，`endgame_decide.py:1441-1469`）：
> 领出时 [bomb + 单张] 且对手两家均非 1 张 → 先出单试探、炸留作回手（skip_gua151）

但**被动跟压侧无对应逻辑**，这正是本缺陷的缺口。

## 四、修复方案

新增 `_q0_passive_keep_bomb_play_scatter(game_state, action_list, ec)`：

| 条件 | 行为 |
|------|------|
| 跟压敌方控牌（`_is_q1_following_enemy_control`） | 否 → None（落回原逻辑） |
| greater 为散牌型（`Single`/`Pair`） | 否 → None |
| 敌未报单（所有敌人 remaining != 1） | 否 → None（报单时用散牌会被直接接走） |
| actionList 中存在非炸弹类 Single/Pair 且能压 greater | 无 → None |
| 命中以上全部 | 选**最小可压散牌**（`_min_card_value` 升序，级牌优先留大牌作冲刺） |

插入点：`_q0_self_sprint` 被动分支，`_q0_passive_sprint_vs_enemy_control` 返回 None
之后、`_select_best_bomb` 之前。

复现局修复后行为：出 `D2`（Single/2）压 Q，保留 `Bomb/5` 作回手冲刺。

## 五、验证

- 新增 `tests/test_gua207_passive_keep_bomb_play_scatter.py` 5 用例全绿：
  1. 复现局（Bomb/5 + D2 + SJ vs Single/Q）→ 出 `D2` 保留 Bomb
  2. greater=Pair + 手含 Pair → 出 Pair 保留炸
  3. 敌报单（remaining==1）→ 不适用，落回出炸
  4. 无散牌可压（仅炸弹）→ 落回出炸
  5. greater 非散牌型（ThreeWithTwo）→ 不触发，落回出炸
- 回归：`test_gua202/205/206/207 + test_gua134` 43 用例全绿
- 全量 `-k "endgame or gua or decision..."`：改动后失败集与基线（去除 GUA-205
  stash 影响）**完全一致**，无新增回归（既有 19 失败均为 M3/V7 环境依赖，与本次无关）

## 六、影响面

- 仅影响 `_q0_self_sprint` 被动分支中「两手冲刺失败 + 有炸弹」的路径
- 领出侧 GUA-168、两手冲刺 `_select_two_turn_sprint_structure`、Q1 封锁逻辑均不受影响
- 敌报单/无散牌可压/非散牌型 greater 场景全部落回原逻辑，无行为回退

## 七、待做

1. commit（GUA-207 范围）
2. 重启 WF-14 监听（若本轮 commit 不涉及监听脚本则无需重启，仅需观察新对局）
3. 实局/批跑验证：复现局 L493-500 场景应改出 `Single/2 (D2)` 而非 `Bomb/5`
4. 观察队胜率 `v8-win-rate-history.md` 环比

## 关联

- GUA-168：领出侧「先出单试探、炸留作回手」，本 issue 为**被动侧镜像**
- GUA-206：完整同花顺/炸弹不判拆核心（同为残局火力浪费类，已修）
