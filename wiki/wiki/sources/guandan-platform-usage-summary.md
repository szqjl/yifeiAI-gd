---
type: source-summary
title: "掼蛋AI算法对抗平台使用说明 - 摘要"
sources:
  - docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md
tags:
  - platform
  - protocol
  - v1006
  - websocket
status: current
related_gua:
  - GUA-042
date: 2026-06-18
---

# 掼蛋AI算法对抗平台使用说明 - 摘要

## 平台基本信息

| 项目 | 详情 |
|------|------|
| 平台名 | 南京邮电大学掼蛋 AI 算法对抗平台 |
| 版本 | v1006（内测） |
| 通信 | WebSocket + JSON |
| 端口 | 23456 |
| 参赛形式 | 4 人 2v2（0+2 vs 1+3） |

## 关键协议

### 队伍构成与坐标
- **teammate_pos = (myPos + 2) % 4**：队友永远在对家
- 0 号位与 2 号位组队，1 号位与 3 号位组队
- 己方打完即"双上"，完成 1 局

### 消息类型（WebSocket JSON）
- 比赛开始/重连/出牌请求/游戏结束
- **进贡/还贡/抗贡机制**（掼蛋特色）
- **级牌系统**（selfRank / oppoRank / curRank）
- A 级双上 = 1 局结束

### actIndex 协议
- 服务端下发合法动作列表 `actionList`
- 客户端回传 **actIndex（下标）** 而非牌型
- 下标 0/1/... 对应合法动作
- 涉及 PASS 时单独标记（"不要"）

## 与项目现状的关联

### 解决 Wiki 待澄清问题
1. **yf_v5 与 yf1_m3 关系**：v1006 平台是统一接入点，所有客户端（yf_v5、yf1_m3 等）均通过 23456 端口连接
2. **WebSocket 重连模式**：v1006 平台**无重连设计**——一局断线即弃权。这与 [[websocket-reconnect-pattern]] 描述的"自动重连"形成对比，平台层根本不允许重连

### 局 ≠ 副的口径
- **局**：完整对抗（A 级双上结束，缴贡/还贡是局内环节）
- **副**：一局内的单回合出牌
- M3 70% 胜率口径=局胜率，PHASE2 0% 胜率=局胜率

## 平台特性对 AI 设计的约束

| 约束 | 含义 |
|------|------|
| 4-head 网络 | action_logits / position_win_rate / action_value / long_term_reward |
| curRank 真值优先级 | 4 级（selfRank > oppoRank > curRank > 牌型点数） |
| 168 伪动作 | 合法动作列表上限，决定策略网络输出维度 |
| 无重连 | 客户端必须保证局内 100% 可用，无法依赖服务端补偿 |

## 交叉引用

- 平台协议细节 → [[guandan-platform-protocol]]
- V7 行为边界 → [[gua-042]]
- 现有平台通信层 → [[module-websocket-manager]]
