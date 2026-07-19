---
type: synthesis
title: "V8 GUA-150 全链路闭环 + Kaggle 首公开"
sources:
  - docs/guandan-brain/handoffs/2026-07-18-v8-gua150-impl-kaggle-publish.md
  - docs/analysis/WF-12-20260716222448436062-副12-yf1-Q1让道决策分析.md
  - docs/analysis/WF-12-20260716222448436062-副12-yf1-Q0让道决策分析.md
  - docs/guandan-brain/ISSUES.md
tags:
  - synthesis
  - v8
  - gua-150
  - kaggle
  - milepost
  - patch-spiral
status: current
related_gua:
  - GUA-135
  - GUA-150
  - GUA-091
  - GUA-057
date: 2026-07-19
---

# V8 GUA-150 全链路闭环 + Kaggle 首公开

## 一句话定位

**2026-07-18 是项目的"双里程碑日"**：规则补丁的最近一次有效闭环（GUA-150）+ NN 训练数据底座的首批公开（Kaggle 184 副）。

## 事件 A：GUA-150 全链路闭环

### 根因 R-D09
- **触发**：`endgame_decide.py:2662` 命中 GUA-135 self_sprint 一刀切 PASS
- **症状**：未比较 self/teammate 冲刺路径长度
- **修复**：
  - `endgame_decide.py` L3416-3424 情形 2 改 intent 比较
  - 新增 `_find_min_non_bomb_lead_action`、`_estimate_self_num_rounds`
- **验证**：`test_gua150_self_sprint_short_path.py` 6/6 pytest 通过；GUA-135 28/28 未破坏
- **提交**：commit `ad52a50` → v8-dev

### 5 问准入全部通过

| 问 | 答 |
|----|----|
| 一类局面？ | ✅ 残局冲刺决策 |
| 可沉意图层？ | ✅ _stage_mid_dispatch |
| P0 止血？ | ✅ R-D09 根因 |
| pytest + trace？ | ✅ 6/6 单元测试 |
| 迁移出口？ | ✅ GUA-091 intent 体系已激活接收 |

### Q0 / Q1 报告分歧裁定

| 维度 | Q0 报告 v1 | Q1 报告（正式结论） |
|------|------------|---------------------|
| 触发行 | L962（兜底） | **L2662（GUA-135）** |
| 根因 | Q0 兜底 PASS | **GUA-135 self_sprint** |
| 修复 | GUA-151 候选 | **GUA-150** |

→ Q1 报告为正式结论，Q0 v2 已修订。

## 事件 B：Kaggle 首公开

### 数据集
- **名称**：`philsz/guandan-v8-data-exploration`
- **规模**：
