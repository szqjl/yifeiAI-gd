---
type: source-summary
title: "M3 诊断报告 (M3_DIAGNOSIS)"
sources:
  - docs/guandan-brain/M3_DIAGNOSIS.md
tags:
  - source-summary
  - engine-m3
  - diagnosis
  - bug-list
status: current
related_gua:
  - GUA-024
  - GUA-025
  - GUA-026
  - GUA-027
  - GUA-028
  - GUA-029
  - GUA-030
  - GUA-031
date: 2026-06-18
---

# M3 诊断报告 (M3_DIAGNOSIS)

## 文件定位
M3 决策引擎的**完整诊断**，含七致命 Bug、场态消息重大发现、勘误记录。是 Wiki 核心源。

## 文档演进
- **首版**：2026-05-27
- **增补**：2026-05-30（GUA-027 场态重算）
- **勘误**：2026-06-01（BUG3 更正）
- ⚠️ Wiki 版本需**以最新（2026-06-01 勘误后）为准**

## M3 引擎概况
- **实现位置**：`src/decision/m3_decision_engine.py`、`src/m/m3/`
- **定位**：当前主交付引擎
- **跑分结果**：22 副 **0 胜** vs lalala
- 详见 wiki-minimax/entities/engine-m3.md

## M3 七致命 Bug

| Bug # | 描述 | 状态 |
|-------|------|------|
| BUG1 | `_active` 下标 -1 → 1 | 待修 |
| BUG2 | 残局两手组合缺失 | 待修 |
| BUG3 | ~~"2"=2 曾被列为 bug~~ | **已勘误，非 bug**（CARD_VALUE_S2V 默认值正确） |
| BUG4 | 无队友协作 | 待修 |
| BUG5 | 炸弹消极（不会主动用炸） | 待修 |
| BUG6 | 场态消息用法 | **GUA-027 已修** |
| BUG7 | [待补] | 待修 |

## ⚠️ 重要勘误
**BUG3 ("2"=2)** 在 2026-06-01 被用户纠正并**移出 bug 列表**：
- `card_val[rank] = 15`（级牌 override，高于 A=14）
- `CARD_VALUE_S2V` 中 `"2"=2` 是**正确默认值**
- Wiki 若已记录"2=2 是 bug"必须更正

## 场态消息重大发现（GUA-027 修复）
- **greaterAction 语义**：本圈当前最大一手 = 被动出牌要压的目标
- M3 曾**误用** `curAction[1]` 算 `curVal`
- 修复后使用 `beatAction` 重算场态
- 详见 greaterAction 语义、[[module-trick-state]]

## playArea 交叉校验
- `publicInfo[].playArea` 是场上真相
- M3 原未用此兜底服务器 `greater` 错误
- 详见 playArea 交叉校验

## 队胜率对照
- M1：**0/12** 队胜
- M3：**7/10** 队胜（同机对照）
- 结论：M1 frozen，M3 为主交付

## 客户端异常静默
- `src/communication/yf1_m3.py` 异常被 `except` **静默捕获**
- 排查 Bug 时需特别注意日志被吞

## 关联
- 引擎实体：wiki-minimax/entities/engine-m3.md
- BUG1 关联：[[module-m3-decision-engine]]
- 场态修复：[[module-trick-state]]
- M2 桥接：[[synthesis-m2-to-m3-migration]]
