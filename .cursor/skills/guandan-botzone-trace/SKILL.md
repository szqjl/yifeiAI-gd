---
name: guandan-botzone-trace
description: >-
  分析 Botzone/OpenGuanDan 平台对局（无 game_records 落盘）某一出牌步的适配层链路：
  读 logs/v8_vs_botzone_*.log 的 actionList 摘要与 greater、复现 _classify_action 判型
  与 generate_follow_actions 候选，归类 R-B01～R-B08 根因，导向 GUA 与 pytest。
  Use when Botzone, 平台对局, 该压不压, 牌型误判, Free, actionList 候选缺失, WF-13,
  适配层, botzone_adapter.
---

# Botzone 平台对局适配层链路分析（WF-13）

## §0 强制检查表（未跑通禁止写结论）

每次分析前**必须**按顺序执行 `python scripts/checks/check_botzone_trace.py <日志> --by-cards <greater 牌面>`（或 `--step N`），脚本必须输出全 ✅ 才可继续。**任何 ❌ 立即停止，向用户报失败项；禁止凭记忆跳过**。

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 日志存在 + 含 `[botzone_adapter]` | 文件存在，含适配器行 |
| 2 | match 定局 | `--match` 前缀命中 ≥1 个 `stage=play` request |
| 3 | 目标摘要定位 | `--by-cards` 牌面反查成功，或 `--step` 序号合法 |
| 4 | actionList 摘要可解析 | `types=` 字典 + `greater=` 列表（领出 `None` 合法） |
| 5 | greater 判型标注 | `Free` = ⚠️ R-B01 判型 bug 信号（**不阻断**，是分析对象） |
| 6 | 决策行存在 | 日志含 `决策:` 或 `跟牌轮无可压动作` |
| 7 | 结论记录合规 | 追加进 `docs/guandan-brain/ITERATIONS.md`（不写 docs/analysis 报告） |

**禁止**：
- 不跑脚本就贴结论
- 跑出 ❌ 强行继续（必须先修复原因）
- 跑出 ✅ 后修改日志补数

## §0.1 一键运行（推荐 · 强约束）

```bash
# 按 greater 牌面反查（推荐，免疫「第 N 回合」口径差）
python scripts/checks/check_botzone_trace.py \
    logs/v8_vs_botzone_20260804_170909.log \
    --match 6a71ace3 --by-cards D2,C3,C4,D5,D6
```

可选参数：
- `--step N`：match 过滤后的第 N 条 actionList 摘要（先 `rg -n "actionList 摘要"` 数序号）
- `--iterations PATH`：指定 ITERATIONS.md 路径（合规检查，默认 `docs/guandan-brain/ITERATIONS.md`）

退出码：
- `0` = 全 ✅，可继续分析
- `1` = 有 ❌，禁止写结论，先修复

## 真源

完整步骤与模板：[`docs/guandan-brain/workflows/WF-13-botzone-decision-trace.md`](../../docs/guandan-brain/workflows/WF-13-botzone-decision-trace.md)

汇报格式：[`docs/guandan-brain/工作流.md`](../../docs/guandan-brain/工作流.md) §2.7

## 动手顺序（不可跳 · 已在 §0 检查表覆盖）

§0 检查脚本全 ✅ 后，按以下顺序继续：

0. 读 [`SCRIPT_INDEX.md`](../../docs/guandan-brain/SCRIPT_INDEX.md) §三 WF-13 行
1. 定位日志：`logs/v8_vs_botzone_YYYYMMDD_HHMMSS.log`（**Botzone 无 game_records**）
2. 读目标 request 的 `actionList 摘要`：`types` / `greater` / `must_play`
3. 读 `play request raw` 的 `history` 还原圈况（greater 出牌者 + 队友/对手 PASS）
4. 复现判型：`adapter._classify_action(<greater 牌面>)`（`_classify_action` 1015）
5. 复现候选：`ActionListGenerator(cur_rank).generate_follow_actions(hand, greater)`（297）
6. 对照摘要 types 差异 → 写 R-Bxx（§4 taxonomy）
7. 意图层（候选正常仍 PASS）→ 归 **R-B08**，转 WF-12 管线分析

## 适配层链路速记

```text
request(history) → 解析 greater(_bz_response_to_v8_action 判型)
→ must_play/接风判定 → generate_follow_actions(候选)
→ actionList(摘要打印) → 引擎 decide → 合法性防线 _beats → 决策
```

**关键信号**：`actionList 摘要.greater` 首元素 = `Free` ⇒ 判型 bug（R-B01），跟牌候选整型缺失；`greater` 正常但 `types` 缺牌型 ⇒ 候选生成分支缺失（R-B02）。

## 禁止

- 不读日志就下结论
- 把 `actionList 摘要.types` 当「我方全部可出牌」——它是**引擎候选**，缺失即根因信号
- 把整局口径的「第 N 回合」直接当日志摘要序号（先 `rg` 数或 `--by-cards` 反查）
- 改日志或牌谱

## 产出

- 给用户：`docs/guandan-brain/ITERATIONS.md` 新增一行（§6 记录模板）+ §2.7 格式汇报
- 可复现缺陷：`ISSUES.md` 新 GUA 或更新 open GUA + pytest 构造态（`tests/test_botzone_adapter.py`）
- 修后复验：重跑 `check_botzone_trace.py`（greater 从 Free 转正确类型）+ 相关 pytest
