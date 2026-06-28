# V7 Agent 启动指南（Bootstrap）

> **工作流真源（步骤 / 格式 / Skill）**：[`工作流.md`](./工作流.md)  
> **新 Agent 第一句**：[`AGENT_FIRST_MESSAGE.md`](./AGENT_FIRST_MESSAGE.md)  
> 本文件 = V7 **深读**（环境、批跑恢复、命令大全）；新会话优先 **工作流 WF-01**，不必全文通读。

---

## 1. 新 Agent · 第一句（复制即用）

见 **[`AGENT_FIRST_MESSAGE.md`](./AGENT_FIRST_MESSAGE.md)**（默认走 **工作流 WF-01**）。

<details>
<summary>旧版首句（已废弃，展开仅作对照）</summary>

```text
先按 docs/guandan-brain/AGENT_BOOTSTRAP.md §1～3 读完并完成自测，再读 ITERATIONS 最新一行，然后等我派任务。
```

</details>

---

## 2. 项目定位（V7 实验线）

| 项 | 内容 |
|----|------|
| **项目** | YiFeiAI-GD（掼蛋 AI 客户端），南京邮电大学掼蛋 AI 算法对抗平台 v1006 |
| **工作目录** | `d:\guandanscore\YiFeiAI-GD` |
| **Python** | 项目自带 venv（Windows Python 3.13） |
| **离线平台** | `guandan_offline_v1006.exe N`（N = 局数，非副数） |
| **WebSocket** | `ws://127.0.0.1:23456/game/{user_info}` |
| **当前分支** | `v7-dev` |
| **引擎** | 深度学习胜率引擎 `src/decision/ultimate_win_rate_engine_v7.py` |
| **客户端** | `yf1_v7.py` / `yf2_v7.py` |

> **V7 是实验线**，与 `m-dev`（M 系列硬编码规则引擎）独立开发。  
> 提交必须推 `git push origin v7-dev`，**绝不混推 m-dev**。

---

## 3. 核心概念（局/副/victoryNum）——三句定音

```text
副（小局）= episodeOver = game_records 每条 JSON
局（整局）= 2→A 双上过关；exe N / completed_games = N 局（≠ N 副）
victoryNum[0] vs [1] = 各队赢几局；须 [0]=[2]、[1]=[3]；批跑 N 局时 [0]+[1]=N
```

### 关键关系

- **局 ⊃ 多副**（1 局可含数十副；实测 N=1 局 → 59 副）
- **队伍**：0+2 一队，1+3 一队（连接顺序决定）
- **`--target-games`** 须为 **3 的倍数**（3/9/12）；**勿用 10**

### victoryNum 自检

| 值 | 含义 |
|----|------|
| `[0,3,0,3]` | lalala 赢 3 局，V7 赢 0 局 |
| `[3,0,3,0]` | V7 赢 3 局，lalala 赢 0 局 |
| `[1,2,1,0]` | **不可信**（同队不一致） |

### GUA-033 定音（exe 固定 3 局 + fallback）

```text
先读 platform-data-interpretation §2 + §4.3.1，再动批跑/victoryNum 相关代码或报告。

定音五句：
1. 台账 batch_games 真源 = batch_executor/current_batch.json，不是 WebSocket settingTimes。
2. 本包 v1006 offline exe 单次会话固定 3 平台局；argv 1/3/10 实测均无效。
3. gameResult.victoryNum 是会话 3 局合计，禁止裸信；[0]+[1]≠batch_games 时用 gameOver 计数 fallback。
4. batch_games=1 时 fallback 只认领 curTimes=1 → 落盘 [0]+[1]=1；不等于「平台只打 1 局」。
5. 对账看 batch_executor/latest_victory_num.json：victoryNum=采用值，server_vn_raw=WebSocket 原文，vn_source=server|fallback。
```

---

## 3.5. 快速查上下文（LLM Wiki）🆕

