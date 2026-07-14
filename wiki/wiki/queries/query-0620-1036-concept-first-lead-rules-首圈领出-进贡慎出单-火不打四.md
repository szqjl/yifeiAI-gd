---
type: query-answer
title: "concept-first-lead-rules 首圈领出 进贡慎出单 火不打四 顺子慎始发 P-H01 P-H05"
date: 2026-06-20
sources:
  - queries/query-0620-1032-领出-含义-首出-第一手-策略.md
  - sources/PRINCIPLES_MAPPING-summary.md
  - queries/query-0620-1036-首出策略-领出-首发-第一手-出牌策略.md
  - sources/source-skills-08-straight-skills-summary.md
  - sources/source-skills-01-basic-principles-summary.md
  - concepts/concept-first-lead-rules.md
  - concepts/concept-guandan-principles-pillars.md
  - sources/GUA-032-completion-summary.md
  - concepts/principles-mapping.md
  - sources/m3-skills-mapping-gua030-summary.md
---

# concept-first-lead-rules 首圈领出 进贡慎出单 火不打四 顺子慎始发 P-H01 P-H05

# 首圈领出规则 · 首出高压线（P-H01 / P-H02 / P-H05）

## 一、领出 vs 首出（概念区分）

| 术语 | 含义 | 性质 |
|------|------|------|
| **领出** | 每副由谁先出第一张 | **规则产物**（平台/规则决定） |
| **首出** | 领出者打出的**第一手牌** | **策略决策** |
| **第一手** | 同"首出" | 口语 |

⚠️ **领出 ≠ 首出策略**。[1][6]

## 二、领出规则（谁先出）[6]

| 场景 | 领出者 |
|------|--------|
| 第一副 | 服务器决定 |
| 第二副起（普通进贡） | 进贡给上游者（受贡者）领出 |
| 双下 | 三游领出 |
| 抗贡 | 上游（头游）领出 |
| 普通升级 | 上游（头游）领出 |

> M3 引擎与批跑数据 **以平台 act 为准**（实体赛旧规"下游领出"已被覆盖）。[6]

## 三、首出高压线（P0 · M3 已实施）

| 原则 | 含义 | M3 状态 |
|------|------|---------|
| **P-H01 / P-G04** | **进贡慎出单** | ✅ P0 实施 |
| **P-H02** | **火不打四**（4 头炸慎首发）| ✅ P0 实施 |
| **P-H05** | **顺子慎始发** | ✅ P0 实施 |

高压线属于**五条高压线原则**的子集，原文自述"五条"但实列**六条**（多出"不越级上小王"）。[5][7]

## 四、首出牌型含义（牌语信号）[1]

| 首出牌型 | 牌语含义 |
|----------|----------|
| **小单** | 牌力强（无需大牌保护） |
| **小顺** | 牌力强 / 有打有收 |
| **对子** | 试探，意图不明 |
| **高单** | 助攻 / 交牌权 |
| **木板/钢板** | 中性 |
| **三张** | 弱牌（无力组更大牌型） |
| **炸弹** | ⚠️ 高压线慎首发（P-H02） |
| **大顺** | ⚠️ 高压线慎首发（P-H05） |

## 五、归属与张力

- **P-H01 / P-H05**：M3 P0 实际仅落这两条。[9][10]
- **P-H05 归属张力**：§十八 顺子技巧称 P-H05 属既有 P0/GUA-032；§十九 三连对称"P-H05 可扩"——待澄清。[4]
- **CALC-M02 与 P-H01 合并机会**：进贡无级牌 + `numofnext==1` → `_active` 禁过小单，可与 P-H01 合并关单。[8]

## 六、V7 引擎首出决策 [1][3]

```
输入：手牌 + main_rank + 局况
  ↓
1. SF_FIRST：识别同花顺苗子
  ↓
2. BOMB_FIRST：识别炸弹
  ↓
3. enumerate_groupings()：枚举所有组法
  ↓
4. _score_power()：5 维评分（0.3 炸弹 + 0.3 手数 + 0.1 回收 + 0.1 灵活 + 0.2 去单化）
  ↓
5. 选择 power_score 最高的组法
```

### V7 关键 Guard 规则
- **R10 领出不炸**（GUA-066）— 首发炸弹硬排除
- **R07/R08/R09 队友保护**（GUA-065）

### V7 已知限制（与 P-H 系列相关）
- **首发 +1 分**未实现（口诀建议但未纳入）
- **配 5 头炸策略冲突**（未显式惩罚 → 与 P-H02 火不打四张力）
- **孤张定律 / A 下放**未量化

### 批跑表现鸿沟
- 单元测试 27/27 通过；实战 9 局队胜率 **0%**（GUA-062）

---

## 关键参考

- **概念**：[[concept-first-lead-rules]] [6] / [[concept-guandan-principles-pillars]] [7]
- **源文档**：[[source-skills-01-basic-principles-summary]] [5] / [[source-skills-08-straight-skills-summary]] [4]
- **原则映射**：[[PRINCIPLES_MAPPING-summary]] [2] / [[principles-mapping]] [9]
- **GUA**：GUA-030（原则映射）/ GUA-032（记牌算牌 + P-H05）[8] / GUA-062（V7 组牌）/ GUA-066（领出不炸）
- **查询**：[query-0620-1032 领出策略] [1] / [query-0620-1036 首出策略] [3]
