# 本次会话工作总结 — 2026-05-28 / 29

## 快速概览

✅ **核心翻案：昨日 "可能是平台 bug" 结论被证伪**
- 真根因 = ① Python 环境错位（py→3.14 缺 websockets） ② 旧 test 脚本只启 2 客户端（PDF 要 4 个）
- 离线平台 v1006 完全正常，3 局对战一次跑通，决策入口 562/567 次，P0②触发 6 次

✅ **selfRank/oppoRank/curRank 字段恢复**
- recorder 历史漏写，新代码已补；yf_replay 多级 fallback 兼容旧记录
- 实测新记录 `curRank='A'` 与对手已升 A 级吻合

📊 **工作量统计**
- 新建文件：3 个（`tests/test_p0_4clients.py`、`scripts/analyze_decisions.py`、`docs/analysis/agent-sessions/HANDOFF_PROMPT_20260528.md`）
- 修改文件：5 个（`yf1_m1.py`、`yf2_m1.py`、`scripts/tools/yf_replay.py`、`START_M1_GUI.bat`、`docs/README.md`）
- 远程提交：`126b573 feat(yf_replay): ...` 已 push 至 origin/m-dev
- 新增 memory：`python-environment-warning.md`、`platform-4-clients-required.md`

---

## 1️⃣ 离线平台不发出牌请求 — 翻案

**昨日错误结论**（来自 `P0_IMPLEMENTATION_COMPLETE_20260528.md` § 六 / `P0_DIAGNOSIS_20260528.md`）：
> 离线平台 v1006 在所有客户端连接后仍不发送出牌请求（可能是平台 bug 或特定配置）
> 无法在自动化脚本中完整验证游戏交互

**今日证伪 — 两层伪装**：

| 层 | 实际原因 | 证据 |
|---|---|---|
| 表层 | 旧 `test_p0_single_game.py` / `test_p0_correct.py` 只启 yf1_m1 + yf2_m1 两个客户端 | PDF 第 2 页明文："连满 4 人之后游戏将自动开始" |
| 深层 | 改为启 4 客户端后仍崩 → 因为 `sys.executable` 被 `py.exe` 解析到 Python 3.14（裸环境缺 websockets），4 客户端瞬间全部 `ModuleNotFoundError` | 各客户端 stdout 落盘后清晰可见 traceback |

**修复**：
- `tests/test_p0_4clients.py` 强制走 Python 3.13 (`_resolve_python()`)、监听 `Ready for connect.`、启动 4 客户端（yf1_m1 + lalala_client3 + yf2_m1 + lalala_client4），每客户端 stdout 独立落盘
- `START_M1_GUI.bat` 启动器从 `py` 改为 `python`

**实测**：2026-05-28 09:27 跑完 3 局 → `gameOver, curTimes:3, settingTimes:3` 正常退出。后续 20 局批量跑（NUM_GAMES=30 实际 20 局），见 `batch30_p0_trigger_vs_winrate_20260528.md`。

**沉淀**：
- memory `python-environment-warning.md` — 任何入口禁用 `py.exe` / `sys.executable`
- memory `platform-4-clients-required.md` — 平台必须 4 客户端连满

---

## 2️⃣ selfRank/oppoRank/curRank 字段恢复

**发现**：M1 game_records 中 `my_decisions[].context` 缺级牌字段，导致 `yf_replay` 永远显示默认 '2' 级。

