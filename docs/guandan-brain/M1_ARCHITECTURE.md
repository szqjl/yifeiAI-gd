# M1 架构综述

> 本文档全面描述 M1（硬编码规则引擎）的架构设计。
> 维护者：yifeGDBOT 团队 | 分支：`m1-dev`

---

## 1. 概述

M1 是基于规则的硬编码决策引擎，与 V4/V5/V6（神经网络/混合）并列，属于 M 系列（Hardcoded Rules）。

**核心特性**：
- 纯硬编码规则，无模型文件
- 5 阶段细分路由（开局 / 中局前期 / 中局后期 / 残局前期 / 残局后期）
- 主动 / 被动出牌分离
- 12 个阶段处理器（10 个常规 + TributeHandler + BackHandler）
- 共用层与 V 系列共享（策略引擎、优先级系统、配合策略等）

**入口文件**：`src/decision/rule_based_decision_engine_m1.py`

**调试入口**：`engine.get_phase_info(message)` 可查询当前走了哪个 Handler（`rule_based_decision_engine_m1.py:231`）

---

## 2. 架构图

```
                         ┌─────────────────────────────┐
                         │   RuleBasedDecisionEngineM1  │  ← 主入口
                         │        decide(message)        │
                         └──────────────┬────────────────┘
                                        │
                          ┌─────────────▼──────────────┐
                          │        StageRouter          │  ← 阶段路由器
                          │   route(message) → handler  │
                          └─────────────┬───────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼──────────┐    ┌──────────▼──────────┐   ┌─────────▼─────────┐
    │  tribute_handler   │    │  back_handler        │   │   play 阶段路由    │
    │  (进贡处理器)       │    │  (还贡处理器)        │   │  → 10个Handler    │
    └────────────────────┘    └─────────────────────┘   └─────────┬─────────┘
                                                                   │
                              ┌────────────────────────────────────┼────────┐
                              │          5 阶段 × 2 模式             │        │
                    ┌─────────▼─────────┐              ┌───────────▼────────┐ │
                    │   OpeningActive  │              │  OpeningPassive     │ │
                    ├──────────────────┤              ├────────────────────┤ │
                    │ MidEarlyActive   │              │ MidEarlyPassive     │ │
                    ├──────────────────┤              ├────────────────────┤ │
                    │ MidLateActive    │              │ MidLatePassive      │ │
                    ├──────────────────┤              ├────────────────────┤ │
                    │ EndgameEarlyActive│             │ EndgameEarlyPassive│ │
                    ├──────────────────┤              ├────────────────────┤ │
                    │ EndgameLateActive │              │ EndgameLatePassive │ │
                    └──────────────────┘              └────────────────────┘ │

     每个 PhaseHandler 内部调用策略系统（共用于 M1 和 V 系列）：
     ┌─────────────────────────────────────────────────────────┐
     │  TeammateProtectionStrategy   队友保护策略（保护队友出牌）│
     │  PrioritySystem / EnhancedPrioritySystem  优先级排序    │
     │  CardValueSystem  牌值计算（基于 curRank）             │
     │  HandStructureAnalyzer  手牌结构分析                    │
     │  OptimalCombinationScanner  最优组合扫描                │
     └─────────────────────────────────────────────────────────┘
```

---

## 3. 核心组件

### 3.1 RuleBasedDecisionEngineM1（主入口）

**文件**：`src/decision/rule_based_decision_engine_m1.py`

```python
class RuleBasedDecisionEngineM1:
    def __init__(self, player_id: int = 0, config: Dict = None):
        # 10 个常规阶段处理器
        self.handlers = {
            'opening_active': OpeningActiveHandler(...),
            'opening_passive': OpeningPassiveHandler(...),
            'mid_early_active': MidEarlyActiveHandler(...),
            'mid_early_passive': MidEarlyPassiveHandler(...),
            'mid_late_active': MidLateActiveHandler(...),
            'mid_late_passive': MidLatePassiveHandler(...),
            'endgame_early_active': EndgameEarlyActiveHandler(...),
            'endgame_early_passive': EndgameEarlyPassiveHandler(...),
            'endgame_late_active': EndgameLateActiveHandler(...),
            'endgame_late_passive': EndgameLatePassiveHandler(...),
        }
        # 特殊阶段处理器
        self.tribute_handler = TributeHandler(...)
        self.back_handler = BackHandler(...)
        # 路由器
        self.router = StageRouter(config)
    def decide(self, message: Dict) -> int:
        # 核心决策：路由 → handler.handle() → 结果验证
```

