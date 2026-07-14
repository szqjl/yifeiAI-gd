---
type: concept
title: "决策根因 taxonomy R-D01~R-D08"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - wf-12
  - root-cause
  - taxonomy
  - decision-pipeline
status: current
related_gua:
  - GUA-062
  - GUA-075
date: 2026-06-28
---

# 决策根因 taxonomy R-D01~R-D08

## 概述

WF-12 决策链路分析工作流提出 8 类根因标签，用于在决策链路还原后定位失败原因。每条根因对应 [[decision-pipeline-v7]] 的特定层。

## 根因清单

| 标签 | 描述 | 常见层 | 典型案例 |
|------|------|--------|----------|
| R-D01 | 推荐被 mask 挡（一致性拦截） | L2′ | 推荐命中但 group_members 与 card_mask 不一致 |
| R-D02 | 推荐缺失（候选为空） | L4 | filter_action_list 把所有合法候选过滤掉 |
| R-D03 | 残局未命中 | L1 | EndgamePreprocessor Q0~Q3 全部失败 |
| R-D04 | 组牌锁死（无合法候选） | L0 | grouping_engine_v2 输出为空 |
| R-D05 | 启发式劣选 | L7 | `_heuristic_select` 选择 BC argmax collapse 后的 Single |
| R-D06 | 场态误读 | L0b / L3 | MemoryTracker / guard 对 curRank / 级牌判断错 |
| R-D07 | 记录贡还（漏记贡牌） | L0b | 进贡/还贡环节状态错位 |
| R-D08 | 知识未接入 | L6 / L7 | 规则文档存在但代码未读取（如同花顺压四炸） |

## 使用方法

1. 用 [[wf-12-decision-trace]] 的链路还原表定位层
2. 在该层及上游 1~2 层查找匹配的 R-D 标签
3. 标签前缀固定为 R-D，便于 grep 与统计

## 典型案例映射

### GUA-062 卡2级 80.5% Single 决策
- 链路：L6 → L7 → L8
- 标签：**R-D05**（启发式劣选）
- 辅因：**R-D08**（知识未接入，级牌压制规则未生效）

### GUA-075 card_mask Dict 键冲突
- 链路：L0 → L2 → L2′ → L4
- 标签：**R-D01**（推荐被 mask 挡）
- 根因：multiset 用 Dict 编码时同牌型键覆盖

## 与 guard R-Gxxx 的关系

| 维度 | R-Gxxx (guard) | R-Dxx (根因) |
|------|----------------|--------------|
| 位置 | L3 校验层 | 全链路诊断 |
| 作用 | 拒绝非法输出 | 定位失败原因 |
| 命名 | 规约编号 | 根因编号 |

## 相关页面

- [[wf-12-decision-trace]] — 标签提出处
- [[decision-pipeline-v7]] — 标签作用层
- [[gua062-batch-eval-summary]] — R-D05 案例
- [[cardmask-multiset-fix]] — R-D01 案例
