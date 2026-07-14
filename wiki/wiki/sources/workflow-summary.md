---
type: source-summary
title: "工作流矩阵与 Skill 规划"
sources:
  - docs/guandan-brain/工作流.md
tags:
  - workflow
  - matrix
  - skill
  - multi-agent
status: current
related_gua: []
date: 2026-06-29
---

# 工作流矩阵与 Skill 规划

## 摘要

`工作流.md` 定义项目的**工作流矩阵**（WF-01～WF-12）与 **Skill 规划**，明确各环节职责、产出与对应工具/脚本。本文对其结构化摘要，并指出文档内部状态不一致需统一。

## 工作流矩阵（WF-01～WF-12）

| ID | 名称 | 关键内容 | 关联 GUA/模块 |
|----|------|----------|---------------|
| WF-01 | 数据采集 | 客户端日志落盘 | `client_std_1.py` / `client_std_3.py` |
| WF-02 | 批跑执行 | `run_v7_vs_lalala_games.py` / `run_m3_vs_lalala_games.py` | GUA-044 handshake |
| WF-03 | 结果解析 | `analyze_v7_rounds.py` / 复盘 | [[batch-evaluation]] |
| **WF-04** | **数据汇报口径** | **必须含 `vn_source`、`batch_games` 真源、`server_vn_raw` fallback** | — |
| WF-05 | 缺陷登记 | 分配 GUA 编号 | GUA 全谱 |
| WF-06 | 根因诊断 | R-D01～R-D08 标签 | [[v7-win-rate-history-summary]] |
| WF-07 | 修复实施 | commit / branch | `v7-dev` / `m-dev` |
| WF-08 | 冒烟验证 | `qoder_smoke.py` | 50 局 ≥40% 触发 ON |
| WF-09 | 复盘定音 | `yf_replay.py` | tol ≥3 局 |
| WF-10 | 知识沉淀 | `wiki.py ingest` | 本 Wiki |
| WF-11 | 推送前校验 | `pre_push_validate.py` / `verify_gitignore.py` | — |
| **WF-12** | **决策链路** | **R-D01～R-D08 根因标签 + 决策链批跑** | GUA-072 |

## Skill 规划（来自工作流.md §7）

> ⚠️ **状态不一致**：§7 列出 Skill 规划，但 §4 又把其中多个标 ✅「已有」。本文按 §7 现状记录，更新时需统一。

| Skill | 状态 | 备注 |
|-------|------|------|
| 数据汇报口径 | ✅ / 🚧 | WF-04 已基本就位 |
| 批跑参数校验 | ✅ | --target-games 3 倍数检查 |
| BC 训练质量评估 | 🚧 | val_acc ↔ 实战胜率 gap |
| Guard 叠加分析 | ✅ | R10～R16 + group_consistency_filter |
| 根因标签自动标注 | 🚧 | R-D01～R-D08 自动化 |
| 残局激活统计 | ✅ | check_endgame_agent.py 扫描 |
| Wiki 摄入 | ✅ | `wiki.py ingest` |
| 推送前 lint | ✅ | `pre_push_validate.py` |

## Wiki vs 原文件分工

| 职责 | 原文件 | Wiki |
|------|--------|------|
| **真源**（单行记录/原始日志） | `v7-win-rate-history.md` / `analyze_v7_rounds.py` 输出 | — |
| **结构化索引** | — | `index.md` / `overview.md` |
| **实体摘要** | GUA 描述分散 | `entities/gua-xxx.md` |
| **概念/方法论** | README 局部提及 | `concepts/*.md` |
| **综合分析** | 临时分析报告 | `synthesis/*.md` |
| **操作日志** | — | `log.md` |

## 输出格式约定

- **数据汇报**：必须含 `vn_source`（取值：`batch_games` / `server_vn_raw`）
- **批跑参数**：`--target-games` 必须是 3 的倍数（3/9/12）
- **GUA 引用**：全文一致 `GUA-xxx`
- **wikilink**：`[页面-stem]`（例如 `[[gua-080]]`）
- **复盘定音**：单局波动不构成结论，至少 3 局

## 关联 GUA

- **GUA-044**：handshake 四席就绪门闩（WF-02 前置）
- **GUA-072**：拆炸时序押后（WF-12 决策链案例）

## 链接

- 项目门户：[[README-summary]]
- 脚本索引：[[SCRIPT_INDEX-summary]]
- V7 KPI 历史：[[v7-win-rate-history-summary]]
- 批跑体系：[[batch-evaluation]]
- 决策链路标签：[[v7-win-rate-history-summary#复发排查流程]]
