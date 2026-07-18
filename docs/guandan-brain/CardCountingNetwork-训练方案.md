# CardCountingNetwork 训练方案

> 创建时间：2026-07-18
> 状态：方案待评审
> 关联：GUA-057（已登记，open P1 🔴）— NN 记牌模块。本方案 = GUA-057 的训练方案落地文档
> 真源：`掼蛋AI自我进化-随机应变套路.md` §套路七、`人类掼蛋决策流程完整分析.md` §4.2、`组牌-NN衔接设计-软引导vs硬约束.md` §十、`掼蛋AI技术路径重校-V系列方法论反思.md` §5.3

> 修订记录：
> - **v1（2026-07-18 上午）**：初版，状态"方案待评审"
> - **v2（2026-07-18 下午）**：评审修订版。整合 ISSUES GUA-057 备注列评审意见（总评 7.5/10）。**修订 6 项**：
>   1. **§3.1 前置依赖现况警告**——GUA-072 仍 open P0 🔴，Phase 1 启动需同步推进
>   2. **§2.1 输入维度补充**——新增 stage_onehot（7 维）+ 	ribute_transfer_events（变长）
>   3. **§2.2 状态定义补充**——新增进贡/还贡/抗贡/逢人配 4 情形处理
>   4. **§4.4 模型规模表拆细**——参数量精确计算 319K、推理延迟基准 4 硬件、Baseline 对照（含 LSTM 50K）
>   5. **§7.2 heuristic 规则 ⑨ 完整草案**——补伪代码 + 5 项等价性 pytest 设计（降级路径必须返回 0.0）
>   6. **§8 加 Phase 0**——1 周数据 + 形式化验证（5 项硬门槛产出）；Phase 1 改 LSTM baseline
>   7. **§11.1 验收补充**——新增 ECE/MCE/Brier 校准 + 大王小王/Bomb recall@0.5（漏报代价大于误报）
>   8. **核心赌注措辞校准**——Phase 1-3 失败 ≠ NN 路线失败，仅证"用 7700 样本 + Transformer 监督学习"失败
> - **v3（2026-07-18 傍晚）**：GUA-072 实际状态审计更新。pytest 39/39 全绿 → GUA-072 代码实施 100%，仅关单条件 ④ 批跑验证未达。与 GUA-079 三层根因层①②互锁。**Phase 1 LSTM baseline 启动不依赖 GUA-072 关单**。
---

## 零、一句话定位

**训练一个从出牌历史推断各家剩余牌分布的 NN 模块——输入完整（出牌序列）、输出低维（108 槽位 × 3 状态）、有精确 ground truth（初始手牌 + 已出牌反推）、不依赖端到端 BC 的成功。** 这是 V 系列两年来从未被训练过的、Document 1 诊断出的最核心缺失组件。

---

## 一、为什么先训这个，而不是动作模块

### 1.1 三个否定性结论的共同指向

| 失败案例 | 教训 | 指向 |
|---|---|---|
| V5 + 1312 人类数据 BC | 完全匹配率 0%，卡牌级别 97% | 端到端 BC 在大动作空间走不通 |
| V7 + M3 胜局 BC | argmax collapse（2048 维只用 2 维） | 固定 slot softmax 是错误架构 |
| welkin03 / DanZero+ 外部验证 | 都不做端到端 BC，都做候选集评分 | 行业共识：压缩动作空间再选 |

三个教训合流：**让 NN 做它最擅长的小而精的事（从序列推断分布），而不是强迫它做端到端的复杂映射（手牌→2048维动作）。**

### 1.2 记牌模块满足"可训"的四个充要条件

| 条件 | 端到端 BC | 记牌 NN | 说明 |
|---|:---:|:---:|---|
| 输入完整 | ❌ 缺对手手牌 | ✅ 出牌历史全可见 | BC 的监督信号依赖不可见的对手手牌 |
| 输出低维 | ❌ 2048 维动作 | ✅ 108×3=324 维 | argmax collapse 不会发生 |
| 有 ground truth | ❌ 无明确标签 | ✅ 初始手牌+已出牌反推 | 100% 精确，不需人工标注 |
| 独立可测 | ❌ 需整局因果链 | ✅ 每步可对账 | 推断 vs 真实剩余牌，秒级评估 |

### 1.3 与现有 MemoryTracker 的关系

现有 `src/v/nn/features/memory_tracker.py` 的 `MemoryTracker` 已经做了**确定性记牌**（已出几张、剩几张），但它的排除法推断（`_infer_after_play`）极其粗糙——只知道"某牌已出2张则别人没有"，不知道"某牌可能在谁手里"。

```
MemoryTracker（现有）：确定性追踪 → "大王出了1张，还剩1张"
CardCountingNetwork（本方案）：概率推断 → "剩余大王在对手A手里概率60%，对手B手里30%，队友手里10%"
```

NN 记牌不是替代 MemoryTracker，而是给它提供**概率信念向量**，让 heuristic_select 从"零信念决策"升级为"有信息的决策"。

---

## 二、任务定义

### 2.1 形式化

给定第 t 步时的可观信息，预测每张牌每个副本的状态归属。

```
输入：
  - 出牌历史序列 H_t = [(seat_0, action_0), ..., (seat_{t-1}, action_{t-1})]
  - 自己当前手牌 hand_me（27→递减）
  - 级牌 curRank
  - 进贡/还贡/抗贡状态 tribute_state
  - 各家剩余牌数 publicInfo[].rest（4 维）

输出：
  - 108 个槽位的 3 类状态概率分布
  - 槽位 = 54 种牌 × 2 副本
  - 3 类 = {PLAYED, PARTNER_HAND, OPPONENT_HAND}
  - MY_HAND 不预测（已知，从输入排除）
**输入维度补充（2026-07-18 评审 · 评审发现 ②）**：原 §2.1 输入块缺两个关键维度——
- **stage_onehot（7 维）**：stage ∈ {eginning 	ribute nti-tribute ack play episodeOver gameOver}（与平台术语对齐表一致，见 AGENTS.md）。**为什么必须**：_heuristic_select 按阶段分流（早/中/末局规则权重差 10×），记牌 NN 若同参数压缩早期（剩余 100 张、分布均匀）和末期（剩余 5-10 张、博弈尖锐）会显著退化。
- **	ribute_transfer_events（变长序列）**：每条事件 = (giver_seat, taker_seat, cards[≤3]) 记录进/还贡/抗贡的牌归属转移。**为什么必须**：原 3 分类 {PLAYED, PARTNER_HAND, OPPONENT_HAND} 把进贡后被对手拿走的牌直接归 OPPONENT_HAND——但**归属发生事件驱动的非单调转移**，无事件序列 NN 学不到。uild_ground_truth 在 tribute/back 事件点必须同步更新 slot 归属（见 §3.3 修订）。
  - 输出形状：(108, 3) 经 softmax → 每副本 3 类概率和为 1
```

### 2.2 为什么是 3 分类不是 4 分类

| 状态 | 是否预测 | 原因 |
|---|:---:|---|
| PLAYED（已出） | ✅ 预测 | 虽然规则可算，但 NN 学会它可作为"信念校准基线" |
| MY_HAND（在我手） | ❌ 不预测 | 自己手牌已知，直接从输入排除对应副本 |
| PARTNER_HAND（队友手） | ✅ 预测 | **核心任务**——推断队友有什么牌 |
| OPPONENT_HAND（对手手） | ✅ 预测 | **核心任务**——推断对手威胁 |


**状态定义补充（2026-07-18 评审 · 评审发现 ①）**：3 分类 {PLAYED, PARTNER_HAND, OPPONENT_HAND} 把"已发到手里但还没出"压缩掉了，但掼蛋有几个**非 MY_HAND 但非 PARTNER/OPPONENT** 的真实情形，必须显式建模：

