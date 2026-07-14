---
type: source-summary
title: "fixes/ 目录整体概览"
sources:
  - docs/fixes/EVALUATOR_COMPATIBILITY_REPORT.md
  - docs/fixes/GAME_RECORD_SAVE_FIX.md
  - docs/fixes/GAME_RECORD_VICTORYNUM_CHECK.md
  - docs/fixes/V7_GUI_PATH_VALIDATION_FIX.md
tags:
  - fixes
  - overview
  - doc-cluster
status: current
related_gua: []
date: 2026-06-18
---

# fixes/ 目录整体概览

## 收录文件

| 文件 | 主题 | 关联引擎/模块 |
|------|------|---------------|
| evaluator-compatibility-report-summary | 评测器兼容性 | 评测器/批跑 |
| game-record-save-fix-summary | 对局记录保存 | 数据持久化 |
| game-record-victorynum-check-summary | 胜局数字段校验 | 数据校验 |
| v7-gui-path-validation-fix-summary | GUI 路径校验 | V7 引擎/GUI |

## 模式识别

- **数据层 fix 集中**：`GAME_RECORD_*` 系列说明对局记录是反复出问题的模块
- **V7 起步阶段**：`V7_GUI_PATH_VALIDATION_FIX` 表明 V7 仍处于可用性打磨期
- **评测链 fix**：`EVALUATOR_COMPATIBILITY_REPORT` 影响 wiki-minimax/concepts/batch-evaluation.md 的可信度

## 待办

- 将这批 fix 与 GUA-001~061 编号体系做交叉映射
- 在 overview 页面中归入"V7 引擎迭代"时间线
