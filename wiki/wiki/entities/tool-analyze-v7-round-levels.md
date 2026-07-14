---
type: entity-module
title: "V7 副级分析工具 (analyze_v7_round_levels.py)"
sources:
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - tool
  - v7
  - analysis
  - round-level
status: current
related_gua: []
date: 2026-06-17
---

# V7 副级分析工具 (analyze_v7_round_levels.py)

## 模块定义
`scripts/tools/analyze_v7_round_levels.py` — V7 引擎副级（round-level）数据官方分析工具。

## 核心功能

### 替代手动分析
- **之前**：手动 `grep curRank` / `order` 从日志提取
- **现在**：一行命令自动分析

### 主要能力

| 功能 | 说明 |
|------|------|
| 副级胜率 | 按 curRank 分组统计胜率 |
| order 分布 | 出牌顺序频次 |
| 时间序列 | 副级耗时分布 |
| 异常牌局 | 标记超时/异常局 |

## 使用方式

```bash
# 标准用法
python scripts/tools/analyze_v7_round_levels.py \
  --records game_records_v7/ \
  --output reports/v7_round_analysis.csv
```

## 必跑时机

- ✅ 每次 V7 批跑结束后
- ✅ 训练数据生成前
- ✅ 模型效果回归时

## 关联页面
- wiki-minimax/concepts/batch-evaluation.md — 评测体系
- wiki/entities/engine-v7.md — V7 引擎
- [[dual-data-channel]] — 数据通道
