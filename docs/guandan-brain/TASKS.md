# 任务看板（Task Board）

> 当前迭代来源：`ITERATIONS.md` 最后一行。Hermes 定迭代后在此拆任务，执行 AI 在此认领+回写交接，Hermes 验收后归档。

## 任务字段说明

每条任务包含：任务ID | 来源 GUA | 派给 | 状态 | 任务块 | 交接摘要

- **状态**：`待接` → `进行中` → `待验收` → `已完成` / `已取消`
- **派给**：`opencode` 或 `cursor`

---

## 当前任务

_当前无活跃任务。全部已验收归档，见下方。_

---

## 完成任务归档

| 任务ID | 来源 | 派给 | 最终状态 | 交接摘要 | 验收人 |
|--------|------|------|---------|---------|-------|
| PHASE2-001 | GUA-022 | cursor | 已完成 | 10/10 对局，队胜率 0%；yf1 近似 PASS 10，yf2 近似 PASS 1；GUA-022 未达关单条件 | Hermes |
| PHASE2-002 | GUA-022 | cursor | 已完成 | pass_num 注入 yf1/yf2_m1；`_build_context` 补 numofnext/numofpre/numofgreaterPos 等；strategy 用 numofnext≤4 抑制无脑 PASS；`pytest tests/test_decision_gua022_gua014.py` **7 passed** | Hermes |
| PHASE2-003 | GUA-014 | cursor | 已完成 | 拆牌与优先级优化：`enhanced_priority_system.py` rank 计数拆牌惩罚、Trips 降权 0.55；`phase_handlers.py` OpeningActive 过滤拆结构/优先 TwoTrips、OpeningPassive 级牌王先于拆对；`stage_router.py` 辅助方法；`pytest` 10 passed | Hermes |
| PHASE2-004 | GUA-022 | cursor | 已完成 | `TeamOffensiveStrategy` + `_apply_team_strategies`；保护策略仅队友控牌；`pytest` 15 passed；批跑 10/10：队胜率 0% | Hermes |
| PHASE2-005 | GUA-022 | cursor | 已完成 | 接风判主动、`_coerce_non_pass_if_available`、智能路由缓存 coerce；`pytest` 19 passed；批跑：yf2 近似 **8→1**（合理遗留）；yf1 近似 PASS 仍 **10**；队胜率仍 0% | Hermes |

## 使用说明

### Hermes（总协调）创建任务模板

```markdown
| TASK-xxx | GUA-xxx | opencode/cursor | 待接 | **【任务】**...**【范围】**...**【依据】**...**【交付】**...**【完成定义】** | |
```

### 执行 AI 认领

把状态从 `待接` 改为 `进行中`。

### 执行 AI 回写交接

在交接摘要列填入一句话交接（含改动文件、验证结论）。

### Hermes 验收

审查后：
- 通过 → 状态改 `已完成`，移到归档表，更新 `ITERATIONS.md` / `ISSUES.md`
- 不通过 → 状态改 `待接`，在交接列说明退回原因

---


