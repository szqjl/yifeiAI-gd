# Agent 启动指南：读这一篇就够了

> **目标**：新 Agent 读完本文 → 掌握项目全貌（不漏关键知识、不需人类逐一点名）  
> **前置**：本文默认你是新会话，直接读即可开始干活。

---

## 1. 项目一句话定位

**YiFeiAI-GD**：南邮掼蛋 AI 算法对抗平台客户端（v1006 旧平台 + OpenGuanDan 新平台双线），核心目标是**让 AI 在四人结对掼蛋中达到甚至超越人类高手水平**。

**当前分支**：`v8-dev`（OpenGuanDan 新平台，WebSocket 协议）

---

## 2. 多版本并存（必读 · 定音）

| 引擎 | 分支 | 通信 | 状态 | 定位 |
|------|------|------|------|------|
| **M1** | `m-dev` | v1006 TCP | **frozen** | 非交付基线；仅 bugfix |
| **M3** | `m-dev` | v1006 TCP | **active** | 主交付线；P0 guard 规则引擎；队胜率 KPI 基线 |
| **V7** | `v7-dev` | v1006 TCP | active | NN 实验线（神经网络决策） |
| **V8** | `v8-dev` | OpenGuanDan WebSocket | **active** | V7 迁移新平台；**当前开发主线** |

> **定音**：队胜率 KPI 自 2026-05-31 起**只看 M3 批跑**。V7/V8 是实验线，V8 迁移自 V7（commit 2904c08），决策管线**一字不改**，仅换通信层。

---

## 3. 掼蛋规则（5 分钟速通）

### 3.1 数据口径（三句定音）

```
副（小局）= episodeOver = game_records 每条 JSON
局（整局）= 2→A 双上过关；exe N局（≠ N副）
victoryNum[0] vs [1] = 各队赢几局；须 [0]=[2]、[1]=[3]；批跑 N 局时 [0]+[1]=N
```

### 3.2 核心规则速查

- **108 张**：每人 27 张，无底牌
- **牌型大小**：王炸 > 八星炸 > … > 六星炸 > **同花顺 > 五星炸 > 四星炸**；同花顺可压 5 张（含）以内炸弹；超 5 张炸弹可压同花顺
- **逢人配**：红桃级牌（H + curRank），可组任意合法牌型，**不得与大王/小王组牌**，进贡时红桃级牌免进
- **进贡**（第二副起）：末游→头游进最大牌（红桃级牌除外）；头游还 ≤10 点或最小牌
- **抗贡**：持双大王免进贡
- **升级**：双上（头游+二游）+3 级；头游+三游+2 级；头游+末游+1 级；无人头游不升
- **赢一局**：等级 A **且** A 级本副双上；未赢则 A 级连续 2 副不双上 → 降回 2 级
- **平台 stage**：`beginning` → `tribute` → `anti-tribute` → `back` → `play` → `episodeOver` → `gameOver` → `gameResult`

### 3.3 术语对照（平台标准名 vs 内部名）

| 类别 | 平台标准 | 内部可能混用 |
|------|----------|-------------|
| 单张 | `Single` | `single` |
| 对子 | `Pair` | `pair` |
| 三张 | `Trips` | `trips` |
| 三带二 | `ThreeWithTwo` | `three_with_two` |
| 钢板 | `TwoTrips` | `two_trips` |
| 同花顺 | `StraightFlush` | `straight_flush` |
| 炸弹 | `Bomb` | `bomb` |
| 特殊动作 | `PASS` / `tribute` / `back` | — |
| 阶段 | `play` / `episodeOver` / `gameOver` | 把 episodeOver 叫「局」是错的 |
| 等级字段 | `curRank` / `selfRank` / `oppoRank` | 与协议不同名的别称 |

> **铁律**：文档与代码中的术语必须与平台使用说明一致。真源顺序：平台 PDF > `掼蛋AI算法对抗平台使用说明.md` > `guandan-platform-v1006.mdc` > `platform-data-interpretation.md`

---

## 4. 核心决策链路（调用栈 · 定音）

**V7 和 V8 决策链路完全共用**，V8 仅换了通信层（TCP → WebSocket），`UltimateWinRateEngineV7` 一字不改。

```
游戏服务器 (guandan.exe / guandan_offline_v1006.exe)
    ↓ WebSocket
yf1_v8.py / yf2_v8.py（V8 通信层）
    ↓
UltimateWinRateEngineV7.decide()  [src/v/nn/ultimate_win_rate_engine_v7.py:450]
    │
    ├─ EndgamePreprocessor().preprocess()  ← 残局识别
    │    若 ec['is_active'] == True：
    │        └─ EndgameDecider.decide()   ← 残局专用决策器（组合，非继承）
    │             ├─ pick_double_second_small_single()
    │           ├─ pick_teammate_sprint_small_single()
    │           ├─ apply_banned_filter()
    │           └─ decide()
    │
    └─ GUA-075 主路径（残局未命中时）
         ├─ _recommend_play()              ← 推荐方案
         ├─ _match_actionList()             ← 匹配 actionList
         ├─ Guard filter                   ← 硬规则（R01-R15）
         ├─ _group_consistency_filter       ← 组牌一致性过滤（角色驱动）
         ├─ 接风/投喂策略
         ├─ _model_decision()              ← NN forward（BC 模型）
         ├─ _heuristic_select()            ← 启发式回退
         └─ validate_decision
```