> **从 v7.2 开始**，`docs/guandan-brain/` + `docs/analysis/` 已接入 LLM Wiki。  
> 知识被 LLM「编译」一次后持久化，新 Agent 不需要逐文件探索。

```bash
# 初始化 & 首次摄入（一次性）
python scripts/wiki.py init         # 已执行
python scripts/wiki.py ingest       # 摄入 107 个源文件 → 生成 Wiki 页面

# 日常查询（不跑 ingest，直接问）
python scripts/wiki.py query "V7 当前 P0 是什么？"
python scripts/wiki.py query "最近批跑胜率？GUA-061 是什么？"

# 维护
python scripts/wiki.py status       # 查看待摄入变化
python scripts/wiki.py lint         # 健康检查（断链/孤立/格式）
```

> **Wiki 目录**：`wiki/`（`purpose.md` 定义目标，`schema.md` 定义结构规则）  
> **来源**：`docs/guandan-brain/` + `docs/analysis/`

---

## 3.6. 出牌顺序与上下家策略 🆕

出牌顺序为**固定顺时针轮转**：`pos 0 → pos 1 → pos 2 → pos 3 → pos 0 → ...`

对于 V7（pos 0 或 2），上家/下家出大牌时的策略差别：

| 场景 | 顺序 | 结论 |
|------|------|------|
| **上家出大牌**（V7 压不过） | V7 PASS → 下家(对手)先接 → 队友最后 | **不太需要急炸** — 队友还能救 |
| **下家出大牌**（V7 压不过） | 队友第一个接 → 上家(对手)接 → V7 最后 | **最安全** — 队友先救，V7 最后兜底就行 |

> 上家(pos 1/3，`(my_pos+3)%4`)：V7 之前出牌的人  
> 下家(pos 3/1，`(my_pos+1)%4`)：V7 之后出牌的人  
> 队友(pos (my_pos+2)%4)：对角线，始终中间隔一个人

---

## 4. 改代码前必读顺序

0. **`python scripts/wiki.py query "当前状态"`** — 🆕 快速了解 P0 / 最新迭代 / 关键指标
1. **`docs/guandan-brain/ISSUES.md`** — open 条目 + P0 标签；完成定义见 `issues/GUA-xxx-completion.md`
2. **`docs/guandan-brain/ITERATIONS.md`** — 最新一行，确认目标与完成定义；用法见顶部「如何使用」
3. **`docs/guandan-brain/TASKS.md`** — 当前活跃任务
4. **`docs/guandan-brain/EVAL.md`** — 评测入口与通过标准

### 按任务跳转

| 任务 | 必读 |
|------|------|
| 分析批跑胜率、填 ITERATIONS | `AGENTS.md` § 数据解读口径 + `platform-data-interpretation` §3.3 |
| 改 `yf*_v7.py`、落盘逻辑 | `guandan-platform-v1006` + `platform-data-interpretation` §3.4 |
| 改 **V7** 引擎/策略 | `ISSUES` V7 段落（GUA-050+）、`V7-实施方案.md`、引擎入口 `ultimate_win_rate_engine_v7.py::decide()` |
| 改 **V7 NN 模型** | `ISSUES` + `ITERATIONS` V7 训练相关行 + 模型目录 `models/` |

---

## 5. 提交/推送检查清单

### 动手前

- [ ] 当前分支：`git branch -vv` → **`v7-dev`**（非 main，非 m-dev）
- [ ] 已 `git status` / `git diff --stat`，**未** `git add .` 盲加
- [ ] 未纳入 Layer 2：`v7_vs_lalala_scores.json`、`game_records/`、`models/*.pth`、`logs/`

### Commit 规则

| 项 | 要求 |
|----|------|
| 前缀 | `[V-nn-v7]` / `[docs]` |
| 推送 | **`git push origin v7-dev`** |
| 禁止 | 推 `main` 或 `m-dev`、`--force`、跳过 hooks |

---

## 6. 关键路径映射

