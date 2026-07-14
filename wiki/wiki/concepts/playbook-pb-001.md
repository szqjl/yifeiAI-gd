---
type: concept
title: "PB-001：拆炸时序押后"
status: current
date: 2026-06-22
sources:
  - docs/guandan-brain/playbooks/PB-001-gua072-bomb-break-timing.md
  - docs/guandan-brain/playbooks/README.md
tags:
  - playbook
  - bomb
  - timing
  - v7
related_gua:
  - GUA-072
  - GUA-080
related_workflow: WF-11
---

# PB-001：拆炸时序押后

## 核心论断

> **策略分支前不要消耗「本应由分支决定」的资源。**

应用到拆炸问题：

- **不要**在还没决定「保炸 vs 拆炸」之前，就先把炸弹消耗在三连对检测中
- **应该**先识别炸弹 → 进入 BOMB_FIRST 分支 → 在分支内决定保炸或拆炸

## 适用范围

- V7 `grouping_engine.py` 任意涉及「炸弹 vs 其他牌型」取舍的场景
- 类似模式的泛化：「分支决定权」早于「资源消耗」的所有情形

## 不适用范围

- 炸弹数量确定（无需分支）的简单情形
- 其他引擎版本（M3 / M1）的拆炸逻辑（M3 走规则引擎，时序问题不显著）

## 决策树

```
进入组牌枚举
    │
    ├── 1. 识别所有炸弹（4 张 / 王炸）
    │
    ├── 2. 标记「炸弹候选集」B
    │
    ├── 3. 分支决策（BOMB_FIRST）
    │      │
    │      ├── 3a. 保炸方案：保留 B 中所有炸弹，其他牌型自由枚举
    │      │
    │      └── 3b. 结构优先方案：尝试拆 B 中炸弹凑三连对等
    │
    └── 4. 评分对比，选最优
```

## 反例（违反 Playbook 的代价）

**错误做法**：先做三连对检测 → 用剩下的牌识别炸弹 → 最后对比方案。

**代价**：
- 三连对检测会把炸弹「拆散」消耗掉
- 即使后续识别出炸弹，也无法还原
- 导致保炸方案永远产出空集，决策权被提前剥夺

## 验证命令

```bash
python scripts/checks/check_grouping_engine.py
```

应通过且覆盖以下 case：
- 5 张中炸 + 可组三连对场景
- 6 张中炸 + 多种拆法场景
- 王炸 + 任意手牌（不应被任何牌型吃掉）

## 历史定音

| 日期 | 定音内容 | 来源 |
|------|----------|------|
| 2026-06-22 | 「不改阈值改时序」 | GUA-080 completion doc |

## 关联 commit

- `f91f0af` — `grouping_engine.py` 拆炸时序修复（PB-001 的代码兑现）

## 升格路径

PB-001 是 [[playbook-methodology]]（WF-11）的**首个升格范例**，完整升格条件：

1. ✅ 同类问题再现：GUA-072（阈值）+ GUA-080（时序）
2. ✅ 可复现验证命令：`check_grouping_engine.py`
3. ✅ 反例：见上
4. ✅ 人类定音：「不改阈值改时序」

## 关联阅读

- [[playbook-methodology]] — WF-11 方法论
- [[gua-072]] — 拆炸阈值（PB-001 解决的前置问题）
- [[gua-080]] — 拆炸时序（PB-001 沉淀后产出的新 GUA）
- [[grouping-engine-architecture]] — 24 维主路径架构
