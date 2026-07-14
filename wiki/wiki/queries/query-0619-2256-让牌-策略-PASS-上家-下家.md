---
type: query-answer
title: "让牌 策略 PASS 上家 下家"
date: 2026-06-19
sources:
  - wiki/wiki-minimax/concepts/teammate-yielding.md
  - queries/query-0619-1100-队友保护-teammate-protection-投喂.md
  - queries/query-0619-1117-送牌-喂牌-投喂-队友-让牌-送队友.md
  - sources/m1-pass-gua020-021-summary.md
  - entities/module-teammate-opportunity-finder.md
  - concepts/stagerouter-forced-nonpass-fallback.md
  - concepts/concept-four-card-power-pillars.md
  - sources/source-skills-31-passing-skills-summary.md
  - sources/source-strategy-01-core-01-teammate-protection-summary.md
  - concepts/concept-engine-mapping-principles.md
---

# 让牌 策略 PASS 上家 下家

# 让牌 / 策略 / PASS / 上家 / 下家

## 核心结论

让牌是掼蛋 2v2 团队协作的核心策略簇（送牌/喂牌/投喂/让牌/送队友 是同一策略的不同口语表达），主要映射到 **GUA-031** 的 PASS-P01~P04 四原则 [1][2][3]。

---

## 一、四项基本原则 [1][2][3][7]

### 1. 谁打谁收
- **先发有回手**：先手出牌必须考虑能否收回牌权
- **搭档接牌慎重**：队友接牌要谨慎，避免让其陷入困境

### 2. 配合至上（四大喂牌技巧）

| 技巧 | 说明 |
|------|------|
| **让道** | 避开队友牌型（不出大牌抢队友牌权） |
| **反向喂牌** | 逆向支援队友 |
| **拆牌喂牌** | 拆自家牌型喂队友 |
| **先大后小** | 先用大牌清路、再用小牌喂 |

### 3. 打上家卡下家
- 压制对家上游，阻止其跑牌

### 4. 强牌弱打 / 弱牌强打
- 强牌时隐藏实力，弱牌时强攻抢分

---

## 二、M3 引擎实现：GUA-031 PASS-P01~P04 [1][2]

| 原则 | 场景 | 动作 | 置信度 |
|------|------|------|--------|
| **PASS-P01** | 主动 | 送小单让队友接牌 | high |
| **PASS-P02** | 主动 | 防送炸（不主动给队友出炸机会） | high |
| **PASS-P03** | 被动 | `_is_teammate_greater` 时 `return 0` 让道 | high |
| **PASS-P04** | 主动 | 逢五喂队友 | **low**（未批跑验证） |

### 关键边界
- **GUA-026**：PASS 不放宽"三带二禁拆炸弹/耗级牌"
- **GUA-029**：PASS 不放宽 R5"不压队友"原则
- **PASS-P04**：以 flag 控制默认开关，需批跑验证胜率

### 实现位置
- `m3_utils._is_teammate_greater` — 辅助函数
- `m3_utils._active` — PASS-P01/P02/P04
- `m3_utils._passive` — PASS-P03

---

## 三、上家 / 下家：打上家卡下家原则 [1][7][9]

"打上家卡下家"是四项基本原则之一——**压制对家上游**（打上家），**阻止其跑牌**（卡下家）。

### 残局末段博弈 [2][3]

| 局面 | 主策略 | 优先级 |
|------|--------|--------|
| 4 人在场 | GUA-029 通用 | — |
| 队友 rest | **GUA-031 让道** | 优先于 GUA-034 |
| 对手 [myPos+2] rest | **GUA-034 solo_sprint** 拦头 | — |
| 接风 + 队友是 Pair/Bomb | GUA-036 TEAM-P01 接风让道 | 让道 > 评分最高 |

**冲突解决**：
- 队友 rest > 对手 rest（互斥时走 GUA-031）
- 让道（WIND-P01 / TEAM-P01）> 评分最高

---

## 四、M1 引擎实现：TeammateOpportunityFinder (P0-③) [2][3][5]