| 真实状态 | 原 3 分类归宿 | 修正方案 |
|---|---|---|
| **进贡中被对手拿走的牌**（我方头游 → 进贡给对手） | 错入 OPPONENT_HAND | 单独子状态 TRIBUTED_OPPONENT，由 	ribute_transfer_events 驱动 |
| **还贡中获得的牌**（还贡阶段拿回） | 错入 MY_HAND | 同上，事件驱动转移 |
| **抗贡状态**（双方均不进贡） | 无特殊处理 | OK，但 	ribute_state 显式建模 	ribute_state=anti |
| **王牌/逢人配**（curRank 本身的特殊升级） | 仅作 curRank 标量输入 | **弱**——逢人配的存在会让某些牌"不在 108 槽位规则内"。**Phase 1 不处理**（数据驱动），但在 108 槽位定义中确认 curRank 双副本计入 |

**§3.3 Ground Truth 构建必须处理 tribute 转移**：在每个 tribute/back 事件点（ctions 中 kind=tribute/back），更新对应牌副本的归属标签，不依赖 NN 自行推断事件。Phase 1 实装：遍历 ctions 找到所有 tribute/back 节点 → 维护 slot_ownership dict → 每个样本步 t 时取当前 ownership 作 ground truth。
> 注：对手有 2 家，本方案 Phase 1 不区分对手 A 和对手 B（合并为 OPPONENT_HAND 池）。Phase 2 如果有自对弈 4 家数据，升级为 4 分类（拆分 OPPONENT_A / OPPONENT_B）。

### 2.5 人类式记忆：事件驱动的反事实后验更新

仅统计“谁出了什么牌”还不是人类记牌。人类会把“本来能做但没有做”的行为也当作信息，并根据牌型相生相克关系更新对各家的隐藏牌型信念。因此 CardCountingNetwork 必须从静态牌面预测升级为：

```text
观察事件 E_t
→ 判断对方是否具有合法反制机会
→ 记录对方实际选择（压制 / PASS / 转换牌型）
→ 计算该“不作为”是否具有信息价值
→ 更新 P(隐藏牌型 | 历史、位置、剩余牌数)
```

#### 2.5.1 事件一：小王未被大王压制

当任意一家出了小王，对手具有合法大王压制机会却没有使用大王时，更新：

```text
P(opponent_has_big_joker | small_joker_played, legal_big_joker_counter, opponent_passed)
```

在以下条件同时成立时，这是高信息量负证据：

- 对手是有资格行动的对手，而非队友；
- 当前确实存在合法的大王压制动作；
- 对手没有被迫 PASS、没有已经失去牌权；
- 不处于明显需要保留王牌的残局或队友让牌场景。

满足条件时，可将该对手持有大王的后验概率显著下调，经验上可接近 90%–95% 的排除强度；但不得写死为确定结论。若存在保留炸弹、诱导、配合或误判可能，必须降低更新幅度。

#### 2.5.2 事件二：小牌型被压后不反压

当对手打出较小的 `Straight` 或 `ThreeWithTwo`，被我方以同牌型合法压制后，对手具有反压机会却没有继续压制，记录“被压后不反压”事件：

```python
{
    "actor": 1,
    "action": ["Straight", "6", cards],
    "greater_action": ["Straight", "8", greater_cards],
    "could_have_countered": True,
    "response": "PASS",
    "remaining_cards": 7,
    "counter_shape_relation": {
        "Straight": "ThreeWithTwo",
        "ThreeWithTwo": "Straight",
    },
}
```

该事件不能直接证明对手持有相克牌型，但应产生如下后验更新：

- 对手持有更大同型牌的概率下降；
- 对手保留相生牌型的概率上升：小 `Straight` 被压后，提高 `ThreeWithTwo` 信念；小 `ThreeWithTwo` 被压后，提高 `Straight` 信念；
- 若对手随后主动领出相生牌型，前一事件与后一事件合并为强证据；
- 若对手随后突然停牌或进入残局，则保留“有牌但暂不暴露”和“没有该牌型”两种解释。

模型必须学习“可能有牌但选择不出”和“根本没有牌”的区别，不能把一次 PASS 直接当成确定缺牌。

#### 2.5.3 事件记录的最小字段

每个可产生信息的行动窗口至少记录：

| 字段 | 含义 |
|---|---|
| `actor` | 行动席位 |
| `action` | 当前平台动作，使用 `Single`/`Pair`/`Trips`/`ThreeWithTwo`/`Straight`/`Bomb` 等标准名 |
| `greater_action` | 当前牌权及最大已出牌型 |
| `legal_counters` | 当时实际合法反制动作集合 |
| `could_have_suppressed` | 是否存在可行压制 |
| `did_not_suppress` | 是否选择 PASS 或未反压 |
| `suppression_context` | 对手、队友、领出者及轮次关系 |
| `rest_before/after` | 行动前后剩余牌数 |
| `shape_relation` | 当前牌型与相生相克牌型的关系 |
| `information_strength` | 该事件对后验更新的强度 |

不能只从 `actionList` 推断“没有压制”：必须确认对方当时拥有行动机会、对应牌型合法、且不是服务器未提供完整候选的异常情况。

#### 2.5.4 牌型信念与后验变化

每个对手和队友维护牌型信念，而不是单一布尔值：

```python
shape_belief[seat] = {
    "Straight": 0.72,
    "ThreeWithTwo": 0.81,
    "Trips": 0.44,
    "Pair": 0.35,
    "Bomb": 0.18,
}
```

每次事件产生显式变化：

```python
belief_update = {
    "event": "small_straight_suppressed_then_no_counter",
    "seat": 1,
    "before": {"Straight": 0.52, "ThreeWithTwo": 0.38},
    "delta": {"Straight": -0.15, "ThreeWithTwo": +0.20},
    "after": {"Straight": 0.37, "ThreeWithTwo": 0.58},
    "confidence": 0.72,
}
```

信念更新应满足：

- 硬事实优先于行为推断；
- 行为推断只能改变概率，不能覆盖已知持牌或已出牌事实；
- 牌语、算牌和相生相克是软证据，必须带来源与强度；
- 观察到反例后可以回撤既有信念，不能永久锁死第一次判断。

#### 2.5.5 牌语与反事实训练任务

除槽位分类和级牌归属外，训练样本增加四项监督：

1. `counter_opportunity_head`：判断对手是否拥有合法反制机会；
2. `inaction_information_head`：判断一次 PASS/不反压是否具有信息价值；
3. `shape_posterior_head`：预测各席位 `Straight`、`ThreeWithTwo`、`Pair`、`Trips`、`Bomb` 等牌型后验；
4. `belief_delta_head`：预测观察新事件前后的信念变化 `delta_belief`。

训练目标不是复述行为，而是学习：

```text
P(shape | history_before)
→ 观察“能压而不压”或“被压后不反压”
→ P(shape | history_after)
```

建议增加反事实样本对：同一牌面下分别模拟“有合法反制并 PASS”和“根本没有合法反制”，强制模型区分两类事件。

#### 2.5.6 对决策层的使用边界

- 高信息强度事件可以进入启发式风险评分，但仍不得绕过平台合法性检查。
- 低信息强度事件只用于排序，不得触发硬禁止。
- 对手大王被高置信度排除后，可降低其王压风险；不能据此断言其他炸弹不存在。
- 小 `Straight`/`ThreeWithTwo` 被压后不反压，优先用于调整后续相生牌型的推荐顺序，而不是立即拆解自己的核心牌型。
- 所有事件推断必须写入 decision trace，包含证据、先验、后验和置信度，支持回放复盘。

### 2.4 级牌专项：从“计数”升级为“归属信念”

本方案必须同时回答四个问题：当前级牌出了几张、还剩几张、剩余级牌分别可能在哪一家、这些概率如何改变出牌推荐。级牌不能只作为 `curRank` 标量或一个剩余数量特征；它是记牌、算牌、牌语和牌型相克关系的共同枢纽。

