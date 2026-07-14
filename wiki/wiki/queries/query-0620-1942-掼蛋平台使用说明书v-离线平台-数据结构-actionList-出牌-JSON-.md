---
type: query-answer
title: "掼蛋平台使用说明书v1006 离线平台 数据结构 actionList 出牌 JSON 协议字段"
date: 2026-06-20
sources:
  - queries/query-0619-2132-助攻-主公-role-组牌-出牌.md
  - concepts/concept-card-type-encoding.md
  - concepts/grouping-vs-playing-stage.md
  - concepts/guandan-platform-protocol.md
  - concepts/batch-evaluation.md
  - queries/query-0620-1043-V-角色判定-主攻-助攻-超弱牌-role-score-power.md
  - queries/query-0620-1942-掼蛋平台使用说明书-v-数据结构-牌面编码-card-encoding.md
  - sources/source-platform-data-interpretation-summary.md
  - concepts/dual-data-channel-recovery.md
  - queries/query-0619-0826-批跑脚本-命令-参数-批跑入口-batch-executor.md
---

# 掼蛋平台使用说明书v1006 离线平台 数据结构 actionList 出牌 JSON 协议字段

# 掼蛋平台 v1006 — actionList 出牌 JSON 协议字段

根据 Wiki 内容，v1006 平台的 **actionList**（合法动作列表）采用统一 3 元组结构下发，客户端**回传 actIndex（下标）**而非牌型[{1}][{2}]。

---

## 1. actionList 数据结构

服务端下发的 `actionList` 是 JSON 数组，每个元素代表一个合法动作：

```json
{
  "actionList": [
    {"type": "PASS"},
    {"type": "SINGLE", "card": "H5"},
    {"type": "PAIR", "cards": ["H6", "H7"]},
    ...
  ]
}
```

---

## 2. 出牌 3 元组通用结构

对于实际出牌（非 PASS），所有动作遵循 **`[type, rank, cards]`** 3 元组：

```json
["<type>", "<rank>", ["<card1>", "<card2>", ...]]
```

| 字段 | 含义 | 示例 |
|------|------|------|
| `type` | 牌型名 | `"Single"`, `"Pair"`, `"Bomb"` |
| `rank` | 级牌标记 | `"R"`=王炸无级牌, `"2"`-`"A"`=级牌点数 |
| `cards` | 牌面编码列表 | `["HR", "SB"]` |

---

## 3. 11 种牌型 JSON 对照表

| 牌型 | type | rank 示例 | cards 示例 |
|------|------|-----------|------------|
| 单张 | `Single` | `"A"` | `["HA"]` |
| 对子 | `Pair` | `"K"` | `["SK","DK"]` |
| 三张 | `Triple` | `"5"` | `["S5","D5","C5"]` |
| 三带二 | `Triple+Single` | `"7"` | `["H7","S7","D7","D3","S9"]` |
| 顺子 | `Straight` | `"R"` | `["H3","S4","D5","C6","S7"]` |
| 同花顺 | `Flush Straight` | `"R"` | `["H3","H4","H5","H6","H7"]` |
| 三连对 | `Consecutive Pairs` | `"R"` | `["H3","D3","S4","D4","H5","D5"]` |
| 钢板 | `Plate` | `"R"` | `["H3","D3","S3","S4","D4","C4"]` |
| 炸弹 | `Bomb` | `"9"` | `["H9","S9","D9","C9"]` |
| 天王炸 | `Bomb` | `"R"` | `["HR","HR","SB","SB"]` ⚠️ |
| 星级炸弹 | `Bomb` | `"R"` | `["H3","H4","H5","H6","H7"]` |

---

## 4. 关键字段特殊性

### ⚠️ 王炸编码
- 王炸 type 是 `Bomb`，但 **rank = `"R"`**（无级牌标记）
- **不参与级牌比较**，王炸 ≠ 同花顺 4 星
- 4 张王 = 2 大王(`B`) + 2 小王(`R`)

```json
["Bomb", "R", ["HR", "HR", "SB", "SB"]]
```

### ⚠️ PASS 是独立项
- PASS 是 `actionList` 中的独立元素（标记"不要"），**不属于 3 元组**
- 示例：`{"type": "PASS"}`

---

## 5. 牌面编码

| 字符 | 含义 |
|------|------|
| `H` | 红桃（Hearts） |
| `S` | 黑桃（Spades） |
| `D` | 方块（Diamonds） |
| `C` | 梅花（Clubs） |
| `B` | 大王（Big Joker） |
| `R` | 小王（Red Joker） |
| `2`-`10,J,Q,K,A` | 牌面点数 |

---

## 6. 进贡/还贡/抗贡 JSON 动作

进贡阶段使用单独的 JSON 格式（非出牌 3 元组）：

```json
{ "act": "Tribute",     "from": <seat>, "to": <seat>, "card": "S2" }
{ "act": "Back",        "from": <seat>, "to": <seat>, "card": "D7" }
{ "act": "AntiTribute", "player": <seat> }
```

---

## 7. 客户端响应：actIndex 协议

| 项目 | 说明 |
|------|------|
| **回传字段** | `actIndex`（整数下标） |
| **下标起点** | `0/1/2/...` 对应合法动作 |
| **设计意图** | 避免客户端/服务端牌型描述不一致；服务端无需解析牌型字符串 |
| **维度约束** | 168 伪动作上限（策略网络输出维度）[{4}] |

**响应示例**：
```json
{
  "actIndex": 1   // 表示选择 actionList[1] 对应的动作
}
```

---

## 引用
- [{1}] 牌型 JSON 编码（含王炸特殊性、3 元组结构）
- [{2}] v1006 平台协议（actIndex 回传、PASS 独立项、168 上限）
- [{3}] 牌型手册源摘要（11 种合法牌型定义）
- [{4}] v1006 平台参数与维度约束
