```markdown
---
type: entity-engine
title: "M3 引擎（规则决策）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - engine
  - m3
  - rule-based
  - legacy
status: current
related_gua:
  - GUA-024
  - GUA-025
  - GUA-026
  - GUA-027
  - GUA-028
  - GUA-029
  - GUA-030
  - GUA-031
  - GUA-032
  - GUA-034
  - GUA-035
  - GUA-036
date: 2026-07-15
---

# M3 引擎（规则决策）

## 引擎定位

M3 是项目 **规则引擎时代的巅峰**，在 [[engine-m1]]/M2 基础上集成了完整的 Guard 体系、策略映射、技能映射。

## 关键迭代

| 迭代文件 | GUA 范围 | 主题 |
|----------|----------|------|
| `m3-integration-gua024-028` | GUA-024~028 | M3 集成 |
| `m3-strategy-gua026-029` | GUA-026/029 | M3 策略 |
| `m3-guards-gua031-036` | GUA-031~036 | M3 Guards |
| `m3-skills-mapping-gua030` | GUA-030 | M3 技能映射 |

## 核心能力

- 完整的 Guard 体系（R07~R12 前身）
- 角色阈值（主攻/助攻/超弱）
- 策略映射表
- 技能→动作的映射

## 局限

- 纯规则，缺乏对复杂局面的泛化能力
- 对 Lalala 胜率仍偏低
- 这是项目向 V7 NN 引擎迁移的根本原因

## 当前角色

- 作为 V7 的 **validate 兜底层**（见 [[guard-heuristic-pipeline]]）
- 作为 BC 训练的 **教师信号来源**（已被 [[bc-argmax-collapse]] 证伪）

## 关联

- [[engine-m1]]
- [[engine-v7]]
- [[guard-heuristic-pipeline]]
```

---