**平台术语约束**：文档中的牌型使用 `Single`、`Pair`、`Trips`、`ThreeWithTwo`、`Straight`、`StraightFlush`、`Bomb`；阶段使用 `beginning`、`tribute`、`anti-tribute`、`back`、`play`、`episodeOver`、`gameOver`。内部 `level_belief` 仅表示模型信念，不替代平台 `action[0]`。

#### 级牌状态定义

对当前级点 `curRank`，两副牌共有 8 张级牌（不含逢人配特殊语义的额外解释）。每个决策步维护：

```python
level_belief = {
    "rank": cur_rank,
    "total": 8,
    "played": int,
    "remaining": int,
    "by_seat": {0: float, 1: float, 2: float, 3: float},
    "cards": {
        "S2": {"status": "unknown", "seat_prob": {0: float, 1: float, 2: float, 3: float}},
    },
}
```

- `played`：由公开出牌历史逐张累计，必须与 8 张总量对账。
- `remaining`：`8 - played - known_my_level_cards`；不能把自己的已知手牌重复计算为未知牌。
- `by_seat`：剩余级牌落在四席的边际概率，和为 1；不确定时保留 `UNKNOWN`，禁止硬判归属。
- `cards`：逐张级牌的状态与席位概率；已出为 `PLAYED`，自己持有为 `MY_HAND`，其余按排除法和行为信号分配概率。

#### 级牌归属推断信号

1. **硬事实**：自己的手牌、已出级牌、`publicInfo[].rest`、`tribute`/`back`/`anti-tribute` 转移事件。
2. **算牌约束**：某家剩余牌数、该级牌已知副本数、同点牌缺口、炸弹候选和牌型组合容量。
3. **牌语信号**：某家主动领出 `Single`、`Pair`、`Trips`、`ThreeWithTwo` 或 `Straight`，以及对相应牌型的跟牌、过牌和突然停牌；牌语只能提高或降低概率，不能替代硬事实。
4. **相生相克信号**：`ThreeWithTwo` 未被回收时提高对方 `Straight` 信念，`Straight` 未被回收时提高对方 `ThreeWithTwo` 信念；类似关系只作为软证据，防止把诱导动作当成确定牌型。
5. **信息价值信号**：试探动作必须满足“被压后仍有回收路径”；记录试探结果，更新对应席位的牌型和级牌后验概率。

#### 决策消费规则

- 对手持有级牌的概率高：提高普通出牌被压风险，优先选择可回收的 `Single`/`Pair` 或保留控牌结构。
- 队友持有级牌且队友处于冲刺窗口：减少抢队友牌权，优先送出其可能需要的牌型。
- 自己保有级牌：将其计入回收能力和残局安全度，不能只按普通点数排序。
- 级牌归属置信度低：只做软评分，不触发硬禁止；低延迟或模型异常时回退到 `MemoryTracker` 的确定性计数。

### 2.3 与人类记牌的对应

| 人类记牌行为 | 本方案输出 |
|---|---|
| "大王出了几张" | PLAYED 概率 |
| "队友可能有大王" | PARTNER_HAND 概率 |
| "对手可能藏炸弹" | OPPONENT_HAND 中 Bomb 牌点的概率聚合 |
| "级牌还剩几张在谁手" | 级牌槽位的 3 类分布 |

---

## 三、数据来源与 Ground Truth 构建

### 3.1 数据现状勘察结果

| 字段 | 位置 | 完整性 | 用途 |
|---|---|:---:|---|
| `initial_hand` | 顶层 | ✅ 27 张 | 自己初始手牌 |
| `all_players_hands` | 顶层 | ⚠️ 单条仅自己 | 需合并同局 yf1+yf2 |
| `actions` | 顶层 | ✅ 完整序列 | 出牌历史（~100 步/副） |
| `my_decisions` | 顶层 | ✅ 32 步/副 | 我方决策点（训练样本采集点） |
| `result.victoryNum` | 顶层 | ✅ | 胜负过滤 |
| `context.restCards` | actions[].context | ❌ 空数组 | 平台未填充，不可用 |

**关键发现**：`all_players_hands` 单条记录只有自己（键 "0"），但文件名成对出现（yf1+yf2 同局），recorder 已有 `_merge_same_game_records()` 合并逻辑。合并后可拿到 2 家（队友对）完整初始手牌。
**前置依赖现况警告（2026-07-18 评审）**：本方案 §三 写「前置条件 GUA-072 closed」——但 ISSUES GUA-072 当前状态 `open P0 🔴`。**2026-07-18 状态审计更新**：`rule_card_counter.py`（725 行）+ `memory_tracker.py` 贡牌/抗贡算王 + `tests/test_gua072_*`（含 `test_memory_tracker_tribute_joker.py`）**pytest 39/39 全绿**（实测 v8-dev 当前状态）。代码层已就绪：**关单条件 ①②③ ✅**；**关单条件 ④ 批跑副胜率环比**——v7-dev 历史累计 1/33 队胜（3.0%）远低于 ≥10% 阈值，与 GUA-079 三层根因（单牌倒置+拆炸凑压+残局静默）互锁：层③已修，层①②（`_heuristic_select` 缺最小压制规则 + 组牌引擎临时借调 API）仍未修复。**结论**：GUA-072 在 v7-dev 代码实施 100%，**唯一开放**是关单条件 ④ 的跑批验证。**对 GUA-057 的实际意义**：Phase 1 LSTM baseline 启动**不依赖 GUA-072 关单**（可独立训练 NN 记牌模块，ground truth 构建与 RuleCardCounter 输出无耦合），仅在 Phase 3 集成（heuristic_select 消费 belief 向量）时需 GUA-072 同步推进。**GUA-071 heuristic 副胜率**仍待观测，与 GUA-072 一样是集成阶段的瓶颈。


### 3.2 文件配对与合并

```
同局文件名模式：
  {timestamp} [yf1_v8]-[opponent]-[round]-[level].json
  {timestamp} [yf2_v8]-[opponent]-[round]-[level].json

合并后：
  all_players_hands = {
    "yf1_pos": [...27张...],   # yf1 初始手牌
    "yf2_pos": [...27张...],   # yf2 初始手牌（队友）
  }
  # 对手 2 家手牌未知 → 通过排除法推算对手池
```

### 3.3 Ground Truth 精确构建算法

对每副牌的每个决策步 t，构建 108 槽位的真实状态标签：

```python
def build_ground_truth(
    initial_hands: Dict[int, List[str]],  # {yf1_pos: [...], yf2_pos: [...]}
    actions: List[Dict],                   # 完整出牌序列
    my_pos: int,                          # 当前样本的视角（yf1 或 yf2）
    step_t: int,                          # 决策步索引
    cur_rank: str,
) -> np.ndarray:
    """
    返回 (108, 3) 的 one-hot 标签。
    列 0 = PLAYED, 列 1 = PARTNER_HAND, 列 2 = OPPONENT_HAND
    MY_HAND 对应副本标记为 -1（不参与 loss）
    """
    partner_pos = (my_pos + 2) % 4
    opponent_positions = {(my_pos + 1) % 4, (my_pos + 3) % 4}

    # 1. 初始化：所有副本 = UNKNOWN
    # card_slot[card_type][copy_idx] = state
    # state: -1=unknown, 0=played, 1=my_hand, 2=partner, 3=opponent
    card_slots = {ct: [-1, -1] for ct in ALL_CARD_TYPES}

    # 2. 标记我方和队友的初始手牌
    my_initial = initial_hands.get(my_pos, [])
    partner_initial = initial_hands.get(partner_pos, [])
    for card in my_initial:
        _assign_to_slot(card_slots, card, 1)  # MY_HAND
    for card in partner_initial:
        _assign_to_slot(card_slots, card, 2)  # PARTNER_HAND

    # 3. 回放出牌序列 actions[0..t-1]，标记 PLAYED
    for i in range(step_t):
        action = actions[i]
        seat = action["cur_pos"]
        cards = action["cur_action"][2] if len(action["cur_action"]) >= 3 else []
        for card in cards:
            _assign_to_slot(card_slots, card, 0)  # PLAYED

    # 4. 剩余 unknown 副本 = 对手手牌
    for ct in ALL_CARD_TYPES:
        for copy_idx in range(2):
            if card_slots[ct][copy_idx] == -1:
                card_slots[ct][copy_idx] = 3  # OPPONENT_HAND

    # 5. 转为 (108, 3) one-hot，MY_HAND 标记为 -1（loss mask）
    labels = np.zeros((108, 3), dtype=np.float32)
    mask = np.ones(108, dtype=np.float32)  # 1=参与loss, 0=跳过
    for ct_idx, ct in enumerate(ALL_CARD_TYPES):
        for copy_idx in range(2):
            slot = ct_idx * 2 + copy_idx
            state = card_slots[ct][copy_idx]
            if state == 1:  # MY_HAND
                mask[slot] = 0  # 跳过
            else:
                labels[slot, state] = 1.0  # one-hot
    return labels, mask
```

