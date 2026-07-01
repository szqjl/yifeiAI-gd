# V7 组牌引擎 v2（GUA-062）

> 日期：2026-06-18
> 状态：**closed** ✅ — P0-A/P0-B/P0-C/P1/P2 全部完成，49 pytest passed
> 父 GUA：GUA-062
> 关联：GUA-061（closed）、GUA-060（BC 天花板）、GUA-039b（自对弈验证）

## 重要区分：组牌 vs 出牌

| | 组牌阶段（阶段0） | 出牌阶段（阶段2/3） |
|---|---|---|
| **时机** | 拿到 27 张手牌后，出牌前 | 每圈出牌时 |
| **职责** | 牌型识别、多方案生成、方案评分 | 牌型选择、具体牌张选择、出牌顺序 |
| **回收能力** | **静态评估**：方案中各种牌型是否有兜底大牌 → 方案质量打分 | **K 原则判断**：我现在出这张牌能不能收回 → 实时决策 |
| **归属** | ✅ **GUA-062** | ❌ 属于 V7 policy / 出牌决策引擎 |

**结论**：GUA-062 只做组牌阶段的静态回收评估，不做出牌阶段的 K 原则实时判断。

## 背景

GUA-061 从 M3 提取了组牌逻辑，但 M3 原始组牌本身就很弱——缺少文档主张的两个核心维度：
- **回收能力**（静态评估）：权重 0.3，GUA-061 完全没有
- **灵活性**：权重 0.2，GUA-061 完全没有

来源分析：
- `人类掼蛋决策流程完整分析.md` §阶段0 组牌评估维度（炸弹0.3+手数0.2+回收能力0.3+灵活性0.2）
- `人类掼蛋决策流程完整分析.md` §阶段2.2 能回收判断（文档在此处是出牌阶段用法，不是组牌阶段）
- `人类掼蛋决策流程完整分析.md` §8.8.3 K 原则完整定义（属于出牌策略，不是组牌评分）
- `04_card_grouping_skills.md` §一 牌力计分法（登基牌+3/普通炸+2/赘牌-1）
- GUA-061 当前实现：6 维等权评分，无回收能力，无灵活性，4 策略贪心标签

## 实施计划

### P0-A：静态回收评估 — 1.5h

对方案中每种牌型静态评估是否有兜底大牌（方案质量打分）：

```python
def _score_recovery_static(plan: GroupingPlan, cur_rank: str) -> float:
    """
    组牌阶段的静态回收评估。

    不是判断「我现在出这张牌能否收回」（那是出牌阶段 K 原则的事），
    而是评估「这个方案中，各类牌型有多少有兜底大牌」。

    兜底大牌定义：手牌中有更大的同类型牌。
    """
    scores = []

    # 单张兜底：有大王/小王/级牌/K 以上单牌
    if plan.singles:
        big_singles = [s for s in plan.singles
                       if _rank_value(s) >= _rank_value('K')]
        scores.append(len(big_singles) / max(len(plan.singles), 1))

    # 对子兜底：有 KK 以上对子
    if plan.pairs:
        big_pairs = [p for p in plan.pairs
                     if _rank_value(p[0]) >= _rank_value('K')]
        scores.append(len(big_pairs) / max(len(plan.pairs), 1))

    # 顺子兜底：有更大顺子
    if plan.straights:
        recoverable = sum(1 for s in plan.straights
                          if _has_bigger_straight_in_plan(s, plan))
        scores.append(recoverable / len(plan.straights))

    # 三带二兜底：有更大三带二
    if plan.trips:
        recoverable = sum(1 for t in plan.trips
                          if _has_bigger_trip_in_plan(t, plan))
        scores.append(recoverable / len(plan.trips))

    # 豁免牌型（不需要评估）：
    # - 炸弹：本身就是压制手段
    # - 钢板/木板/三张：稀有牌型，天然难压
    # - 同花顺：顶级牌型

    if not scores:
        return 0.5  # 无需要兜底的牌型 → 默认中等

    return sum(scores) / len(scores)
```

**与 K 原则的区别**：
- 静态回收评估：打分用，不参与出牌顺序决策
- K 原则：出牌时实时判断"我现在出这个能不能收回"，决定「先出弱牌保留大牌」还是「出大牌争夺牌权」

