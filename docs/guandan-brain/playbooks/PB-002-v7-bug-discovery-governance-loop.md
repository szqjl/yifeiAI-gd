# PB-002：V7 缺陷发现闭环 — 回放降级为抽检，前移静态校验/矩阵测试/异常扫描

| 字段 | 内容 |
|------|------|
| **场景** | V7 / 残局 / Guard / 推荐路径连续出现「看回放 → 修一点 → 再冒出同类洞」时 |
| **问题** | 纯人工回放发现缺陷的链路太慢、太局部，容易把“个案修补”误当成“类别收敛” |
| **做法** | 把发现链路拆成 4 层：静态一致性校验 → 构造态参数化测试 → 批量异常扫描 → 少量 WF-12 深挖 |
| **反例** | 直接翻牌谱逐手找 bug；为单副回放写特例；没做静态校验就进批跑；修完只看同一副 replay |
| **验证** | 见下文“验证”节 |
| **关联** | GUA-078、GUA-099、GUA-100；`ITERATIONS` 2026-06-30 PB-002 行 |
| **Skill / check** | WF-12 `guandan-decision-trace`；`tests/test_gua078_endgame_tracker_decide_entry.py`；`scripts/checks/check_q1_rule_table_consistency.py`；`scripts/checks/check_endgame_anomalies.py` |

---

## 背景

2026-06-30 连续两轮 WF-12 暴露了同一类低效：

- 先从 `69/79` 看到 **对子报单漏压**，修出 GUA-099
- 再从 `76/79` 看到 **单张 9 漏压**，继续追出 GUA-100

根因并不是两副牌“很特别”，而是同一套残局 Q1 约束分散在多层：

1. `endgame_rule` / `BAOSHU_RULE` 配置表
2. `apply_banned_filter()` 的硬过滤
3. Q1 的排序/兜底/特判
4. `my_decisions` / `actionList_sample` / log 的可观测性

如果只靠人工翻回放，会不断陷入：

```text
看回放 → 发现个案 → 修一处 → 再跑 → 新个案暴露同类矛盾
```

本 Playbook 的定音是：**回放保留，但降级为“抽检与归因”；类别收敛要前移到静态校验、参数化测试和批量异常扫描。**

## 做法（详）

### 1. 静态一致性校验先行

凡是“规则表驱动”的模块，先校验配置表，再看回放。

**最低要求**：

- `recommended_types` 映射出的动作类型，不得与同条 `banned_types` 冲突
- `block_with` 映射出的动作类型，不得被同条 `never_play` 再禁掉
- 若规则表需要例外，必须在代码里有显式特判，并在注释中写明

**适用对象**：

- `endgame_rule`
- `BAOSHU_RULE`
- 未来的推荐优先级表 / heuristic 打分表 / 角色阈值表

**本次实证**：

- GUA-100 就是 `remaining=1/3/5` 的静态冲突，本应在跑批前被拦住，而不是靠回放里看到 `PASS`

### 2. 用参数化测试收敛“类别”，不要只锁单副

每发现一个新类问题，第一反应不是“再记一个回放”，而是：

1. 提炼出影响维度
2. 做成参数化矩阵
3. 把回放仅作为锚点注释

**残局 Q1 当前最小矩阵**：

- `remaining=1,2,3,4,5,6`
- 当前控牌类型：`Single / Pair`
- 候选中是否存在 `Single / Pair / Bomb`
- 是否存在 `banned_filter` 先删空推荐动作

**本次落地**：

- `tests/test_gua078_endgame_tracker_decide_entry.py`
  - `remaining=1..6` 的 `recommended/banned` 不冲突校验
  - `remaining=1/3/5` 推荐单张时，`apply_banned_filter()` 不得删空 `Single`

### 3. 批量异常扫描替代“人工翻完整回放”

WF-12 深挖只应该看“机器先报出来的异常样本”，而不是从头翻一整批牌谱。

**推荐扫描对象**：