**三层 context 路径**（详见 [docs/README.md](../README.md#🔧-已知字段约定--近期修复)）：

| 字段位置 | 写入函数 | 现状 |
|---|---|---|
| `game_info` | `start_game()` 入参 | 调用方传 None |
| `actions[].context` | `notify/play` 广播 data | 广播消息不含级牌 |
| `my_decisions[].context` | yf1_m1.py:381 / yf2_m1.py:385 自建 | **漏塞 selfRank/oppoRank/curRank** ❌ |

**修复**：
- `yf1_m1.py:385-391` / `yf2_m1.py:385-391` 在 `decision_context` 补 3 字段（从 act 消息 data 直接取）
- `scripts/tools/yf_replay.py:498-527` `_resolve_levels` 改三层 fallback：`game_info → my_decisions → actions`

**实测**：2026-05-29 跑的新记录 `20260529003420492436 [yf1_m1]-[25].json` → `selfRank='2', oppoRank='A', curRank='A'`（对手已升 A，与昨日 0 胜结论一致）。旧 4000+ 个 None 文件仍 fallback 到 '2'，向后兼容。

---

## 3️⃣ 决策模式提取工具

**新增**：`scripts/analyze_decisions.py`（约 170 行）

- 自动识别 M1/M2/M3 三种 JSON 结构（`actions[]` vs `my_decisions[]`）
- 输出每玩家：决策数、PASS率、炸弹数 / 首炸时机 / 被动率 / 牌型分布
- 可选 `--md OUT.md` 写 markdown 报告

**首次抽样**（最近 30 个文件）：
- yf1_m1: 50.7% PASS 率, 1.60 炸弹/局
- yf2_m1: 51.6% PASS 率, 0.93 炸弹/局

20 局 batch30 后细化数据见 `batch30_p0_trigger_vs_winrate_20260528.md`。

---

## 4️⃣ yf_replay 功能改动 & 独占提交

**改动**（+97 / -44 行）：
- 主窗口固定为 1280×920
- canvas 绑定 `<Configure>`，尺寸变化时整副重绘
- 对局列表按文件 mtime 倒序，最新置顶
- `_resolve_levels` 三层 fallback（见 §2）
- 四座位牌面与级牌标签布局微调

**提交链**（均已 push 至 `origin/m-dev`，HEAD = 8826755）：

| commit | 内容 | 范围 |
|---|---|---|
| `126b573` | feat(yf_replay): 窗口尺寸/响应式重绘/级数 fallback/座位布局微调 | scripts/tools/yf_replay.py |
| `7f18ac9` | docs: yf_replay 结案同步 handoff/治理方案，docs/README 级数字段约定 | docs/README.md + handoff 文档 |
| `8826755` | fix(M-m1): decision_context 写入级数字段，清理根目录测试脚本 | yf1_m1.py / yf2_m1.py + 删 `_test_*.py` 等 |

---

## 5️⃣ 接力提示词

新增 `docs/analysis/agent-sessions/HANDOFF_PROMPT_20260528.md`，自包含给下个 agent 的提示词；后续叠加了 batch30 数据并把候选 A/B 标记完成。

---

## 6️⃣ 仍未提交的本地改动

> 截至本 summary 提交时（HEAD = 8826755）工作区残留：

- `.batch_executor.lock` — 工作目录运行残留（每次跑都会变，建议加 .gitignore）
- 新增脚本/记录文件（untracked）：
  - `scripts/analyze_decisions.py`（决策模式提取工具，§3）
  - `tests/test_p0_4clients.py`（4 客户端验证脚本，§1）
  - `docs/analysis/agent-sessions/decision_patterns_sample.md`
  - `docs/analysis/agent-sessions/decisions_20260528_batch30.md`
  - `moe_training/`
  - `src/communication/Test_N1.py` / `Test_N2.py` / `Test_V1.py` / `Test_V2.py`
  - `src/decision/test_stage1.py`
  - `src/test_modules.py`

这些建议下一会话**先判定去留**再决定提交：`analyze_decisions.py` / `test_p0_4clients.py` 是已经被 HANDOFF_PROMPT 引用的入口，应该尽快提交；`Test_*.py` / `test_stage1.py` 不清楚是不是临时调试脚本。

---

## 待办（按 HANDOFF_PROMPT 候选）

- **C. 推进 P1（强化学习 / 对手建模）**
- **D. M1 PASS 率仍 ~49% + 0 胜场，调主动出牌策略**（最优先）
- **E. P0①③④ 死路诊断**（20 局 0 触发，handler 入口加无条件 INFO 后再跑一批）

参见 [HANDOFF_PROMPT_20260528.md](HANDOFF_PROMPT_20260528.md)。

---

**生成时间**：2026-05-29
**会话覆盖**：2026-05-28 凌晨 → 2026-05-29 凌晨