### P0-B：灵活性评分 — 1h

1. 牌型多样性：有多少种不同牌型（0~6 类）
2. 方案差异性：与兄弟方案的差异程度（炸弹数/轮数差异）
3. 两维度归一化后等权平均

### P0-C：评分公式升级 — 0.5h

替换当前 `_score_plan()` 的 6 维等权为文档 4 维加权：

```python
plan.score = (
    0.3 * bomb_score +         # 炸弹数
    0.2 * rounds_score +       # 手数
    0.3 * recovery_score +     # 静态回收评估（新增）
    0.2 * flexibility_score    # 灵活性（新增）
)
```

### P1：牌力计分 + 角色定位 — 1.5h

从 `04_card_grouping_skills.md` §一 提取评分规则：
- 登基牌炸弹 +3（4 个级牌/5 头+/同花顺）
- 普通四头炸 +2
- 登基牌 +1（大王/对级牌/A-K 顺子/木板/钢板）
- 赘牌 -1（小顺子/小三带二/小对子/小单张）

角色映射（2026-06-19 降阈）：
- 7+ → 超强主攻
- 4-6 → 主攻
- 1-3 → 助攻
- <1 → 超弱

### P2：真回溯多方案 — 2h

当前 4 策略贪心标签 → 4 策略 × 2~3 回溯变体 = 8-16 方案：
- 每个策略生成主方案 + 最小组牌变体 + 最大组牌变体
- 去重后预期 5-8 个有效方案

## 不做什么（留给 V7 policy / 出牌决策引擎）

| 事项 | 理由 |
|------|------|
| 出牌时的实时 K 原则判断 | 属于阶段2/阶段3出牌决策，不是组牌引擎职责 |
| 出牌顺序（先出不能回收的牌） | 属于出牌决策引擎的策略逻辑 |
| 试探阶段的风险评估 | 依赖对手建模和局势判断，不在组牌阶段做 |

## 完成定义

1. `grouping_engine.py` 升级：新增 `_score_recovery_static()` / `_score_flexibility()` / `_score_power()` / `determine_role()`
2. 评分公式替换为 4 维加权
3. `_enumerate_plans_v2()` 新增回溯变体
4. pytest ≥15 case（含静态回收评估各牌型 / 级牌为 K 降级 / 豁免牌型 / 牌力计分 / 角色定位）
5. 24 维特征向量兼容（不改变维度数，但 0~7 维来自新评分）

## 验证方法

- BC 重训对比（受 GUA-060 限制，预计 val_acc 仍 37% 区间，但方案质量可人工审计）
- 等 GUA-039b 自对弈跑通后，用新评分 vs 旧评分的方案选择做实战对比

## 实施结果（2026-06-18）

### 新增函数

| 函数 | 用途 | 行数 |
|------|------|------|
| `_rank_to_value()` | rank 字符 → 数值 | 7 |
| `_has_bigger_straight_in_plan()` | 方案内更大顺子检测 | 10 |
| `_has_bigger_trip_in_plan()` | 方案内更大三带二检测 | 10 |
| `_score_recovery_static()` | P0-A 静态回收评估 | 45 |
| `_score_flexibility()` | P0-B 灵活性评分 | 25 |
| `_score_power()` | P1 牌力计分 | 35 |
| `determine_role()` | P1 角色定位 | 10 |
| `_score_plan_v2()` | P0-C 4 维加权评分 | 25 |

### 修改内容

| 修改 | 说明 |
|------|------|
| `GroupingPlan` 新增字段 | bomb_score/rounds_score/recovery_score/flexibility_score/power_score/role |
| `_enumerate_plans()` 升级 | 5 策略→6 策略（+NO_STRAIGHTS / +ALL_COMBOS），生成全部方案后统一 v2 评分 |
| `_extract_features()` 适配 | 策略 ID 映射扩至 6，方案数归一化 /6 |
| 移除 `_score_plan()` | 被 `_score_plan_v2()` 替代 |

### 测试

- pytest：**49/49 passed**（原 31 + 新增 18 GUA-062 case）
- 5 个新测试类：TestGUA062RecoveryScore / TestGUA062FlexibilityScore / TestGUA062PowerScore / TestGUA062BacktrackVariants / TestGUA062ScoringFormula
- 下游兼容：memory_tracker、bc_dataset 正常导入
