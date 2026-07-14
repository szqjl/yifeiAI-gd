---
type: concept
title: "牌力计算法 (V7 _score_power)"
sources:
  - docs/knowledge/skills/07_opening/04_card_grouping_skills.md
tags:
  - concept
  - power-scoring
  - v7
  - scoring
status: current
related_gua:
  - GUA-030
  - GUA-032
date: 2026-06-18
---

# 牌力计算法 (V7 _score_power)

V7 引擎的**量化牌力评估体系**，实现于 `src/v/nn/features/grouping_engine.py` 的 `_score_power()` 函数。

## 5 维评分公式

V7 引擎采用**加权求和**的牌力评分：

```
power_score = 0.3 × bomb_score    # 炸弹
            + 0.3 × round_count   # 手数（轮次）
            + 0.1 × recycle_score # 回收（配火复用）
            + 0.1 × flex_score    # 灵活度（活牌）
            + 0.2 × singles_score # 去单化
```

| 维度 | 权重 | 含义 |
|------|------|------|
| 炸弹 | 0.3 | 炸弹数量与质量 |
| 手数 | 0.3 | 完成出牌需要的轮次 |
| 回收 | 0.1 | 配火后的复用程度 |
| 灵活 | 0.1 | 牌型变化余地 |
| 去单化 | 0.2 | 单张消除程度 |

## 4 级牌力分级

| 牌力等级 | 分值范围 | 角色定位 |
|---------|---------|---------|
| 超强牌 | ≥8 | 主攻无悬念 |
| 强牌 | 5-7 | 主攻 |
| 中弱牌 | 2-4 | 助攻 / 临界 |
| 超弱牌 | <2 | 超弱牌 |

**主攻/助攻临界线**：4-5 分

## 加/减分规则表（V7 _score_power）

| 牌型/事件 | 加/减分 | 备注 |
|----------|--------|------|
| 同花顺 | +3 | SF_FIRST |
| 5 头炸 | +3/个 | 配 5 头炸策略存疑（见限制） |
| 普通 4 头炸 | +2/个 | BOMB_FIRST |
| 四大天王 | +4 | 特殊王炸 |
| 配 6 头炸 | +4/个 | 宜配中小不配大 |
| 首发 | +1（**未实现**） | 已知 limitation |

## 与角色定位的关系

```
强牌 (5-7+)     → 主攻组牌：全面组牌，奔最大化
中弱牌 (2-4)    → 助攻组牌：精简配火，保留变化
超弱牌 (<2)     → 超弱牌组牌：配火优先，过渡为主
```

详见 [[concept-role-positioning]]。

## 角色转换规则

- **主攻转助攻**：当对手牌力过强或己方牌力大幅消耗时，残牌兜底转为助攻
- 触发条件（待 GUA 确认）：预计胜率 < 30% 或 主攻牌型被压制

## 已知限制

1. **"首发 +1 分"未实现**：口诀建议但 V7 引擎未纳入，待后续 GUA
2. **配 5 头炸策略冲突**：口诀"忌配 5 头炸"，但 V7 +3/个 未显式惩罚，需确认
3. **孤张定律/A 下放**：尚未量化进评分

## 关联

- 上游：[[concept-card-grouping-principles]]
- 下游：[[concept-role-positioning]]、[[engine-v7-grouping]]
- 模块：wiki/entities/module-grouping-engine.md
- 引擎映射：[[gua-030]]