### 3.6 级牌 Ground Truth 与概率标签

级牌标签必须从初始四席手牌、公开出牌序列和 `tribute`/`back` 转移事件逐步重放生成，不允许使用决策结果反推标签。每个时间步同时保存硬标签与可观测信号：

| 标签 | 定义 |
|---|---|
| `level_played_count` | 截止当前步已公开打出的级牌张数 |
| `level_remaining_count` | 8 张总量扣除已出和己方已知持有后的剩余数 |
| `level_owner_seat` | 逐张级牌真实归属；已出牌单独标记 `PLAYED` |
| `level_owner_distribution` | 对模型输入可见信息下的席位后验分布，评估时与真实归属对账 |
| `level_type_context` | 级牌参与的 `Single`/`Pair`/`Trips`/`ThreeWithTwo`/`Straight`/`Bomb` 等牌型上下文 |

标签构建约束：

- 先处理事件顺序，再处理牌型；同一时间步中 `tribute`、`back`、`anti-tribute` 的归属变化必须先于下一次 `play`。
- 对每张级牌保留 `known`、`inferred`、`unknown` 三种证据来源；训练损失可对硬事实加权，对软推断不作为标签泄露。
- 训练样本按副切分，不能把同一副牌的不同时间步拆到 train/val 两侧。
- 同时生成计数任务、归属任务、牌型上下文任务，避免模型只学会“级牌出现次数”而不会定位持牌人。

### 3.4 样本采集策略

每副牌产生多个训练样本（每个 `my_decisions` 步一个样本）：

```
一副牌：
  actions: ~100 步
  my_decisions: ~32 步（我方出牌/PASS 的决策点）

样本采集：
  对每个 my_decision 步 t：
    输入 = actions[0..t-1] + my_hand_at_t + curRank + tribute_state
    标签 = build_ground_truth(initial_hands, actions, my_pos, t, curRank)

  → 每副产生 ~32 个样本
  → 120 副 game_records_v8 → ~3840 样本
  → 扩展到 game_records_v8_kaggle (121 副) → ~7700 样本
```

### 3.5 数据集切分（防泄露）

> welkin03 教训（`组牌-NN衔接设计.md` §11.4）：同局相邻状态会泄露，必须按整局切分。

```python
# 按 game_id 切分，不按样本切分
all_game_ids = sorted(set(game_id for each record))
train_games, val_games = split_by_game(all_game_ids, val_ratio=0.2)

train_samples = [s for s in samples if s.game_id in train_games]
val_samples = [s for s in samples if s.game_id in val_games]
```

---

## 四、模型架构

### 4.1 总体设计

```
┌─────────────────────────────────────────────────────────┐
│                    输入编码层                              │
│  ├─ 出牌历史序列 → Transformer Encoder (可变长)            │
│  ├─ 自己手牌     → 108 维 one-hot                        │
│  ├─ 级牌/进贡    → embedding                             │
│  └─ 各家剩牌数   → 4 维 float                            │
│        维度：seq_emb(128) + hand(108) + misc(16) = 252    │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│                    融合层                                  │
│  Linear(252, 256) → ReLU → Dropout(0.1)                  │
│  Linear(256, 256) → ReLU → Dropout(0.1)                  │
│        维度：256                                          │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│                    输出头                                  │
│  对 108 个槽位各自做 3 类分类                              │
│  Linear(256, 108*3) → reshape (108, 3) → softmax        │
│        维度：108 × 3 = 324                                │
└─────────────────────────────────────────────────────────┘
```

### 4.2 出牌历史序列编码

每步出牌编码为 54 维向量（出牌的牌 one-hot），附加 4 维出牌者位置 one-hot：

```python
class PlayHistoryEncoder(nn.Module):
    """出牌历史序列编码器（Transformer）"""

    def __init__(self, d_model=64, nhead=4, num_layers=2):
        super().__init__()
        # 每步编码：54(牌) + 4(出牌者位置) + 4(动作类型 embedding) = 62 维
        self.step_proj = nn.Linear(62, d_model)
        self.pos_encoder = PositionalEncoding(d_model, max_len=200)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=128,
            dropout=0.1, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.output_proj = nn.Linear(d_model, 128)  # 输出 128 维序列摘要

    def forward(self, history_steps: torch.Tensor, padding_mask: torch.Tensor):
        """
        Args:
            history_steps: (batch, seq_len, 62) 每步出牌编码
            padding_mask: (batch, seq_len) True=padding 位置
        Returns:
            (batch, 128) 序列摘要向量
        """
        x = self.step_proj(history_steps)  # (B, L, d_model)
        x = self.pos_encoder(x)
        x = self.transformer(x, src_key_padding_mask=padding_mask)
        # 取最后一个非 padding 位置的输出作为摘要
        # 或用 mean pooling
        out = x.mean(dim=1)  # (B, d_model)
        return self.output_proj(out)
```

> 为什么用 Transformer 不用 LSTM：出牌历史中"第 3 圈出的牌"和"第 15 圈出的牌"都可能对推断"对手手里还有什么"有影响，长程依赖适合 attention。序列长度 ~100，Transformer 完全可处理。

### 4.3 完整模型

```python
class CardCountingNetwork(nn.Module):
    """记牌 NN：出牌历史 + 自己手牌 → 各家剩余牌分布"""

    def __init__(self, d_model=64):
        super().__init__()
        self.history_encoder = PlayHistoryEncoder(d_model=d_model)
        self.hand_proj = nn.Linear(108, 64)  # 自己手牌 108 维（54种×2副本计数）
        self.misc_proj = nn.Linear(16, 32)   # 级牌+进贡+剩牌数
        self.fusion = nn.Sequential(
            nn.Linear(128 + 64 + 32, 256),  # 224 → 256
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
        )
        self.output_head = nn.Linear(256, 108 * 3)  # 108 槽位 × 3 类

    def forward(self, history_steps, padding_mask, my_hand, misc_features):
        """
        Returns:
            logits: (batch, 108, 3) 每槽位 3 类 logits
        """
        seq_emb = self.history_encoder(history_steps, padding_mask)  # (B, 128)
        hand_emb = self.hand_proj(my_hand)        # (B, 64)
        misc_emb = self.misc_proj(misc_features)  # (B, 32)
        fused = torch.cat([seq_emb, hand_emb, misc_emb], dim=1)  # (B, 224)
        fused = self.fusion(fused)                # (B, 256)
        logits = self.output_head(fused)          # (B, 324)
        return logits.view(-1, 108, 3)            # (B, 108, 3)
```

### 4.4 参数量估算

| 组件 | 参数量 |
|---|---:|
| PlayHistoryEncoder (Transformer 2层) | ~80K |
| hand_proj + misc_proj | ~10K |
| fusion (2层 MLP) | ~120K |
| output_head | ~83K |
| **总计** | **~290K** |

