# Agent 启动指南（Bootstrap）

> **新 Agent 第一句**：`阅读 docs/guandan-brain/AGENT_BOOTSTRAP.md`  
> 版本: v1 | 2026-06-06 | 本文件 + `AGENTS.md` = 新会话全部必读

---

## 1. 项目定位

| 项 | 内容 |
|----|------|
| **项目** | YiFeiAI-GD（掼蛋AI客户端），南京邮电大学掼蛋AI算法对抗平台 v1006 |
| **工作目录** | `d:\guandanscore\YiFeiAI-GD` |
| **Python** | 项目自带 venv（Windows Python 3.13） |
| **离线平台** | `guandan_offline_v1006.exe N`（N = 局数，非副数） |
| **WebSocket** | `ws://127.0.0.1:23456/game/{user_info}` |

### 两条开发线

| 引擎 | 分支 | 类型 | 核心文件 |
|------|------|------|----------|
| **M 系列** | `m-dev` | 硬编码规则引擎 | `src/m/m3/`、`yf1_m3.py`/`yf2_m3.py` |
| **V7** | `v7-dev` | 深度学习胜率引擎 | `src/decision/ultimate_win_rate_engine_v7.py`、`yf1_v7.py`/`yf2_v7.py` |

**当前状态**：
- **M3** = 主交付 + `IDecisionProvider` 底座（active）
- **M1 frozen**（GUA-022 closed）：仅 bugfix/协议/记录/pytest，**勿开 M1 策略 GUA**
- **V7** = 实验线（v7-dev），V7-001~V7-010 开发中

---

## 2. 核心概念（局/副/victoryNum）

### 三句定音（背这个就够开工）

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
| `[0,3,0,3]` | lalala 赢 3 局，M3 赢 0 局 |
| `[3,0,3,0]` | M3 赢 3 局，lalala 赢 0 局 |
| `[1,2,1,0]` | **不可信**（同队不一致） |

---

## 3. 改代码前必读顺序

1. **`docs/guandan-brain/ISSUES.md`** — open 条目，确认与本轮相关
2. **`docs/guandan-brain/ITERATIONS.md`** — 最新一行，确认目标与完成定义
3. **`docs/guandan-brain/TASKS.md`** — 当前活跃任务
4. **`docs/guandan-brain/EVAL.md`** — 评测入口与通过标准

### 按任务跳转

| 任务 | 必读 |
|------|------|
| 分析批跑胜率、填 ITERATIONS | `AGENTS.md` § 数据解读口径 + `platform-data-interpretation` §3.3 |
| 改 `yf*_m*.py`、落盘逻辑 | `guandan-platform-v1006` + `platform-data-interpretation` §3.4 |
| 改 **M3** 决策/策略 | `ISSUES` open（tag=`m3`）、`ITERATIONS` 最新行、`PRINCIPLES_MAPPING.md` |
| 改 **V7** 引擎 | `ISSUES` V7 段落、`V7-实施方案.md`、引擎入口 `ultimate_win_rate_engine_v7.py::decide()` |

---

## 4. 提交/推送检查清单

### 动手前

- [ ] 当前分支：`git branch -vv` → **`m-dev`** 或 **`v7-dev`**（非 main）
- [ ] 已 `git status` / `git diff --stat`，**未** `git add .` 盲加
- [ ] 未纳入 Layer 2：`game_scores_m2.json`、`game_records/`、`models/*.pth`、`logs/`

### Commit 规则

| 项 | 要求 |
|----|------|
| 前缀 | `[docs]` / `[M-m2]` / `[M-m3]` / `[V-nn-v7]` |
| 推送 | `git push origin m-dev` 或 `git push origin v7-dev` |
| 禁止 | 推 `main`、`--force`、跳过 hooks |

---

## 5. 关键路径映射

| 用途 | 路径 |
|------|------|
| **迭代大脑** | `docs/guandan-brain/` |
| **缺陷登记** | `docs/guandan-brain/ISSUES.md` |
| **迭代日志** | `docs/guandan-brain/ITERATIONS.md` |
| **评测标准** | `docs/guandan-brain/EVAL.md` |
| **平台协议** | `docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md` |
| **数据解读** | `docs/knowledge/platform-data-interpretation.md` |
| **M3 诊断** | `docs/guandan-brain/M3_DIAGNOSIS.md` |
| **原则映射** | `docs/guandan-brain/PRINCIPLES_MAPPING.md` |
| **V7 方案** | `docs/guandan-brain/V7-实施方案.md` |
| **仓库治理** | `docs/governance/M-V-Series-治理方案.md` |
| **牌谱回放** | `scripts/tools/yf_replay.py` / `YF_REPLAY.bat` |

---

## 6. 常用命令

```bash
# 切分支
git checkout -f v7-dev

# 推送
git push origin v7-dev

# V7 启动
start_v7_gui.py          # Linux
START_V7_GUI.bat         # Windows GUI 对战
START_V7_AUTO.bat        # 自动启动服务器+客户端

# V7 vs lalala 批跑
venv\Scripts\python.exe scripts\launchers\v7\run_v7_vs_lalala_games.py --games 3
venv\Scripts\python.exe scripts\launchers\v7\run_v7_vs_lalala_games.py --games 12
# 战绩文件：v7_vs_lalala_scores.json
# M3 批跑：m3_vs_lalala_scores.json
# M1 批跑：game_scores.json

# 牌谱回放
YF_REPLAY.bat
python scripts/tools/yf_replay.py

# 测试
python tests/test_v7_engine_load.py
```

---

## 7. 协作原则

1. **短任务短 prompt**：单个提示词 <= 40 行
2. **长任务拆回合**：拆成多个短任务串行调度
3. **一个回合一个目标**：做完验证关单再开下一个
4. **不传信任**：子 Agent 报告的结果必须验证
5. **产出验证优先**：任何声称修复/完成的，必须读文件确认
