---
title: yifeGDBOT 掼蛋AI onboarding
name: yifegdbot-onboarding
description: 掼蛋AI决策系统项目入门 — 架构理解、文档索引、GUA问题框架、测试方法
trigger: 当需要了解yifeGDBOT项目、或接手GUA任务时
category: productivity
---

# yifeGDBOT 掼蛋AI — 入门指南

## 项目是什么

南京邮电大学掼蛋AI算法对抗平台的客户端实现，支持AI自动出牌决策。
平台地址：`https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html`
仓库：`C:\yifeGDBOT`（本地路径）

---

## 核心架构：两条并行线（非替代！）

```
┌─────────────────────────────────────────────────────┐
│  M1 系列（硬编码规则引擎）        V4/V5/V6 系列（神经网络/混合）│
│  分支: m-dev                 分支: v6-dev（规划）          │
│  RuleBasedDecisionEngineM1     HybridDecisionEngineV4/V5  │
│  5阶段细分路由                    3层/4层决策架构             │
│  纯规则，无模型文件               需要训练，有bc_model文件     │
└─────────────────────────────────────────────────────┘
                    ↑
           src/decision/ 共用层
           （被所有版本共享）
```

### M1（硬编码规则引擎）

- **不是 ML 模型**，是纯硬编码规则引擎
- 架构：`RuleBasedDecisionEngineM1` → `StageRouter` → 10个 PhaseHandlers + `StrategyEngine` + `HandStructureAnalyzer`
- 5阶段细分（各分主动/被动）：
  - Opening（开局，剩余 >20）
  - MidEarly（中局前期，15-20）
  - MidLate（中局后期，10-15）
  - EndgameEarly（残局前期，5-10）
  - EndgameLate（残局后期，≤5）
- 客户端入口：`src/communication/yf1_m1.py` / `yf2_m1.py`

### V系列（神经网络/混合决策）

- V4：4层决策（HybridDecisionEngineV4）
- V5：3层决策（HybridDecisionEngineV5）：Rule-Based → Knowledge Enhanced → Random Fallback
- V6：优化版，规划中（见 `docs/implementation/`）
- **需要训练**，有 bc_model 文件（不上 Git）
- 训练 pipeline：`docs/training/` 有 BC预训练 + RL自弈（stage0-8）

### 共用层（关键！）

`src/decision/` 下的代码被**所有版本共用**：
- `cooperation.py` — 配合策略
- `card_type_handlers.py` — 牌型处理器
- `card_power_evaluator.py` — 牌力评估
- `card_grouping_strategy.py` — 配牌策略
- `enhanced_priority_system.py` — 优先级系统
- 等等

**GUA-014（拆牌与优先级不合理）标记为 `policy | 共用`，意味着它同时影响 M1 和 V4/V5/V6**

---

## 关键文档索引

### 必读（每次接手任务前）

| 文档 | 作用 |
|------|------|
| `docs/guandan-brain/README.md` | 迭代大脑入口 |
| `docs/guandan-brain/ISSUES.md` | 所有 GUA 缺陷登记 |
| `docs/guandan-brain/ITERATIONS.md` | 每轮迭代记录 |
| `docs/guandan-brain/EVAL.md` | 评测用例台账 |
| `README.md`（根目录） | 项目总览+M1使用说明 |

### 架构参考

| 文档 | 作用 |
|------|------|
| `docs/掼蛋AI客户端架构方案.md` | 详细架构设计（2552行） |
| `docs/guandan-brain/AGENT_HUB.md` | 指挥系统（Hermes/OpenCode/Cursor） |
| `docs/guandan-brain/MULTI_AGENT_ORCHESTRATION.md` | 多Agent协作历程 |

### 实施参考

| 文档 | 作用 |
|------|------|
| `docs/implementation/实施指导_总览_执行手册.md` | V6优化计划（6阶段） |
| `docs/training/YF硬编码完整提升计划优化版.md` | M1提升路线图 |

---

## GUA 问题框架

### 当前 open 的 GUA

| ID | 版本 | 严重 | 简述 |
|----|------|------|------|
| GUA-014 | **共用** | P2 | 拆牌与优先级不合理（影响所有版本） |
| GUA-015 | v6 | P2 | V6路线与验收未闭环 |
| GUA-016 | 训练 | P1 | 训练样本大量空action_cards |
| GUA-017 | 训练 | P1 | 损失尺度与预测行为异常 |
| GUA-018 | 训练 | P2 | 策略理解率指标曾为0 |
| **GUA-022** | **m1** | **P1** | **M1对lalala队胜率过低（0胜场）** |

### GUA-022 专题

**目标**：M1 对 lalala 队胜率过低，victoryNum 长期为 `[0,3,0,3]`（0+2队未胜）

**已尝试**（4轮迭代，均失败）：
- 共用层强化：`strategy_engine.py`（队友保护）+ `enhanced_priority_system.py`（优先级）
- 战绩：10局 / 10局 → victoryNum 全为 `[0,3,0,3]`

**核心矛盾**：
- 共用层改动（GUA-014）**同时影响 M1 和 V系列**，不能只改 M1
- 如果共用层问题不解决，V6 优化再好也会被拖累
- 但 M1 是纯规则引擎，没有自动优化手段，只能人工调参+对局验证

---

## 如何测试 M1

### 切换分支

```bash
cd /c/yifeGDBOT
git checkout m-dev
```

### 离线批量测试（推荐）