| 用途 | 路径 |
|------|------|
| **迭代大脑** | `docs/guandan-brain/` |
| **缺陷登记** | `docs/guandan-brain/ISSUES.md` |
| **迭代日志** | `docs/guandan-brain/ITERATIONS.md` |
| **评测标准** | `docs/guandan-brain/EVAL.md` |
| **平台协议** | `docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md` |
| **数据解读** | `docs/knowledge/platform-data-interpretation.md` |
| **V7 方案** | `docs/guandan-brain/V7-实施方案.md` |
| **仓库治理** | `docs/governance/M-V-Series-治理方案.md` |
| **牌谱回放** | `scripts/tools/yf_replay.py` / `YF_REPLAY.bat` |
| **本地评测清单** | `docs/guandan-brain/LOCAL_EVAL_CHECKLIST.md` |
| **LLM Wiki 入口** | `scripts/wiki.py`（`status`/`query`/`ingest`/`lint`） |
| **V7 副级等级分析** | `scripts/tools/analyze_v7_round_levels.py` |
| **组牌引擎独立测试** | `scripts/checks/check_grouping_engine.py` |
| **V7 调试 GUI** | `tests/debug_v7_gui.py`（`START_V7_GUI.bat` 启动；手牌录入→组局→对手出牌→V7应对全流程可视化；含随机发牌 + localStorage 记忆） |

> **V7 副级分析工具**（每次 V7 批跑后必跑）：
> ```bash
> python scripts/tools/analyze_v7_round_levels.py                    # 全量 V7 批跑副级表
> python scripts/tools/analyze_v7_round_levels.py --game-id <ID>     # 单局分析
> ```
> 输出：每副「起始级 / V7末级 / lalala推断级 / 赢家 / 剩余牌数 / 出牌顺序」
> 用途：解释 0-3 局战绩背后的真实副级博弈——V7 赢了几副、谁先跑光、谁先双上过 A。
> 替代：手动 grep `curRank` / `order`（已废弃，不再手动统计）。

> **组牌引擎独立测试**（改 `grouping_engine.py` 后必跑）：
> ```bash
> python scripts/checks/check_grouping_engine.py                          # 默认测试手牌（27张，rank=3）
> python scripts/checks/check_grouping_engine.py --rank 4                 # 指定级牌
> python scripts/checks/check_grouping_engine.py --hand RJ,RJ,S6,CA,...   # 自定义手牌
> ```
> 输出：所有枚举方案的 5 维评分明细表（炸弹/手数/回收/灵活/去单化）+ 27/27 完整性校验 + best_plan 牌型摘要 + 总分回算验证。
> 用途：验证组牌引擎改动后评分逻辑正确、方案枚举完整、无回归。

---

## 7. 常用命令

> **⚠️ Python 环境**：本机**无 venv**，直接用 `python` 命令（系统 Python 3.14.4）。
> **⚠️ 分支**：M3 / V7 批跑**均可在 v7-dev 直接跑**（M3 客户端/引擎 import 测试通过）。
> **⚠️ 数据目录分离**：M3 批跑 → `game_records/`，V7 批跑 → `game_records_v7/`（训练只读 V7 数据）。

```bash
# 切分支
git checkout -f v7-dev

# 推送
git push origin v7-dev

# V7 启动
START_V7_GUI.bat         # Windows GUI 对战
START_V7_AUTO.bat        # 自动启动服务器+客户端

# V7 vs lalala 批跑（当前分支 v7-dev）
python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 3
python scripts\launchers\v7\run_v7_vs_lalala_games.py --games 12
# 战绩文件：v7_vs_lalala_scores.json

# M3 vs lalala 批跑（当前分支 v7-dev，直接跑）
python scripts\launchers\m\run_m3_vs_lalala_games.py --games 3
python scripts\launchers\m\run_m3_vs_lalala_games.py --games 12
# 战绩文件：m3_vs_lalala_scores.json

# 牌谱回放
YF_REPLAY.bat
python scripts/tools/yf_replay.py

# 测试
python tests/test_v7_engine_load.py
```

---

## 8. 批跑数据恢复（game_records 丢失/被清时）