**决策流程**：
1. 接收游戏状态 `message`（含 `actionList`、`handCards`、`stage` 等）
2. 优先使用服务器发送的最新 `handCards`
3. 调用 `router.route(message)` 路由到对应 handler
4. **Engine 层兜底**：验证决策结果中的卡牌是否在手牌中，若不在则回退到 `_first_non_pass_index()`
5. **Router 层兜底**：若 handler 返回 PASS 但存在非 PASS 动作，强制返回第一个非 PASS 动作索引（跳过 index 0，从 index 1 开始找）

**决策数据流示例**：
```
message = {
    "stage": "play",
    "handCards": ["S7", "H7", "DK", ...],   # 27张手牌
    "actionList": [["PASS"], ["Single", "7", ["S7"]], ["Pair", "7", ["S7","H7"]], ...],
    "curAction": ["Single", "7", ["S7"]],     # 对手出了单张7（有值则被动）
    "curPos": 1, "greaterPos": 1, "myPos": 0,
    "publicInfo": [{"rest": 27}, {"rest": 22}, {"rest": 27}, {"rest": 27}]
}
# → router.route(message)
# → MidEarlyPassiveHandler.handle(message)
# → 返回 actionList 索引（如 2）
```

### 3.2 StageRouter（阶段路由器）

**文件**：`src/decision/stage_router.py` → `class StageRouter`

**路由维度**：

| 维度 | 值 | 说明 |
|------|-----|------|
| stage | `play` / `tribute` / `back` | 游戏阶段 |
| game_phase | `opening` / `mid_early` / `mid_late` / `endgame_early` / `endgame_late` | 5 阶段 |
| play_mode | `active` / `passive` | 主动 / 被动 |

**阶段划分**（按剩余手牌数，阈值与代码 `stage_router.py:540-551` 一致）：

| 阶段 | 剩余牌数 | 主动 Handler | 被动 Handler |
|------|----------|-------------|--------------|
| 开局 | > 20（21–27） | OpeningActiveHandler | OpeningPassiveHandler |
| 中局前期 | > 15（16–20） | MidEarlyActiveHandler | MidEarlyPassiveHandler |
| 中局后期 | > 10（11–15） | MidLateActiveHandler | MidLatePassiveHandler |
| 残局前期 | > 5（6–10） | EndgameEarlyActiveHandler | EndgameEarlyPassiveHandler |
| 残局后期 | ≤ 5 | EndgameLateActiveHandler | EndgameLatePassiveHandler |

**注**：边界值归属下一档（如恰好 15 张时走中局后期，恰好 5 张时走残局后期）。

**主动 vs 被动判断**：
- `curAction` 存在且非空 → 被动（跟牌）
- `curAction` 为空 → 主动（首发）
- `curAction` 可能为字符串（服务端序列化），内部会用 `ast.literal_eval` 解析（`stage_router.py:564-570`）

**Router 层最终防线**（GUA-021 修复，`stage_router.py:496-534`）：
StageRouter 在 handler 返回后检查：如果返回的是 PASS 但 actionList 中存在非 PASS 动作，则**跳过 index 0**（PASS 所在位置），从 index 1 开始找第一个非 PASS，返回其索引。这解决了「有多选却误 PASS」的问题。

**关键实现细节**：index 0 通常是 PASS，故从 index 1 开始查找；若 index 1 仍无非 PASS，再检查 index 0（防御性兜底）。

### 3.3 BasePhaseHandler（处理器基类）

**文件**：`src/decision/stage_router.py` → `class BasePhaseHandler`

所有 PhaseHandler 继承此类。它提供：

