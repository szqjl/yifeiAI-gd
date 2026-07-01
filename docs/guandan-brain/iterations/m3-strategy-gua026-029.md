---
tags: [M3, strategy, GUA-026, GUA-029, ThreeWithTwo, bomb]
created: 2026-05-30
updated: 2026-05-31
topic: M3 三带二拆牌保护与炸弹规则
related: [[M3-Development]], [[m3-integration-gua024-028]]
---

# M3 策略：三带二拆牌 + 炸弹规则（GUA-026 / GUA-029）

> 来源：[[ITERATIONS]] 2026-05-30 ~ 2026-05-31（9 条迭代）

## GUA-026：三带二拆牌/炸弹保护

| 日期 | 迭代 | 关键内容 |
|------|------|----------|
| 2026-05-30 | 落地 | `_uses_level_rank_cards`、`_three_with_two_protect_ok`、`_pick_three_with_two`；不拆炸弹、不消耗级牌、常态不拆 trips |
| 2026-05-30 | 净盘批跑验收 | 10 局，yf1 PASS 47.7% / yf2 46.8%；含级牌三带二 2+1 |
| 2026-05-31 | 关单 + 12 局复跑 | 队胜 **11/12（91.7%）**；H+curRank 三带二 39 次；**GUA-026 closed** ✅ |

**涉及文件**：
- `m3_decision_engine`（`_ThreeWithTwo` 统一过滤）
- `tests/test_m3_gua026.py` **3 passed**

## GUA-029：炸弹可执行规则包

### R1–R6 规则清单

| 规则 | 内容 | 状态 |
|------|------|------|
| R1 | `choose_bomb` 格式修复（`action[1]` 对齐 v1006） | ✅ |
| R2 | 必回炸 | ✅ |
| R3 | ≤7 张阻断兜底 | ✅ |
| R4 | 炸不打四 | ✅ |
| R5 | 不压队友 | ✅ |
| R6 | 残局 one_hand / `_active` 炸弹一手清 | ✅ |

### 迭代记录

| 日期 | 迭代 | 关键结果 |
|------|------|----------|
| 2026-05-30 | 登记 + 分析 | 样例局 yf1 5×8 全程未出；根因 `action[-1]` TypeError |
| 2026-05-30 | R1–R6 落地 | `test_m3_gua029.py` **8 passed**；回归 16 passed |
| 2026-05-30 | 3 局验收 | 炸弹 yf1=69 / yf2=65（bug 消除 ✅）；队胜仍 [3,0,3,0]×3 |
| 2026-05-31 | 净盘 ≥10 对验收 | 炸弹 yf1=175 / yf2=152；**GUA-029 closed** ✅ |

**涉及文件**：
- `m3_utils.choose_bomb`
- `m3_decision_engine`（`_is_teammate_greater`、`_gua029_*` 系列）
- `tests/test_m3_gua029.py`