1. 启动离线服务端 `D:/GDAI/server/windows/guandan_offline_v1006.exe`
2. 运行 M1 测试 GUI 或批跑脚本

### 单局手动测试

```bash
# 终端1：启动客户端1（Player 0）
python src/communication/yf1_m1.py

# 终端2：启动客户端2（Player 2）
python src/communication/yf2_m1.py
```

---

## 指挥系统（Agent Hub）

```
人类 → Hermes（指挥官）→ OpenCode/Cursor（执行AI）→ yifeGDBOT代码
```

- **Hermes**：`C:\Users\Surfa\AppData\Local\hermes\hermes-agent`
  - profile: `hermes-win`
  - kanban 看板：`yi-fei_gd`（当前工作台）、`default`（已归档）
- **OpenCode CLI**：v1.15.5（已修复 PATH 劫持问题）
  - profile：`opencode-eng`（terminal.cwd=`C:\yifeGDBOT`）
  - 主力路径：`opencode run -m <model> "<task>"`
  - **不走 ACP 协议**（架构性不兼容）
- **Cursor CLI**：共享桌面 session 认证
  - 调用方式：`ask-cursor '...'` 或 `ask-cursor --timeout N "<task>"`
  - **`--mode agent`** 才能写文件（默认 `ask` 只读，不可写文档）
  - `--model` 选底层模型，`--mode` 选工作方式

### 双 CLI 协同工作流

```
1. opencode 执行任务 → 写代码/改文件
2. cursor review → 发现问题/改进点（重试直到质量合格）
3. opencode 修复 → 提交最终版本
```

---

## 重要文件路径

```
C:\yifeGDBOT\
├── src/
│   ├── decision/              # 决策引擎（含共用层）
│   │   ├── rule_based_decision_engine_m1.py   # M1主入口
│   │   ├── stage_router.py                   # 阶段路由器
│   │   ├── hybrid_decision_engine_v5.py       # V5主入口
│   │   ├── cooperation.py                     # 配合策略（共用）
│   │   └── ...
│   ├── communication/      # 客户端
│   │   ├── yf1_m1.py / yf2_m1.py             # M1客户端
│   │   ├── yf1_v4.py / yf2_v4.py             # V4客户端
│   │   ├── yf1_v5.py / yf2_v5.py             # V5客户端
│   │   └── yf1_v6.py.bak / yf2_v6.py.bak     # V6备份（非活跃）
│   └── game_logic/        # 游戏状态管理
├── docs/
│   ├── guandan-brain/      # 迭代大脑
│   │   ├── ISSUES.md      # GUA缺陷登记
│   │   ├── ITERATIONS.md  # 迭代日志
│   │   ├── EVAL.md        # 评测台账
│   │   └── AGENT_HUB.md   # 指挥系统
│   └── training/           # 训练文档
└── tests/                  # 测试代码
```

---

## 踩过的坑（经验教训）

1. **指挥官必须先查文件再开口**：没有去读 `ITERATIONS.md` 就凭记忆说4轮迭代，实际是8轮。作为指挥官，连基本事实都没确认就开口，是态度问题，不是能力问题。不确定就去查，不要惰性。
2. **ACP 协议架构性不兼容**：OpenCode ACP 是完整 Agent，有自己工具集，无法返回 `<tool_call>`，导致 Hermes 收不到工具调用 → worker 被判 crash → 死循环
3. **`.env` 的 `MINIMAX_CN_BASE_URL` 覆盖 `config.yaml`**：改完 config.yaml 要检查 .env
4. **Claude 模型在中国地区封锁**（HTTP 403）：用 DeepSeek via openrouter
5. **`config.yaml` 的空字符串 `api_key: ''` 覆盖 `.env` 的真实 key**：需要移除该字段
6. **opencode run 语法**：`opencode run -m <model> "<任务>"`（`-m` 参数，不是 `--print`）
7. **opencode 探索 agent 超时**：opencode 的 Explore Agent 会自动读大量相关文件，容易超时。调用时加 `--no-explore` 或用 `opencode run`（非 `opencode` 交互）更可控
8. **ask-cursor --file 截断**：大文档用 `--file` 管道容易截断；改用让 AI 直接读文件路径更可靠
9. **ask-cursor 默认 ask 模式不能写文件**：默认 `--mode ask`（只读），要落盘必须加 `--mode agent`（可写）。之前 cursor 评审结果写不进文件就是这个原因

---

## 下一步判断框架

接手 GUA 任务时，先问自己：

1. **影响范围**：是 M1 专用，还是共用层问题（影响所有版本）？
2. **技术路线**：M1 靠人工调参 + 对局验证；V 系列靠训练 pipeline
3. **验证方式**：M1 改完跑离线批测；V 系列看训练指标
4. **优先级**：GUA-022 > GUA-014（共用作弊） > 其他

---

## 评论区

> 本节供 OpenCode / Cursor 直接书写评审意见，写完后通知 Hermes 即可。

| 评审人 | 日期 | 评审文档 | 状态 |
|--------|------|----------|------|
| opencode | 2026-05-21 | reviews/yifegdbot-onboarding_OPENCODE.md | 已完成 |
| cursor | 2026-05-21 | reviews/yifegdbot-onboarding_CURSOR.md | 已完成 |
| opencode | 2026-05-21 | reviews/M1_ARCHITECTURE_OPENCODE.md | 已完成，已修订 |
| cursor | 2026-05-21 | reviews/M1_ARCHITECTURE_CURSOR.md | 已完成，已修订 |