**模型规模补充（2026-07-18 评审 · 评审发现 ④）**：原 §4.4 给"~290K 参数 / <5ms 推理"但缺硬件/计算/baseline 对照，拆分如下——

#### 4.4.1 参数量精确计算

| 组件 | 形状 | 参数量 |
|---|---|---:|
| step_proj | Linear(62, 64) | 62×64+64 = **4,032** |
| Transformer Encoder (2 层) | d=64, head=4, FFN=128 | 2 × (4×64×64 + 2×64×128 + 4×64) ≈ **82,432** |
| Transformer output_proj | Linear(64, 128) | 64×128+128 = **8,320** |
| hand_proj | Linear(108, 64) | 108×64+64 = **6,976** |
| misc_proj | Linear(16, 32) | 16×32+32 = **544** |
| usion (Linear-ReLU-Dropout) ×2 | 224→256, 256→256 | (224×256+256) + (256×256+256) = **133,632** |
| output_head | Linear(256, 324) | 256×324+324 = **83,268** |
| **总计** | | **~319K**（原文 290K 是四舍五入） |

#### 4.4.2 推理延迟基准（必须跑出实测数字，不可只写"<5ms"）

| 硬件 | seq_len | batch_size | 延迟（待 Phase 1 实测） |
|---|---|---|---|
| CPU (Intel i7-12700) | 100 | 1 | <50ms 目标 |
| CPU 同上 | 100 | 8 | <100ms 目标 |
| GPU (RTX 3060) | 100 | 1 | <5ms 目标 |
| GPU 同上 | 100 | 64 | <20ms 目标 |

**实测代码**（Phase 1 必跑）：scripts/bench_card_counting.py 用 	orch.cuda.Event 或 	ime.perf_counter 跑 1000 次取平均 + p99。

#### 4.4.3 Baseline 对照（Phase 1 LSTM 必须跑过）

原方案默认 Transformer，但**7700 步 / 324 维输出 ≈ 24 样本/维度**，319K 参数严重过拟合。Phase 1 强制先跑 ~50K 参数的 LSTM baseline：

| 模型 | 参数量 | 评估目的 |
|---|---:|---|
| 规则记牌（现有 MemoryTracker 排除法） | 0 | **必须超越的下界**——NN 训不出超过这个就失败 |
| LSTM baseline | ~50K | 验证**形式化可行性**——能学到 70%+ 槽位准确率则继续 |
| Transformer（本方案） | ~319K | **Phase 2 才上**——需 ~5× 当前数据量（38500+ 步）|

**风险点**：若 LSTM baseline 达不到规则记牌精度，**不升级 Transformer**，直接调整任务设计（缩减输出维度 / 改多任务学习 / 改检索式）。
远小于 V7 BC model（1M），但任务维度也远小于（324 vs 2048）。参数效率合理。

---

## 五、训练规格

### 5.1 损失函数

```python
def masked_cross_entropy(logits, labels, mask):
    """
    Args:
        logits: (B, 108, 3)
        labels: (B, 108, 3) one-hot
        mask: (B, 108) 1=参与loss, 0=MY_HAND跳过
    """
    B, S, C = logits.shape
    # 每槽位交叉熵
    ce = F.cross_entropy(
        logits.view(B * S, C),
        labels.argmax(dim=-1).view(B * S),
        reduction='none'
    ).view(B, S)
    # 应用 mask
    ce = ce * mask
    # 按非 mask 槽位数平均
    return ce.sum() / mask.sum().clamp(min=1)
```

### 5.2 类别权重（处理不平衡）

| 类别 | 占比 | 权重 |
|---|:---:|:---:|
| PLAYED | ~40%（随 t 增长） | 1.0 |
| PARTNER_HAND | ~25% | 1.2 |
| OPPONENT_HAND | ~35% | 1.0 |

> PARTNER_HAND 略加权，因为推断队友手牌是配合决策的关键，且样本相对少。

### 5.3 训练超参

| 参数 | 值 | 理由 |
|---|---|---|
| optimizer | AdamW | Transformer 标配 |
| lr | 1e-4 | 小模型用小 lr |
| weight_decay | 1e-4 | 防 overfit |
| batch_size | 64 | ~7700 样本，64 合理 |
| epochs | 50 | 早停 |
| early_stop_patience | 10 | val_loss 不降 10 轮停 |
| scheduler | CosineAnnealingLR | 标配 |
| gradient_clip | 1.0 | Transformer 防梯度爆炸 |
| train/val split | 按局 8:2 | 防同局泄露 |

### 5.6 事件后验更新损失

在级牌与槽位任务之外，事件推断使用“前后验 + 事件有效性”联合训练：

```text
L_event = 0.30 L_counter_opportunity
         + 0.20 L_inaction_information
         + 0.35 L_shape_posterior
         + 0.15 L_belief_delta
```

`L_belief_delta` 只在事件前后都能由完整牌谱重放得到 ground truth 时计算；缺少合法反制集合或 actionList 不完整时使用 mask，避免把平台候选缺失误学成“对手没有牌”。总损失为：

```text
L_total = L_slot + 0.25 L_level_count + 0.50 L_level_owner
          + 0.15 L_level_type + 0.30 L_event
```

其中事件任务的权重不得压过硬事实牌位任务；模型必须先记准已经出的牌，再学习“为什么没有压”。
### 5.5 级牌多任务训练目标

在基础 108 槽位状态分类外，增加三个轻量输出头：

1. `level_count_head`：预测 `played` 与 `remaining`，使用 Poisson/Huber 或整数交叉熵。
2. `level_owner_head`：对每张未出级牌预测 `{my, partner, opp, unknown}`，使用带掩码的交叉熵；对明确已出牌使用 `PLAYED` 监督。
3. `level_type_head`：预测级牌最近参与的牌型及其牌语上下文，使用多标签 BCE；平台牌型名称保持 PascalCase。

总损失：

```text
L = L_slot + 0.25 L_level_count + 0.50 L_level_owner + 0.15 L_level_type
```

其中 `L_level_owner` 权重高于牌型上下文，因为“级牌在哪家”直接影响压制、送牌和避免被接；低置信度或信息不可辨识的样本可采用 `unknown` 掩码，避免强迫模型过拟合。

### 5.4 训练入口

新建 `scripts/train_card_counting_v8.py`（登记 SCRIPT_INDEX.md）：

```python
def main():
    # 1. 加载 + 合并 game_records
    samples = load_counting_samples(
        record_dir="game_records_v8",
        require_pair_merge=True,  # 强制 yf1+yf2 配对
    )
    # 2. 按局切分
    train_samples, val_samples = split_by_game(samples, val_ratio=0.2)
    # 3. 训练
    model = CardCountingNetwork()
    trainer = CountingTrainer(model, lr=1e-4, ...)
    trainer.fit(train_samples, val_samples, epochs=50)
    # 4. 保存
    torch.save(model.state_dict(), "models/card_counting_v8.pth")
```

---

## 六、评估指标

### 6.1 主指标：槽位级准确率

```
槽位级准确率 = 预测状态 == 真实状态 的槽位数 / 总非 MY_HAND 槽位数
```

目标：> 75%（基线规则记牌能到 ~60%，NN 应显著超过）

### 6.2 分项指标

| 指标 | 定义 | 目标 | 决策意义 |
|---|---|:---:|---|
| PLAYED 准确率 | 已出牌被正确预测为 PLAYED | > 95% | 信念校准基线 |
| PARTNER 准确率 | 队友手牌被正确预测 | > 65% | 配合决策 |
| OPPONENT 准确率 | 对手手牌被正确预测 | > 60% | 威胁评估 |
| 大王/小王专项 | 王张归属预测准确 | > 70% | 控场关键 |
| 级牌专项 | 级牌归属预测准确 | > 65% | 升级节奏 |
| 炸弹牌点专项 | 4张同点牌归属预测 | > 60% | 炸弹风险 |

### 6.5 事件驱动记忆评估

