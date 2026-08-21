# GUA-260 · 锁敌整牌残手质量评分

## 现象

match `6a87e5a30fbd680d7c7d8acf`：手牌 `555+777+H3`，下家剩 2，组牌为 **2×trips + scatter**。Q1 锁敌打出 `ThreeWithTwo/5`，残手两张散单。合理路径：`Trips/5 → Trips/7 → Single/3`。

## 根因

`_select_enemy_one_locking_structure` 用静态 `_q1_structure_priority`（TWT≻Trips），**不评估出牌后残手**，也不惩罚拆核心 trips。

## 修复原则（反缝合）

锁敌领出选牌统一为残手质量评分，**扩评分器，不新开特判名**：

| 优先级 | 信号 | 含义 |
|--------|------|------|
| 1 | `breaks_core` | 是否拆组牌核心（trips/straight/…） |
| 2 | `bomb_destroy` | 是否拆炸 |
| 3 | `residue_hands` | 出后手数（越少越好） |
| 4 | `scatter_only` | 残手是否全散单（无对/三可回手） |
| 5 | `structure_priority` | 牌型名仅作软并列打破 |

**能锁敌**仍由上层 gate（敌剩 1/2 + 整牌候选）保证；本函数只在「都能锁」的候选里比残手。

## 后续同类问题怎么处理

1. 先问：是否「多候选都能过同一 gate（锁敌/冲刺/喂牌）」但选错？
2. 是 → **往本评分键加一维**（或修残手估计算子），写 pytest 覆盖该残手形态。
3. 否 → 才考虑新 gate / 新分支（真正新场景）。

禁止：再写「若手牌含双 trips 且敌剩 2 则强制 Trips」这类样本特判。

## 验证

`tests/test_gua260_locking_residue_quality.py` 4/4；GUA-219 / GUA-078 锁敌回归通过。
