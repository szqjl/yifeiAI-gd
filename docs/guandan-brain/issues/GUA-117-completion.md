# GUA-117 完成定义（助攻出牌 · Layer2 领出 + Layer0 guard + pytest）

> 登记 **2026-07-05**。设计真源：[`助攻出牌-阶段划分设计口径.md`](../助攻出牌-阶段划分设计口径.md)。技能真源：[`助攻出牌要领.txt`](../../archive/skill/助攻出牌要领.txt)。  
> **关单拍板（方案 A）**：§6 **#1–#7 全部 ✅** 才可关 v1；禁止仅「S1 + 3.1 + 路由 + Q1」提前关单。

## 范围

| 层 | 内容 | 状态（2026-07-05） |
|----|------|-------------------|
| **Layer 2 领出** | `stage_assist_feed.recommend_assist_lead()`：S1-1/S1-2、3.1+Q1、2.1 S1-1 回落 | ✅ 已实现（`ITERATIONS` v7-gua117-assist-prefer-pipeline） |
| **路由** | 助攻/超弱 `is_lead` → assist feed；091 退役 `mid_feed_teammate_lead` | ✅ |
| **Layer 0 guard** | §四 **B1–B6** + 约束 1 让权（助攻/超弱全阶段） | ✅ **117-2a–2g**（`assist_layer0_guard.py`） |
| **pytest §6-7** | 领出 + B1–B6 各 ≥1 case + 队友领牌 PASS | ✅ **117-7a–7f**（86/86 bundle） |
| **P1（不挡 v1）** | GUA-094 真 2.1、L81 顺最小散牌、2.2 炸送同款、B7/B8 | → **GUA-118–121**（见下 §P1/P2） |

**角色**：`助攻` / `超弱` **同一选牌器 + 同一 guard 集**。  
**禁止**：新建 `_stage_assist_pass_response()`；非领出仍走 075 / 091 / Q1（§4.3）。

---

## P1 / P2 后序（不挡 v1 关单）

> **登记 2026-07-05**。ISSUES 主表：**GUA-118**（P2）、**GUA-119–121**（P1）。建议顺序见 `ITERATIONS` **gua117-p1-p2-roadmap**。

| 子任务 ID | ISSUES | 说明 | 依赖 |
|-----------|--------|------|------|
| **117-P2** | **GUA-118** | §三 L81：队友领牌时 **顺最小散牌**（单 5–9 / 小对）；`_recommend_play` 队友分支，不新函数 | GUA-117 v1 关单后可并行 |
| **117-P1-094** | **GUA-119** | stage_2 **真 2.1 同款**；替换 S1-1 回落 / `_feed_mid_match_fallback` | **GUA-094** |
| **117-P1-gf** | **GUA-120** | Q2 **P1+**：V5 `group_filter` **硬约束**（117-2d 软禁之上） | GUA-094 → GUA-119 建议 |
| **117-P1-misc** | **GUA-121** | 2.2 炸送同款、B7/B8、P1-R09 批跑、sprint_fire 助攻开放 | 见 [[GUA-121-completion]] |

---

## §6 总清单（关单 gate）

| # | 交付项 | 子任务 ID | 状态 |
|---|--------|-----------|------|
| 1 | `recommend_assist_lead()` | — | ✅ |
| 2 | Layer0 B1–B6 | **117-2a … 117-2g** | ✅ |
| 3 | S1-1 / S1-2 | — | ✅ |
| 4 | 2.1（无 094 → S1-1 回落） | — | ✅ |
| 5 | 3.1 + Q1 表 + rest≥6 回落 | — | ✅ |
| 6 | 路由 + 091 fake feed 退役 | — | ✅ |
| 7 | pytest 全量 | **117-7a … 117-7f** | ✅ |

---

## #2 Layer0 — 子任务（117-2a … 117-2g）

落点主文件：`src/v/nn/guards/v7_guards.py`（`filter_action_list` 或新增 `_assist_blacklist_*`）；必要时 `ultimate_win_rate_engine_v7.py` 注入 `_role` / `_current_stage`。  
触发条件：`game_state['_role'] in ('助攻', '超弱')`（与 GUA-113 Q1 同源字段）。

