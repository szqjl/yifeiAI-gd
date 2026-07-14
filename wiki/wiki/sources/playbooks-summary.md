---
type: source-summary
title: "Playbook 索引与典范 (PB-001/002)"
sources:
  - docs/guandan-brain/playbooks/README.md
  - docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md
  - docs/guandan-brain/playbooks/PB-002-v7-bug-discovery-governance-loop.md
tags:
  - playbook
  - governance
  - v7
status: current
related_gua:
  - GUA-072
date: 2026-06-19
---

# Playbook 索引

## 文件作用
Playbook 是从"具体迭代"升格为"可复用方法论"的载体，每个 PB 记录一条成功路径与触发条件。

## 当前 Playbook 清单

### PB-001 — 炸弹拆牌时机 (GUA-072)
记录炸弹在 `_score_recovery_static` 评估中的拆牌时机决策路径。

### PB-002 — V7 Bug 发现治理循环
记录 V7 NN 引擎下，从 issue 发现→ablation→fix→验证的完整治理闭环。

## 升格机制
- **触发**：迭代中出现 ≥3 次相同模式
- **WF-11**：Playbook 升格工作流
- **关联**：与 GUA/工作流分工 — GUA 是缺陷条目，工作流是 SOP，Playbook 是方法论典范

## 关联
- [[playbook-governance]] — 概念页
- [[工作流-summary]] — 工作流 SOP
