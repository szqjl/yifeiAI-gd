---
type: concept
title: "WF-12 决策链路分析工作流"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
  - docs/analysis/archive/level2-root-cause.md
tags:
  - workflow
  - wf-12
  - decision-trace
  - root-cause
  - methodology
status: current
related_gua:
  - GUA-075
  - GUA-079
  - GUA-081
date: 2026-06-29
---

# WF-12 决策链路分析工作流

## 定位

WF-12 是**单步微观决策还原**工作流，与 [[batch-evaluation]]（WF-04，局/副级聚合）和 [[game-scoring-tracking]]（WF-06，局级/副级回放）共同构成完整的分析体系。

**核心区别**：
- WF-04 回答"**整体胜率是多少**"
- WF-06 回答"**这一局/这一副是怎么打的**"
- WF-12 回答"**这一个动作为什么是这样选出来的**"

## 输入与输出

| 项目 | 描述 |
|------|------|
| 输入 | 单步 action + 上下文（手牌、last_play、curRank、玩家身份） |
| 输出 | 决策链代码层还原报告 + R-D 根因分类 + 修复建议 |
| 粒度 | 1 个 action（一次出牌/跟牌/PASS） |
| 工具 | 决策日志 + `UltimateWinRateEngineV7.decide()` 源码对照 |

## 核心方法论

### 1. R-D01~R-D08 根因 taxonomy

8 类代码层根因标签，用于对单步决策的"为什么"做标准化归因：

- **R-D01**：Guard 误拦截
- **R-D02**：组牌引擎评分未接入
- **R-D03**：card_mask 数据丢失
- **R-D04**：BC argmax collapse
- **R-D05**：推荐管线跳过保护
- **R-D06**：残局管线误判
- **R-D07**：启发式规则错误
- **R-D08**：未知/其他

### 2. L0~L8 决策管线

详见 [[v7-decision-pipeline-layers]]。

### 3. 报告模板

单步决策还原报告的标准结构：
1. 上下文快照（手牌/牌型/curRank/位置）
2. actionList 候选 + 实际选择
3. 决策链逐层还原（哪一层返回了结果）
4. R-D 根因分类
5. 修复建议 + 关联 GUA

## 锚点案例

- **[[gua-081]]**：四炸 `8888` 压 `666+22` 缺 fallback → 回退到 actIndex=116（WF-12 §7 范例）
- **GUA-075** 命中路径：推荐绕过 `_group_consistency_filter` 导致 bomb/SF 被拆（详见 [[gua075-recommendation-pipeline]]）

## 与现有体系的关系

- **上游**：WF-04 批跑发现胜率异常 → 定位到局/副 → WF-06 回放定位到关键 action → WF-12 单步还原
- **下游**：WF-12 输出 R-D 分类 + GUA 编号 → 进入 ISSUES 生命周期管理

## 关键教训

1. **"pytest 通过 ≠ 实战有效"**（GUA-062 教训）：单测只能验证代码逻辑，无法验证决策链是否真正使用
2. **"closed 状态 vs 实际效能"张力**：GUA 闭环不等于问题解决，需 WF-12 持续追踪决策链
3. **复现证伪纪律**：南邮 actionList 报告 44 例经 WF-12 复现 0 例成立 → 文档归档 + 勘误

## 关联页面

- [[v7-decision-pipeline-layers]]
- [[gua075-recommendation-pipeline]]
- [[cardmask-multiset-defect]]
- [[bc-argmax-collapse]]
- [[gua-081]]
- [[gua-062]]
