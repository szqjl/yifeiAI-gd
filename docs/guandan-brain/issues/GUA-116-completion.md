# GUA-116 完成定义（主攻领出整牌型）

> 登记 **2026-07-06**。设计真源：[`V7-主攻领出-阶段划分设计口径.md`](../V7-主攻领出-阶段划分设计口径.md)。

## 范围

| 项 | 内容 | 状态 |
|----|------|------|
| **入口** | `stage_main_attack_lead.recommend_main_attack_lead()` | ✅ |
| **路由** | stage_0/1 `_stage_open_plan`、stage_2 `_stage_mid_dispatch`、075 fallback 主攻 `is_lead` | ✅ |
| **P1（O10）** | 有王或 ≥2 张 &lt;10 散单 → **倒数第二小** | ✅ |
| **P2/P3** | TWT/顺 **整组可领 is_core** + 回手泛化（同型/K原则/炸）+ **L11/L14 stage_1 defer** | ✅ v1.1（2026-07-10） |
| **P3b/c/d** | **TwoTrips / ThreePair / 天然 Trips**（炸回手；禁半组钢板） | ✅ v1.2（2026-07-10） |
| **P4** | 天然小对（3–9，禁级牌对；不抠 TWT/连对子结构） | ✅ |
| **领出 filter** | `_is_partial_composite_lead`：自由领出禁半组钢板 Trips / 半组三连对 Pair | ✅ |
| **§5 锚点 pytest** | WF-12 orphan + P1/P4/defer + core 整顺/TWT+炸 + 炸+钢板 TwoTrips + 半组禁 | ✅ |

## 关单条件

| 项 | 要求 |
|----|------|
| **代码** | `src/v/nn/stage_main_attack_lead.py` + 路由接线 |
| **测试** | `tests/test_gua116_main_attack_lead.py` + 091/090 回归不退化 |
| **文档** | `V7-主攻领出-阶段划分设计口径.md` 代码现状行更新 |

**CI 命令**：

```bash
python -m pytest tests/test_gua116_main_attack_lead.py tests/test_gua090_stage_open_plan.py tests/test_gua091_stage_mid_dispatch.py -q
```

## 不作关单

- M3 批跑队胜率 KPI
- stage_2 被压改炸 plan（仍 R11+091，非本 GUA 范围）
