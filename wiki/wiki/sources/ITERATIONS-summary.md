```markdown
---
type: source-summary
title: "ITERATIONS.md 摘要（迭代日志 MOC 入口）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - iterations
  - moc
  - obsidian-style
  - v7
  - v8
status: current
related_gua:
  - GUA-061
  - GUA-062
  - GUA-063
  - GUA-064
  - GUA-065
  - GUA-066
  - GUA-068
  - GUA-069
  - GUA-070
  - GUA-072
  - GUA-073
date: 2026-07-15
---

# ITERATIONS.md 摘要

## 文件定位
**迭代日志的 MOC（Map of Content）入口**，按 Obsidian 风格组织，所有 V7/V8 迭代条目以 GUA 编号锚定。

## 章节结构

| 章节 | 内容 | 关键 GUA |
|------|------|----------|
| V7 主迭代 | R7~R12 阶段演进 | GUA-061~073 |
| V7 行为克隆 | BC v2/v3 重训 | GUA-064 |
| V7 组牌引擎 | v2 五维评分 | GUA-062 |
| V7 Guard 管道 | 三层决策管线整理 | GUA-073 |
| V7 规则记牌 | belief input 引入 | GUA-072 |
| V8 平台迁移 | OpenGuanDan 对接 | GUA-143~148 |

## V7 关键迭代时间线

1. **R7**：GUA-061 V7 BC v3 重训
2. **R8**：GUA-062 组牌引擎 v2 主轴
3. **R9**：GUA-063 组牌→NN 衔接三缺口修复（已 closed）
4. **R10**：GUA-064 argmax collapse 确认 + GUA-066 领出不炸
5. **R11**：GUA-068 全局抑制牌节流 + GUA-069 超弱 core 保护
6. **R12**：GUA-070 不拆对子出单 + GUA-072 规则记牌引擎
7. **整理**：GUA-073 Guard-Heuristic 管道职责划分

## 核心论点

1. **V7 BC 路线已死**：GUA-064 5 次批跑 0/12 一致结论，argmax collapse 不可治
2. **GUA-039b 自对弈是唯一解**：从 BC 转向 RL 自对弈
3. **组牌 v2 已转纯特征**：组牌引擎 v2 从"主导引擎"降级为"特征提供者"
4. **M3→V7 知识传承**：GUA-065 队友识别从 M3 `_Single()`、`_update_teammate_last_trick` 借鉴
5. **副胜率方差警告**：3.7% vs 25.5% vs 7.0% 剧烈波动，≥9 局是统计意义门槛

## 关联页面

- [[gua-064]] — argmax collapse 硬瓶颈
- [[gua-062]] — 组牌引擎 v2 主轴
- [[gua-073]] — 三层决策管线整理
- [[engine-v7]] — V7 引擎
- [[engine-v8]] — V8 引擎
- [[bc-argmax-collapse]] — BC 失败核心概念
- [[three-layer-decision-pipeline]] — Guard→Heuristic→validate
```

---
