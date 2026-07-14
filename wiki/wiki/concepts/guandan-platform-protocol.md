---
type: concept
title: "v1006 掼蛋平台协议与消息格式"
sources:
  - docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md
tags:
  - platform
  - protocol
  - v1006
  - websocket
  - actindex
status: current
related_gua:
  - GUA-042
date: 2026-06-18
---

# v1006 掼蛋平台协议与消息格式

## 平台规格

| 项目 | 规格 |
|------|------|
| 平台 | 南京邮电大学掼蛋 AI 算法对抗平台 |
| 版本 | v1006（内测） |
| 通信 | WebSocket + JSON |
| 端口 | 23456 |
| 参赛 | 4 人 2v2（0+2 vs 1+3） |

## 队伍坐标

```
座位布局：
   0 (我方)    1 (敌方)
   2 (队友)    3 (敌方)

teammate_pos = (myPos + 2) % 4
```

- 0 号位与 2 号位组队（同上家或下家看具体规则）
- 1 号位与 3 号位组队
- **A 级双上** = 1 局结束

## actIndex 协议

### 核心规则
- 服务端下发合法动作列表 `actionList`（JSON 数组）
- 客户端**回传 actIndex（下标）**而非牌型
- 下标 0/1/2/... 对应合法动作
- PASS 是 actionList 中的独立项（标记"不要"）

### 为什么用下标？
- 避免客户端/服务端牌型描述不一致
- 服务端无需解析牌型字符串
- 168 伪动作上限（策略网络输出维度）

### 协议示例
```json
// 服务端下发
{
  "actionList": [
    {"type": "PASS"},
    {"type": "SINGLE", "card": "H5"},
    {"type": "PAIR", "cards": ["H6", "H7"]},
    ...
  ]
}

// 客户端回传
{
  "actIndex": 1
}
```

## 关键消息类型

| 消息 | 方向 | 说明 |
|------|------|------|
| 游戏开始 | S→C | 初始手牌、curRank、座位 |
| 出牌请求 | S→C | actionList |
| 出牌响应 | C→S | actIndex |
| 游戏结束 | S→C | 胜负、双上信息 |
| 进贡通知 | S→C | 进贡/还贡/抗贡 |
| 重连 | 双向 | **平台无重连设计** |

## 平台约束

| 约束 | 含义 |
|------|------|
| 23456 端口 | 唯一接入点 |
| 4 客户端同局 | 每个客户端独立连接 |
| 无重连 | 断线即弃权（一局） |
| 无错误处理 | 客户端必须保证局内 100% 可用 |
| curRank 4 级 | selfRank > oppoRank > curRank > 牌型点数 |
| 168 伪动作上限 | 策略网络输出维度 |

## 局 vs 副的口径

- **局**：完整对抗（A 级双上结束）
- **副**：局内的单回合出牌
- **关键**：进贡/还贡是**局内**环节，不算独立局
- 胜率统计：必须明确是"局胜率"还是"副胜率"（参见 wiki-minimax/concepts/batch-evaluation.md）

## 与现有 Wiki 的关系

### 已澄清的待澄清问题
- **yf_v5 与 yf1_m3**：v1006 平台是统一接入，所有客户端（yf_v5、yf1_m3 等）通过 23456 端口连接
- **WebSocket 重连模式**：平台**无重连设计**，与现有 [[websocket-reconnect-pattern]] 冲突

### 平台层 vs 项目层
- 平台层：v1006 23456 端口协议（不可改）
- 项目层：客户端实现（可改）
- V7 引擎可继承 yf_v5 的 WebSocket 模式，但必须用 v1006 协议

## 交叉引用

- 平台使用说明 → [[guandan-platform-usage-summary]]
- V7 行为边界 → [[gua-042]]
- WebSocket 通信 → [[module-websocket-manager]]
- 批跑胜率口径 → wiki-minimax/concepts/batch-evaluation.md
