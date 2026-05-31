# M3 完整诊断报告：22副0胜根因

> M 系列代际文档 · 与 [M2_OPTIMIZATION.md](M2_OPTIMIZATION.md)、[M1_ARCHITECTURE.md](M1_ARCHITECTURE.md) 同级  
> 分析日期: 2026-05-27（初版）；**2026-05-30 增补「场态消息用法」重大发现**  
> 测试数据: 4整局22副 / M3(vs lalala) / 0胜0平22负 / 对手均升至A级

---

## ⚠️ 重大发现（2026-05-30）：M3 对服务器 WebSocket 消息「用法不完整、不够准确」

> **登记**：[`ISSUES.md`](ISSUES.md) **GUA-027**  
> **依据**：[`docs/gdrules/掼蛋平台使用说明书1006.md`](../gdrules/掼蛋平台使用说明书1006.md)（v1006）、`offline_platform/guandan_offline_v1006/clients/state.py`、19 局 yf1/yf2 录制审计（`scripts/tools/audit_greater_in_records.py`）

### 结论（一句话）

M3 **不是**「读错字段名」或「漏读 act 键」；而是 **读到了 `curAction` / `greaterAction` / `publicInfo`，却没有按平台完整语义使用**——被动决策偏依赖 `curAction` 算牌力，**未始终以 `greaterAction` 为「本圈要压的目标」**，也 **未用 `publicInfo[].playArea` 校验或重算本圈最大**。这会导致场态理解偏差，进而影响出牌；与 lalala 同源逻辑，属于 **observation + policy** 双层问题。

### 平台说明书语义（v1006 真源）

| 字段 | 含义 |
|------|------|
| `curPos` / `curAction` | **刚发生的那一步**：谁出牌、出了什么（含 PASS） |
| `greaterPos` / `greaterAction` | **本圈当前最大一手**：被动出牌时要压的目标 |
| 接风 / 领出 | `curPos=-1`，`greaterPos=-1`，动作为 `None` |
| `publicInfo[].playArea`（**act**） | 各玩家当前出牌区；说明书 act 示例中与「最大动作」文字描述一致，是更贴近「场上真相」的状态 |

**notify 示例**（1 号出单张 2）：`cur` 与 `greater` 相同——因为 **刚出的牌恰好成为本圈最大**，并非「两字段永远同义」。

**act 示例**（说明书 §play）：文字写「当前动作为 X 号-…，**最大动作为** Y 号-…」，并给出四家 `playArea`。接风/率先出牌时 `curPos=-1`、`greaterPos=-1`。

### M3 现状：读了什么、用了什么

**客户端 `yf1_m3` / `yf2_m3`（act）已读取**：

- `curPos` / `curAction`、`greaterPos` / `greaterAction`
- `publicInfo`（含 `playArea`）、`actionList`、`handCards`、`curRank` 等

**决策引擎 `m3_decision_engine`（`src/m/m3/`）实际用法**：

| 说明书要求 | M3 现状 | 风险 |
|-----------|---------|------|
| 被动比牌以 `greaterAction` 为准 | 仅在 `curAction[0]=="PASS"` 时把 `curAction` 替换为 `greaterAction`；否则 `_Single/_Pair/...` 用 **`curAction[1]`** 算 `curVal` | 上一手出了牌但未压过本圈最大时，会把「上一手点数」当成要压的目标 |
| `publicInfo.playArea` 参与场态 | **决策路径中未使用**（仅录制 context 可能带上） | 无法交叉校验 greater；服务器 greater 错时无兜底 |
| notify 与 act 一致性 | 未校验 | 录制 JSON 的 greater 可能与决策时刻 act 不一致时无感知 |

**典型代码路径**（与 lalala `action.py` 同源）：

```python
# m3_decision_engine._passive
if curAction[0] == "PASS":
    curAction = greaterAction   # 仅 PASS 时改用 greater
# 否则仍用 curAction 分发并算 curVal
curVal = card_val[curAction[1]]  # 应用 greaterAction[1] 的场景未覆盖
```

### 审计证据（2026-05-30，19 局 yf1/yf2 录制）

运行 `python scripts/tools/audit_greater_in_records.py`：

- 非 PASS 步：**100%** `cur_pos == greater_pos`（notify 录制）
- 可比对单牌步（约 582 步）：**~40.5%** 出现「按 `playArea`/上一手 greater 推断的本圈最大」与 **notify 中 `greaterAction` 不一致**（例：A 为本圈最大后，1 号出 9，greater 仍被记为 9 而非 A）
- M3 实战读 **WebSocket act**，不读 JSON；act 日志中同一步 **`greaterAction` 亦为 9** → 不单是「录制读错」，而是 **协议字段赋值或语义** 与说明书「本圈最大」不一致，且 **M3 未用 playArea 自救**