**关键文件**：
- `src/v/nn/ultimate_win_rate_engine_v7.py` — 决策核心，`decide()` 入口
- `src/v/nn/endgame/endgame_decide.py` — 残局决策器（`EndgameDecider`）
- `src/v/nn/endgame/endgame_preprocessor.py` — 残局识别（`EndgamePreprocessor`）
- `src/v/nn/features/grouping_engine.py` — 组牌引擎（`enumerate_groupings()`、`to_card_mask()`）

---

## 5. 组牌引擎：三层架构（定音）

```
enumerate_groupings()（一次跑，三产出）
    │
    ├─ features（all_plans 汇总，24维）→ NN 软引导
    ├─ card_mask（best_plan，27×3：[group_id, is_core, group_size]）
    │    → _group_consistency_filter 前置过滤
    └─ role（主攻/助攻）→ 决定过滤强度

管线顺序（定音）：Guard → _group_consistency_filter → NN/heuristic
主攻：移除「拆核心牌型」动作（炸弹/同花顺等）
助攻：全部放行（自由发挥）
安全阀：自己≤5张 / 对手≤2张 / 队友1张且下家非1张 → 全部放行
```

> `to_card_mask()` 已实现（`grouping_engine.py:136`），返回 `Tuple[Dict, Dict, Dict]` 三个映射。

---

## 6. 人类决策流程（对标 · 核心目标）

人类打牌的 4 阶段（V 系列 AI 的核心差距所在）：

| 阶段 | 时机 | 人类 | V 系列 AI |
|------|------|------|-----------|
| 阶段0 | 开局27张 | 组牌多方案生成+评估 | ❌ 跳过或单次固定 |
| 阶段1 | 首圈前 | 角色定位（主攻/助攻） | ❌ 无角色概念 |
| 阶段2 | 第1-5圈 | 试探：回收能力判断+风险评估 | ❌ 端到端静态映射 |
| 阶段3 | 第6-10圈 | 动态调整：记忆追踪+角色转换+炸弹决策 | ❌ 无动态调整 |
| 阶段4 | 剩余≤10张 | 残局：精确记忆+出牌顺序优化 | ❌ 无专门残局 |

**核心贯穿原则**：`争夺牌权，尽快出清手牌`

---

## 7. GUA 编号体系与知识库

### 7.1 当前最新 GUA

**GUA-168**（`endgame bomb+single lead fix` — bomb+单张结构先出单试探，炸弹兜底）

### 7.2 ISSUES 与 ITERATIONS

| 文件 | 作用 | 读法 |
|------|------|------|
| `docs/guandan-brain/ISSUES.md` | 缺陷登记簿 | 表格中找 `open` + `P0`；已完成的看 `issues/GUA-xxx-completion.md` |
| `docs/guandan-brain/ITERATIONS.md` | 迭代日志 | 底部高亮最新一行；按 wikilink 点入详情 |
| `docs/guandan-brain/handoff/` | 接续文档 | 文件名含日期+GUA 编号；接续时直接读对应文件 |

### 7.3 核心文档索引

| 文档 | 作用 |
|------|------|
| `docs/guandan-brain/工作流.md` | 完整工作流体系（WF-01 ~ WF-12） |
| `docs/guandan-brain/AGENT_FIRST_MESSAGE.md` | 新会话/换机/接续的"一句话触发"模板 |
| `docs/guandan-brain/v8-win-rate-history.md` | V8 批跑 KPI 历史（每次批跑强制记录） |
| `docs/knowledge/rules/01_basic_rules/README.md` | 掼蛋基础规则索引 |
| `docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md` | 组牌→NN 衔接架构（三层过滤） |
| `docs/guandan-brain/人类掼蛋决策流程完整分析.md` | 人类决策链路对照（4阶段） |
| `docs/guandan-brain/掼蛋AI自我进化-随机应变套路.md` | NN/RL 在掼蛋中的局限性与模块化路线 |
| `docs/knowledge/platform-data-interpretation.md` | 局/副/批跑口径定音 |
| `.cursor/rules/guandan-platform-v1006.mdc` | 平台协议速查 |

---

## 8. 常用命令速查

> **Python 环境**：本机 venv `.venv`（Python 3.14.4）；激活方式：`.venv\Scripts\Activate.ps1` 或直接用 `.venv\Scripts\python.exe`

