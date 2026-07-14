---
type: concept
title: "Playbook 升格方法论（WF-11）"
status: current
date: 2026-06-22
sources:
  - docs/guandan-brain/playbooks/README.md
  - docs/guandan-brain/playbooks/_template.md
  - docs/guandan-brain/工作流.md
tags:
  - playbook
  - workflow
  - wf-11
  - methodology
related_gua:
  - GUA-072
related_playbook: PB-001
---

# Playbook 升格方法论（WF-11）

## 什么是 Playbook

Playbook 是把「同类问题的最佳处置范式」从单次 GUA 修复中**抽取、固化、复用**的载体。它不是 ISSUE 的替代，而是 ISSUE 的**经验沉淀**。

## 与 GUA 的关系

| 维度 | GUA（ISSUE） | Playbook |
|------|--------------|----------|
| 时间轴 | 单点缺陷的全生命周期 | 横向方法论 |
| 触发 | 发现问题 | 同类问题**再现** |
| 内容 | 根因 + 修复 + 验证 | 模式 + 决策树 + 反例 |
| 读者 | 当前修复者 | 未来遇到同类问题的人 |

> **口诀**：GUA 是「这一次怎么修」，Playbook 是「下次再遇到怎么修」。

## 升格条件（WF-11 硬要求）

一个 GUA 修复经验可以升格为 Playbook，**必须同时满足**：

1. **同类问题再现** — 至少在两个 GUA 中独立出现过同模式
2. **可复现验证命令** — 有明确的脚本/单测可以验证遵守 Playbook
3. **反例** — 至少 1 个「不遵守会怎样」的反例（让后人知道为什么必须遵守）
4. **人类定音** — 关键判断点必须有人类拍板（如 PB-001 的「不改阈值改时序」）

## Playbook 模板（`_template.md`）

参考 `docs/guandan-brain/playbooks/_template.md` 规范字段：

- 标题、ID、状态、关联 GUA
- **核心论断**（一句话表达方法）
- 适用范围 / 不适用范围
- 决策树（什么情况下走哪个分支）
- 反例（违反 Playbook 的代价）
- 验证命令
- 历史定音记录

## 当前 Playbook 清单

| ID | 标题 | 核心论断 | 关联 GUA | 状态 |
|----|------|----------|----------|------|
| [[playbook-pb-001]] | 拆炸时序押后 | 策略分支前不要消耗「本应由分支决定」的资源 | GUA-072 | 已升格 |
| _更多待建_ | — | — | — | — |

## 为什么需要 Playbook

掼蛋 AI 的迭代过程中，「同一种错误反复犯」是最大的隐性成本：

- GUA-072 修过拆炸阈值，但**时序问题**作为新 GUA-080 又出现
- 没有 Playbook，每个 Agent 都会重新摸索一遍
- 有 Playbook，新 Agent 接手时直接读到「下次这么做」

## 与 Wiki 的分工

| 载体 | 角色 | 更新频率 |
|------|------|----------|
| GUA（ISSUES.md） | 实时 GPS — 当前在修什么 | 高 |
| Iteration Log（ITERATIONS.md） | 行车记录 — 改了什么 | 极高 |
| Handoff | 交接班 — 下一步做什么 | 高 |
| Playbook | 经验沉淀 — 下次怎么做 | 低（升格才更新） |
| **Wiki** | **综合知识 — 全景视图** | **中** |

## 关联阅读

- [[playbook-pb-001]] — 首个升格范例
- [[agent-workflow]] — WF-11 在工作流中的位置
- [[gua-072]] — PB-001 解决的前置问题
- [[gua-080]] — PB-001 沉淀后产出的新 GUA
