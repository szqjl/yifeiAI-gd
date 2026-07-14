---
type: concept
title: "V7-dev / m-dev 分支隔离策略"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - git
  - branch
  - isolation
  - workflow
status: current
related_gua: []
date: 2026-06-17
---

# V7-dev / m-dev 分支隔离策略

## 定义
V7 与 M3 引擎开发使用 **独立 Git 分支**，绝不混推的硬规则。

## 分支拓扑

| 分支 | 用途 | 客户端 | 数据目录 |
|------|------|--------|----------|
| `v7-dev` | V7 NN 引擎主开发 | `yf1_v7.py` / `yf2_v7.py` | `game_records_v7/` |
| `m-dev` | M3 规则引擎维护 | `yf1_m3.py` / `yf2_m3.py` | `game_records/` |

## 硬规则

1. **绝不混推**：V7 的代码改动禁止 push 到 `m-dev`，反之亦然
2. **数据目录分离**：
   - M3 牌谱 → `game_records/`
   - V7 牌谱 + BC 训练数据 → `game_records_v7/`
3. **客户端绑定**：每个分支固定使用对应 `yf*` 客户端
4. **批跑脚本分离**：
   - V7 → `scripts/launchers/v7/run_v7_vs_lalala_games.py`
   - M3 → `scripts/launchers/m/run_m3_vs_lalala_games.py`

## 设计动机

- M3 规则引擎已瓶颈，与 V7 NN 引擎架构差异巨大
- 混推导致数据目录污染、训练数据污染、客户端不匹配
- 隔离后两线可独立实验线推进

## 违反后果
- 牌谱格式不一致 → 分析脚本崩溃
- BC 训练数据混入 M3 → 模型污染
- 客户端 API 不匹配 → 运行时报错

## 关联页面
- [[agent-bootstrap-workflow]] — Agent 切换任务线
- [[wiki-system]] — 知识管理
- [[code-quality-gate]] — 推送门控
