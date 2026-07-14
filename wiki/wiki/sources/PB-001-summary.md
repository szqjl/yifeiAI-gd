---
type: source-summary
title: "PB-001：拆炸时序押后（方法论摘要）"
status: current
date: 2026-06-22
sources:
  - docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md
tags:
  - source-summary
  - playbook
related_gua:
  - GUA-072
  - GUA-080
related_playbook: PB-001
---

# PB-001-gua072-bomb-break-timing.md 摘要

## 文件元信息

- **路径**：`docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md`
- **字符数**：3087
- **类型**：Playbook（首个升格范例）
- **关联 GUA**：GUA-072（拆炸阈值）+ GUA-080（拆炸取舍）

## 核心提取

### 一句话总结

**拆炸问题应分两步走：先定阈值（GUA-072），再定时序（PB-001 / GUA-080）。时序问题用「押后拆炸」解决，而不是回头改阈值。**

### 关键论点

1. **GUA-072 已关闭阈值问题**：`_safe_to_break_bomb` 阈值 ≤10（J/Q/K/A 保护）
2. **剩余问题属于「时序」**：阈值已定，但「什么时候拆」仍不确定
3. **PB-001 核心**：BOMB_FIRST 分支前不消耗炸弹资源
4. **决策树**：
   - 识别所有炸弹 → 标记候选集 → BOMB_FIRST 分支（保炸 vs 拆炸）→ 评分
5. **验证**：`scripts/checks/check_grouping_engine.py`（WF-05 唯一验收入口）

### 关联实体

- **代码**：`src/v/nn/features/grouping_engine.py`
- **commit**：f91f0af（拆炸时序修复）
- **降级触发**：`src/v/nn/features/memory_tracker.py`（grouping_engine 导入失败）
- **关联分析脚本**：`scripts/analysis/compare_sf_detection_vs_multipass.py`

### 升格条件满足度

| 条件 | 状态 |
|------|------|
| 同类问题再现 | ✅ GUA-072 + GUA-080 |
| 可复现验证命令 | ✅ `check_grouping_engine.py` |
| 反例 | ✅ 「先三连对后炸弹」的错误做法 |
| 人类定音 | ✅ 「不改阈值改时序」 |

## 引用建议

本文档是 [[playbook-pb-001]] 的原始来源，详细决策树与反例分析请查阅原文。

## 关联阅读

- [[playbook-pb-001]] — 渲染后的概念页
- [[playbook-methodology]] — WF-11 升格方法论
- [[gua-080]] — PB-001 沉淀后产出的新 GUA