**策略栈**（通过 `_init_strategy_engine()` 初始化，共 5 个组件）：

1. **TeammateProtectionStrategy** — 队友保护
   - `HighValueProtectionRule`：队友出大牌时保护
   - `LowCardCountProtectionRule`：队友剩牌少时保护
   - 可选 `EnhancedCollaborationStrategy`（当 `use_enhanced_collaboration=True`）

2. **PrioritySystem / EnhancedPrioritySystem** — 优先级排序
   - 评估动作优先级，可选增强版
   - 当 `use_enhanced_priority=True` 时使用增强版

3. **CardValueSystem** — 牌值计算
   - 定义在 `strategy_engine.py:543`（589行文件）
   - 基于当前级牌（`curRank`）计算牌值

**辅助系统**：

| 系统 | 作用 |
|------|------|
| `HandStructureAnalyzer` | 分析手牌结构（对/三张/炸弹/顺子等） |
| `OptimalCombinationScanner` | 扫描最优组合、多余单张 |

**工具方法**：

| 方法 | 作用 |
|------|------|
| `_validate_action_cards()` | 验证动作中的卡牌是否在手牌中（卡牌一致性） |
| `_filter_valid_actions()` | 过滤有效动作 |
| `_scan_hand_combination()` | 扫描手牌最优组合 |
| `_build_context()` | 构建策略上下文（含各玩家剩余牌数、阶段等） |
| `_action_list_has_non_pass()` | 检查是否存在非 PASS 动作 |
| `_evaluate_split_impact()` | 评估拆牌影响（拆对/拆三张/拆炸弹的惩罚） |

### 3.4 阶段处理器

**文件**：`src/decision/phase_handlers.py`

**概览**：共 12 个 Handler，其中 10 个常规 Handler + 2 个特殊 Handler（TributeHandler、BackHandler）。

**重要**：10 个常规 Handler 中，有 2 个是继承复用（非独立实现）：
- `MidLatePassiveHandler` 继承自 `MidEarlyPassiveHandler`
- `EndgameLatePassiveHandler` 继承自 `EndgameEarlyPassiveHandler`

每个 Handler 实现 `handle(message) → int`（返回 actionList 索引）。

| Handler | 阶段 | 模式 | 策略要点 |
|---------|------|------|---------|
| OpeningActiveHandler | 开局 | 主动 | 建立牌型结构，不追求快速出完 |
| OpeningPassiveHandler | 开局 | 被动 | 优先顺走多余单张，压制对手 |
| MidEarlyActiveHandler | 中局前期 | 主动 | 推进牌型，消耗对手 |
| MidEarlyPassiveHandler | 中局前期 | 被动 | 配合队友，控制节奏 |
| MidLateActiveHandler | 中局后期 | 主动 | 控制节奏，配合队友 |
| MidLatePassiveHandler | 中局后期 | 被动 | 继承 BasePhaseHandler |
| EndgameEarlyActiveHandler | 残局前期 | 主动 | 收牌，配合队友抢先 |
| EndgameEarlyPassiveHandler | 残局前期 | 被动 | 收牌，让队友占优 |
| EndgameLateActiveHandler | 残局后期 | 主动 | 快速出牌或让队友收牌 |
| EndgameLatePassiveHandler | 残局后期 | 被动 | 继承 EndgameEarlyPassiveHandler |

### 3.5 特殊处理器

**TributeHandler**（进贡）
- 当 `stage == "tribute"` 时调用
- 决定进贡哪张牌给上一轮的最大出牌者

**BackHandler**（还贡）
- 当 `stage == "back"` 时调用
- 决定还贡哪张牌给队友

### 3.6 策略引擎

**文件**：`src/decision/strategy_engine.py`

主要类：

| 类 | 作用 |
|----|------|
| `ProtectionRule` | 保护规则基类（ABC） |
| `HighValueProtectionRule` | 高牌值保护（队友出大牌时保护） |
| `LowCardCountProtectionRule` | 低牌数保护（队友剩牌少时保护） |
| `TeammateProtectionStrategy` | 队友保护策略（组合上述规则） |
| `PrioritySystem` | 基础优先级系统 |
| `EnhancedPrioritySystem` | 增强优先级系统（可配置开关） |
| `CardValueSystem` | 牌值系统 |

