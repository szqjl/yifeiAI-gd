---
type: source-summary
title: "ISSUES.md 主表摘要"
sources:
  - docs/guandan-brain/ISSUES.md
tags:
  - gua-master-table
  - issues-tracking
  - state-of-record
status: current
related_gua:
  - GUA-052
  - GUA-061
  - GUA-135
  - GUA-136
  - GUA-137
  - GUA-138
  - GUA-143
  - GUA-144
  - GUA-145
  - GUA-146
date: 2026-07-16
---

# ISSUES.md 主表摘要

## 概述

`ISSUES.md` 是掼蛋 AI 项目的**缺陷主表**（Single Source of Truth），记录所有 GUA（GuanDan AI）条目的生命周期状态。每条 GUA 包含：编号、标题、状态（open/closed）、优先级（P0/P1/P2）、负责人、关联分支/提交。

## 当前主表结构（截至 2026-07-16）

| 段位 | 范围 | 状态 |
|------|------|------|
| 早期已关闭 | GUA-001 ~ GUA-052 | 多为 closed（部分 P0 历史遗留） |
| 进行中 sprint | GUA-135 ~ GUA-146 | 大部分 open，少数 draft 待登记 |

## 关键观察

### GUA-135：双进优先级判定（P0 open）
- sprint_capability 算法的初始实现
- 数据源：剩余手牌 ≥4 张同点 → 判定为「冲刺」
- **已知缺陷**：粗粒度，未考虑炸弹/单手/贡牌贡献

### GUA-136/137/138（draft 2026-07-08 待登记）
> ⚠️ **数据完整性警告**：ISSUES.md 主表在 GUA-054 行附近被截断（原始文本以 `9` 结尾），**GUA-136/137/138 在主表中可能尚未正式登记**。三份完成定义文档均标注 `draft（2026-07-08 待登记）`。
>
> **行动项**：下次摄入前需读完整 ISSUES.md 确认这些条目是否已加入主表。

### GUA-143~146：V8 迁移基础设施
- handoff §背景声称「文件已全部创建」
- 但 ISSUES.md 主表标注这 4 条仍为 open
- **未冒烟状态**：代码齐套但未跑通端到端
- 详见 [[v8-migration-handoff]]

## 重要约定

1. **状态字段**：`open` / `closed` / `draft`
2. **优先级**：`P0`（必须解决）/ `P1`（应该解决）/ `P2`（可选）
3. **每条 GUA 必须有完成定义**：完成条件 / 验收标准 / 回归测试
4. **关闭流程**：实现 → 单测 → 集成测试 → 批跑验证 → 关闭

## 相关 Wiki 页面

- [[gua-135]] — 双进优先级判定（上游）
- [[gua-136]] — 玩家剩牌估算增强（数据源升级 1）
- [[gua-137]] — 玩家整手结构推断增强（数据源升级 2）
- [[gua-138]] — grouping_engine 推理性能优化（数据源升级 3）
- [[v8-migration-handoff]] — V8 迁移基础设施齐套状态
- [[sprint-precision-upgrade-chain]] — sprint 评估升级链综合

## 已知问题

1. **表格截断**：GUA-054 之后的行可能未读完
2. **GUA-136/137/138 未登记**：draft 状态与主表脱节
3. **GUA-143~146 状态模糊**：handoff vs 主表说法不一致