### 与 GUA-024 的关系

**GUA-024（已关闭）** 修的是 `curAction[-1]` 误用、字符串化 dispatch、记牌 PASS 等——让 M3 **能出牌**。  
**GUA-027（本发现）** 是更上一层：**在能出牌的前提下，场态（要跟哪一手）可能算错**，属于 observation/信息集问题，会传导到 policy（该压 A 却以为只须压 9 → 错误 PASS 或乱出）。

### 修复方向（尚未实施，供下轮迭代）

| 优先级 | 项 | 说明 |
|--------|-----|------|
| ~~**P0**~~ | ~~被动 `_Single/_Pair/_Trips/...`~~ | **已实现 2026-05-30（GUA-027 closed）**：`game_logic/trick_state.py` + M3 `_passive` 用 `beatAction` |
| ~~**P0**~~ | ~~`publicInfo.playArea`~~ | **已实现**：`resolve_effective_greater`；回放 `TrickSequenceTracker` |
| P1 | 回放 `yf_replay` | 与 M3 共用 trick_state（**已接入**显示「本圈最大(重算)」） |
| P2 | 协议侧 | 向平台确认 notify/act 中 greater 语义；离线服「错误动作不处理」与 greater 赋值关系 |

### 非本问题的误判

- ❌ 「JSON 字段名读错」（如 `greaterPos` vs 说明书 OCR 笔误 `qreaterPos`）
- ❌ 「仅回放 bug」（M3 决策不读录制文件）
- ❌ 「服务器单独帮 lalala 改 greater」（lalala 与 M3 同源字段用法；现有证据更像 **全场同一套消息 + 客户端未用全 playArea**）

---

## 比对基准: lalala 原始代码 (`D:\NYGD\lalala\`)

M3 的理论设计是"忠实移植 lalala 决策引擎"，但实际代码中存在多处致命差异。

---

## 🐛 BUG 1（致命）：`_active` 方法中 action 下标错误

**文件**: `src/decision/m3_decision_engine.py:1171`

| lalala (`action.py:1175`) 正确 | M3 错误 |
|---|---|
| `card_value_s2v[actionList[acti][1]]` | `card_val[actionList[acti][-1]]` |

服务端 actionList 格式: `['Single', '4', ['S4']]`
- **lalala** 取 `[1]` = `'4'` (rank 字符串), `card_val['4']` = 4 ✅
- **M3** 取 `[-1]` = `['S4']` (cards 列表!), `card_val[['S4']]` → `TypeError: unhashable type: 'list'` 💥

触发条件: 主动出牌 + 下家剩1张 + handcards 有单张。

异常被 `yf1_m3.py:115` 的 `except` 静默捕获, 默认发 `actIndex=0`(PASS)。残局关键机会被直接放弃。

---

## 🐛 BUG 2（策略缺失）：残局两手牌组合分析未移植

**文件**: lalala `action.py:1117-1127` → M3 中完全不存在

lalala 在 `active()` 中有残局关键逻辑:
```python
if len(handcards) <= 12:
    for i in range(len(actionList)):
        for j in range(i+1, len(actionList)):
            if len(actionList[i][-1]) + len(actionList[j][-1]) == len(handcards):
                combine_list = actionList[i][-1] + actionList[j][-1]
                if combine_list.sort(...) == handcards.sort(...):
                    twohand_candidatelist.append((i, j))
```

这段代码在 ≤12 张时枚举"两手出完"的配对组合, 是掼蛋残局规划的核心。M3 完全没有移植此逻辑, 导致残局只会逐张出小牌。

---

## ~~🐛 BUG 3（策略扭曲）~~ 已更正：此处非 bug

**~~CARD_VALUE_S2V 中 "2"=2~~** — 此前分析错误。

### 勘误说明

经用户指出，掼蛋规则是：
- **打2时**：2是级牌 → `card_val["2"] = 15` (override)，2 > A ✅
- **打其他级别(3~A)时**：2**不是**级牌，2变成最小牌（比3还小）

M3 代码：
```python
card_val = CARD_VALUE_S2V.copy()  # "2": 2 (非级牌时最小)
card_val[rank] = 15               # 当前级牌排值升至最高
```
- 打5时：2=2, 5=15 → 2 < 3 < 4 < 6 < 7 < ... < A < 5(级) ✅
- 打2时：2=15 → 3 < 4 < ... < A < 2(级) ✅

