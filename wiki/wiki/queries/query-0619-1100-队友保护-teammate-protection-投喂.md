---
type: query-answer
title: "队友保护 teammate protection 投喂"
date: 2026-06-19
sources:
  - sources/source-strategy-01-core-01-teammate-protection-summary.md
  - concepts/concept-four-card-power-pillars.md
  - wiki/wiki-minimax/concepts/teammate-yielding.md
  - entities/module-teammate-opportunity-finder.md
  - sources/source-skills-readme-summary.md
  - concepts/p0-m1-cooperation-improvements.md
  - entities/gua-003.md
  - sources/p0_implementation_reports-summary.md
  - synthesis/m3-endgame-guard.md
  - wiki/wiki-minimax/concepts/bomb-execution-rules.md
---

# 队友保护 teammate protection 投喂

# 队友保护 / 投喂（Teammate Protection & Feeding）

队友保护/投喂是掼蛋作为 2v2 团队游戏的核心策略层，Wiki 中涉及 **M3 决策引擎** 和 **M1 引擎 P0 改进** 两条独立演进路线。

---

## 一、战略原则层（来源：[1][2]）

### 掼蛋四项基本原则（[[concept-four-card-power-pillars]]）

1. **谁打谁收** — 先发有回手、搭档接牌慎重
2. **配合至上** — 四大喂牌技巧（让道 / 反向喂牌 / 拆牌喂牌 / 先大后小）
3. **打上家卡下家** — 压制对家上游
4. **强牌弱打 / 弱牌强打** — 隐藏实力或强攻抢分

### 炸弹红黑名单
- **红名单**：关键冲刺 / 队友即将跑牌
- **黑名单**：牌力不足 / 不能保证回手

---

## 二、M3 引擎实现（wiki-minimax/concepts/teammate-yielding.md，GUA-031）

GUA-031 定义了 **PASS-P01~P04 四原则**：

| 原则 | 场景 | 动作 | 置信度 |
|------|------|------|--------|
| **PASS-P01** | 主动 | 送小单让队友接牌 | high |
| **PASS-P02** | 主动 | 防送炸（不主动给队友出炸机会） | high |
| **PASS-P03** | 被动 | `_is_teammate_greater` 时 `return 0` 让道 | high |
| **PASS-P04** | 主动 | 逢五喂队友 | **low**（弱推断，未批跑验证） |

### 关键边界
- **GUA-026**：PASS 不放宽"三带二禁拆炸弹/耗级牌"
- **GUA-029**：PASS 不放宽 R5"不压队友"原则
- **PASS-P04**：以 flag 控制默认开关，需批跑验证胜率

### 实现位置
- `m3_utils._is_teammate_greater` — 辅助函数
- `m3_utils._active` — PASS-P01/P02/P04
- `m3_utils._passive` — PASS-P03

---

## 三、M1 引擎 P0 改进（wiki/concepts/p0-m1-cooperation-improvements.md，GUA-003）

M1 0% 胜率根因：**Lv2 队伙联动能力缺失**。

### P0-③ TeammateOpportunityFinder（[[module-teammate-opportunity-finder]]）
- **文件**：`teammate_opportunity_finder.py`（176 行 / 7272 bytes）
- **职责**：识别队友可能跑牌的机会，**主动传牌配合**
- **Commit**：`f4de5b7`
- **核心洞察**：传牌是**协作非攻击**，集成到 **PassiveHandler**（接牌方）而非 ActiveHandler

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

### ⚠️ 当前阻塞（GUA-003 [7]）
- ✅ 已实现并集成到 4 个 PassiveHandler
- ❌ **20 局批跑 0 触发**（疑似 dead code 或条件过严）
- 下一步：检查 PassiveHandler 是否真的调用、加单元测试、降低触发门槛验证通路

---

## 四、末段博弈综合（synthesis-m3-endgame-guard）

残局时三个 GUA 形成「常态 → 让道 → 拦头」三层结构：

| 局面 | 主策略 |
|------|--------|
| 4 人在场 | GUA-029 通用 |
| 队友 rest | **GUA-031 让道**（优先于 GUA-034） |
| 对手 [myPos+2] rest | **GUA-034 solo_sprint** |

**关键边界**：队友 rest 优先于对手 rest；同时发生时走 GUA-031 而非 GUA-034。

---

## 五、核心代码契约

```python
def is_teammate_controlling(state, teammate_id):
    """判断队友是否在控制牌权"""
    pass

def should_pass_for_teammate(state, teammate_id, action):
    """判断是否应让道给队友"""
    pass

def _should_feed_teammate(state, teammate_id, my_action):
    """判断是否应喂牌给队友"""
    pass
```

---

## 六、紧张点 / 待澄清

1. **"送三张/三带二" vs "P-J03 示弱送夯"** [1] — 触发条件需在 GUA-031 实施跟踪中区分
2. **PASS-P04 置信度=low** [3] — 弱推断，需批跑验证
3. **"代码完成" ≠ "代码生效"** [6] — GUA-003 已集成但 0 触发，需排查 dead code 风险
4. **GUA 追溯缺失** [8] — P0 文档群未引用 GUA 编号，违反 Wiki 脊柱原则

---

**关联 GUA**：GUA-003 / GUA-026 / GUA-029 / GUA-030 / GUA-031 / GUA-032 / GUA-033 / GUA-034
