---
type: concept
title: "2026-06-19 战略转向 (heuristic 替代 NN)"
sources:
  - docs/guandan-brain/ISSUES.md
tags:
  - strategic-pivot
  - v7
  - history
status: current
related_gua:
  - GUA-064
  - GUA-071
  - GUA-072
date: 2026-06-19
---

# 2026-06-19 战略转向 (heuristic 替代 NN)

V7 引擎路线的重大调整节点,需作为重要历史事件永久记录。

## 转向背景
- V7 NN 引擎累计 1/69 局胜(1.4%)
- [[gua-064|GUA-064]] BC argmax collapse 确证为硬瓶颈
- 06-17 重训 val_acc 从 82.57% 跌至 35.19%(触发 [[gua-059|GUA-059]])
- 2026-06-19 heuristic 综合批跑 0/9 局,副胜率 2.4%

## 决策内容
1. V7 NN argmax 路线暂缓(非废弃,需根本性重设计)
2. 行牌决策改用 8 优先级 heuristic([[gua-071|GUA-071]])
3. NN 仅在 Guard 过滤后做随机选择
4. 启动 [[three-engine-tdd-pipeline|三引擎 TDD 管线]]([[gua-072|GUA-072]] → [[gua-057|GUA-057]] → [[gua-058|GUA-058]])

## 影响范围
- [[gua-054|GUA-054]]/[[gua-055|GUA-055]] 设计为 V7 NN 精细评估服务,转向后需要重新审视
- [[gua-057|GUA-057]]/[[gua-058|GUA-058]] 战略降级
- V5+ 长期路线保持不变(规划层面)

## 与 M3 关系
- M3 仍是主交付线(队胜率 81% 稳定)
- V7 继续作为实验线,目标: 找到替代 M3 的 NN 路径
- 不得让 V7 实验污染 M3 主线

## 历史定位
- 2026-06-19 与 2026-05-31 M1 frozen 共同构成「规则引擎稳定, NN 引擎探索」的双轨格局
- 是 [[gua-038|GUA-038]] 条件性 closed 的延伸后果
- 是 [[gua-064|GUA-064]] 的应对方案

## 后续观察点
- heuristic 副胜率是否能突破 [[gua-065|GUA-065]] 25.5% 基线
- 三引擎 TDD 管线是否能稳定执行
- 是否能找到 NN argmax 之外的 NN 决策路径
