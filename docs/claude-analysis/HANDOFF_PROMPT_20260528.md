# 接力提示词 — 给下一个 Agent

> 用法：把下面分隔线之间的内容整段贴给新的 Claude / Cursor / 其他 agent 即可接续推进。
> 生成时间：2026-05-28（修复了离线平台 4 客户端联调和 Python 环境陷阱之后）

---

我在做掼蛋 AI 项目（`D:\guandanscore\YiFeiAI-GD`），当前分支 `m1-dev`。
昨天 (2026-05-28) 完成了 P0 四项改进的实施 + 离线平台联调，今天接续往下推进。

## 必读上下文（按顺序）

1. `CLAUDE.md`（项目根，约定、目录结构、分支策略）
2. `C:\Users\Jennifer\.claude\projects\D--guandanscore-YiFeiAI-GD\memory\MEMORY.md`
   特别是这两条记忆，避免重复踩坑：
   - `python-environment-warning.md`：项目依赖装在 Python 3.13，必须用 `python` 不能用 `py`/`sys.executable`
   - `platform-4-clients-required.md`：离线平台必须 4 客户端连满才发 act 请求
3. `docs/claude-analysis/P0_IMPLEMENTATION_COMPLETE_20260528.md`（P0 实施清单）
4. `docs/claude-analysis/decision_patterns_sample.md`（最近 30 局决策模式抽样）

## 已验证可跑的入口（不要再写新的启动脚本）

- 一键自动化对战 + P0 验证：
  ```
  cd D:/guandanscore/YiFeiAI-GD
  python tests/test_p0_4clients.py
  ```
  脚本会：监听 `Ready for connect.` → 启 4 客户端 → 跑 `NUM_GAMES=3` 局 → 解析日志统计【P0改进①②③④】触发数。
  默认 `NUM_GAMES=3`，要跑大批量改 `test_p0_4clients.py` 顶部的 `NUM_GAMES` 即可。

- GUI 批量对战：`python batch_executor_gui_m1.py`（`START_M1_GUI.bat` 已修，启动器是 `python` 不是 `py`）

- 决策模式提取（M1/M2/M3 自适应）：
  ```
  python scripts/analyze_decisions.py --top-n 50 --md docs/claude-analysis/decisions_<date>.md
  ```

## 当前实测数据（2026-05-28 10:07 跑完批量 NUM_GAMES=30 → 20 局）

完整报告：`docs/claude-analysis/batch30_p0_trigger_vs_winrate_20260528.md`

- yf1_m1: 499 决策 / PASS 49.1% / 31 炸弹（1.55/局）
- yf2_m1: 493 决策 / PASS 48.9% / 25 炸弹（1.25/局）
- 胜负：我方 0 胜，对手 3 胜（victoryNum=[0,3,0,3]），无平局
- P0②：yf1=4 / yf2=4（**对称**，昨日不对称属小样本方差，候选 B 可排除）
- P0①③④：20 局 0 触发（分支冷，下一步需诊断）
- ⚠️ 新发现：平台 `NUM_GAMES` **不是局数**，30 → 实际只跑 20 局。见 memory `platform-num-games-not-round-count.md`

## 下一步候选任务（让用户选一项执行，不要全做）

**A. ~~跑 30~50 局大批量对战，统计 P0①②③④ 各自触发率与胜率~~ ✅ 已完成 2026-05-28**
- 见 `docs/claude-analysis/batch30_p0_trigger_vs_winrate_20260528.md`

**B. ~~排查 yf1/yf2 P0 触发不对称~~ ✅ 已排除（20 局后对称）**

**C. 推进 P1（强化学习 / 对手建模）**
- 见 `docs/claude-analysis/05-root-cause-analysis.md`

**D. M1 PASS 率仍 ~49% + 0 胜场，调主动出牌策略（最优先）**
- 重点看 `docs/skill/出炸弹要领.txt` 和 `doc/M2_OPTIMIZATION.md` "极端被动" 节
- 同样的根因可能存在于 M1 的 `OpeningActiveHandler` / `MidEarlyActiveHandler`

**E. P0①③④ 死路诊断（新增，与 D 可并行）**
- 三个分支在 20 局/992 决策中 0 触发，需先在 handler 入口加无条件 INFO 日志，再跑一批看是否能进入函数体；若进得去但条件不满足，再针对性放宽阈值。

## 硬性约束

- 时间不要硬编码，全部 `datetime.now()`
- 不要再启动只有 2 个客户端的"测试脚本"（旧的 `test_p0_single_game.py` / `test_p0_correct.py` 是错的，不要复用）
- 改决策逻辑前先读 `docs/guandan-brain/README.md`
- 用户偏好简洁回答，不要写长篇总结，不要走代码风格清理这种附带工作

请先告诉我你打算做 A/B/C/D 哪一项，再开干。

---

## 维护说明

- 当 P0 触发率/胜率有新数据时，更新本文件 "当前实测数据" 节
- 当下一步任务被完成或废弃时，从候选列表中移除
- 当发现新的环境陷阱时，加到 "硬性约束" 节，并同步写入 `~/.claude/projects/.../memory/`
