# YiFeiAI-GD · Agent 入口

> **工作流真源（步骤 / 产出格式 / Skill 索引）**：[`docs/guandan-brain/工作流.md`](docs/guandan-brain/工作流.md)  
> **新会话人类首句**：[`docs/guandan-brain/AGENT_FIRST_MESSAGE.md`](docs/guandan-brain/AGENT_FIRST_MESSAGE.md)  
> **V7 深读（环境/批跑/命令）**：[`docs/guandan-brain/AGENT_BOOTSTRAP.md`](docs/guandan-brain/AGENT_BOOTSTRAP.md)

新 Agent 默认执行 **工作流 WF-01**（读 ITERATIONS 最新一行 + ISSUES open P0 → 3 行汇报），无需人类重复项目背景。

---

## 项目一句

掼蛋 AI 客户端（南邮 v1006 / OpenGuanDan）；**改 AI 行为真源** = `docs/guandan-brain/`（ISSUES、ITERATIONS、EVAL）。当前活跃：**v8-dev**（OpenGuanDan 新版服务器迁移，从 v7-dev 复制）、**v7-dev**（V7/组牌，v1006 回退基线）与 **m-dev**（M3 交付）；**M1 frozen**；队 KPI **只看 M3 批跑**。

---

## 用户偏好

- 简体中文；Agent **自动执行**终端命令（git/python/pytest 已 allowlist）。
- **仅明确要求时** commit / push → 工作流 **WF-08** + [`AGENT_PUSH_CHECKLIST.md`](docs/guandan-brain/AGENT_PUSH_CHECKLIST.md)。
- 改 M3/V7 决策或解读批跑前：读 ISSUES open + ITERATIONS 最新行（`.cursor/rules/guandan-context.mdc`）。
- 接续：「继续 / handoff / 按迭代」→ 工作流 **WF-07**。
- 脚本前先查 [`SCRIPT_INDEX.md`](docs/guandan-brain/SCRIPT_INDEX.md)；新脚本须登记索引。
- 知识检索：**Wiki 综合** → `python scripts/wiki.py query`；**实时**（ITERATIONS/ISSUES/handoff）→ 直接读原文件（工作流 **WF-09**）。
- 掼蛋规则：`.cursor/rules/guandan-knowledge.mdc`；回放不篡改真实流水。

---

## 数据口径（三句）

- **副** = `game_records` 每条 JSON；**局** = 平台整局 / `completed_games`；**局 ⊃ 多副**。
- 队胜看 **`victoryNum[0]` vs `[1]`**（0+2 一队，1+3 一队）；禁止四席相加。
- 批跑 `--target-games` 须 **3 的倍数**（3/9/12）；勿用 10。

---

## 术语与平台一致（强制）

**文档与代码中的术语，必须与平台使用说明一致。** 真源（按优先级）：

1. [`offline_platform/掼蛋平台使用说明书v1006.pdf`](offline_platform/掼蛋平台使用说明书v1006.pdf)
2. [`docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md`](docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md)
3. [`.cursor/rules/guandan-platform-v1006.mdc`](.cursor/rules/guandan-platform-v1006.mdc)（协议速查）
4. [`docs/knowledge/platform-data-interpretation.md`](docs/knowledge/platform-data-interpretation.md)（局/副/批跑口径）

### 必须对齐的平台术语（示例）

| 类别 | 平台标准写法 | 禁止混用（除非下方例外） |
|------|-------------|-------------------------|
| 牌型 / `action[0]` | `Single` `Pair` `Trips` `ThreeWithTwo` `ThreePair` `TwoTrips` `Straight` `StraightFlush` `Bomb` | `single` `pair` `bomb` `straight_flush` `three_with_two` … |
| 特殊动作 | `PASS` `tribute` `back` | 自造 snake_case 动作类型名 |
| 阶段 `stage` | `beginning` `tribute` `anti-tribute` `back` `play` `episodeOver` `gameOver` `gameResult` | 把 `episodeOver` 叫「局」、把 `gameOver` 叫「副」 |
| 等级字段 | `curRank` `selfRank` `oppoRank` | 与协议不同名的别称 |
| 计数单位 | **局**（`completed_games` / `victoryNum`）、**副**（`game_records` 条 / `episodeOver`） | 用牌谱条数当局数 |

### 无法与平台完全一致的例外

组牌引擎等**内部子结构**键（非 `actionList` 声明）可保留，但须在**定义处**用注释标明与平台名的对应关系，例如：

- `group_type`：`trip_in_three_with_two` / `pair_in_three_with_two` → 平台 `ThreeWithTwo`（GUA-070 拆分子组）
- `group_type`：`pair_in_three_pair` → 平台 `ThreePair`
- `group_type`：`trip_in_steel_plate` → 平台 `TwoTrips`（钢板）
- `GroupingPlan` 字段名（如 `straight_flushes`、`three_with_twos`）→ 数据结构名，**不是**平台 `action[0]`；导出/对接时用 `StraightFlush` / `ThreeWithTwo` 等

**禁止**：再引入 `three_with_two`、`three_pair`、`two_trips` 等**从未由组牌产出、却假装是 group_type** 的幽灵键（见 ITERATIONS `v7-group-type-platform-unify`）。