> **前提**：`game_records/*.json` 或 `game_records_v7/*.json` 全部丢失，但日志文件还在。**不要重新跑局**，日志足够恢复全部 victoryNum。

### 数据目录分离策略

| 引擎 | game_records 目录 | 用途 |
|------|------------------|------|
| M3 | `game_records/` | M3 批跑数据（BC训练数据源） |
| V7 | `game_records_v7/` | V7 批跑数据 + V7 BC训练 |

> **注意**：两个目录**完全隔离**，避免数据混杂。M3 批跑存入 `game_records/`，V7 批跑存入 `game_records_v7/`。训练脚本 `train_bc_v7.py` 默认读取 `game_records_v7/`。

### 为什么能恢复——双重数据通道

```
掼蛋服务器 v1006.exe
├─ WebSocket ──→ yf1_v7.py ──→ latest_victory_num.json (覆盖写入，仅最后一批)
│                              game_records/*.json    (被误清 = 丢失)
│
└─ stdout ──→ executor.py read_stdout() ──→ logs/v7_vs_lalala_*.log  (所有行逐行落盘)
                                              v7_vs_lalala_scores.json (score tracker)
```

**通道 B（stdout → 日志）与 game_records 生命周期完全解耦**：日志由 `logging.basicConfig` 在进程入口一次性绑定 FileHandler，`executor.py` 后台线程 `read_stdout()` 把服务端 stdout 每一行经 `self.logger.info("[服务器] {line}")` 写入同一个日志文件。清了 `game_records` 不影响日志。

### 三步恢复法

| 步骤 | 操作 | 命令/文件 |
|------|------|-----------|
| 1 | 读最后一批快照 | `Get-Content batch_executor/latest_victory_num.json` |
| 2 | 搜日志中全部批末 vn | `Select-String -Path "logs/v7_vs_lalala_*.log" -Pattern "vn_source\|server_vn\|批末\|victoryNum"` |
| 3 | 交叉计算队胜率 | 合计各批 `victoryNum[0]+[2]` vs `[1]+[3]` |

**日志关键字**：
- `批末 victoryNum 校验通过:` — executor 每批末对账输出
- `批末对账：采用 vn=` — 含 vn_source + server_vn_raw
- `达到设定场次` — 服务端 stdout 原文（含各位置胜利次数）

### 四层 victoryNum 写入清单

| 序号 | 数据层 | 写入者 | 粒度 | 覆盖/追加 |
|------|--------|--------|------|-----------|
| 1 | `latest_victory_num.json` | `yf1_v7.py`（Player 0） | 最后一批 | **覆盖** |
| 2 | `logs/v7_vs_lalala_*.log` | `executor.py`（stdout 镜像） | 全部批次 | **追加** |
| 3 | `v7_vs_lalala_scores.json` | `executor.py`（score tracker） | 全部批次 | **覆盖** |
| 4 | `game_records_v7/*.json`（V7）或 `game_records/*.json`（M3） | `v7_game_recorder.py` / `game_recorder.py` | 每副 | **追加** |

**结论**：只要 2 或 3 还在，victoryNum 永不会丢。即使 1+4 全丢，从 2 搜关键行即可完整恢复。

---

## 9. 协作原则

1. **短任务短 prompt**：单个提示词 <= 40 行
2. **长任务拆回合**：拆成多个短任务串行调度
3. **一个回合一个目标**：做完验证关单再开下一个
4. **不传信任**：子 Agent 报告的结果必须验证
5. **产出验证优先**：任何声称修复/完成的，必须读文件确认

---

## 延伸阅读

- 完整 5 分钟路径：[README.md](./README.md)
- 详版真源：[platform-data-interpretation.md](../knowledge/platform-data-interpretation.md)
- 数据恢复详版：[数据恢复链分析.md](../analysis/数据恢复链分析.md)
- 提交前必读：[AGENT_PUSH_CHECKLIST.md](./AGENT_PUSH_CHECKLIST.md)
