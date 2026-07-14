---
type: concept
title: "离线平台 v1006 协议与参数"
sources:
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
  - docs/knowledge/platform-data-interpretation.md
tags:
  - v1006
  - 平台
  - 协议
  - 离线
status: current
related_gua: []
date: 2026-06-21
---

# 离线平台 v1006 协议与参数

## 平台信息
- 可执行文件：`offline_platform/guandan_offline_v1006.exe`
- 官方文档：`掼蛋平台使用说明书v1006.pdf`

## 关键参数 N 的含义

> **N = 局数**（不是副数！）

### 实测验证
- 命令行参数 `target-games 1` → 实际打完 **59 副**
- 1 局从 2 打到 A 双上，平均约 6 副 → 50 次循环 ≈ 300 副
- 实测 59 副表明平台在某种条件下提前终止（或取的是局数而非副数）
- 与 [[platform-data-interpretation]] 中的实测结论一致

### 官方定义（说明书）
> "游戏次数（一方从 2 打到 A，并且双下）"

⚠️ 此定义与实测"局数"略有差异，实测应以 [[platform-data-interpretation]] 为准。

## 协议关键字段

| 字段 | 含义 | 用途 |
|------|------|------|
| `order` | 本副完牌顺序（4 个座位名次） | 判定本副胜负 |
| `curRank` | 当前级数（2-10、J、Q、K、A） | 判定本队级别 |
| `selfRank` | 本队的级数 | 用于升级计算 |
| `oppoRank` | 对方级数 | 用于升级计算 |
| `selfSeat` | 本方座位（0/2 或 1/3） | 识别本队 |
| `oppoSeat` | 对方座位 | 识别对手 |
| `tribute` | 进贡信息 | 跨副进贡/还贡 |
| `target-games` | 命令行参数 | 控制局数 |

## 协议特征
- **客户端需跨副跟踪 curRank 变化**才能判定局结束（单副消息无法判定局结束）
- 升级后的 curRank 变化发生在**下一副开始前**
- `order` 是单副内确定信息，无需跨副状态

## 与 batch_executor 的关系
- `executor.py` 通过前缀匹配 `_count_new_paired_games()` 统计场次
- `game_scores_m*.json` 中 `rounds[]` 存副级数据，`games[]` 存局级数据
- yf1 负责写 JSON，yf2 仅打日志（**race condition 规避**）

## 关联页面
- [[局不等于副]]：N=局数的语义背景
- [[game-scoring-tracking]]：协议字段如何被消费
- [[batch-evaluation]]：批跑评测如何调用平台
- [[platform-data-interpretation]]：N 含义的实测结论