新增类型名、文档章节名或 JSON 字段前：先查上表真源；若用内部名，**代码写行内注释，文档写「平台名 ↔ 内部名」对照一句**。

---

## 净盘（批跑前标准动作）

**何时**：关单验收、KPI 环比、多样本观测前——须清空本轮 Layer 2 产物，避免旧牌谱/旧 vn 混入统计。对应工作流 **WF-04** 跑批前一步。

**目录分离**：M3 牌谱 → `game_records/`；V7 牌谱 → `game_records_v7/`（**勿混清**——只清本次批跑对应目录，除非明确做全仓净盘）。

| 线 | 必清 |
|----|------|
| **M3** | `game_records/*.json` |
| **V7** | `game_records_v7/*.json` |
| **共用** | `logs/*`（`batch_executor_*.log`、`m3_vs_lalala_*.log`、`v7_vs_lalala_*.log` 等） |

**同批还应清**（否则 `completed_games`/vn 对账会串批）：`batch_executor/latest_victory_num.json`、`batch_executor/current_batch.json`、`execution_state.json`（若存在）、`tmp/.batch_executor.lock`；以及对应战绩文件 **M3** → `m3_vs_lalala_scores.json` + `m3_vs_lalala_state.json`（+ 若 GUI 用过 `game_scores.json`）；**V7** → `v7_vs_lalala_scores.json` + `v7_vs_lalala_state.json`。

**PowerShell（仓库 Git 根目录）**：

```powershell
# --- V7 净盘（run_v7_vs_lalala_games 前）---
Get-Process guandan_offline_v1006 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item tmp\.batch_executor.lock -ErrorAction SilentlyContinue
Get-ChildItem game_records_v7 -Filter *.json -ErrorAction SilentlyContinue | Remove-Item -Force
Remove-Item v7_vs_lalala_scores.json, v7_vs_lalala_state.json -ErrorAction SilentlyContinue
Remove-Item batch_executor\latest_victory_num.json, batch_executor\current_batch.json -ErrorAction SilentlyContinue
Remove-Item execution_state.json -ErrorAction SilentlyContinue
Get-ChildItem logs -File -ErrorAction SilentlyContinue | Remove-Item -Force

# --- M3 净盘（run_m3_vs_lalala / batch_executor M3 前）---
# 同上停进程与 lock；改清 game_records 与 m3 战绩：
Get-ChildItem game_records -Filter *.json -ErrorAction SilentlyContinue | Remove-Item -Force
Remove-Item m3_vs_lalala_scores.json, m3_vs_lalala_state.json -ErrorAction SilentlyContinue
# logs / batch_executor 状态文件同上
```

**注意**：

- 以上均为 **Layer 2**，**禁止 commit**（见治理 §6）。
- 误清 `game_records` 但 **`logs/` 仍在** → 可从日志恢复 `victoryNum`，勿立刻重跑；见 [`AGENT_BOOTSTRAP.md`](docs/guandan-brain/AGENT_BOOTSTRAP.md) §8。
- 需保留牌谱作分析时，先 **复制到仓库外** 或 `data/eval/` 再净盘，勿只删不备份。

---

## 项目 Skill（`.cursor/skills/`）

| 场景 | Skill |
|------|-------|
| 新会话 / 自启动 | `guandan-session-start` |
| 批跑 / 胜率分析 | `guandan-batch-eval` |
| **yf 出牌决策链路 / 败招根因** | **`guandan-decision-trace`**（WF-12） |
| 组牌引擎测试 | `guandan-grouping-engine` |
| handoff 接续 | `guandan-handoff-continue` |
| commit / push | `guandan-git-push` |

完整列表与待建 Skill：工作流 §7。

---

## Wiki 速查

| 实时（不走 Wiki） | Wiki 适合 |
|-------------------|-----------|
| ITERATIONS 最新、ISSUES 状态、handoff | GUA 释义、概念、模块关系、批跑约束 |

```bash
python scripts/wiki.py query "关键词"
```

改了 `docs/` 后按需：`python scripts/wiki.py ingest`

---

## Kaggle 发布

批跑结束后将牌谱同步到 Kaggle 数据集（对比修复前后 KPI）。

**同步脚本**：`scripts/kaggle/sync_v8.py`

```powershell
# 1. 同步 + 打包 zip（推荐手动上传）
python scripts\kaggle\sync_v8.py --zip --title "Guandan V8 Records (Post-Fix 73eps)"

# 2. 打开 https://www.kaggle.com/datasets/new，上传 _kaggle_data.zip
```

**文件名转换**：`[yf1_v8]-[opponent_1_3]-[1]-[2]` → `yf1_v8_opponent_1_3_1_2`（Kaggle 禁止 `[]`）

**数据集区分**：文件名时间戳前缀（`20260716` = 修复前，`20260718` = 修复后）

**Kaggle 凭证**：`%USERPROFILE%\.kaggle\access_token`（API Token，非旧版 kaggle.json）

**注意**：kaggle CLI 2.x `datasets create` 有 `KaggleObject.from_dict()` bug，推荐 `--zip` 手动上传。
