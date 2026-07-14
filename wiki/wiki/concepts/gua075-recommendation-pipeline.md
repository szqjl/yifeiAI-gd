---
type: concept
title: "GUA-075 推荐管线"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
  - docs/analysis/archive/2026-06-21-cardmask-dict-collision.md
tags:
  - gua-075
  - v7
  - recommendation
  - guard
  - cardmask
status: current
related_gua:
  - GUA-075
  - GUA-081
date: 2026-06-29
---

# GUA-075 推荐管线

## 概述

GUA-075 是 V7 L2 推荐管线的核心案例，承载「**L2 推荐 → L2′ 拦截 → 回退**」的完整机制。也是 [[cardmask-multiset-defect]] 的关键触发点之一。

## 管线流程

```
L2 推荐命中 (_recommend_play)
        ↓
L2′ 保护拦截 (_group_consistency_filter, 行 268-287)
        ↓
   通过？ ──否──→ 回退到 L3/L4
        ↓ 是
返回候选动作
```

## 历史 Bug

### Bug 1：命中路径绕过保护

**症状**：候选是 bomb/SF 时，命中路径**直接 return**，跳过 `_group_consistency_filter` 调用。

**后果**：
- bomb 被错误拆为顺子
- SF（5 张同花）被错误拆为 5 张单张

**修复**：2026-06-21 handoff，修改行 268-287，强制命中路径也走 `_group_consistency_filter`。

### Bug 2：_basic_classify 复用 dict 冲突

**症状**：行 699 `_basic_classify` 使用 `Dict[str, tuple]` 存储 card_mask，重复牌（双 SQ）共用 key 后写覆盖前写。

**后果**：手牌解析时丢牌，导致 _group_consistency_filter 输入错误，**保护失效**。

**状态**：**未修复**（2026-06-29 仍 open），multiset 改造进行中。

详见 [[cardmask-multiset-defect]]。

## GUA-075 角色

| 角色 | 描述 |
|------|------|
| 推荐管线承载者 | L2 四场景推荐（领出/跟上家/卡下家/让对家） |
| 保护机制触发者 | L2′ 强制走 `_group_consistency_filter` |
| cardmask 缺陷受害者 | `_basic_classify` 行 699 同型问题 |
| WF-12 锚点 | 决策链路分析工作流的核心案例 |

## 关联 GUA

- **[[gua-081]]**：GUA-075 下一档同型问题（缺 fallback）
- **GUA-079**：最小压制启发式
- **GUA-072**：MemoryTracker 降级路径

## 关联页面

- [[wf12-decision-trace]]
- [[v7-decision-pipeline-layers]]
- [[cardmask-multiset-defect]]
- [[gua-075]]
- [[gua-081]]