| 指标 | 定义 | 目标 |
|---|---|---|
| 合法反制机会识别准确率 | `could_have_suppressed` 与重放 ground truth 对比 | ≥ 95% |
| PASS 信息价值 AUROC | 区分“能压而不压”和“根本不能压” | ≥ 0.85 |
| 小王未被大王压制校准 | 条件事件后对手持大王概率的 ECE | < 0.10 |
| 相生牌型后验方向准确率 | `Straight` 被压后对 `ThreeWithTwo` 的增益方向正确率，反之亦然 | ≥ 80% |
| belief delta MAE | 预测事件前后牌型概率变化误差 | ≤ 0.15 |
| 事件解释完整率 | trace 是否包含事件、合法机会、先验、后验、置信度 | 100% |

验收必须包含反事实配对：同一牌面分别构造“对手有合法反制但 PASS”和“对手没有合法反制”，模型不得把两者混为同一种缺牌证据。
### 6.4 级牌专项评估

| 指标 | 定义 | 目标 |
|---|---|---|
| 级牌计数 MAE | `played`/`remaining` 的平均绝对误差 | ≤ 0.10 张 |
| 级牌逐张归属准确率 | 未出级牌真实席位预测准确率 | ≥ 75% |
| 级牌 owner macro-F1 | `partner`/`opponent`/`unknown` 宏平均 F1 | ≥ 0.70 |
| 级牌归属 ECE | 逐张最大席位概率校准误差 | < 0.10 |
| 对手级牌 recall@0.5 | 实际在对手手中的级牌，被预测为对手概率 > 0.5 的比例 | ≥ 85% |
| 队友级牌 precision@0.5 | 预测队友持有的级牌中真实属于队友的比例 | ≥ 80% |
| 级牌牌型上下文准确率 | 最近参与 `Single`/`Pair`/`Trips`/`ThreeWithTwo`/`Straight`/`Bomb` 的识别 | ≥ 75% |

必须额外报告“只计数基线”与“加入归属信念”的差异：对手压制成功率、队友送牌成功率、自己出牌被意外接牌率。若归属信念提升了计数指标但恶化决策指标，不得直接集成。

### 6.3 决策级指标（集成后批跑验证）

| 指标 | 定义 | 目标 |
|---|---|:---:|
| 炸弹浪费率下降 | heuristic ⑧"有同型不炸"触发率 | 下降 > 20% |
| 队友投喂命中率 | 投喂后队友成功接牌率 | 上升 > 10% |
| 副胜率 | vs Lalala | > 30%（当前 25.5%） |

> 决策级指标是批跑后才看的，不是训练阶段的验收标准。训练阶段只看槽位级 + 分项指标。

---

## 七、集成路径

### 7.1 输出注入 MemoryTracker

在 `MemoryTracker` 新增 `belief_vector` 字段，由 CardCountingNetwork 推理填充：

```python
class MemoryTracker:
    def __init__(self, ...):
        # ... 现有代码 ...
        self._belief_vector: Optional[np.ndarray] = None  # (108, 3) 概率
        self._counting_model: Optional[CardCountingNetwork] = None
        self._counting_enabled = False

    def load_counting_model(self, model_path: str):
        """加载训好的记牌 NN"""
        self._counting_model = CardCountingNetwork()
        self._counting_model.load_state_dict(torch.load(model_path))
        self._counting_model.eval()
        self._counting_enabled = True

    def update_belief(self, game_state: Dict):
        """每步 decide() 前调用，更新信念向量"""
        if not self._counting_enabled:
            return
        # 1. 构建输入（出牌历史序列 + 自己手牌 + misc）
        history_steps, padding_mask, my_hand, misc = self._encode_input(game_state)
        # 2. NN 推理
        with torch.no_grad():
            logits = self._counting_model(history_steps, padding_mask, my_hand, misc)
            self._belief_vector = F.softmax(logits, dim=-1).cpu().numpy()  # (108, 3)
        # 3. 性能监控
        # 推理 > 20ms → 降级为规则记牌
```

### 7.2 heuristic_select 读取信念

在 `ultimate_win_rate_engine_v7.py` 的 `_heuristic_select` 新增信念驱动的加分规则：

```python
# 新增 heuristic 规则 ⑨：信念驱动炸弹风险
def _heuristic_belief_bomb_risk(action, belief_vector, card_mask):
    """如果动作出的牌可能被对手炸弹压制，且对手持有炸弹概率高，扣分"""
    if belief_vector is None:
        return 0.0
    # 查对手持有当前牌点 4 张的概率
    # belief_vector[card_slot, OPPONENT_HAND] > 0.6 → 高风险
**heuristic 规则 ⑨ 完整草案（2026-07-18 评审 · 评审发现 ⑤）**：原 §7.2 只给"返回负分 ...", 不构成可落地方案。完整草案：

`python
# 新增 heuristic 规则 ⑨：信念驱动炸弹风险规避
def _heuristic_belief_bomb_risk(
    action: dict,                  # 待评分动作 {"cards": [...], "type": "..."}
    belief_vector: np.ndarray,     # (108, 3) PARTNER_HAND/OPPONENT_HAND/PLAYED 概率
    card_mask: np.ndarray,         # (108,) 1=在手牌可用
    game_state: dict,              # 含 _role, hand_size, stage
) -> float:
    """
    信念驱动炸弹风险评分。
    
    触发条件：
      - belief_vector 非空（NN 已推理）
      - action 是非 PASS 出牌动作
    
    评分规则：
      1. 若动作含 4 张同牌（疑似自己炸弹），检查 belief 中对手持有更大炸弹概率
         → belief_opp_bomb_higher = sum(P(slot in OPPONENT_HAND) for slot in all_bomb_slots with rank > action.rank)
         → 若 > 0.5 扣 200 分（不出炸，避免被压）
      2. 若动作出单张/对子（非炸），检查 belief 中对手持有该牌点炸弹概率
         → belief_opp_bomb_same_rank = sum(P(slot in OPPONENT_HAND) for slot in bomb_slots of action.rank)
         → 若 > 0.3 扣 100 分（出小牌被炸风险高）
      3. 末局（stage=play, hand_size<=5）信念权重 ×1.5（残局决策更敏感）
    """
    if belief_vector is None:
        return 0.0  # 降级路径：belief 不可用时与无 belief 完全等价
    
    score = 0.0
    opp_hand_prob = belief_vector[:, 2]  # OPPONENT_HAND 索引 = 2
    action_cards = action.get("cards", [])
    action_rank = action.get("rank", 0)
    hand_size = len(game_state.get("handCards", []))
    stage = game_state.get("stage", "play")
    is_endgame = (hand_size <= 5 and stage == "play")
    
    # 规则 1: 自己疑似炸出 → 检查对手更大炸弹
    if len(action_cards) == 4:  # 4 张同牌 = 炸弹
        higher_bomb_slots = get_bomb_slots_with_rank_gt(action_rank)
        opp_higher_bomb = opp_hand_prob[higher_bomb_slots].sum()
        if opp_higher_bomb > 0.5:
            score -= 200 * (1.5 if is_endgame else 1.0)
    
    # 规则 2: 出小牌 → 检查对手同点炸弹
    bomb_slots_same_rank = get_bomb_slots_with_rank_eq(action_rank)
    opp_bomb_same = opp_hand_prob[bomb_slots_same_rank].sum()
    if opp_bomb_same > 0.3:
        score -= 100 * (1.5 if is_endgame else 1.0)
    
    return score
