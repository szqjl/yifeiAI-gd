---
type: source-summary
title: "V7 vs M3 vs Lalala KPI 诊断重写版（2026-06-29）"
sources:
  - docs/analysis/v7-kpi-vs-m3-vs-lalala-2026-06-29.md
tags:
  - kpi
  - v7
  - m3
  - lalala
  - state-machine
  - design
status: current
related_gua:
  - GUA-013
  - GUA-064
  - GUA-071
  - GUA-072
  - GUA-075
  - GUA-089
  - GUA-090
  - GUA-091
  - GUA-092
date: 2026-06-29
---

# V7 vs M3 vs Lalala KPI 诊断重写版（2026-06-29）

## 来源
- 原始文件：`docs/analysis/v7-kpi-vs-m3-vs-lalala-2026-06-29.md`
- 字数：约 20000 字（本批最重磅文档）

## 文档定位
本文件是 V7 当前状态的**重写版诊断**，包含 6 个独立观点，其中 4 个与项目既有结论不一致。**这种独立判断需被 Wiki 显式记录为 tension**。

## KPI 数据
- V7 累计对 lalala 队胜：0.7%
- M3 累计对 lalala 队胜：~70%
- V7 单局胜率（最新批跑）：1.1%

## 六个独立观点
1. **观点 1**：V7 0% 队胜根因是 [[GUA-064]] BC argmax collapse + [[GUA-013]] 手牌跟踪 + [[GUA-072]] card_mask 退化，**不是信念建模缺失**——信念建模降为 P2 长期方向
2. **观点 2**：[[GUA-071]] heuristic 很可能长期是 V7 决策主体，NN 退化为信念建模和 RL 微调——升格为 P0 主轴
3. **观点 3**：状态机切点从 5 阶段（开局→角色→试探→中期→残局）简化为 **3 段 20/10/5**（手牌张数切分）
4. **观点 4**：M3 GUA-036 教训是 V7 状态机设计的核心约束——加规则有负收益，必须单条净盘验证
5. **观点 5**：相生相克推断（`_inference_phase_relation`，IP-01~IP-13）应作为阶段 2 决策辅助输入
6. **观点 6**：阶段 2（中期）启用 NN 决策，阶段 0/1/3 强制走 heuristic，避免叠加负收益

## 5 维状态机矩阵（设计稿）
| 阶段 | 张数 | 主决策 | Guard 启用 | 输入源 | 输出 |
|------|------|--------|-----------|--------|------|
| 0 开局组牌 | 27→20 | heuristic | 同花顺保护、炸弹被拆 | 手牌全集 | 组牌方案 v2 |
| 1 角色 | 20→15 | heuristic | 同上 | MemoryTracker | 试探出牌 |
| 2 中期 | 15→8 | NN+Guard | 相生相克 Guard | 完整 MemoryTracker | 动态出牌 |
| 3 残局 | 8→0 | heuristic | 单张保护、炸弹保护 | 残局 MemoryTracker | 决胜出牌 |

> 注：原 5 阶段（开局→角色→试探→中期→残局）经 M3 758 副数据校核后简化为 3 段 20/10/5

## tension 清单
- 与既有结论的 4 处不一致已在文档内显式记录
- 详见 synthesis-v7-state-machine-design 综合页

## 关联
- 详见 [[engine-v7]] [[engine-m3]]
- 详见 stage-state-machine [[bc-argmax-collapse]] gua-036-lesson guard-stage-tagging