| 子任务 | 黑名单 | 拦截语义 | 实现要点 | 依赖 |
|--------|--------|----------|----------|------|
| **117-2a** | **B1** | 队友为圈最大时，禁 **A/级/王/炸弹/SF** 压队友 | 扩展 R05/R07：助攻角色下 bomb-like + 高点 Single/Pair 硬剔除；intent `assist_yield_teammate` | GUA-065、GUA-113 |
| **117-2b** | **B2** | 助攻 **自由领出**禁主动炸弹、长顺、连对 | `is_lead` + stage_1/2 在 guard 或 feed 出口二次校验；与 S1 首发禁令对齐 | `stage_assist_feed` |
| **117-2c** | **B3** | 拿权禁出队友 **从未出过** 的牌型（陌生顺/连对/三带等） | 消费 `MemoryTracker` / `player_history` 队友 `send` 牌型集合；stage_2 领出与 rest≥6 回落路径均覆盖 | GUA-052；094 前用「无记录→仅允许 S1 允许型」 |
| **117-2d** | **B4** | 前期（stage_1/2）禁 **拆完整配套** 三带/顺/连对 **做无谓消耗** | **Q2 已拍板（2026-07-05）**：v1 **`v7_guards` 软禁** — role=助攻/超弱 + `_action_breaks_core` / 组牌 `is_core` 过滤拆顺、拆三带、拆连对之 **非送牌/非压敌** 候选；intent `assist_guard_b4`。**不做** V5 `group_filter` 硬约束（P1+，依赖 GUA-094 / 队友高频牌型） | GUA-069 `_group_consistency_filter` 可复用思路 |
| **117-2e** | **B5** | 无压制需求、无对手冲刺风险时禁 **主动开炸** | 助攻角色扩展 R05/R11：非 rescue/sprint 场景剔 bomb-like；与 091 `mid_bomb_cutoff` 助攻分支对齐 | GUA-091、R11 |
| **117-2f** | **B6** | 残局送牌与队友 `rest` **牌型不匹配** | `assist_is_close(rest)` 时仅允许 `assist_prefer_for(rest)` 型；与 Q2/R08/R09 一致，**领出 + 非领出 feed 双路径** | `assist_prefer_table`、Q1 ✅ |
| **117-2g** | **约束 1 让权** | 队友控牌：三带/顺 **PASS**（L81 顺最小散牌属 **P2**，v1 仍 PASS 即可） | 与 B1 分工：B1=禁高点/炸压；让权=非 bomb-like 结构 PASS（075/091/Q1 已有部分；guard 层补 **漏网**） | §4.3、GUA-113 |

**117-2 整体验收**：`filter_action_list`（或等价）在 role=助攻/超弱 时，B1–B6 **均有可触达分支**；`GUA-098` trace 可打 `assist_guard_b*` intent（若已接入）。

---

## #7 pytest — 子任务（117-7a … 117-7f）

主文件：`tests/test_gua117_assist_layer0_guard.py`（新建，或拆分多个 `test_gua117_*`）。  
**构造态**为主；不绑具体 `game_id`（见 ISSUES 头部验收理念）。

| 子任务 | 覆盖 | 最低 case 数 | 验收 |
|--------|------|--------------|------|
| **117-7a** | **S1-1** 10 点以下最小对领出 | ≥1 | `assist_feed_s1_small_pair`；含 99，禁 T+ 对 |
| **117-7b** | **S1-2** 6–10 中单；**S1-2b** 无 6–10 → 第二小散单 | ≥2 | `assist_feed_s1_mid_single` / `assist_feed_s1_second_single`；例 2+5→5 |
| **117-7c** | **3.1 rest=1** 最小单 feed | ≥1 | Q2 / prefer / R08 链；可扩展现有 `test_gua117_assist_prefer_pipeline.py` |
| **117-7d** | **B1–B6** 各 ≥1 | **6** | 每条黑名单独立构造 `actionList` + role=助攻；断言被 guard 剔除或 feed 不选中 |
| **117-7e** | **队友领牌 PASS** | ≥2 | stage_1 `_recommend_play`、stage_2 `_stage_mid_dispatch`、Q1 GUA-113 各 1 case |
| **117-7f** | **回归 bundle** | — | 显式路径（PowerShell 勿用 glob）：`pytest tests/test_gua117_assist_layer0_guard.py tests/test_gua117_assist_prefer_pipeline.py tests/test_gua117_stage1_open.py tests/test_gua065_teammate_protection.py tests/test_gua078_endgame_tracker_decide_entry.py tests/test_gua091_stage_mid_dispatch.py tests/test_gua116_main_attack_lead.py -q` → **86/86** ✅ |

**117-7 整体验收**：117-7a–7e 全部存在且 pass；117-7f 作为 CI/关单命令写进本文件与 `ITERATIONS` 末行。

---

## 仍开放（不挡子任务开工，挡关单）

（无 — Q4 已闭合，见下表。）

## 已闭合（实施参考）

| ID | 结论 |
|----|------|
| **Q2** | **v1 = B4 软禁**（117-2d）；**P1+ = V5 group_filter + 队友高频牌型** |
| **Q4** | **不可 PASS**；S1-× 窄 fallback，禁顺/连对/三带/炸，优先最小 Pair/Single |

---

## 关单条件（GUA-117 v1）

| 项 | 要求 |
|----|------|
| **代码** | §6 #1–#6 ✅；**#2 117-2a–2g 全部落地** |
| **测试** | **#7 117-7a–7f 全部 pass** |
| **文档** | `助攻出牌-阶段划分设计口径.md` §6 状态列更新；`ITERATIONS` 追加关单行 |
| **不作关单** | **GUA-118–121**（P1/P2 续包）、M3 批跑队胜率 KPI |

**建议实施顺序**：117-2f（与 Q1 同源）→ 117-2a/2g → 117-2b → 117-2e → 117-2c → 117-2d（Q2）→ 117-7d 与 2 同步补测 → 117-7a–7c/7e → 117-7f 回归。