`"2": 2` 是正确的默认值，级牌时会被 override。此条从 bug 列表中移除。

---

## 🐛 BUG 4（配合缺失）：完全无队友协作策略

从 22 副的 finishing order 可见:

```
[3, 1, 0, 2]  →  lalala 包揽头游、二游, M3 三游、末游
[1, 3, 0, 2]  →  同上, lalala 方互换位置
```

M3 `_passive` 只检查 `(myPos+2)%4 == greaterPos` 来决定是否管队友的牌, 但缺乏:
- 传牌给队友的主动策略
- 根据队友剩牌数做决策的意识
- 压制对手为队友创造机会的逻辑

相比之下, lalala 通过原始 `State` 和 `Action` 类维护完整的 `history` 和 `remain_cards`, 天然包含了对手建模。

---

## 🐛 BUG 5（炸弹策略消极）：几乎不用炸弹

M3 的炸弹使用条件非常保守:
- **被动**: 仅当 `pass_num >= 5` 或 `my_pass_num >= 3` 时才考虑
- **主动**: 优先出所有非炸弹牌型, 炸弹基本不主动使用
- **对炸弹**: 仅 `cur_Bomb_num >= 3` 或 `greaterPos` 剩牌 ≤18 时用

从服务器日志可见 lalala 会果断用炸弹终结, 而 M3 从未主动使用炸弹抢控。

---

## 📊 日志表现复盘

服务器日志 (`m3_run_error.log`) 第一副实际流程:

```
1. yf1_m3 (M3 P0) 先手 → 出 S4 (合理, 最小单张)
2. client3 (lalala P1) 出 HT → 压住, 拿回控制权
3. yf1_m3 / yf2_m3 → 连续 PASS × 10+ 次
4. client4 (lalala P3) 出 炸弹 8888 → 直接结束该轮
5. yf2_m3 进贡 C5, yf1_m3 进贡 HR(红桃级牌!)
6. client3 还贡 D8, client4 还贡 C9
   → M3 进贡最好的牌, 只拿回 3 和 8/9
7. 下一轮开始 M3 手牌更劣势, 继续输
```

恶性循环: 输→进贡好牌→拿回烂牌→更输→再进贡...

---

## 🔧 修复优先级

| 优先级 | Bug | 修复难度 | 预期提升 |
|---|---|---|---|
| **P0** | **BUG6: 场态消息用法（GUA-027）** | 中等（greaterAction + playArea 重算） | 被动跟牌/压牌正确率；减少「以为压 9 实际须压 A」类失误 |
| P0 | BUG1: index -1 → 1 | 改1行 | 消除残局崩溃, 恢复关键出牌机会 |
| P0 | BUG2: 两手牌组合 | 移植 ~15行 | 残局规划能力恢复 |
| P1 | BUG4: 配合策略 | 较大 | 长期竞争力 |
| P1 | BUG5: 炸弹策略 | 调阈值 | 恢复控场能力 |

> BUG3 ("2"=2) 已确认为正确规则，移出列表。详见上方勘误。  
> **BUG6** 详见文首「重大发现（2026-05-30）」；与 GUA-024 互补，不重复。

---

## 📝 对话记录

### 下一步行动计划（已记录，暂不执行）

1. 复制 lalala 客户端为 MC，与 lalala 跑对局验证一致性

### Q: M3对掼蛋最基本的规则是否了解？是否有硬编码？比如队友保护、送牌给队友、争取头游、压制对手、还贡牌等？

**A: M3 对掼蛋基本规则的掌握程度非常浅，几乎全是硬编码阈值，缺乏真正的策略理解。**

| 策略 | 状态 | 说明 |
|---|---|---|
| 队友保护 | ❌ 极弱 | 仅检查 `(myPos+2)%4 == greaterPos` 决定"是否让队友走"，无保护队友出牌权逻辑 |
| 送牌给队友 | ❌ 不存在 | 不分析队友手牌，不会主动出队友可能有的牌型 |
| 争取头游 | ❌ 不存在 | 无"头游优先"评分体系，残局两手组合分析缺失 |
| 压制对手 | ❌ 极弱 | 炸弹阈值高（pass≥5才考虑），从不主动用炸弹抢控 |
| 还贡策略 | ⚠️ 有但弱 | 有专门逻辑但仅限"避免拆顺子/三连对"等简单规则 |
| 进贡策略 | ❌ 简单 | 仅检查是否包含级牌，否则选第一个 |

**核心问题**：M3 本质是 if-then 决策树 + 硬编码阈值（如 `cur = [9,10,9,8,10,10,2]`），无任何学习成分或动态评估。`_Single` 方法中 10+ 个硬编码阈值（`max_val-2`、`pass_num>=5`、`numofnext<=4` 等），全靠手工调参。