- **文件**：`teammate_opportunity_finder.py`（176 行 / 7272 bytes）
- **关键 Commit**：`f4de5b7`
- **核心洞察**：传牌本质是**协作非攻击**，因此集成到 **PassiveHandler**（接牌方）而非 ActiveHandler

### 4 个集成点
| Handler | 集成位置 |
|---------|----------|
| `OpeningPassiveHandler` | L524-547 |
| `MidEarlyPassiveHandler` | L1428-1455 |
| `MidLatePassiveHandler` | L2303-2326 |
| `EndgameEarlyPassiveHandler` | L2940-2963 |

### 调优参数（激进策略）
| 参数 | 保守 → 激进 |
|------|-------------|
| `teammate_remain` | 15 → **12** |
| `card_power` | 4 → **3** |

### ⚠️ 当前阻塞（GUA-003）
- ✅ 已实现 + 已集成 4 个 PassiveHandler
- ❌ **20 局批跑 0 触发** — 疑似 dead code 或条件过严
- 下一步：检查 PassiveHandler 是否真的调用、加单元测试、降低触发门槛验证通路

---

## 五、StageRouter 强制非 PASS 兜底机制（GUA-061）[6]

M1 中 `stage_router.py` 的**兜底逻辑**：当所有合法动作评估后无可出牌时，强制选择一个非 PASS 动作以避免直接弃权。

### 实际表现（问题诊断）
1. **过牌过大**：在末游位仍出炸弹等高代价牌型
2. **忽略队友**：未考虑队友是否需要过牌
3. **战术失衡**：强制出牌导致手牌结构破坏

### 修复方向
- **方案 A**：完全允许 PASS（风险：连续 PASS 送局）
- **方案 B**：智能兜底——优先最小代价牌型（复用 `choose_bomb` 逻辑）
- **方案 C（V7 路线）**：通过 PPO 奖励信号让网络学会「合理 PASS」语义

---

## 六、炸弹使用红黑名单 [7][9]

### 红名单（建议使用）
- 关键冲刺阶段
- 队友即将跑牌
- 必胜局面

### 黑名单（避免使用）
- 牌力不足时
- 不能保证回手
- 浪费在非关键局面

---

## 七、残牌张数策略矩阵 [8]

| 剩余张数 | 策略 |
|----------|------|
| 2 张 | 先中大后小 |
| 3-4 张 | 送单/对/三张通路 |
| 5 张 | 大概率三带二，送三带二或顺子 |
| 6 张 | 5+1 送单，4+2 送对 |
| 7 张 | 有王出单/对子通路 |
| 8 张 | 单/对/三张 |
| 9 张 | 送 5 张牌型（三带二/杂花顺） |
| 10 张 | 三带二 + 杂花顺优先 |

---

## 八、紧张点 / 待澄清

1. **PASS-P04 置信度=low** [1][2] — 弱推断，需批跑验证胜率提升
2. **GUA-003 "代码完成" ≠ "代码生效"** [2][3] — 0 触发，需排查 dead code 风险
3. **"送三张/三带二" vs "P-J03 示弱送夯"** [1][2] — 触发条件需在 GUA-031 实施跟踪中区分
4. **GUA-061 强制非 PASS 兜底** [6] — 与过牌过大同根因，需选修复方案
5. **文档口径分歧** [8][10] — "逢五出对"在 02 归 P1、在 31 归 P0，需核对 `PRINCIPLES_MAPPING.md`

---

## 关联 GUA 索引

**GUA-003** / GUA-020 / GUA-021 / **GUA-026** / **GUA-029** / **GUA-030** / **GUA-031** / GUA-032 / GUA-033 / **GUA-034** / GUA-036 / **GUA-061**

---

**关联页面**：[teammate-yielding] [team-coordination] [concept-four-card-power-pillars] [concept-p0-m1-cooperation-improvements] [module-teammate-opportunity-finder] [stagerouter-forced-nonpass-fallback] [concept-engine-mapping-principles] [bomb-execution-rules] [m3-endgame-guard]
