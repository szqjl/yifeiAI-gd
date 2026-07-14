---
type: concept
title: "胜负追踪架构（副级+局级）"
sources:
  - docs/analysis/agent-sessions/guandan-basic-knowledge.md
tags:
  - 追踪
  - 架构
  - 副级
  - 局级
status: current
related_gua: []
date: 2026-06-21
---

# 胜负追踪架构（副级 + 局级）

## 双轨追踪模型

掼蛋 AI 引擎需要在两个层级追踪游戏状态：

| 层级 | 触发条件 | 输出 | 存储位置 |
|------|----------|------|----------|
| **副级**（round） | 一副牌打完（4 人完牌） | `order`、升级数 | `game_scores_m*.json` 的 `rounds[]` |
| **局级**（game） | A 级双上 / A↔2 循环满 50 次 | 胜负 + 升级轨迹 | `game_scores_m*.json` 的 `games[]` |

⚠️ 局结束**只能跨副追踪** curRank 变化判定，单副消息无法判定局结束。

## 关键函数（以 M2 为例）

### 副级追踪
- `_update_level_info()` —— 根据 order 更新本队级数
- `_determine_round_result()` —— 判定本副 win/loss/draw
- `_save_round_result()` —— 写入 JSON
- `_load_scores()` / `_save_scores()` —— JSON 持久化

### 局级追踪
- `_detect_game_end()` —— 检测局结束（A 双上 / 对方双上 / A→2）
- `_save_game_end()` —— 写入局结果

### 批跑统计
- `_count_new_paired_games()` —— 统计已配对的局数（executor.py 调用）

## 副结果判定算法

```python
def _determine_round_result(order, self_seats):
    """
    order: list of 4 seat indices in finish order
    self_seats: set of {0, 2} or {1, 3}
    """
    self_indices = [order.index(s) for s in self_seats if s in order]
    if sum(self_indices) <= 2:  # 本队占据前两名 → 双上
        return 'win'
    if max(self_indices) >= 2:  # 对方占前两名 → 双下
        return 'loss'
    return 'draw'
```

## 局检测条件

| 条件 | 含义 |
|------|------|
| `curRank == A` 且本队双上 | **赢局** |
| `curRank == A` 且对方双上 | **输局**（A 级双下） |
| `curRank == 2` 且上副为 A | **输局**（A→2 循环触发） |
| 累计 A↔2 循环 50 次 | **平局** |

## yf1 / yf2 分工（race condition 规避）

| Agent | 职责 | 文件 |
|-------|------|------|
| **yf1_m*.py** | 写 JSON 持久化 | `game_scores_m*.json` |
| **yf2_m*.py** | 仅打日志 | 控制台 / log 文件 |

> **为什么不双向写？**
> yf1 和 yf2 是对家关系（同队），都观察到相同 `order`。若双方都写 JSON，在并发场景下可能产生 race condition。让 yf1 独占写、yf2 仅打日志，是简单可靠的协调策略。

## JSON 结构

```json
{
  "rounds": [
    {
      "round_id": 1,
      "order": [2, 0, 3, 1],
      "self_rank_before": 2,
      "self_rank_after": 5,
      "result": "win",
      "upgrade": 3
    }
  ],
  "games": [
    {
      "game_id": 1,
      "start_round": 1,
      "end_round": 6,
      "start_rank": 2,
      "end_rank": "A",
      "final_result": "win",
      "rounds_count": 6
    }
  ]
}
```

## 关联页面
- [[局不等于副]]：为何需要双轨
- [[guandan-basic-rules]]：规则侧的判定依据
- [[batch-evaluation]]：批跑如何消费这些数据
- [[engine-m2]]：M2 的实现
