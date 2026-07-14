---
type: source-summary
title: "yifegdbot onboarding SKILL 摘要"
sources:
  - docs/guandan-brain/SKILL_yifegdbot-onboarding.md
tags:
  - skill
  - onboarding
  - yifegdbot
status: current
related_gua: []
date: 2026-06-20
---

# SKILL_yifegdbot-onboarding 摘要

yifegdbot（一服掼蛋 bot）的 onboarding 技能文档，覆盖环境准备、代码组织、典型任务。

## 核心内容

- **环境准备**：Python 版本、依赖、平台协议（v1006）
- **代码组织**：m-dev / v7-dev 双分支并行
- **典型任务**：批跑、Guard 规则迭代、heuristic 调整
- **评测标准**：局胜率 vs 副胜率（[[局不等于副]]）

## 与 AGENT_BOOTSTRAP 的关系

- `AGENT_BOOTSTRAP.md` 偏向"快速恢复上下文"
- `SKILL_yifegdbot-onboarding.md` 偏向"完整 skill 手册"
- 两者互补，新 Agent 建议先读 AGENT_BOOTSTRAP，再查 SKILL

## 相关页面

- [[AGENT_BOOTSTRAP-summary]]
- [[offline-platform-v1006]]
- [[局不等于副]]