### 8.1 批跑

```bash
# V8 vs lalala（当前主线）
python scripts\launchers\v8\run_v8_vs_lalala_games.py --games 3
python scripts\launchers\v8\run_v8_vs_lalala_games.py --games 9   # 推荐档位

# V8 vs V8 自对弈（验证引擎一致性）
python scripts\launchers\v8\run_v8_vs_v8_games.py --games 3

# V7 vs lalala
python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 3

# M3 vs lalala
python scripts\launchers\m\run_m3_vs_lalala_games.py --games 3
```

**V8 KPI 历史（最新）**：

| 日期 | 目标 | 批跑命令 | 局数 | 队胜率 | 副数 | 副头游率 | 双上率 |
|------|------|----------|------|--------|------|----------|--------|
| 2026-07-21 | GUA-154+12局回归 | `--games 12` | **12** | **10/12（83.3%）** | 171 | 57.9% | 17.5% |
| 2026-07-18 | GUA-151/152/153三修复 | `--games 9` | 9 | **9/9（100%）** | 60 | 71.7% | 28.3% |
| 2026-07-18 | GUA-151/152/153首跑 | `--games 6` | 6 | **4/6（66.7%）** | 73 | 63.0% | 24.7% |

> 真源：`docs/guandan-brain/v8-win-rate-history.md`（每次批跑后强制记录至此表）

### 8.2 分析

```bash
# 批跑结果分析（WF-04 主工具）
python scripts\analysis\analyze_v7_rounds.py --all                        # V7
python scripts\analysis\analyze_v7_rounds.py --dir game_records_v8 --all  # V8

# 副级 curRank 分析（可选）
python scripts\tools\analyze_v7_round_levels.py
```

### 8.3 测试

```bash
# 用 python3.14（hermes 本机 venv 的 python）
python3.14 -m pytest tests/test_gua168_bomb_plus_single_lead.py -v       # 单个 GUA
python3.14 -m pytest tests/ -k "endgame or GUA-15" -v --ignore=tests/test_gui_launch.py  # endgame 回归

# 组牌引擎独立测试
python scripts\checks\check_grouping_engine.py

# 残局智能体调试
python scripts\checks\check_endgame_agent.py --hand ... --players ...
```

### 8.4 Wiki

```bash
python scripts/wiki.py query "关键词"     # 日常查询
python scripts/wiki.py status             # 待摄入变化
python scripts/wiki.py ingest             # 摄入（不常用）
```

---

## 9. 自测验证（新 Agent 必做）

读完全文后，用以下问题验证是否真正掌握：

- [ ] **数据口径**：副和局的区别是什么？victoryNum[0] 和 [1] 分别代表什么？
- [ ] **决策链路**：从 yf1_v8.py 收到服务器消息到返回 actIndex，调用了哪些关键函数？
- [ ] **管线顺序**：`decide()` 中 Guard filter 和 `_group_consistency_filter` 谁先执行？
- [ ] **组牌角色**：主攻时，拆炸弹的动作会不会进入 NN 的候选池？
- [ ] **V8 vs V7**：`yf1_v8.py` 和 `yf1_v7.py` 的决策引擎是同一个吗？
- [ ] **最新 GUA**：当前 open 的最高编号 GUA 是哪个？
- [ ] **批跑 KPI**：V8 队胜率最近记录是多少局胜率多少？

若无法回答以上全部问题 → 回读本文件对应章节，或 `python scripts/wiki.py query "关键词"`。

---

## 10. 工作流速查（按场景）

| 场景 | 工作流 | 首条消息 |
|------|--------|----------|
| 新会话 | WF-01 | `按 docs/guandan-brain/工作流.md WF-01 自启动：读 ITERATIONS 最新一行 + ISSUES open P0` |
| 换机/handoff 接续 | WF-07 | `按工作流 WF-07 接续：读 handoff + ITERATIONS 最新一行` |
| 批跑/胜率分析 | WF-04 | `按工作流 WF-04：解读批跑数据` |
| yf 出牌/败招分析 | WF-12 | `按工作流 WF-12：分析 yf 决策链路` |
| 改 V7/V8 引擎 | WF-02+WF-05 | `按工作流 WF-02 + WF-05` |
| 提交/推送 | WF-08 | `按工作流 WF-08 + AGENT_PUSH_CHECKLIST` |

---

## 11. 协作原则

1. **短任务短 prompt**：单个提示词 ≤ 40 行
2. **长任务拆回合**：拆成多个短任务串行调度
3. **一个回合一个目标**：做完验证关单再开下一个
4. **不传信任**：子 Agent 报告的结果必须验证
5. **产出验证优先**：任何声称修复/完成的，必须读文件确认

---

*最后更新：2026-07-26（同步 v8-dev 最新状态）*
