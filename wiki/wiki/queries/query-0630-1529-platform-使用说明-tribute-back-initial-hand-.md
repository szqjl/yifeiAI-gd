---
type: query-answer
title: "platform 使用说明 tribute back initial_hand handCards curRank"
date: 2026-06-30
sources:
---

# platform 使用说明 tribute back initial_hand handCards curRank

# Platform 使用说明：tribute / back / initial_hand / handCards / curRank

## 1. 协议位置

| 阶段 | 字段 | 来源 | Wiki 引用 |
|------|------|------|-----------|
| 发牌 | `handCards` (27 张) | `gameStart` notify | [{1}] |
| 副级牌 | `curRank` | `act.stage.play.curRank` | [{4}][{7}] |
| 进/还贡 | `tribute` / `Back` / `AntiTribute` | 跨副消息 | [{1}][{9}] |

---

## 2. initial_hand（贡前手牌）

- **定义**：来自 `gameStart.notify.handCards`（发牌后、还贡前的 **27 张**）[{1}]
- **特征**：发牌瞬间固定，跨主牌阶段持续作为基准

### ⚠️ 易错点（[[GUA-067]]）

`bc_dataset.py` 策略 2 用 `current_hand = initial_hand - played_cards` 只能减不能加：

| 场景 | 后果 |
|------|------|
| 已还走的牌 | 多算（应 remove） |
| 收到的贡牌 | 少算（应 add） |
| → 训练样本 | 手牌特征**偏移** |

**修复**：`adjust_initial_hand_for_tribute_back()` 在 4 条贡牌/还贡路径上实时调整 [{1}]

| 事件 | 动作 |
|------|------|
| 收贡 | add 收到的牌 |
| 收还 | add 还回的牌 |
| 进贡 | remove 贡出的牌 |
| 还牌 | remove 还回的牌 |

**关闭条件**：批跑验证 `initial_hand` 张数 = 27（贡后）且不含已贡出牌

---

## 3. tribute（进/还贡）动作协议

### JSON 结构（非出牌 3 元组，独立格式）[{9}]

```json
{ "act": "Tribute",     "from": <seat>, "to": <seat>, "card": "S2" }
{ "act": "Back",        "from": <seat>, "to": <seat>, "card": "D7" }
{ "act": "AntiTribute", "player": <seat> }
```

### V7 引擎相关缺陷

| GUA | 问题 | 状态 |
|-----|------|------|
| **GUA-086** | 进/还贡出牌 `remove` 路径传参错 | ✅ closed（2026-06-29）[{5}][{10}] |
| **GUA-087** | actions 流水漏 tribute 阶段出牌 | 📝 observation（documentation-only）[{2}] |

**GUA-086 修复**：引入 `extract_tribute_back_card` helper，从 `selected[2][0]` 提取单张，修复 4 处调用点（`yf1_v7.py` / `yf2_v7.py` 各 2 处）[{5}]

---

## 4. handCards（27 张）

- **来源**：`gameStart` notify
- **作用域**：本副开始时全场 4 人各 27 张
- **存储位置**：`initial_hand`（见上节）
- **消费方**：
---

## 5. curRank（本副级牌）

### 三等级字段区分（核心易错点）[{7}]

| 字段 | 含义 | 作用域 | 更新时机 |
|------|------|--------|----------|
| **`curRank`** | **本副**级牌 | 全场 4 人共用 | 每副开始由平台确定 |
| `selfRank` | 我方队伍等级 | 我方 2 人累积 | 仅**获胜方**升级时更新 |
| `oppoRank` | 对方队伍等级 | 对方 2 人累积 | 仅**获胜方**升级时更新 |

### 关键特性

- **逢人配** = `H + curRank`（红桃 + 当前级牌）
- 每副开始时由平台发牌决定，全场 4 人**共享同一 curRank**
- **不是**队伍等级（队伍等级看 selfRank/oppoRank）

### ⚠️ 升级路径（[[concept-pass-a-rule]]）[{7}]

| 胜负 | selfRank 变化 |
|------|--------------|
| 本队赢 | 按胜负升级表更新 |
| 本队输 | selfRank 不变 |
| 平局 | 双方都不变 |

> A 级必须双上才算赢局；连续 2 副未胜降回 2 [{8}]

---

## 6. 数据流汇总图

```
gameStart.notify
  └─ handCards (27张) → initial_hand
        ↓
     主牌阶段: current_hand = initial_hand - played_cards
        ↓
     跨副: tribute / back 事件
        ├─ GUA-086: remove 路径修复（closed）
        ├─ GUA-067: adjust_initial_hand_for_tribute_back()
        └─ GUA-087: actions 流水（documentation-only）
        ↓
     每副开始: curRank 更新（全场共用）
```

---

## 引用

- [{1}] [[GUA-067]] 训练数据 initial_hand 贡前手牌偏移
- [{2}] [[GUA-087]] actions 流水漏 tribute 阶段出牌
- [{4}] [[offline-platform-v1006]] 离线平台 v1006 协议
- [{5}] [[GUA-086]] 进/还贡出牌 remove 路径传参错
- [{7}] [[concept-three-rank-fields]] 三等级字段
- [{8}] [[query-0630-0935]] 批跑数据解读 5 步法
- [{9}] [[query-0620-1942]] actionList 出牌 JSON 协议字段
- [{10}] [[query-0629-2000]] GUA-086 闭环记录
