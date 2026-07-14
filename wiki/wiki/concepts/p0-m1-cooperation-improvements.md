---
type: concept
title: "M1 P0协作能力改进"
sources:
  - docs/analysis/agent-sessions/p0_complete_summary.md
  - docs/analysis/agent-sessions/P0_DIAGNOSIS_20260528.md
  - docs/analysis/agent-sessions/P0_IMPLEMENTATION_COMPLETE_20260528.md
  - docs/analysis/agent-sessions/p0_tuning_report.md
tags:
  - m1-engine
  - cooperation
  - p0-improvements
  - three-layer-strategy
status: current
related_gua:
  - GUA-033
date: 2026-06-18
---

# M1 P0 协作能力改进

## 设计哲学

M1 引擎的 P0 改进不是"修 bug"，而是**补能力层级**。M1 0% 胜率根因不在决策逻辑，而在 Lv2（队伙联动）能力的彻底缺失。

### 三层战略对照

| 层级 | 能力 | M1 状态 | 改进方式 |
|------|------|---------|----------|
| Lv1 | 个别决策 | ✅ 完整 | — |
| Lv2 | 队伙联动 | ❌ 缺失 | P0 改进 |
| Lv3 | 全局对抗 | ⚠️ 弱 | 待后续 |

## P0 四件套

### P0-① 历史信息追踪

- **模块**：`history_tracker.py`（265 行 / 6991 bytes）
- **职责**：追踪已出牌，推断剩余牌组成
- **价值**：决策时知道"对手可能有什么牌"
- **典型应用**：避免被炸、识别对手牌型弱点

### P0-② 残局两手规划

- **模块**：`endgame_planner.py`（229 行 / 7413 bytes）
- **职责**：当自己剩 ≤ 2 手时，提前规划出完顺序
- **集成点**：`EndgameLateActiveHandler`
- **价值**：避免"出大牌后被压死"或"留小牌走不掉"
- **M3 教训**：M3 22 副全负，部分因缺此能力

### P0-③ 主动传牌给队友

- **模块**：`teammate_opportunity_finder.py`（176 行 / 7272 bytes）
- **职责**：识别队友可能跑牌的机会，主动配合
- **集成点**：4 个 PassiveHandler（**关键设计选择**）
- **核心洞察**：传牌本质是**协作非攻击**
  - 集成到 Passive（接牌方）而非 Active（出牌方）更合理
  - ActiveHandler 出牌时只需判断"出哪张"，是否传牌由接牌侧判断
- **覆盖位置**：
  - `OpeningPassiveHandler` @ L524-547
  - `MidEarlyPassiveHandler` @ L1428-1455
  - `MidLatePassiveHandler` @ L2303-2326
  - `EndgameEarlyPassiveHandler` @ L2940-2963

### P0-④ 主动炸弹控场（增强）

- **模块**：`bomb_strategy.py` 增强（+20 行 / 13889 bytes）
- **职责**：识别炸弹的最佳使用时机
- **状态**：✅ 实现但 **M1 未激活**（V5/V6 预留）
- **GUA 警示**：标记"预留"而非"完成"

## 防御性编程

所有 P0 新代码包 `try/except`：
- 模块故障不导致引擎崩溃
- 主决策循环优先级最高，新功能失败必须可降级
- 激进调优过度触发的风险被 try/except 兜底

## 调优哲学

| 调优取向 | 风险 | 收益 |
|----------|------|------|
| **保守** | 维持 0% 胜率，无法验证 | — |
| **激进** | 过度触发（try/except 保护） | 可能发现有效信号 |

**结论**：在 0% 基础线上，激进调优的期望收益 > 风险。

| 参数 | 保守 | 激进（采用） |
|------|------|--------------|
| `endgame_threshold` | 12 | **10** |
| `teammate_remain` | 15 | **12** |
| `card_power` | 4 | **3** |

## 验证教训（关键）

**"代码完成" ≠ "代码生效"**

P0-① 和 P0-② 在 `p0_verification_status` 中第一轮验证**触发次数=0**。这暴露两个问题：
1. 配置/路径可能有问题
2. 验证脚本可能根本没运行到对应模块
3. 离线平台端口阻塞使真实对局验证无法进行

**Wiki 原则**：所有策略改动必须经过离线批跑验证胜率，不能仅靠代码审查。

## 关联

- [[engine-m1]] — 改进实施目标
- [[module-history-tracker]] / [[module-endgame-planner]] / [[module-teammate-opportunity-finder]] / [[module-bomb-strategy]]
- [[concept-batch-evaluation]] — 验证方法论
- wiki-minimax/entities/gua-033.md — 批跑评测 GUA
- synthesis-m1-p0-iteration-story — 完整故事
