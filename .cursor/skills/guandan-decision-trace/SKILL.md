---
name: guandan-decision-trace
description: >-
  分析 yf1/yf2 某一出牌步的完整决策链路：读 game_records my_decisions、
  客户端日志 GUA-075/残局/Guard/heuristic，还原 decide() 管线，归类 R-D01～R-D08 根因，
  导向 GUA 与 pytest。Use when 决策链路, 为何出这手, yf 出牌分析, WF-12,
  我方不胜, 败招根因, actIndex, GUA-075 拦截.
---

# yf 决策链路分析（WF-12）

## §0 强制检查表（未跑通禁止写结论）

每次分析前**必须**按顺序执行 `python scripts/checks/check_decision_trace.py <game_records_file> <step>`，脚本必须输出所有 ✅ 才可继续。**任何 ❌ 立即停止，向用户报失败项；禁止凭记忆跳过**。

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 牌谱 JSON 存在 + 可解析 | 文件存在，`json.load()` 无异常 |
| 2 | 玩家标识对齐 | yf1→`player_id==0`，yf2→`player_id==2` |
| 3 | 步号合法性 | `1 <= step <= len(actions)` |
| 4 | 步号归属正确 | `actions[step-1].cur_pos == player_id`（否则该步非分析对象出牌） |
| 5 | `my_decisions` 至少 1 条 `play` 决策 | `find_decision_at_step` 不抛 `no play my_decisions` |
| 6 | ordinal + action_key 双校验通过 | decision.action 与 actions[step-1].cur_action 一致 |
| 7 | yf2 必须配对 yf2 JSON | 同 `[round]-[suffix]`，非 yf1 game_id |
| 8 | 客户端日志存在 | `logs/yf{1\|2}_*.log` 至少 1 个匹配 start_time |
| 9 | 报告路径合规 | 写到 `docs/analysis/WF-12-<game_id>-<副序>-<yf>-<主题>.md` |

**禁止**：
- 不跑脚本就贴结论
- 跑出 ❌ 强行继续（必须先修复原因）
- 跑出 ✅ 后修改牌谱或日志补数

## §0.1 一键运行（推荐 · 强约束）

```bash
# 必须显式指定步号；yf1/yf2 由文件名 client 段自动判定
python scripts/checks/check_decision_trace.py \
    "game_records_v8/20260721083150239049 [yf1_v8]-[opponent_1_3]-[1]-[2].json" \
    --step 14
```

可选参数：
- `--no-pair-check`：yf1 模式跳过 yf2 配对（默认 yf2 必须配对）
- `--report-path PATH`：指定输出报告路径（默认按 §5 命名规则）

退出码：
- `0` = 全 ✅，可继续写报告
- `1` = 有 ❌，禁止写结论，先修复

**禁止**：
- 不跑脚本就贴结论
- 跑出 ❌ 强行继续（必须先修复原因）
- 跑出 ✅ 后修改牌谱或日志补数

## 真源

完整步骤与模板：[`docs/guandan-brain/workflows/WF-12-yf-decision-trace.md`](../../docs/guandan-brain/workflows/WF-12-yf-decision-trace.md)

汇报格式：[`docs/guandan-brain/工作流.md`](../../docs/guandan-brain/工作流.md) §2.6

## 动手顺序（不可跳 · 已在 §0 检查表覆盖）

§0 检查脚本全 ✅ 后，按以下顺序继续：

0. 读 [`SCRIPT_INDEX.md`](../../docs/guandan-brain/SCRIPT_INDEX.md) §三 WF-12 行
1. **yf1**：开人类给的 `*yf1_*` JSON；**yf2**：§2.1 配对 `*yf2_*` JSON（禁止用 yf1 game_id）
2. §2.2 用 **`find_decision_at_step`**（ordinal + `action_key` 双校验）→ `my_decisions.context.handCards` / `curRank`；勿全表搜 action
3. `actions[]` 还原圈况
4. `logs/yf{1|2}_*.log` 搜 ±1s 补管线证据
5. 写命中层 / R-Dxx

## V7 管线速记

组牌 → 信念 → **残局** → **GUA-075** → mask 拦截? → Guard → 组牌过滤 → NN → heuristic

**关键**：`GUA-075 主路径 ✅` = L2 成功；仅有 `推荐被组牌保护拦截` = L2′ 失败 → 必写回退路径。

## 禁止

- 不读日志就下结论
- **分析 yf2 未配对 yf2 JSON，或把 `cur_action` 当整手**
- 用单局 replay 逐步一致作关单标准
- 改牌谱

## 产出

- 给用户：§2.6 格式报告
- 可复现缺陷：`ISSUES.md` 新 GUA 或更新 open GUA + `issues/GUA-xxx-completion.md`
- 可选：`replay_word.md` 追加典型步摘要
