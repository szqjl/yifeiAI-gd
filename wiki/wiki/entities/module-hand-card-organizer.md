---
type: entity-module
title: "HandCardOrganizer 手牌整理器"
sources:
  - docs/guandan-brain/人类掼蛋决策流程完整分析.md
tags:
  - module
  - memory
  - hand-reorder
  - v7-architecture
status: current
related_gua: []
date: 2026-06-18
---

# HandCardOrganizer 手牌整理器

## 模块定义

**HandCardOrganizer** 是模拟**人类手牌物理记忆机制**的模块:在 AI 内部对 27 张手牌进行**物理重排序**,按区域分组,降低后续模块的认知负荷。

## 设计动机

### 人类为什么整理手牌?

人类拿牌后会**自动分组**摆放:
- 炸弹放一起
- 顺子按花色排
- 三张/对子归类
- 单张放最后

这不是装饰,而是**工作记忆的物理扩展**——通过空间位置减少认知负荷。

### AI 为什么需要这个?

- 神经网络的输入如果是**无序的 27 张牌**,难以学到"分组"概念
- 通过**显式区域索引**,相当于**给 NN 一个提示**
- 区域索引 = 人类"用手指分组"的 AI 对应物

## 核心职责

| 职责 | 说明 |
|------|------|
| 区域划分 | 将手牌按牌型划分为若干区域 |
| 物理重排序 | 输出一组**有序**的牌列表 |
| 区域索引生成 | 为每张牌生成区域 ID |
| 区域大小统计 | 输出每个区域的牌数 |

## 区域定义

```yaml
regions:
  bomb: List[Card]          # 炸弹区
  straight_flush: List[Card] # 同花顺区
  sequence: List[Card]       # 顺子区
  triple: List[Card]         # 三张区
  pair: List[Card]           # 对子区
  single: List[Card]         # 单张区
```

## 输入输出

### 输入
- `hand_cards`: 27 张手牌(原始顺序)

### 输出
- `organized_cards`: 有序的 27 张牌
- `region_index`: Dict[Card, RegionID]
- `region_stats`: Dict[RegionID, int]

## 与其他模块的关系

- **上游**:无(每次拿牌后调用)
- **下游**:GroupingEngine、MemoryTracker

## 学术对应

- **区域索引** = Transformer 中的**位置编码**(Position Encoding)
- **物理重排序** = 人类认知中的**组块化**(Chunking)

## 关联页面

- 结构化记忆概念
- 类人决策五阶段
- V7 引擎
