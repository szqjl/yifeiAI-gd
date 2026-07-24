# Handoff: C 情形博弈纠错 — yf2 结构性稳定头游

| 字段 | 内容 |
|------|------|
| 日期 | 2026-07-24 |
| 分支 | `v8-dev` |
| 状态 | **observation 纠错，无代码改动** |
| 关联 ISSUES | （无新增 GUA；GUA-159/160/161 框架已覆盖） |
| 关联迭代 | ITERATIONS `v8-sf-endgame-c-scenario-correction` 行 |
| 锚点 | `game_records_v8/20260724070916808898 [yf2_v8]-[opponent_1_3]-[8]-[2].json` 步 68/91 |

## 背景（2 句）

yf2_v8 在 68/91 步空扔 `SF A-5`（5 张♣）作为 lead-1，被用户质疑"为何不先 SB 领出"。追溯到 GUA-137 sprint 评估、`_has_dominating_sprint()` guard 草案、C 情形（opp 持 SF 9-K + 单 K + 对 8 = 8 张）博弈分析时，**上一轮把 "opp 持 SF 9-K" 机械等同为 opp 必胜**，误判 Option B（@3 PASS）→ yf2 后续任意出牌被 SF 9-K 吃 → opp 头游。

## 纠错前错误结论（错）

> 理性 opp 选 Option B（@3 PASS）→ yf2 输了

## 纠错后正确结论（对）

> C 情形下 yf2 头游是结构性稳定解；Option A/B 两条分叉均为 yf2 头游

### 正确反制链 1（Option B 路径：@3 持 SF 9-K 但不主动出）

yf2 68/91 起手持 SB + J 炸 + SF A-5 + Q = 4 张：

| 步 | yf2 | @3 | yf1 | @1 | 牌面 |
|---|---|---|---|---|---|
| 68 | **SB** | PASS | PASS | PASS / 大王 / 炸 | 4 - 1 = 3 张 |
| 69 | **J 炸** 或 **SF A-5** 反压制回收 | — | — | — | 2 张 |
| 70 | **Q** | — | — | — | 1 张 |
| 71 | **SF A-5** 或 **J 炸** 收官 | — | — | — | 0 张 |

**结果**：yf2 头游，@3 的 8 张整局锁死。

### 正确反制链 2（Option A 路径：@3 主动出 SF 9-K 吃 SB）

- @3 出手后剩 K + 对 8 = 3 张 → yf2 出 K → @3 对 8 → yf2 J 炸回收。
- **@3 主动升级反而败得更快**。

## 关键反讽（理解 C 情形稳定性）

- **SF 不可拆**：opp 持 SF 9-K 时，K 不可单独出（被 yf2 SB 抢出牌权）。
- **双重反压制通道**：yf2 的 SB 反压制 + J 炸回收，两条通道任一条成立即 yf2 头游。
- **SF 越强越不敢出**：SF 9-K 越强，opp 越不敢出（出就被炸回收），opp 越不出，yf2 越安全清场。

## 纠错根源

把 "opp 持 SF 9-K" 机械等同为 opp 必胜，忽略了 opp 自身牌型约束（SF 不可拆 + yf2 双重反压制通道）。

## 行动

- **无代码改动**
- **无 pytest 新增**
- **不单独立 GUA**（属于 GUA-159「同型可压时禁炸弹 lead-1」/ GUA-160「队友冲刺期散单优先」框架战术范畴）
- **不再新增 `_has_dominating_sprint` 拦截**（之前的拦截草案属于过度防御，C 情形结构性稳定解已通过现有规则覆盖）

## 后续 / 待澄清

- **44/90 旧问**：在最早一副牌谱（`20260721082741446037 [yf1_v8]-[opponent_1_3]-[35]-[2].json`）中 yf2 前步 3 炸获得出牌权后为何再空扔 44/90，本轮未澄清，不影响 C 情形主线。
- **冲刺 vs 防守**：本档 wiki 触发 = solo-sprint（5 张 + 队友存活约束），C 情形不属于 solo-sprint 触发条件，但策略同源（优先 SB 领出 + 双重反压制通道）。

## 交付清单

| 文件 | 改动 |
|------|------|
| `docs/guandan-brain/ITERATIONS.md` | 追加 `v8-sf-endgame-c-scenario-correction` 行（observation） |
| `wiki/wiki/concepts/solo-sprint.md` | 追加「C 情形示例」段（结构性稳定解） |
| `docs/guandan-brain/handoff/2026-07-24-V8-sf-endgame-c-scenario-correction.md` | 本 handoff 摘要 |

## 一句话结论

> **C 情形下 yf2 头游是结构性稳定解**（SB 反压制 + J 炸回收双重通道），无需任何拦截；当前净盘已完成、AGENTS.md 已修订、ITERATIONS 与 wiki 已同步本轮纠错。
