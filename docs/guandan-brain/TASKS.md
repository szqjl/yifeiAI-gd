# 任务看板（Task Board）

> 当前迭代来源：`ITERATIONS.md` 最后一行。Hermes 定迭代后在此拆任务，执行 AI 在此认领+回写交接，Hermes 验收后归档。

## 任务字段说明

每条任务包含：任务ID | 来源 GUA | 派给 | 状态 | 任务块 | 交接摘要

- **状态**：`待接` → `进行中` → `待验收` → `已完成` / `已取消`
- **派给**：`opencode` 或 `cursor`

---

## 当前任务

| 任务ID | 来源 | 派给 | 状态 | 任务摘要 | 交接摘要 |
|--------|------|------|------|---------|---------|
| PHASE2-001 | GUA-022 | 人类 | 待接 | **【任务】**实际对局验证：M1 vs lalala 跑 ≥10 对局，统计队胜率**【范围】**本机离线服 + batch/GUI**【依据】**PHASE2-002 代码已落地**【交付】**胜率数据回填 ITERATIONS**【完成定义】**队胜率 >50% | |
| PHASE2-003 | GUA-014 | cursor | 待接 | **【任务】**GUA-014联动：拆牌与优先级优化**【范围】**共用 decision 层**【依据】**与 GUA-022 联动**【交付】**优化后决策逻辑**【完成定义】**pytest 通过 + 对局验证 | |

---

## 完成任务归档

| 任务ID | 来源 | 派给 | 最终状态 | 交接摘要 | 验收人 |
|--------|------|------|---------|---------|-------|
| PHASE2-002 | GUA-022 | cursor | 待验收 | pass_num 注入 yf1/yf2_m1；`_build_context` 补 numofnext/numofpre/numofgreaterPos 等；strategy 用 numofnext≤4 抑制无脑 PASS；`pytest tests/test_decision_gua022_gua014.py` **7 passed** | Hermes |

---

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

## 历史任务行（已归档，勿重复认领）

| PHASE2-001 | GUA-022 | cursor | 已合并至上方「当前任务」人类执行 | 实际对局验证 | |
| PHASE2-002 | GUA-022 | opencode | 已由 cursor 完成 | context 补全 | 见归档表 |
| PHASE2-003 | GUA-014 | cursor | 见上方当前任务 | GUA-014 联动 | |
