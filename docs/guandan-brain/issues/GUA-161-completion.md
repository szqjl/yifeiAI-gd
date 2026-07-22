# GUA-161 完成定义

> **GUA-161**：队友已头游时清最小散单，并禁止同牌选择较弱 Straight 声明
> **登记/关单**：2026-07-22
> **严重级别**：P0
> **关联**：GUA-078（残局 Q1）、GUA-135（双进优先级）、GUA-160（队友六张送单）

## 锚点

`20260722202506820193 [yf1_v8]-[opponent_1_3]-[6]-[2].json` 步 82–83。

- 第 82 手 yf1 手牌为自然散张 `H4/S5/H6/CJ` 加 `StraightFlush(9-K)`，队友 yf2 已头游。
- 旧残局 Q1 因敌方剩 9 张而优先 `recommended_types=['Straight', ...]`，直接打光整结构，留下四个散单，违背争双上的清散顺序。
- 相同实牌 `H9+C9+CJ+CQ+CK` 在 actionList 同时声明为 `Straight` 与 `StraightFlush`；旧逻辑按 actionList 顺序选择较弱的 `Straight`。
- 第 83 手对手四星 `Bomb/J` 压的是平台声明 `Straight`，不是 `StraightFlush`；yf1/yf2 双份牌谱一致，非 recorder 错序。

## 修复

1. 残局 banned/Q1 之前新增双上清散优先级：自由领出、主攻/超强主攻、队友剩 0 张时，从 post-group `card_mask` 选择最小自然散张 `3–9`。
2. 最终动作统一出口增加同牌声明支配：若选中 `Straight`，且原始 actionList 存在完全相同牌张 multiset 的 `StraightFlush`，强制切换到 `StraightFlush` 索引。
3. 不同牌张的 `StraightFlush` 不触发升级；级牌、王及 core 拆单不进入双上清散候选。

## 验收

- [x] 第 82 手构造态从 `Straight/9` 改为 `Single/4 ['H4']`。
- [x] 同牌 `Straight`/`StraightFlush` 最终出口选择 `StraightFlush`。
- [x] 不同牌张不触发声明升级。
- [x] GUA-160 的队友恰剩 6 张送单规则保持通过。
