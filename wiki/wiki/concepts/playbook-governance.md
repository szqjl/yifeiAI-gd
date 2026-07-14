---
type: concept
title: "Playbook 治理与升格机制"
sources:
  - docs/guandan-brain/playbooks/README.md
  - docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md
  - docs/guandan-brain/playbooks/PB-002-v7-bug-discovery-governance-loop.md
tags:
  - playbook
  - governance
  - methodology
status: current
related_gua:
  - GUA-072
date: 2026-06-19
---

# Playbook 治理与升格机制

## 概念
Playbook 是从"具体迭代"升格为"可复用方法论"的载体。区别于 GUA（缺陷条目）和工作流（SOP）。

## 升格条件
- 同一模式在 ≥3 次迭代中出现
- 成功路径已通过批跑验证
- 有明确的触发条件与执行步骤

## 升格流程（WF-11）
1. 识别重复模式
2. 撰写 Playbook 草案（PB-xxx）
3. 关联相关 GUA
4. 团队评审
5. 加入 [[playbooks-summary]] 索引

## 当前 Playbook
- [[PB-001]] — 炸弹拆牌时机（[[GUA-072]]）
- [[PB-002]] — V7 Bug 发现治理循环

## 与 GUA/工作流的分工
| 类型 | 性质 | 作用 |
|------|------|------|
| GUA | 缺陷条目 | 记录"坏"的东西 |
| 工作流 | SOP | 标准化流程 |
| Playbook | 方法论典范 | 记录"成功路径" |

## 关联
- [[playbooks-summary]] — Playbook 索引
- [[工作流-summary]] — 工作流 SOP
- [[ISSUES-summary]] — 缺陷脊柱
