```markdown
---
type: concept
title: "组牌引擎 v2（5 维评分 + 6 方案枚举）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - grouping
  - engine-v2
  - v7
status: current
related_gua:
  - GUA-062
  - GUA-063
date: 2026-07-15
---

# 组牌引擎 v2

## 设计

### 5 维评分
1. 牌型完整度
2. 牌力
3. 控制力
4. 灵活性
5. 去单化（`de_singleton_score`）

### 6 方案枚举
- 单张、对子、三张、顺子、连对、钢板

## 角色分类
- 超强主攻 / 主攻 / 助攻 / 超弱

## 10+ 次迭代
GUA-062 主轴，每次迭代围绕评分权重和方案剪枝。

## 当前定位
**已从主导引擎降级为特征提供者**：
- 输出中间态给 NN
- 不再直接出牌
- 与 [[card-mask-is-core]] 协同

## 关联
- [[module-grouping-engine]] — 模块
- [[gua-062]] — 主 GUA
- [[gua-063]] — 衔接修复
```

---