`

**等价性 pytest 设计（评审发现 ⑤ 配套）**：_heuristic_belief_bomb_risk 的关键不变量是——

| 测试场景 | 输入 belief_vector | 期望 score | 等价性要求 |
|---|---|---:|---|
| 1. belief=None（降级路径） | None | **0.0** | 与当前无 belief 实现完全等价（无回归）|
| 2. belief 全 0（NN 输出占位）| zeros(108,3) | **0.0** | 不触发任何扣分 |
| 3. belief 对手高概率持更大炸弹 | opp_higher_bomb=0.7 | **-200** | 触发规则 1 |
| 4. belief 对手高概率持同点炸弹 | opp_bomb_same=0.5 | **-100** | 触发规则 2 |
| 5. 末局 + 高信念炸弹风险 | hand_size=4, opp_higher_bomb=0.7 | **-300** | 末局 1.5× 权重 |

**实现位置**：ultimate_win_rate_engine_v7.py::_heuristic_select 中插入新规则前必须**先跑测试 1+2**（保证降级等价）。pytest 文件：	ests/test_gua057_belief_bomb_risk.py。
    # 返回负分
    ...
```

### 7.3 集成管线

```
decide()
  ├─ _run_grouping_engine()          ← 组牌（现有）
  ├─ MemoryTracker.update_belief()   ← 【新增】NN 记牌推理
  ├─ filter_action_list (Guard)      ← 硬排除（现有）
  ├─ _group_consistency_filter()     ← 角色过滤（现有）
  ├─ _heuristic_select()             ← 软排序（现有 + 新增信念规则 ⑨）
  └─ validate_decision()             ← 安全网（现有）
```

### 7.4 性能降级策略

| 推理耗时 | 行为 |
|---|---|
| < 10ms | 正常使用 NN 信念 |
| 10-20ms | 警告日志，继续使用 |
| > 20ms | 降级为规则记牌（`MemoryTracker` 现有逻辑） |
| 模型加载失败 | 降级，启动时 warning |

---

## 八、实施路线图

### Phase 0：数据 + 形式化验证（1 周）★ 评审新增 ★

**为什么必须有 Phase 0**：原方案 Phase 1 直接开始数据管道 + 模型训练，但**7700 步 / 324 维 ≈ 24 样本/维度**，319K 参数 Transformer 严重过拟合风险未量化；yf1/yf2 时序对齐未验证；ground truth 是否真"精确重建"未做对账；heuristic 规则 ⑨ 缺等价性测试。**Phase 0 = 不训任何模型，只验数据和形式化**——能把"模型训不出来"这种最坏情况提前发现。

| 任务 | 产出 | 验收 |
|---|---|---|
| V8 牌谱 yf1/yf2 时序对齐校验 | scripts/check_action_ordering.py | 100% 同局顺序一致 |
| Ground truth 手算对账（抽 10 副） | alidate_counting_data.py 增强 | 手算 vs 代码 100% 一致 |
| 模型/数据比例分析（7700 步 vs 319K 参数）| nalysis/param_data_ratio.md | 文档化结论（推荐 LSTM baseline）|
| 规则记牌 baseline 推理精度测量 | scripts/bench_rule_card_counting.py | 槽位准确率数字（必须 NN 超越的下界）|
| heuristic 规则 ⑨ 草案骨架 + 等价性 pytest 骨架 | 	ests/test_gua057_belief_bomb_risk.py | pytest 1+2（降级等价）全绿 |

**Phase 0 完成标准（硬门槛）**：5 项任务全部产出 + pytest 全绿 + baseline 精度数字到手。**任一项未通过，禁止进入 Phase 1**。

### Phase 1：数据管道 + LSTM baseline（2-3 天 · 评审修改）

| 任务 | 产出 | 验收 |
|---|---|---|
| yf1+yf2 文件配对合并 | merge_paired_records() | 配对率 > 95% |
| Ground truth 构建器（含 tribute 转移）| uild_ground_truth() | 单元测试：已知局 100% 正确 + tribute 转移正确 |
| 样本采集 + 按局切分 | load_counting_samples() | ~7700 样本，train/val 无同局泄露 |
| 数据完整性校验脚本 | alidate_counting_data.py | 108 槽位状态穷尽（PLAYED+MY+PARTNER+OPPONENT=108）+ tribute 事件全捕获 |
| **LSTM baseline 训练** ★ | src/v/nn/models/card_counting_lstm.py | 参数量 ~50K，槽位准确率 ≥ 规则记牌 baseline |
| LSTM baseline 评估 | scripts/eval_card_counting_lstm.py | 与 Transformer 同指标对照 |

**为什么先 LSTM 不 Transformer**：见 §4.4.3 数据/参数比例分析。LSTM baseline 验证**形式化可行性**——能学到 70%+ 槽位准确率则 Phase 2 升级 Transformer；否则调整任务设计。
### Phase 2：模型训练（2-3 天）

| 任务 | 产出 | 验收 |
|---|---|---|
| `CardCountingNetwork` 模型 | `src/v/nn/models/card_counting.py` | 前向传播维度正确 |
| 训练脚本 | `scripts/train_card_counting_v8.py` | 训练收敛，val_loss 下降 |
| 评估脚本 | `scripts/eval_card_counting_v8.py` | 槽位准确率 > 75% |
| 模型保存 | `models/card_counting_v8.pth` | 可加载推理 |

### Phase 3：集成验证（3-5 天）

| 任务 | 产出 | 验收 |
|---|---|---|
| MemoryTracker 接入 | `update_belief()` 方法 | 推理 < 20ms |
| heuristic 信念规则 ⑨ | `_heuristic_belief_bomb_risk()` | 单元测试通过 |
| 批跑验证 | 9 局 vs Lalala | 副胜率 > 30% |
| 性能降级测试 | 模拟超时 | 降级后不崩溃 |

### Phase 4（可选）：自对弈数据增强

如果 Phase 1-3 验证有效，搭建自对弈环境（4 席都是 yf 客户端），获取 4 家完整 `all_players_hands`，升级为 4 分类（拆分 OPPONENT_A / OPPONENT_B）。

---

## 九、风险与对策

### 9.1 数据量风险

| 风险 | 现状 | 对策 |
|---|---|---|
| 样本不足 | ~7700 样本，可能不够 | 1. 扩展到 game_records_v8_kaggle（+121 副）<br>2. 数据增强：同一局从 yf1 和 yf2 两个视角各采一遍<br>3. 如仍不足，搭建自对弈快速产数据 |

### 9.2 对手手牌不可观测风险

| 风险 | 说明 | 对策 |
|---|---|---|
| OPPONENT_HAND 是推算的 | 108 - 已出 - 我 - 队友 = 对手池，但不知具体在对手 A 还是 B | Phase 1 合并为 OPPONENT_HAND 池，不区分 A/B；Phase 4 自对弈后升级 |
| 对手可能贡牌打乱 | 进贡后手牌转移 | `build_ground_truth` 中处理 tribute/back 事件，更新 slot 归属 |

### 9.3 模型过拟合风险

| 风险 | 对策 |
|---|---|
| 小数据 + Transformer 过拟合 | 1. Dropout 0.1<br>2. 早停 patience=10<br>3. weight_decay 1e-4<br>4. 按局切分防泄露 |
| 训练数据都来自 vs Lalala | 1. 记牌任务的 ground truth 与对手强弱无关（牌的归属是客观的）<br>2. 但出牌序列风格会偏 Lalala → Phase 4 自对弈补充多样性 |

### 9.4 工程集成风险

| 风险 | 对策 |
|---|---|
| 推理延迟超标 | 1. 模型仅 290K 参数，预期 < 5ms<br>2. 降级策略兜底<br>3. 可用 ONNX 导出加速 |
| 与现有 MemoryTracker 冲突 | 1. NN 只读不写 card_state<br>2. belief_vector 作为独立字段，不覆盖现有追踪逻辑<br>3. 降级时无缝回退到规则记牌 |

---

## 十、与现有代码的对接清单