- `game_records_v7/*.json`
- `my_decisions[].context.actionList_sample`
- `game_decision_traces/*.jsonl`（GUA-098 接入后优先）

**优先异常模式**：

- 对手剩 1 张 / 3 张且我方存在合法同型可压，最终却 `PASS`
- `recommended_types` 非空，但 `apply_banned_filter()` 后只剩 `PASS`
- 命中 `layer=残局管线` 且 `action_index=0` 的高风险步
- `actionList_size>1` 但单一规则层把所有推荐同型删空

**当前可用脚手架**：

- `scripts/checks/check_endgame_agent.py --scan`
  先看 Q0-Q3 命中率、激活率，再决定是否值得做 WF-12 逐手复盘
- `scripts/checks/check_endgame_anomalies.py`
  直接聚类“敌方临门却 PASS”“recommended 被过滤到只剩 PASS”的高风险步

### 4. WF-12 保留，但降级为“少量样本的归因层”

WF-12 不取消，但职责改成：

- 对异常扫描报出的样本做根因分类
- 判定属于：
  - 规则表冲突
  - 过滤层问题
  - 排序 / 兜底问题
  - 推荐缺失
  - 可观测性缺失

**WF-12 的正确使用方式**：

```text
静态校验 / 异常扫描 先出候选
    ↓
WF-12 深挖 1~3 个代表样本
    ↓
回到测试 / 规则表 / 扫描器修“这一类”
```

而不是：

```text
人工随手挑一副牌
    ↓
发现 bug
    ↓
为这一步写补丁
```

## 这套方案的最低治理集

若时间有限，优先只做下面 3 件事：

### A. 静态 validator

目标：把“规则表自相矛盾”变成提交前或 pytest 时直接失败。

首批覆盖：

- `endgame_rule`
- `BAOSHU_RULE`

### B. 残局异常扫描器

目标：自动列出“Q1/Q2 最可疑步”，把人从大海捞针里解放出来。

首批规则：

- `enemy remaining in {1,3} and legal beater exists and chosen PASS`
- `recommended_types non-empty but filtered candidates only PASS`

### C. 参数化规则矩阵

目标：把 replay 锚点升格为同类场景矩阵。

首批矩阵：

- `remaining=1..6`
- `Single / Pair / Bomb`
- `banned_filter` 前后候选是否被删空

## 验证

```bash
# 1) 规则矩阵回归
python -m pytest tests/test_gua078_endgame_tracker_decide_entry.py -q

# 2) 残局 + 平台格式联动回归
python -m pytest tests/test_gua071_action_format.py tests/test_gua078_endgame_tracker_decide_entry.py -q

# 3) 残局批量扫描（抽检入口）
python scripts/checks/check_endgame_agent.py --scan

# 4) 残局异常聚类（高风险样本入口）
python scripts/checks/check_endgame_anomalies.py --scan-dir game_records_v7 --limit 20
```

**通过标准**：

- 规则表冲突在 pytest 层直接暴露
- `remaining=1/3/5` 不再出现“推荐单张却删空 `Single`”的过滤结果
- 扫描输出里，`Q1 命中 PASS` 的样本可以被快速聚类，而不是只能人工逐手翻

## 反例

- ❌ 修完一个回放锚点，只验证“这副牌现在过了”
- ❌ 把规则矛盾留给 `decide()` 里的特判硬兜底
- ❌ 不做参数化矩阵，只补单一 replay 测试
- ❌ 批跑后直接人工看 70+ 步回放，不先做异常筛选
- ❌ 发现 `PASS` 问题就先怀疑 heuristic/NN，而不先查规则表与过滤层

## 延伸阅读

- [WF-12-yf-decision-trace.md](../workflows/WF-12-yf-decision-trace.md)
- [PB-001-gua072-bomb-break-timing.md](./PB-001-gua072-bomb-break-timing.md)
- [ISSUES.md](../ISSUES.md) 中 GUA-078 / GUA-099 / GUA-100
