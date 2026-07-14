---
type: query-answer
title: "WF-12 yf2 handCards logs"
date: 2026-07-03
sources:
  - wiki/queries\query-0620-2342-yf-记录怎么查-找不到yf-的game-record.md
  - wiki/concepts\wf12-decision-trace.md
  - wiki/concepts\wf-12-decision-trace.md
  - wiki/queries\query-0630-1529-platform-使用说明-tribute-back-initial-hand-.md
  - wiki/sources\WF-12-yf-decision-trace-summary.md
  - wiki/entities\engine-m2.md
  - wiki/sources\v7-system-fixes-summary.md
  - wiki/sources\工作流-summary.md
  - wiki/workflows\wf-12-decision-trace.md
  - wiki/concepts\decision-trace-taxonomy.md
---

# WF-12 yf2 handCards logs

# WF-12 yf2 handCards 决策链路分析

根据 Wiki 内容，**WF-12 是单步微观决策还原工作流**，专门用于分析"**这一个动作为什么是这样选出来的**"。以下是关于 yf2 handCards 相关决策链路分析的关键信息：

---

## 一、WF-12 核心定位

WF-12 关注的是 **yf（yf1/yf2）在某个具体动作的决策链路还原**，特别是 **handCards（手牌）上下文下的单步 action 决策**。

| 维度 | 内容 |
|------|------|
| **粒度** | 1 个 action（一次出牌/跟牌/PASS） |
| **输入** | 单步 action + 上下文（**手牌 handCards**、last_play、curRank、玩家身份） |
| **输出** | 决策链代码层还原报告 + R-D 根因分类 + 修复建议 |
| **工具** | 决策日志 + `UltimateWinRateEngineV7.decide()` 源码对照 |

---

## 二、yf2 handCards 相关的关键背景

### 1. handCards 字段定义 [{4}]

| 字段 | 来源 | 说明 |
|------|------|------|
| `handCards` | `gameStart.notify` | 27 张（发牌后、还贡前） |
| `initial_hand` | 贡前手牌 | 发牌瞬间固定，跨主牌阶段持续作为基准 |
| `current_hand` | 主牌阶段 | `initial_hand - played_cards`（易错点：贡牌未调整） |

### 2. yf2 在 record 中的位置 [{1}]

```json
{
  "players": [
    {"seat": 0, "client": "yf1_v7.py"},
    {"seat": 1, "client": "yf2_v7.py"},   // ← yf2 在 seat=1
    ...
  ],
  "rounds": [
    {
      "actions": [
        {"player": 1, "type": "play", "cards": [...]}  // seat=1 即 yf2
      ]
    }
  ]
}
```

---

## 三、WF-12 在 yf2 handCards 分析中的标准流程

### §1 三源交叉验证（evidence triple）[{9}]

针对 yf2 的 handCards 决策，需要整合：

1. **`actions[]`**：原始动作流（record 中 seat=1 的所有动作）
2. **`my_decisions[]`**：yf2 自报决策（NN 输出 vs 规则兜底）
3. **客户端 log**：如 `logs/yf2_v7_*.log`

### §2 决策管线还原（L0~L8）

将 yf2 在 handCards 状态下的决策逐层还原到 L0~L8：

| 层级 | 内容 |
|------|------|
| **L0** | grouping_engine_v2（组牌引擎） |
| **L0b** | MemoryTracker / guard（场态判断，包括 handCards 张数校验） |
| **L1** | EndgamePreprocessor（残局管线） |
| **L2** | recommendation（推荐管线） |
| **L2′** | `_group_consistency_filter`（一致性过滤） |
| **L3** | guard 校验层 |
| **L4** | filter_action_list（候选过滤） |
| **L6** | 规则知识接入 |
| **L7** | `_heuristic_select`（启发式选择） |
| **L8** | 兜底 fallback |

### §3 R-D01~R-D08 根因归因 [{10}]

