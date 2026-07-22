# GUA-159 完成定义

> **GUA-159**：存在合法同型可压时，降级启发式仍可能选择炸弹
> **登记/关单**：2026-07-22
> **严重级别**：P0
> **关联**：GUA-071（启发式排序）、GUA-075（推荐主路径）、GUA-158（异常降级保护）

## 锚点

`20260722202506921965 [yf2_v8]-[opponent_1_3]-[6]-[2].json` 步 37。

- 对手@3 出 `ThreeWithTwo/6`，yf2 手牌存在合法 `ThreeWithTwo/8 = 888+33`。
- 旧运行代码因 `get_card_rank` 漏导入退出 GUA-075 主路径，进入启发式降级。
- post-Guard/post-group 候选为 `PASS`、`ThreeWithTwo/8`、`Bomb/7`。
- 旧启发式给完整 Bomb core 加 `10000`，同型可压仅对炸弹软扣分，最终 `Bomb/7=9445` 高于 `ThreeWithTwo/8=-15`。

## 修复

1. 当 post-Guard/post-group 候选中存在与 `greaterAction` 同型的合法非炸动作时，将 `Bomb` 与 `StraightFlush` 从启发式评分候选中硬排除。
2. 对手牌为 `Bomb`/`StraightFlush`、自由领出或不存在同型可压动作时，不启用该硬排除。
3. 回放记录 `heuristic_scores` 增加 `hard_blocked_bombs`，保留被硬拦截候选的索引证据。

## 验收

- [x] 锚点构造态在 `ThreeWithTwo/8` 与 `Bomb/7` 同时存在时选择 `ThreeWithTwo/8`。
- [x] 被硬拦截的 Bomb 不进入 `_last_heuristic_scores`。
- [x] 不存在同型可压动作时 Bomb 仍可参与评分并被选择。
- [x] 定向测试 `tests/test_gua159_same_type_hard_blocks_bomb.py` 通过。
