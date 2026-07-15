---
type: source-summary
title: "GUA-044 completion · 批跑四席就绪门闩"
sources:
  - docs/guandan-brain/issues/GUA-044-completion.md
tags:
  - source-summary
  - gua-044
  - batch
  - infrastructure
status: current
related_gua:
  - GUA-044
  - GUA-033
date: 2026-06-17
---

# GUA-044 completion · 批跑四席就绪门闩

## 摘要

GUA-044 是批跑评测体系的基础设施条目，引入**按席位而非计数**的就绪门闩。

## 关键概念

- `CONNECT_ORDER_INDEX` — 席位连接顺序索引
- `clients_ready.json` — 平台侧就绪状态表
- `wait_for_connect_turn` — 等待连接轮次

## 验收标识

✓ 四席已全部连上，平台可安全开局

## 跳过开关

`YF_SKIP_CONNECT_GATE=1` 用于开发态快速跑批（生产环境禁用）。

## 行为反转（breaking change）

旧版批跑在超时后仍会继续开局；GUA-044 后改为：四席未齐 → 中止本批，不再「超时仍继续」。现有依赖旧行为的脚本需迁移。

## 测试

`tests/test_client_ready.py`

## 更新日期

2026-06-06