| 标签 | 描述 | 常见层 |
|------|------|--------|
| **R-D01** | 推荐被 mask 挡（一致性拦截） | L2′ |
| **R-D02** | 推荐缺失（候选为空） | L4 |
| **R-D03** | 残局未命中 | L1 |
| **R-D04** | 组牌锁死（无合法候选） | L0 |
| **R-D05** | 启发式劣选 | L7 |
| **R-D06** | 场态误读 | L0b / L3 |
| **R-D07** | 记录贡还（漏记贡牌） | L0b |
| **R-D08** | 知识未接入 | L6 / L7 |

---

## 四、yf2 handCards 相关历史 GUA 锚点

| GUA | 问题 | 决策链路命中 | 根因标签 |
|-----|------|--------------|----------|
| **GUA-062** | 卡2级 80.5% Single 决策 | L6 → L7 → L8 | R-D05（启发式劣选）+ R-D08（知识未接入） |
| **GUA-075** | card_mask Dict 键冲突 | L0 → L2 → L2′ → L4 | R-D01（推荐被 mask 挡） |
| **GUA-078** | 残局管线 L1 行为记录 | L1 | R-D03（残局未命中） |
| **GUA-081** | 四炸 `8888` 压 `666+22` 缺 fallback → actIndex=116 | L8 | R-D08（知识未接入，兜底缺失） |

---

## 五、实操命令速查

### 1. 定位 yf2 的 handCards 决策日志

```bash
# 1. 确认分支（必须 v7-dev 看 yf2_v7.py）
git branch --show-current

# 2. 找 yf2 的 record（M3 在 game_records/，V7 在 game_records_v7/）
grep -l "yf2_v7" game_records_v7/*.json | tail -5

# 3. 提取 yf2 的 actions（seat=1）
cat game_records_v7/<record>.json | python -c "
import json, sys
data = json.load(sys.stdin)
for r in data['rounds']:
    for a in r['actions']:
        if a['player'] == 1:
            print(r['round_idx'], a)
"

# 4. 客户端 log
ls -lt logs/yf2_v7_*.log | head
```

### 2. 副级 + 局级分析（V7 必走）

```bash
# 局级
python scripts/analysis/analyze_v7_rounds.py \
  --records game_records_v7/ \
  --output reports/yf2_v7_rounds.csv

# 副级（避免「局 ≠ 副」陷阱）
python scripts/analysis/analyze_v7_round_levels.py \
  --records game_records_v7/ \
  --output reports/yf2_v7_round_levels.csv
```

### 3. 卡 2 级切片统计（典型 WF-12 触发场景）

```bash
python scripts/analysis/verify_actionlist_pass_only.py
```

---

## 六、关键注意事项

1. **handCards 易错点（GUA-067）** [{4}]：`current_hand = initial_hand - played_cards` 无法处理贡牌事件。WF-12 分析时需确认 handCards 张数 = 27（贡后）且不含已贡出牌。

2. **分支与目录对应** [{1}]：
   - `m-dev` + `yf2_m3.py` → `game_records/`
   - `v7-dev` + `yf2_v7.py` → `game_records_v7/`

3. **"pytest 通过 ≠ 实战有效"** [{2}]：WF-12 强调关单标准不能以 replay 逐步一致作为通过标准，必须用决策管线标注失败层 + 套用 R-Dxx 标签。

4. **复现证伪纪律** [{2}]：南邮 actionList 报告 44 例经 WF-12 复现 0 例成立 → 需文档归档 + 勘误。

---

## 七、TL;DR

**WF-12 下的 yf2 handCards 决策分析，标准路径是：**

1. 定位 yf2 record（确认分支 + 目录匹配）
2. 提取 seat=1 的 actions[] + handCards 上下文
3. 三源交叉验证（actions + my_decisions + 客户端 log）
4. 逐层还原到 L0~L8 决策管线
5. 套用 R-D01~R-D08 根因标签
6. 输出改良路径建议（**禁止单局特例**）

如果你有具体的 yf2 handCards 决策异常场景（如"为什么这一步 yf2 没出炸"），告诉我 record 文件名或局/副编号，我可以帮你走完整的 WF-12 流程。
