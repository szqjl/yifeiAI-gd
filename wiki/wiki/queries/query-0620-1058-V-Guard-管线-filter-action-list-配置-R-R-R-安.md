---
type: query-answer
title: "V7 Guard 管线 filter_action_list 配置 R08 R14 R15 安全阀"
date: 2026-06-20
sources:
  - queries/query-0620-1036-V-guard-rules-领出不炸-R-R-首出-过滤-首发.md
  - queries/query-0618-1734-v-启动脚本-路径-lalala-import-改动.md
  - sources/SCRIPT_INDEX-summary.md
  - queries/query-0618-2149-v-批跑数据统计-局级-副级.md
  - entities/module-batch-executor.md
  - queries/query-0618-2144-V-vs-Lalala.md
  - queries/query-0619-0826-批跑脚本-命令-参数-批跑入口-batch-executor.md
  - queries/query-0618-1743-V-启动配置-路径配置-SETUP-GUIDE-环境配置.md
  - sources/v7-strategy-gua045-053-summary.md
  - concepts/batch-evaluation.md
---

# V7 Guard 管线 filter_action_list 配置 R08 R14 R15 安全阀

# V7 Guard 管线 filter_action_list 配置中 R08 / R14 / R15 的安全阀作用

## 一、Wiki 中 Guard 规则编号的覆盖情况

Wiki 当前对 V7 Guard 规则编号的记录是**不完整**的：

| 编号 | 主题 | Wiki 状态 |
|------|------|----------|
| R01–R06 | P0 防线（牌型合法性 / 接风 / 炸弹时序 / 队友保护 / 升级阈值 / 终局保护） | ✅ 已 CLOSED [9] |
| R07 / R08 / R09 | 队友保护簇（GUA-065） | ⚠️ 仅 GUA 关联，规则细节未记录 [1] |
| R10 | 领出不炸（GUA-066） | ⚠️ GUA 关联 + 设计意图，**精确触发条件**未记录 [1] |
| R11 | 全局抑制牌节流（GUA-068） | ⚠️ 仅 GUA 关联 [1] |
| R12 / R13 | — | ❌ Wiki 未记录 [1] |
| **R14** | — | ❌ **Wiki 未找到** [1] |
| **R15** | — | ❌ **Wiki 未找到** [1] |

→ **结论**：R08 / R14 / R15 的**安全阀定义、配置位置、触发条件**在 Wiki 中**均无直接记录**。能确认的只有 R08 属于 GUA-065「队友保护簇」的一部分。

---

## 二、Wiki 中关于"安全阀"定位的总体描述

虽然 R08 / R14 / R15 细节缺失，Wiki 对 V7 Guard 壳作为**安全阀**的总体定位是明确的：

### 1. 安全阀 = P0 防线，不解决"赢" [9]

> "Guard 壳保护不出错，不保护赢"

| 指标 | 数值 |
|------|------|
| V7 队胜 | **366/366 = 100%** |
| V7 副胜 | **0/236 = 0%** |
| 教训 | Guard 只能保证不犯蠢，不能赢得比赛 |

### 2. Guard 规则在 `filter_action_list` 中的执行位置 [1][9]

- **模块**：`src/decision/ultimate_win_rate_engine_v7/rule_based/v7_guards.py`
- **执行阶段**：NN 给出候选动作后、动作提交前
- **作用**：**硬排除**（hard-filter）非法 / 危险动作，保证决策不违反掼蛋牌理

### 3. Guard 与首出评分的配合（涉及 R08 间接相关） [1]

```
filter_action_list  (Guard 硬过滤)
        ↓
power_score = 0.3×炸弹 + 0.3×手数 + 0.1×回收 + 0.1×灵活 + 0.2×去单化
        ↓
选择 power_score 最高的动作
```

R08 作为"队友保护簇"的一员，**很可能**在 filter_action_list 中表现为：排除「会帮对手队友过牌 / 放走队友压不住的牌」等候选动作。

---

## 三、关于 R14 / R15 的合理推测（Wiki 未证实）

由于 Wiki 没有 R14 / R15 的任何记录，仅基于 Guard 壳的设计逻辑做**未验证推测**：

| 维度 | 推测方向 | 置信度 |
|------|----------|--------|
| 编号连续性 | R12–R15 大概率是 GUA-068 之后新增的"节流 / 副级 / 终局"类规则 | 低 |
| 配置位置 | 应在 `v7_guards.py` 的 `filter_action_list()` 函数内 | 高（与 R10 同构） |
| 安全阀作用 | 排除极端动作（超长等待、必败追炸、低胜率强行抢分等） | 低 |

> ⚠️ **以上均为推测，不应作为决策依据**。

---

## 四、信息缺口与建议下一步

### 必须查源码确认的内容

| 缺口 | 建议查阅路径 |
|------|--------------|
| R08 精确触发条件 | `src/decision/ultimate_win_rate_engine_v7/rule_based/v7_guards.py` 搜索 `R08` 或 `def _rule_08` |
| R14 / R15 是否存在 | 同上文件全文搜索 `R14` / `R15` |
| filter_action_list 完整规则序列 | 同上文件 `def filter_action_list` 函数体 |
| R08 与 GUA-065 的具体映射 | `docs/guandan-brain/iterations/` 下 GUA-065 文档 |
| R10 / R11 / R14 / R15 的 GUA 归属 | `docs/guandan-brain/ISSUES.md`（GUA 主索引） |

### 建议行动

1. **直接读 `v7_guards.py` 源码**：列出 `filter_action_list` 内所有 `if rule_id == "R0X"` 分支
2. **建 Wiki 页 `entity-r08-r14-r15-guards.md`**：把 R08/R14/R15 的定义、触发条件、边界、例外沉淀
3. **关联 GUA**：确认 R14/R15 是否对应 GUA-066/067/068/069 中的某条，或尚未挂 GUA

---

## 五、关键来源

- [1] V7 guard rules 领出不炸 R10 R14 首出过滤 — R14 明确标记"Wiki 未找到"
- [9] V7 Guard 壳与策略增补摘要 — R01–R06 已 CLOSED，Guard 壳的"不出错"定位
- [5][6] 批跑执行器模块 — 上下文（V7 引擎架构、`v7_guards.py` 归属）

**总结**：R08 属于 GUA-065 队友保护簇但细节未录；**R14、R15 在 Wiki 中完全无记录**。所有三者作为"安全阀"的具体配置、触发条件、GUA 归属，**均需查 `v7_guards.py` 源码与 `docs/guandan-brain/iterations/` 下 GUA 文档**才能确认。