### Q: M3 的组牌能力？有没有组牌函数？

**A: 有，两个组牌函数，但能力有限。**

**`combine_handcards`** (`m3_utils.py:26`) — 按点数分组为 Single/Pair/Trips/Bomb，再检测 Straight/StraightFlush。

**`_get_list`** (`m3_decision_engine.py:1181`) — 构建各牌型的 action list（单张、对子、三张、三带二、三连对、钢板、顺子）。

**不足**：
- 逢人配万能牌特性在组牌中不体现（由服务端处理）
- 无"最优组牌"策略——3333 当炸弹还是拆成 333+3，没有动态权衡
- 无跨牌型重组——不会考虑"顺子里的牌拆出来组别的牌型"

### Q: M3 知不知道队友、对手的概念？

**A: 知道位置映射，但无协作策略。**

知道：
- `myPos`=自己，`(myPos+2)%4`=队友，`(myPos+1)%4`、(myPos-1)%4=对手
- 追踪所有玩家剩牌数 `numofplayers`
- 用 `numoffri`（队友剩牌）控制激进程度
- 检查 `(myPos+2)%4==greaterPos` 判断是否队友控场

不知道/不用：
- ❌ 主动传牌给队友
- ❌ 压制对手为队友创造机会
- ❌ 队友PASS时的接管策略
- ❌ 针对对手牌型的分析

纯算术级别"知道"ID，无真正配合。

### Q: 红心配(逢人配)的用法，M3是否知道优先配什么？非必要不单出？不搭配单张组对子、不搭配对子组三不带？有无硬编码？

**A: M3 对逢人配完全没有战略意识。**

- 组合由**服务端**生成（服务器算好 actionList 里哪些合法），M3 只管从列表里选
- `combine_handcards` 将逢人配当普通牌按点数分组，**不识别万能牌特性**
- 唯一的硬编码：进贡时检查 `rank_card in action[2]` 尽量保留

| 规则 | M3知道吗 |
|---|---|
| 优先配炸弹/同花顺 | ❌ 无偏好 |
| 非必要不单出 | ❌ 当普通牌出 |
| 不配单张成对子 | ❌ 无保护逻辑 |
| 不配对子成三不带 | ❌ 无保护逻辑 |
| 战略保存逢人配 | ❌ 不存在 |

**能跑通是因为服务端保证 actionList 合法性，但 M3 选牌时完全浪费了万能牌的战略价值。**

### Q: M3 对牌力大小是否理解？比如 J > 10 等

**A: 基本牌力顺序理解正确。** `CARD_VALUE_S2V` 中 `3`~`A` 的映射准确（T=10, J=11, Q=12, K=13, A=14），J>10 这类判断没问题。

唯一问题是 `"2": 2`（详见 BUG 3），导致 2 被当成最小牌。另外出牌合法性由服务端校验，M3 的牌值仅用于策略决策，不影响能否出牌。

### Q: M3 对级牌是否有概念？

**A: 有基本概念，但关键逻辑错误。**

有：
- 定义 `rank_card = 'H' + rank` 标识红桃级牌
- `card_val[rank] = 15` 将级牌排值提至 15（高于 A=14）
- 进贡时检查级牌以决定是否保留

缺：
- 不追踪逢人配的万能牌用法——`_update_play_state` 只记牌面值，不记实际充当了什么牌
- `"2": 2` 永远不变，与级牌排值冲突

### Q: 打5时5是级牌，M3是否知道5>A、5<小王？是否知道2这时是最小的？

**A:** 此前回答有误，现更正。

✅ **M3 理解正确**。掼蛋规则：
- 打2时：2是级牌，2 > A，2 < 小王
- 打其他级别(3~A)时：2不是级牌，2变成最小牌（比3还小）

打5时正确排值：
```
2(最小) < 3 < 4 < 6 < 7 < 8 < 9 < T < J < Q < K < A < 5(级) < 小王 < 大王
```

M3 做法：
```python
card_val = CARD_VALUE_S2V.copy()  # 2=2, 3=3, ..., A=14
card_val[rank] = 15               # 级牌=5 时, card_val["5"] = 15
```
- 打5时：2=2 ✅ 最小，5=15 ✅ >A，B=16 ✅ <小王
- 打6时：2=2 ✅ 最小，6=15 ✅ >A
- 打2时：2=15 (override) ✅ >A

**关于此问题，用户纠正了我，M3 的 `"2":2` 是正确的掼蛋规则，非 bug。**
