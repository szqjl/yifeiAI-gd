---
type: query-answer
title: "V7 决策管线 管道顺序 decide 架构"
date: 2026-06-20
sources:
  - sources/SCRIPT_INDEX-summary.md
  - queries/query-0618-1734-v-启动脚本-路径-lalala-import-改动.md
  - queries/query-0620-1852-V-模型训练链路-bc-model-v-来源-GUA-.md
  - queries/query-0618-2144-V-vs-Lalala.md
  - queries/query-0620-1852-V-BC训练-模型文件-训练脚本-train-bc-v-.md
  - queries/query-0618-2149-v-批跑数据统计-局级-副级.md
  - entities/module-batch-executor.md
  - queries/query-0619-0826-批跑脚本-命令-参数-批跑入口-batch-executor.md
  - sources/v7-system-fixes-summary.md
  - queries/query-0620-1058-V-decision-pipeline-decide-领出-is-lead-角色.md
---

# V7 决策管线 管道顺序 decide 架构

# V7 决策管线（Decision Pipeline）架构

## 一、Wiki 直接覆盖的内容

Wiki 中**没有一张专门的图**描绘 V7 决策管线的全貌，但可从多个相关页面拼出主要环节。

### 1. 引擎模块结构 [[2]]（来自 `module-v7-engine`）

```
ultimate_win_rate_engine_v7/
├── __init__.py
├── yf1_v7.py / yf2_v7.py       ← 客户端入口（yf1_v7 = 团队主位）
├── strategy_engine.py            ← 策略引擎（首出/跟牌分支）
├── phase_handlers/               ← 阶段处理器
├── stage_router.py               ← 阶段路由（read state → 路由到 handler）
└── rule_based/                   ← 规则守卫（含 R10 领出不炸 = GUA-066）
```

### 2. 决策管线的"管道顺序"（推断） [[10]]

Wiki 在 `decision pipeline decide is_lead role` 页面给出了最接近的伪代码视图：

```
输入：handcards + main_rank + game_state
    ↓
1. is_lead 参数判断 → True 进入首出分支 / False 进入跟牌分支
    ↓
2. 读取 role 字段（主攻 ≥5分 / 助攻 2-4分 / 超弱 <2分）
    ↓
3. SF_FIRST → BOMB_FIRST → enumerate_groupings()
    ↓
4. _score_power() 5 维评分
   power_score = 0.3×炸弹 + 0.3×手数 + 0.1×回收 + 0.1×灵活 + 0.2×去单化
    ↓
5. 根据 role 调整权重（主攻加重炸弹，超弱加重去单化）
    ↓
6. R10 守卫（is_lead=True 时硬排除炸弹作为首出牌型，GUA-066）
    ↓
输出：最优组法 + 牌力分
```

### 3. 阶段路由

- **stage_router.py** 负责读取 `context` 状态字典，按 `pass_num / numofnext / numofgreaterPos` 等字段 [[2]] 把请求分发到 `phase_handlers/` 下对应的 handler（这些字段由 GUA-037a / GUA-050 推动补全）。

---

## 二、关键 GUAs 与决策管线各环节的映射

| 管线环节 | 涉及 GUA | 性质 |
|----------|----------|------|
| **decide() 入口与签名** | — | Wiki 未列出 `is_lead` / `role` 参数明确定义 |
| **首出分支** | GUA-066（R10 领出不炸） | 首发阶段硬排除炸弹 |
| **角色定位** | GUA-030（角色/配火原则） | role 三分类（主攻/助攻/超弱） |
| **座位 → lead** | GUA-027 | 决定谁是本副领出 |
| **组牌引擎** | GUA-022（combine_handcards） | 根因隔离完成 |
| **炸弹选择** | GUA-014（choose_bomb 最小代价） | 待 P0 改动 |
| **context 字段** | GUA-037a / GUA-050（pass_num 等） | 待 P0 改动 |
| **消息契约** | GUA-062（actionIndex → actIndex） | 早期 fix，待补登 |
| **整体架构** | **GUA-061**（V7 模块化架构） | **P0 阻塞**，未解决前难越 30% 门槛 |

---

## 三、Wiki 信息缺口 ⚠️

以下问题 **Wiki 没有直接答案**，需要读源码确认：

| 缺口 | 说明 |
|------|------|
| `decide()` 完整函数签名 | `is_lead`、`role`、`context` 参数的精确定义未列 |
| role 字段类型 | 字符串 / int / 枚举未确认 |
| role 判定时点 | 上游 pre-decide 计算 vs decide 内部推断？ |
| is_lead 与 role 的耦合 | 非领出时 role 是否仍读取？ |
| stage_router 的具体路由表 | 按哪些 stage 关键字分发到哪些 handler 未列 |
| 5 维评分权重是否随 role 动态调整 | 仅"推断"，源码未确认 |

---

## 四、建议下一步

1. **读源码**（优先级最高）：
   - `src/decision/ultimate_win_rate_engine_v7/yf1_v7.py` — decide 主入口
   - `strategy_engine.py` — 首出/跟牌分支
   - `stage_router.py` — 阶段路由表
   - `rule_based/v7_guards.py` — R10 等规则守卫
2. **集中攻克 GUA-061** — Wiki 多次强调"V7 模块化架构是 30% 胜率门槛的核心阻塞"[[3]]
3. **把 P0 改动落到 decide 管线** — choose_bomb（GUA-014）+ context（GUA-050）+ combine_handcards（GUA-022）三项改动都直接作用在 decide 路径上
4. **批跑验证** — 任何 role/is_lead 行为变更必须走 `run_v7_vs_lalala_games.py` + `analyze_v7_round_levels.py`（副级口径）

---

**主要来源**：
- [[2]] V7 引擎模块结构
- [[3]] V7 vs Lalala 现状（3.0% 胜率 + GUA-061 P0 阻塞）
- [[10]] V7 decision pipeline decide 领出 is_lead role 配置（最直接的一张伪代码视图）

如需**代码级精度的 `decide()` 函数签名、role 枚举、`is_lead` 分支判定条件**，必须读 `yf1_v7.py` / `yf2_v7.py` 源码——Wiki 仅覆盖到模块与伪代码层面。
