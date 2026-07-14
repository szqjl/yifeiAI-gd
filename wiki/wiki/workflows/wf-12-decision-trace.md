---
type: concept
title: "WF-12 yf 决策链路分析"
sources:
  - docs/guandan-brain/workflows/WF-12-yf-decision-trace.md
tags:
  - workflow
  - wf-12
  - v7
  - decision-trace
status: current
related_gua:
  - GUA-075
  - GUA-081
  - GUA-078
  - GUA-062
date: 2026-06-29
---

# WF-12 yf 决策链路分析

## 角色定位

| WF | 视角 | 输出 |
|----|------|------|
| WF-04 | 批跑 KPI | 胜率、子胜率 |
| WF-06 | replay 叙事 | 时序叙述 |
| **WF-12** | **单步微观决策链路** | **R-Dxx + 改良路径** |

## 输入

- `actions[]`：原始动作流
- `my_decisions[]`：AI 自报决策
- 客户端 log（如 `logs/yf1_v7_*.log`）

→ **三源交叉验证**（evidence triple）

## 输出

- R-Dxx 根因标签（8 类）
- 改良路径建议（不能写单局特例）

## 命令速查

```bash
# 卡 2 级切片统计
python scripts/analysis/verify_actionlist_pass_only.py

# 复跑 V7 vs lalala
python scripts/launchers/v7/run_v7_vs_lalala_games.py
```

## 关联

- [[v7-decision-pipeline]]
- [[root-cause-taxonomy-rd]]
- [[gua-075]] / [[gua-081]] / [[gua-062]]
- [[bc-argmax-collapse]]
- [[gua-080]]
