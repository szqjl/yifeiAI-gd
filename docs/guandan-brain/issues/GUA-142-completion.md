# GUA-142 完成定义：敌剩 6 取消强制 Trips，整结构领出保冲刺路径

> **状态**：implemented（2026-07-10）
> **WF-12 锚点**：`20260710141616032842 [yf2_v7]-[opponent_1_3]-[32]-[2].json` 步 **50/90**
> **关联**：GUA-100（规则表）、GUA-116（整组领出）、GUA-135（冲刺能力，本 GUA **不改**其炸定义）

## 0. 现象

自由领出、`@1 rem=6` 时 Q1 因 `endgame_rule[6]=(["Trips"], ["Single","Pair"])` 强制 `Trips/9`，禁掉 `Pair/5`，压过可出的 `ThreePair 8899TT`。

人眼路径：`ThreePair → SB → 剩 HR + SF(9-K) + Pair/5` → 结构冲刺。

## 1. Phase A 收敛

| 项 | 内容 |
|----|------|
| 规则表 | `endgame_rule[6]` → `recommended=["ThreePair","TwoTrips","Straight","Trips"]`，`banned=[]` |
| Q1 钩子 | 自由领出：`ThreePair`/`TwoTrips` 且出完后 `_has_structure_sprint_path`（SF 或炸 + ≤2 手尾）→ 优先整组 |
| 不做 | MemoryTracker 推断敌 6 张；不改 GUA-135 `_has_sprint_capability` 全局语义 |

## 2. 停手条件

1. 锚点构造态：`decide` 出 `ThreePair`，不出 `Trips/9`
2. `remaining=6` 的 `banned` 不含 `Pair`/`Single`
3. pytest：`test_gua142` + 100/141/103/122 回归绿

## 3. CI

```bash
python -m pytest tests/test_gua142_enemy_six_structure_lead.py tests/test_gua100_q1_rule_table_validator.py tests/test_gua141_q1_sort_card_strength.py -q
```
