# GUA-081 完成定义

> **登记**：2026-06-28  
> **回放锚点**：`20260628091707150272` 步 6/7（@3 三带二 666+22 → yf1 四炸 8888）

## 问题 A：三带二推荐拆炸 → 回退 NN/炸

### 现象

GUA-075 `_build_three_with_two_press(strategy="min")` 优先选 **最小能压的三张**（888），与组牌 G0 炸弹冲突 → mask 保护拦截 → 整段回退 → 开局浪费 8 炸。

### 最小修复（已实施）

在 `_build_three_with_two_press` 遍历 `trip_candidates` 时，用 `_get_broken_core_type` 跳过会 **部分拆 bomb/straight_flush core** 的组合，继续尝试下一档三张（如 999+对子）。

调用方 `_recommend_min_press_impl` / `_recommend_max_press_impl` 传入 `card_mask` + `group_type_map` + `group_members`。

### 关单条件

- [x] pytest：888+22 被跳过，999+对子 被推荐（不拆炸）
- [ ] 同回放步 7 日志应出现 `GUA-075 主路径: recommend=ThreeWithTwo/9`（或等效 rank），而非 `actIndex=116 Bomb/8`
- [ ] 批跑副胜率不下降（可选 3 局冒烟）

## 问题 B：贡还后 `initial_hand` 与 `all_players_hands` 不同步

### 现象

`adjust_initial_hand_for_tribute_back` 只改 `initial_hand`；`_validate_action_cards` 读 `all_players_hands`（贡前快照）→ 还贡收到第二张 S8 后出四炸误报「S8 出现 2 次但 initial 仅 1 次」。

### 最小修复（已实施）

`adjust_initial_hand_for_tribute_back` 同步更新 `all_players_hands[str(player_id)]`（add/remove 镜像操作）。

### 关单条件

- [x] pytest：add 还贡牌后 validation 不再 WARN
- [ ] 新批跑同路径无 `卡牌验证失败 … S8` WARNING

## 关联

- GUA-075（推荐法 + mask 保护）
- GUA-067（贡还 initial_hand）
- GUA-080（组牌冻结，本修复只动决策/记录层）
- **分析方法论**：[`workflows/WF-12-yf-decision-trace.md`](../workflows/WF-12-yf-decision-trace.md)（范例 §7）
