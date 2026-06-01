# 本机评测清单（须由你执行）

> **让 AI 根据本轮评测改决策**：复制 **[PROMPT_FOR_DECISION_FIX.md](PROMPT_FOR_DECISION_FIX.md)** 中的整段说明到对话里即可。

> **仓库里的「大脑」文档**（`ISSUES` / `ITERATIONS` / `EVAL` / `scenarios`）可在 Git 中维护；**以下步骤依赖本机离线服务器、窗口环境与真实对局**，须由你在本仓库 **Git 根目录**（当前主工作仓：`c:\yifeGDBOT`）**亲自执行**。  
> 当前轮次若针对 **GUA-021（减少问题 PASS）**：改代码 → 跑对局 → 把统计结果写回 **`ITERATIONS.md`** 对应行。

## 1. 环境

- [ ] Python 可用（`py` / `python`）  
- [ ] 离线服务器 **`guandan_offline_v1006.exe`** 路径已就绪（与 `EVAL.md` / GUI 默认探测一致）  
- [ ] 分支与任务一致（M1 相关建议 **m-dev**）

**说明**：离线服 **`guandan_offline_v1006.exe`** 可能已出现在你的工作区（常见为 `server/guandan_offline_v1006.exe`，或你从平台包解压/复制到任意路径）；也可能**未**纳入 Git、仅在本机某绝对路径——二者都正常。在 GUI 中选对该 exe，或无头 CLI 使用 `--server-path "<路径>"`。**IDE 里的助手**未必能索引到该二进制（忽略规则、沙箱或未同步），故仍以**你本机实际存在的路径**为准；`scripts/gui/batch_executor_gui_m1.py` 的 `possible_paths` 会依次探测若干默认位置。

## 2. M3 批量对战（主交付 · 产出 `game_records`）

**局数档位**（`--target-games` **须为 3 的倍数**，见 [`EVAL.md`](EVAL.md)「批跑局数档位」）：

| 档位 | 局数 | 用途 |
|------|------|------|
| 小批 | **3** | 改代码后快速验证 |
| 中批 | **9** | 策略改动稳定性 |
| 大批 | **12** | 队胜率 KPI / 关单 |

```bash
python -m batch_executor --server-path "<SERVER_EXE>" --target-games 12 \
  --clients src/communication/yf1_m3.py src/communication/run_lalala_client3.py \
            src/communication/yf2_m3.py src/communication/run_lalala_client4.py
```

净盘：跑前清空 `game_records/*.json`。批末 **`victoryNum[0]+[1]` = 该批 `batch_games`**（整批为 3 的倍数时各批均为 3，无尾批 fallback）。

## 2b. M1 批量对战（frozen · 仅回归）

任选其一：

1. **GUI**：`START_M1_GUI.bat` 或 `python scripts/gui/batch_executor_gui_m1.py`  
2. **无头 CLI**：`scenarios/client_sets.json` 的 **`m1`** 四客户端；局数仍须 **3 的倍数**。

跑够 **`ITERATIONS.md`** 里本轮写的场次。

批量执行器在跑完后应满足：`execution_state.json` 的 `target_games` 与本次 `--target-games` 一致，**`completed_games` = 平台批次数累计**（非 `game_records` 文件数）；JSON 内 **`victoryNum` 为四座位累计胜场，不是局数**。落盘 PASS 分析可用成对 match key `(opponent, round, level)` 或 M1 成对 `game_id`。若单局极慢仍被误杀，可在运行前设置环境变量 `BATCH_EXECUTOR_SECONDS_PER_GAME_ESTIMATE`（默认 720）或 `BATCH_EXECUTOR_MIN_BATCH_SECONDS`（默认 180），见 `batch_executor/README.md`。

## 3. 诊断（可选、推荐先做）

```bash
python -m batch_executor --server-path "<SERVER_EXE>" --diagnose-only
```

## 4. 改完代码后的动作

1. 重复 §2，生成**新** `game_records`。  
2. 用与 **`EVAL.md` / `M1_yf1_vs_yf2_comparison.md`** 一致的口径统计 **近似问题 PASS**（`actionList_size>1` 仍选 PASS）。  
3. 更新 **`ITERATIONS.md`**：日期、改动摘要、评测结果摘要、是否关闭 **GUA-021**。  
4. 若指标达标，在 **`ISSUES.md`** 将 **GUA-021** 标为 `closed` 并写 `closed_in`。

## 5. 我（助手）在仓库里**不能**替你完成的

- 启动 Windows 离线 exe、点 GUI、连真实 WebSocket 对局  
- 读取你本机尚未提交到工作区的 `game_records` 新文件（除非你已保存到仓库路径并让我读）

---

**结论**：文档与台账由我（或你在 IDE 里）维护；**跑评测 = 你的本机动作**。完成一轮后把数字写回 **`ITERATIONS.md`** 即可闭环。
