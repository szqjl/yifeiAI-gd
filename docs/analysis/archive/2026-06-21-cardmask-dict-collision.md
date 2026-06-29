# Handoff: card_mask Dict 键冲突导致重复牌丢失

| 字段 | 内容 |
|------|------|
| 日期 | 2026-06-21 |
| 分支 | v7-dev |
| 状态 | 进行中 |

## 背景
分析 game #16 时发现 SA 整局没出，怀疑组牌引擎锁牌。深入后发现 SA 是规则问题（同点不能压同点），但顺带发现 **Q 炸弹（SQ,SQ,HQ,DQ 4张）被 GUA-075 推荐拆解为 ThreeWithTwo Q**。

## 已完成
- [x] 分析 game #16 D0~D18 决策链：SA 两次面对 `Single A` greaterAction，规则上同点不能压同点 → NOT a bug
- [x] 定位 Q 炸弹被拆根因：GUA-075 命中路径跳过 `_group_consistency_filter`，`_quick_guard_validate` 不检查 card_mask 一致性
- [x] **已修复**：在 GUA-075 命中路径（`ultimate_win_rate_engine_v7.py` 行 ~268）加入 card_mask bomb/straight_flush 保护检查
- [x] 发现 `_card_mask` 是 `Dict[str, tuple]`——重复牌（如两张 SQ）共用同一 dict key，后写入覆盖前一张
- [x] 确认 `_basic_classify`（行 699, GUA-072 降级路径）有同样的 dict key 冲突问题
- [x] **验证主路径 `to_card_mask()`（grouping_engine.py L130-202）**：同为 `Dict[str, tuple]`；`for card in group_cards: mask[card]=...` 重复牌串后写覆盖前写

## 未完成 / 进行中
- [ ] **编码修复**：新增 `group_members: Dict[int, List[str]]` + 改 `_get_broken_core_type`/`_action_breaks_core`/诊断日志用 multiset
- [ ] `_basic_classify` 同步
- [ ] pytest（四 Q 炸 + 双 SQ）+ 局#16 副[2] 回放回归

## 关键结论
1. **SA 不出不是 bug**：掼蛋规则「同点数不能压同点数」，SA 打不过对手的 A
2. **Q 炸弹被拆是 GUA-075 跳过保护**：
   - 调用链：`decide() → _recommend_play() → _quick_guard_validate(R10/R01/R05 only) → return` 跳过了 `_group_consistency_filter`
   - **已修复**：GUA-075 命中时补检 card_mask 一致性
3. **card_mask 结构缺陷**：`Dict[str, tuple]` 无法表示重复牌
   - `_basic_classify` 行 699：`card_mask["SQ"]` 只存一张 SQ 的信息
   - 日志里 bombs 只显示 3 张 Q 的原因：`for card, ... in self._card_mask.items()` 中两颗 SQ 合并成一个 key
   - 但 `group_size` 字段（count=4）是正确的——只是日志输出丢了一张

## 数据与产物位置
| 类型 | 路径 |
|------|------|
| 修改文件 | `src/v/nn/ultimate_win_rate_engine_v7.py` (行 268-287 已修改) |
| 分析局 | `game_records_v7/20260621165949060489 [yf1_v7]-[opponent_1_3]-[16]-[2].json` |
| 日志 | `logs/yf1_v7_20260621_165903.log` |

## 下一步唯一动作
**编码 `group_members` multiset 修复**（见 ITERATIONS 2026-06-21 `v7-cardmask-dict-collision-handoff` 行）：改 `to_card_mask` 产出 + engine 消费侧 + pytest；勿再改 GUA-075 ~268 拦截段。

## 不要重做
- SA 问题已结案，不要再分析 SA 为什么不出
- GUA-075 保护拦截已改好，不要再改同一段代码
