---
type: source-summary
title: "Commander Notes 指挥笔记（摘要）"
sources:
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - commander
  - policy
  - collaboration
  - history
status: current
related_gua:
  - GUA-022
  - GUA-033
date: 2026-06-17
---

# Commander Notes 指挥笔记（摘要）

## 来源
- 原始文件：`docs/guandan-brain/COMMANDER_NOTES.md`（5499 字符）
- 类型：指挥官决策笔记

## 核心内容

### 团队配置
- **yf1_m3 + yf2_m3**：M3 团队双客户端
- **yf1_v7 / yf2_v7**：V7 团队双客户端
- **Hermes CLI**：指挥官

### 协作原则
1. **短任务短 prompt**：单回合单目标
2. **长任务拆回合**：复杂任务分步执行
3. **不传信任**：所有产出必须验证
4. **产出验证优先**：数据 > 声明

### 关键历史决策
| # | 主题 | 结论 |
|---|------|------|
| #1 | 局 ≠ 副口径 | GUA-033 定音：1 局 = 双上过关 |
| #3 | 目标基线 | M1 对 lalala >50% 队胜率（**已被 PHASE3 升级为 >90%**） |
| #5 | M1 胜率基线 | "0%(0/88)" 已知失败基线 |
| #6 | T7/T8/T9 测试 | 全部 0% 胜率，GUA-022 根因隔离结论：「非根因」 |

### 目标升级矛盾
- **旧目标**：M1 对 lalala >50% 队胜率（COMMANDER_NOTES #5）
- **新目标**：M1 对 lalala >90% 队胜率（PHASE3 计划 2026-05-24）
- **待确认**：是否仍以 M1 为主线

### P0 代码改动三件套
1. `choose_bomb` 优化
2. `context` 补全
3. `combine_handcards` 修复

## 关联页面
- [[agent-bootstrap-workflow]] — 5 步读法
- [[gua-022]] — 根因隔离结论
- wiki-minimax/entities/gua-033.md — 局/副口径
- [[v7-current-state]] — V7 状态