| 现有文件 | 新增/修改 | 内容 |
|---|---|---|
| `src/v/nn/training/counting_dataset.py` | **新建** | 数据加载、合并、ground truth 构建 |
| `src/v/nn/features/card_counting_network.py` | **新建** | CardCountingNetwork 模型定义（对齐 ISSUES.md GUA-057 登记路径）|
| `scripts/train_card_counting_v8.py` | **新建** | 训练入口（登记 SCRIPT_INDEX.md）|
| `scripts/eval_card_counting_v8.py` | **新建** | 评估脚本 |
| `src/v/nn/features/memory_tracker.py` | **修改** | 新增 `load_counting_model()` / `update_belief()` / `_belief_vector` |
| `src/v/nn/ultimate_win_rate_engine_v7.py` | **修改** | `_heuristic_select` 新增信念规则 ⑨ |
| `docs/guandan-brain/SCRIPT_INDEX.md` | **修改** | 登记 2 个新脚本 |
| `docs/guandan-brain/ISSUES.md` | **修改** | 更新 GUA-057 条目（追加方案文档链接 + 数据勘察结论）|
| `docs/guandan-brain/ITERATIONS.md` | **修改** | 追加 GUA-057 方案编写迭代行 |

---

## 十一、成功标准

**校验指标补充（2026-07-18 评审 · 评审发现 ⑥）**：原 §11.1 只有"平均准确率 > 75% + 大王小王 > 70%"——但决策更关心**关键牌的尾部风险**，平均准确率足够高不代表"对手有大王"不被系统低估。补充以下校准 + 召回指标：

#### 11.1.1 校准指标

| 指标 | 计算 | 目标 | 必要性 |
|---|---|---|---|
| **ECE**（Expected Calibration Error）| 分 10 个 bin，每个 bin |confidence - accuracy| 加权平均 | **< 0.10** | 信念向量必须可信（决策依赖）|
| MCE（Max Calibration Error） | 单 bin 最大偏差 | < 0.20 | 防止极端 bin 失效 |
| Brier Score | MSE of predicted probs | < 0.15 | 综合概率质量 |

**为什么 ECE 必须**：_heuristic_select 用 belief 向量做阈值判断（如 opp_higher_bomb > 0.5 触发扣 200 分），若 ECE > 0.10 阈值不可信，会系统性误判。

#### 11.1.2 关键牌召回指标（漏报代价远大于误报）

| 指标 | 计算 | 目标 |
|---|---|---|
| **大王 recall@0.5** | P(对手有大王) > 0.5 且 ground truth=OPPONENT_HAND 的占比 | **> 90%** |
| 小王 recall@0.5 | 同上 | > 90% |
| 任意 Bomb recall@0.5 | P(对手有任意 Bomb) > 0.5 且实际有的占比 | > 85% |
| 王牌 recall@0.5 | P(对手有 curRank 双副本) > 0.5 且实际有的占比 | > 85% |

**为什么这些必须**：漏报（"对手有大王"预测成"已出"概率 5% 但实际 60%）会直接误导 _heuristic_belief_bomb_risk 的炸弹规避决策，**单次漏报可能丢整局**。误报（预测对手有大王实际没有）代价小——最多让自己少出炸，损失 1 轮节奏。

#### 11.1.3 修订后的完整训练阶段验收（原 4 项 + 新 7 项 = 11 项）

- ✅ 槽位级准确率 > 75%（**平均**）
- ✅ 大王/小王专项准确率 > 70%（**专项**）
- ✅ val_loss 收敛且无过拟合（train/val gap < 5%）
- ✅ 推理延迟 < 20ms（单步）
- ✅ **ECE < 0.10**（校准）
- ✅ **MCE < 0.20**
- ✅ **Brier Score < 0.15**
- ✅ **大王 recall@0.5 > 90%**（关键牌召回）
- ✅ **小王 recall@0.5 > 90%**
- ✅ **任意 Bomb recall@0.5 > 85%**
- ✅ **王牌 recall@0.5 > 85%**

### 11.1.2 事件驱动专项验收

- 小王事件：在明确存在合法大王压制机会的样本中，未压制事件能使对手持大王后验显著下降，且校准 ECE < 0.10。
- 小牌型事件：小 `Straight`/`ThreeWithTwo` 被压后，对手未反压时，同型后验下降、相生牌型后验上升的方向准确率 ≥ 80%。
- 反事实区分：有牌不压与无牌可压的 AUROC ≥ 0.85。
- 队友与对手分离：队友让牌不能被误计为对手缺牌证据；位置关系错误率为 0。
- 事件回放：同一 `history` 重放得到相同事件序列、后验和 `belief_delta`，结果具备确定性。
- 决策安全：事件信念只影响软排序；任何事件模块异常都回退到 `MemoryTracker` 确定性状态。

### 11.1.1 级牌专项验收

- 8 张级牌的 `played + remaining + known_my_level_cards` 在每个样本步严格守恒。
- 级牌计数 MAE ≤ 0.10，不能用平均槽位准确率掩盖计数错误。
- 未出级牌逐张归属准确率 ≥ 75%，对手级牌 recall@0.5 ≥ 85%。
- 级牌归属 ECE < 0.10；置信度不足时必须输出 `unknown`，不得强行归给某一席。
- 含 `tribute`/`back`/`anti-tribute` 的样本单独验收，归属转移零泄漏、零错位。
- 使用牌语、相生相克和算牌信号后，归属模型相对“只看已出数量”基线的 Brier Score 至少下降 10%。

### 11.1 训练阶段验收

- ✅ 槽位级准确率 > 75%
- ✅ 大王/小王专项准确率 > 70%
- ✅ val_loss 收敛且无过拟合（train/val gap < 5%）
- ✅ 推理延迟 < 20ms（单步）

### 11.2 集成阶段验收

- ✅ 批跑 9 局不崩溃
- ✅ 副胜率 > 30%（vs 当前 25.5%）
- ✅ heuristic 信念规则 ⑨ 至少触发 1 次/副
- ✅ 降级策略生效（模拟超时回退正常）

### 11.3 失败标准（需重新评估）

- ❌ 槽位级准确率 < 60%（不如规则记牌）
- ❌ 集成后副胜率下降
- ❌ 推理延迟 > 50ms 且无法优化

---

## 十二、与战略文档的对应

| 战略文档 | 本方案对应 |
|---|---|
| `随机应变套路.md` §套路七 Week 2 | 记牌模块训练（本方案 = Week 2 落地）|
| `人类掼蛋决策流程完整分析.md` §4.2 | 结构化记忆（NN 替代原始序列编码）|
| `组牌-NN衔接设计.md` §10.1 | "2-4 周：NN 记牌模块"（本方案 = 该路线图执行）|
| `技术路径重校.md` §5.3 | 记牌模块为什么是缺失的关键（本方案 = 补这块）|
| `技术路径重校.md` §6.2 行动纲领 3 | "不要放弃 Document 1 的模块化 NN 路线"（本方案 = 践行）|

---

> 本方案的核心赌注：**记牌是 NN 在掼蛋中第一个能做对的事——因为它的输入完整、输出低维、有 ground truth。** 如果这个都做不成，那"NN 打不了掼蛋"就不再是稻草人论证，而是被严格证明的结论。如果做成了，它就是撬动 Guard+heuristic 架构升级为"有信念决策"的第一个支点。

**核心赌注措辞校准（2026-07-18 评审）**：原文末段写"如果这个都做不成，那『NN 打不了掼蛋』就不再是稻草人论证，而是被严格证明的结论"——**这个表述过强，需校准**：

- **Phase 1-3 全部失败** ≠ **"NN 路线"失败**。Phase 1-3 失败只能证明**用 7700 样本做 Transformer 监督学习这条路失败**，其他路径仍未穷尽——
  - **自对弈强化学习**（无监督数据限制）
  - **检索式 / 相似度匹配**（基于局面检索历史决策）
  - **Hybrid 架构**（规则 + NN 混合）
  - **更大规模数据 + 更大模型**（5× 数据后 Transformer 再试）
- 因此本方案**真正可严格证明的命题**是：**"用 7700 样本 + 319K 参数 Transformer 做端到端记牌监督学习"在掼蛋上不收敛**。
- 若要做更广义"NN 打不了掼蛋"的命题，需在所有上述路径都试过且都失败后才能成立。
