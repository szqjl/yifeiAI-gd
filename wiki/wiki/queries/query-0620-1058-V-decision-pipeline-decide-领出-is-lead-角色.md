---
type: query-answer
title: "V7 decision pipeline decide 领出 is_lead 角色 role 配置"
date: 2026-06-20
sources:
  - queries/query-0618-1734-v-启动脚本-路径-lalala-import-改动.md
  - sources/SCRIPT_INDEX-summary.md
  - entities/module-batch-executor.md
  - queries/query-0619-0826-批跑脚本-命令-参数-批跑入口-batch-executor.md
  - queries/query-0618-2149-v-批跑数据统计-局级-副级.md
  - queries/query-0618-2144-V-vs-Lalala.md
  - queries/query-0618-1743-V-启动配置-路径配置-SETUP-GUIDE-环境配置.md
  - queries/query-0620-1036-V-guard-rules-领出不炸-R-R-首出-过滤-首发.md
  - concepts/batch-evaluation.md
  - queries/query-0620-1032-领出-含义-首出-第一手-策略.md
---

# V7 decision pipeline decide 领出 is_lead 角色 role 配置

# V7 Decision Pipeline 中 `is_lead` 角色/Role 配置

## 核心结论

Wiki 中**未直接记录** V7 decision pipeline 中 `decide()` 函数对 `is_lead` 参数、role（角色）字段的具体配置定义（如取值范围、字段映射、传入路径）。但可从以下相关线索拼凑：

---

## 一、相关概念基础

### 1. "领出" vs "首出" 的区分 [10]

| 术语 | 含义 | 决策点 |
|------|------|--------|
| **领出**（is_lead） | 每副牌**由谁先出**（规则产物） | 平台/规则决定 |
| **首出** | 领出者**打出的第一手牌**（策略产物） | 真正的 AI 决策 |

→ `is_lead` 在 decision pipeline 中应作为**前置判断**：当前玩家是否是本副的领出者（lead player）。

### 2. 角色定位驱动的首出 [10]

Wiki 中有明确的**角色（role）三分类**：

| 角色 | 牌力分 | 首出组牌方向 |
|------|--------|--------------|
| **主攻** | ≥5 分 | 全面组牌，可激进配火 |
| **助攻** | 2-4 分 | 精简配火，保留变化 |
| **超弱** | <2 分 | 配火优先，大胆配火 |

→ V7 decision pipeline 的 `decide()` 应在 `is_lead=True` 时进一步读取 role 字段，按上述三类调整 `_score_power()` 权重或策略分支。

---

## 二、V7 首出决策管线（推断）

根据 [10] 与 [8]，V7 在 `is_lead=True` 时的处理流程为：

```
输入：handcards + main_rank + game_state
    ↓
1. 检查 is_lead 参数 → True 进入首出分支
    ↓
2. 读取 role 字段（主攻/助攻/超弱）
    ↓
3. SF_FIRST → BOMB_FIRST → enumerate_groupings()
    ↓
4. _score_power() 5 维评分
   power_score = 0.3×炸弹 + 0.3×手数 + 0.1×回收 + 0.1×灵活 + 0.2×去单化
    ↓
5. 根据 role 调整权重（如主攻加大炸弹权重，超弱加大去单化权重？）
    ↓
输出：最优组法 + 牌力分
```

---

## 三、Wiki 信息缺口 ⚠️

| 缺口 | 说明 |
|------|------|
| `decide()` 函数签名 | Wiki 未列出 `is_lead`、`role` 参数的明确定义 |
| role 字段类型与取值 | 仅有"主攻/助攻/超弱"三类，**枚举/字符串/int 形式未确认** |
| role 的判定依据 | 是从牌力分计算还是上游传入？ |
| role 与 is_lead 的耦合 | 非领出时（`is_lead=False`），role 字段是否仍需读取？ |
| R10 "领出不炸" 规则 [8] | **R10 在 `is_lead=True` 时硬排除炸弹作为首出牌型**（GUA-066） |

---

## 四、关键关联 GUA

| GUA | 关联点 |
|-----|--------|
| **GUA-066** | R10 领出不炸（首发硬排除炸弹）|
| **GUA-062** | V7 组牌引擎单元测试 vs 实战鸿沟 |
| **GUA-030** | 角色/配火原则 |
| **GUA-027** | 座位（决定谁是 lead） |
| **GUA-065** | R07-R09 队友保护簇 |

---

## 五、建议下一步

1. **直接读源码**：
   - `src/decision/ultimate_win_rate_engine_v7/yf1_v7.py`（decide 主入口）
   - `src/decision/ultimate_win_rate_engine_v7/strategy_engine.py`（首出分支）
   - `src/decision/ultimate_win_rate_engine_v7/rule_based/v7_guards.py`（R10 领出不炸）

2. **核对 R10 触发条件**：Wiki 明示"首发阶段硬排除炸弹"，需确认 `is_lead=True` 路径下 R10 的精确拦截点

3. **role 字段溯源**：查 GUA-030（角色定位）原始文档，确认 role 是上游 pre-decide 阶段产出还是 decide 内自行计算

4. **GUA-062 鸿沟**：注意单元测试通过 ≠ 实战胜率，role/is_lead 配置变更后必须经过批跑验证

---

## 主要来源

- [8] V7 Guard 规则（R10 领出不炸）
- [10] 领出/首出策略 + 角色定位驱动的首出
- [4] 批跑执行器（验证管线）

如需更精确的 `decide()` 函数签名、role 枚举定义、`is_lead` 触发分支代码，需读 `yf1_v7.py` / `yf2_v7.py` 源码——**Wiki 未覆盖到代码级细节**。
