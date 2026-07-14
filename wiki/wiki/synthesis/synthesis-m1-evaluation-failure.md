---
type: synthesis
title: "M1 评估失效根因诊断"
sources:
  - docs/guandan-brain/notes/AUTO_RESTART_SYSTEM_STATUS.md
  - docs/guandan-brain/notes/AUTO_RESTART_WORKFLOW_GUIDE.md
tags:
  - synthesis
  - m1
  - root-cause
  - evaluation-failure
status: current
related_gua: []
date: 2026-06-18
---

# M1 评估失效根因诊断

## 现象
- M1 报告胜率 0%（evaluation_failed）
- M1 过度预测：512/512 卡牌（355.37 倍）
- M1 高损失值：191,825.22 / 958,804.55

## 根因（区分**症状 vs 病灶**）

| 层级 | 现象 | 性质 |
|------|------|------|
| 症状 | 胜率 0% | 表面 |
| 症状 | 512/512 过度预测 | 输出异常 |
| **病灶** | game_info 无 game_result 字段 | **评估器基础设施 bug** |
| 病灶 | 评估器 result={} | **数据流断裂** |

## 关键澄清
- **M1 评估器失效 ≠ 模型能力为 0**
- 过度预测是**评估反馈缺失**导致的训练目标崩坏
- 高损失是**无正确标签**下的梯度爆炸

## ⚠️ 命名陷阱
- **M1 (stage7 旧管线) ≠ M3 (现役决策引擎) ≠ V7 (NN 引擎)**
- M1 文档日期 2026-01-12，与 V7/M3 MOC（2026-06-17）相隔 5 个月
- M1 是历史管线，**不应作为 V7 现状的参考**

## 修复方向
1. 优先修 game_info 数据流（注入 game_result 字段）
2. 再考虑是否值得挽救 M1 旧管线（vs 直接放弃、转 V7）
3. 建立"评估器健康检查"作为工作流的前置 gate

## 关联页面
- [[auto-restart-workflow]]
- [[AUTO_RESTART_SYSTEM_STATUS-summary]]
- wiki/entities/engine-v7.md（V7 ≠ M1）
