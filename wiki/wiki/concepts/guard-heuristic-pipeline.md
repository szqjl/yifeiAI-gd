```markdown
---
type: concept
title: "Guard-Heuristic-validate 三层管道"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - architecture
  - v7
  - decision-pipeline
  - guard
status: current
related_gua:
  - GUA-073
  - GUA-031
  - GUA-032
  - GUA-034
  - GUA-035
  - GUA-036
date: 2026-07-15
---

# Guard-Heuristic-validate 三层管道

## 定义

V7 引擎在出牌决策时采用 **三层过滤管道**，明确各层职责边界：

```
候选动作 → [Guard 硬排除] → [Heuristic 软排序] → [validate 兜底] → 最终出牌
```

## 三层职责

### 1. Guard 层（硬排除）

- **职责**：把绝对不合法的动作直接剔除
- **示例**：
  - R07 队友牌型识别 — 不打队友正在做的牌型
  - R08 队友送接保护 — 不抢队友的接牌窗口
  - R09 队友压制保护 — 不压制队友的牌
  - R10 greaterPos 参数一致性 — 避免参数错位导致的非法比较
  - R11 全局抑制牌检查 — 对手出不可压牌时禁止乱炸
  - R12 有自然单时禁止拆对子出单

### 2. Heuristic 层（软排序）

- **职责**：对剩余合法动作打分排序
- **信号**：角色（主攻/助攻/超弱）、炸弹价值、手数、灵活度
- **特征**：5 维评分（炸弹 0.3 + 手数 0.3 + 回收 0.1 + 灵活 0.1 + 去单化 0.2）

### 3. validate 层（兜底）

- **职责**：保证最终输出合法
- **机制**：若 Guard/Heuristic 给出非法动作，回退到 M3 规则兜底

## 架构价值

GUA-073 明确整理三层边界后的收益：

1. **可测试性**：每层可独立单测
2. **可调参性**：Heuristic 权重调整不影响 Guard 硬约束
3. **可解释性**：每层决策都有明确归因

## 已知缺陷

- R11 记忆泄漏（GUA-073 修复）
- Guard 叠加过严可能导致副胜率暴跌（见 GUA-070 17.7% → Guard 综合 3.7%）

## 关联

- [[GUA-073]]
- [[engine-v7]]
- [[role-threshold-system]]
- [[module-v7-guards]]
```

---