---

## 4. 共用层（M1 与 V 系列共享）

以下文件被 M1 和 V 系列共同使用（通过 `BasePhaseHandler` 的 `_init_strategy_engine` 初始化）：

| 文件 | 作用 | M1 用途 |
|------|------|---------|
| `strategy_engine.py` | 策略引擎（含 TeammateProtectionStrategy、CardValueSystem） | 队友保护、牌值计算 |
| `enhanced_priority_system.py` | 增强优先级系统 | 动作优先级排序 |
| `enhanced_collaboration.py` | 增强协作策略（可选，`use_enhanced_collaboration=True` 时启用） | 队友配合 |
| `hand_structure_analyzer.py` | 手牌结构分析 | 牌型识别 |
| `optimal_combination_scanner.py` | 最优组合扫描 | 多余单张计算 |
| `cooperation.py` | 配合策略 | 队友配合决策 |
| `card_type_handlers.py` | 牌型处理器 | 牌型检测 |
| `intelligent_router.py` | 智能路由器（可选，`use_intelligent_router=True` 时启用） | 带缓存的路由 |

**重要**：修改共用层会同时影响 M1 和 V 系列，需要在两个分支上分别验证。

---

## 5. 通信层入口

| 文件 | 用途 |
|------|------|
| `src/communication/yf1_m1.py` | M1 客户端 1（Player 0） |
| `src/communication/yf2_m1.py` | M1 客户端 2（Player 2） |

两套客户端分别对应队伍 0（yf1）和队伍 1（yf2），各自初始化 `RuleBasedDecisionEngineM1`。

---

## 6. 关键配置

`RuleBasedDecisionEngineM1` 支持以下配置项：

| 配置项 | 默认值 | 作用 |
|--------|--------|------|
| `use_intelligent_router` | `False` | 使用 IntelligentStageRouter（带缓存） |
| `use_enhanced_collaboration` | `False` | 使用增强协作策略 |
| `use_enhanced_priority` | `False` | 使用增强优先级系统 |
| `curRank` | `"2"` | 当前级牌 |

---

## 7. 迭代历史（8 轮）

详见 `docs/guandan-brain/ITERATIONS.md`，简要脉络：

| 轮次 | 核心 |
|------|------|
| 1-4 | 文档建设 + 扩样统计，无代码变更 |
| 5 | **首次代码改动**：收紧被动分支 PASS 逻辑（GUA-021 关单） |
| 6-7 | 共用层落地：队友保护策略强化，10 局 0 胜（GUA-022 仍 open） |
| 8 | 修复 victoryNum 链路，100% 非空但队胜率仍为 0 |

---

## 8. 当前 open 的 GUA

详见 `docs/guandan-brain/ISSUES.md`。

| ID | 版本 | 严重度 | 描述 |
|----|------|--------|------|
| GUA-014 | 共用 | P2 | 拆牌与优先级不合理（影响所有版本） |
| GUA-022 | M1 | P1 | M1 对 lalala 队胜率 0（victoryNum = [0,3,0,3]） |

---

## 9. 相关文档

| 文档 | 作用 |
|------|------|
| `docs/guandan-brain/ISSUES.md` | 所有 GUA 缺陷登记 |
| `docs/guandan-brain/ITERATIONS.md` | 8 轮迭代完整记录 |
| `docs/guandan-brain/EVAL.md` | 评测用例台账 |
| `docs/training/YF硬编码完整提升计划优化版.md` | M1 提升路线图 |
| `src/decision/rule_based_decision_engine_m1.py` | M1 主入口（254 行） |
| `src/decision/stage_router.py` | 路由器 + BasePhaseHandler（593 行） |
| `src/decision/phase_handlers.py` | 10 个 PhaseHandler（2773 行） |
| `src/decision/strategy_engine.py` | 策略引擎（589 行） |
