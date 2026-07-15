---
type: source-summary
title: "V7 批跑 cmd 窗口观察（73 秒停顿）"
sources:
  - docs/analysis/archive/批跑cmd窗口观察.md
tags:
  - batch
  - performance
  - cmd-window
  - archive
status: current
date: 2026-06-21
---

# V7 批跑 cmd 窗口观察（73 秒停顿）

## 来源
- 原始文件：`docs/analysis/archive/批跑cmd窗口观察.md`（已归档）
- 字数：约 2700 字

## 核心观察
- 批跑运行期间 cmd 窗口出现 73 秒无输出停顿
- 时间戳定位：`game_records_v7/20260621165949060489 [yf1_v7]-[opponent_1_3]-[16]-[2].json`
- 日志对应：`logs/yf1_v7_20260621_165903.log`

## 推断原因
1. NN 推理批量调度阻塞（BC argmax collapse 反复回退到同一动作）
2. `to_card_mask` 重复牌键冲突触发的 fallback 循环
3. 组牌方案 v2 多方案评分回收过程中的锁竞争

## 排查建议
- 引入单步耗时埋点（每步记录 wall clock）
- 对 argmax collapse 增加随机扰动（epsilon-greedy 退路）
- 详见 [[bc-argmax-collapse]] 与 [[cardmask-multiset-fix]]

## 归档说明
本文件作为单次观察记录，结论已并入 [[synthesis-m3-vs-v7-status]] 性能章节。
