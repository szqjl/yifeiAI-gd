---
type: source-summary
title: "南邮离线平台 actionList 候选缺失观测报告摘要"
sources:
  - docs/analysis/南邮离线平台-actionList候选缺失观测报告.md
tags:
  - observation
  - nanjing-post
  - offline-platform
  - action-list
status: current
date: 2026-06-29
---

# 南邮离线平台 actionList 候选缺失观测报告摘要

## 文件信息
- **路径**：`docs/analysis/南邮离线平台-actionList候选缺失观测报告.md`
- **字符数**：253（短篇观测报告）
- **定位**：南邮离线平台上 actionList（候选动作列表）出现缺失现象的观测记录

## 核心问题
- **现象**：候选动作列表（actionList）在某些局面下缺失或为空
- **平台**：南邮离线评测平台
- **影响**：引擎在该局面下无可选动作，可能导致非法出牌或空过

## 关联方向（推测）
- 可能根因：M3 规则引擎在某些边界局面未生成候选
- 修复方向：见对应 GUA 实体（可能与 GUA-080 关联，也可能独立登记）
- 验证手段：见 [[batch-evaluation]]

## 后续
- 短文档通常对应 1 个具体 GUA
- 建议在 ISSUES.md 中查找是否有 actionList 相关 GUA 编号并建立关联
```

---
