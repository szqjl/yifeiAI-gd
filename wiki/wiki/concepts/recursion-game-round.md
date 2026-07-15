---
type: concept
title: "局 vs 副 的递归解读"
sources:
  - docs/development/AI首秀分析报告.md
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - guandan-rules
  - victory-num
  - definition
status: current
related_gua:
  - GUA-033
date: 2026-07-15
---

# 局 vs 副 的递归解读

## 定音来源

**[[gua-033]]** —— 已定音。

## 核心定义

| 术语 | 含义 |
|------|------|
| **局** | 一局游戏（从发牌到结束） |
| **副** | 一局内的"打副"（升级打法的最小单位） |

掼蛋一局通常包含**多个副**（升级玩法决定副数）。

## victoryNum 的四层写入

1. 单副胜利
2. 单局累计
3. 双队累计（按位置 0+2 vs 1+3）
4. 跨局累计

## 位置映射

```
pos 0 ─┐
       ├─ 队 A
pos 2 ─┘
       
pos 1 ─┐
       ├─ 队 B
pos 3 ─┘
```

**同队 victoryNum 必须一致** —— 这是 GUA-033 自检规则。

## 典型案例：首秀 [0,3,0,3]

参见 [[first-debut-baseline]]。

原始报告：`victoryNum = [0, 3, 0, 3]`（10 局统计）

**正确解读**：
- 位置 1 和位置 3 同属队 B
- 位置 0 和位置 2 同属队 A
- 按队叠加后：队 A = 0+0 = 0 胜，队 B = 3+3 = 6 胜
- 这是纯随机下胜利按位置均匀分布的统计假象
- ⚠️ 但首秀报告未明确标注此为"队胜率"

## 数据解读规则

读取任何 victoryNum 数据时：

1. 先确认是"局"级还是"副"级统计
2. 检查位置是否需要按 (0,2) / (1,3) 配对
3. 校验同队 victoryNum 一致性
4. 与 [[gua-033]] 定音对照

## 出牌顺序

`pos 0 → pos 1 → pos 2 → pos 3` 顺时针。
```

---

## 总结

本次摄入完成 **7 新增 + 5 更新**：

**新增页面**：
1. `wiki/entities/engine-m1.md` — 填补 M1 引擎实体空白
2. `wiki/sources/AI首秀分析报告-summary.md` — 首秀里程碑摘要
3. `wiki/sources/M1_ARCHITECTURE-summary.md` — M1 架构摘要
4. `wiki/sources/AGENT_BOOTSTRAP-summary.md` — Agent 启动摘要
5. `wiki/concepts/stage-router-architecture.md` — 5×2 路由架构概念
6. `wiki/concepts/first-debut-baseline.md` — 随机基准线概念
7. `wiki/concepts/agent-bootstrap-workflow.md` — Agent 工作流概念

**更新页面**：
1. `wiki/index.md` — 新增 4 个索引项
2. `wiki/overview.md` — 补充 M1 frozen 状态与里程碑
3. `wiki/log.md` — 记录本次摄入
4. `wiki/synthesis/synthesis-v7-current-state.md` — 明确 M/V 双线独立性
5. `wiki/concepts/recursion-game-round.md` — 补充 [0,3,0,3] 案例

**关键交叉引用**：`[[gua-033]]`（局≠副）、`[[gua-022]]`（M1 frozen）、`[[stage-router-architecture]]`、`[[first-debut-baseline]]`、`[[batch-evaluation]]` 在多个页面间形成知识图谱。
