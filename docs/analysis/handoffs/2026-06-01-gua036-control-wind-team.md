# Handoff: GUA-036 控权压顺 + 接风配合（M3 guard）

| 字段 | 内容 |
|------|------|
| 日期 | 2026-06-01 |
| 分支 | m-dev @ **31328b5**（GUA-036 **未 commit**，工作区有改动） |
| 状态 | **已结论待验证**（pytest 关单 pass；批跑 KPI / Git 推送待本机） |
| 真源 | [`ISSUES.md`](../../guandan-brain/ISSUES.md) §GUA-036、[`ITERATIONS.md`](../../guandan-brain/ITERATIONS.md) 最后一行 |

## 背景（2～3 句）

batch7（24 局批跑 vn `[1,2,1,2]`）round38 复盘定音：**①** yf2 接风拆 2 打单，未跟队友对子线；**②** 敌出杂顺可压却 PASS，夺权失败。**根因**是 M3 guard 缺口 + `_Straight` 过窄，**不是**缺顺子函数。GUA-036 用 pytest 构造态关单；**replay 仅作发现样例**，见 [`PRINCIPLES_MAPPING.md`](../../guandan-brain/PRINCIPLES_MAPPING.md) §复盘与验收理念。

## 已完成

- [x] **GUA-036 代码** — `src/m/m3/m3_decision_engine.py`
  - **CTRL-P01**：`_gua036_pick_min_straight_beat` — `actionList` 最小够用顺压敌；不依赖 `combine_handcards["Straight"]` 与 `action[-1]` 对齐
  - **CTRL-P02**：`_gua032_straight_degraded(..., passive_seize=True)` — 被动压敌顺豁免 CALC-M03
  - **拆炸不组顺**：`_gua036_straight_breaks_bomb` — 顺子占炸弹成员则跳过，改 `_gua029_try_bomb`
  - **WIND-P01 / TEAM-P01**：`_gua036_team_wind_pick` + `_gua036_teammate_last`（`_update_play_state` 记队友 Pair/Bomb）
  - **`_Straight` 重写**；**`_active`** 在 solo 接风之后插入团队接风分支
- [x] **测试** — `tests/test_m3_gua036.py` **6 passed**；GUA-026/029/031/032/034/035 回归 **42 passed**（本机 `pytest tests/test_m3_gua036.py tests/test_m3_gua031.py … test_m3_gua026.py`）
- [x] **文档关单** — `ISSUES.md` GUA-036 → **closed**；`ITERATIONS.md` / `guandan-brain/README.md` 已追加实施行
- [x] **batch7 复盘样例** — `replay_word.md` 已指向 batch7 round38（**不作 pass 标准**）

## 未完成 / 进行中

- [ ] **Git commit + push** — GUA-036 改动**尚未提交**（见下方「待提交文件」）
- [ ] **净盘 KPI 观测**（可选验收）— 9/12 局 M3 vs lalala，对比 GUA-034/035 后 **75.0%** / **88.9%** 样本是否稳定
- [ ] **V5+** — 整手组牌（222333+顺+炸）→ **V5+-04**，**不在 M3**

## 关键结论（有据）

| 结论 | 依据 |
|------|------|
| 108 张发 4 家两次完全相同 ≈ \(10^{-58}\) → **不能以逐步对齐某 replay 关单** | 用户定音 + `PRINCIPLES_MAPPING.md` §复盘与验收理念 |
| **拆炸不组顺**：压顺若占用炸弹成员 → 优先 Bomb | 用户举例 `78999910J`；GUA-026 同级 |
| batch7 根因 ① 接风拆 2 打单 → **WIND-P01 + TEAM-P01** | round38 yf2 步 37→41 |
| batch7 根因 ② 可压 9–K 顺却 PASS → **CTRL-P01** | round38 yf2 步 54→62 |
| Agent 初版「yf1 步 73 接风出 8888 炸」**非本轮 M3 范围** | batch7 复盘讨论；034/035 仅 solo |

## 待提交文件（GUA-036 核心）

| 路径 | 说明 |
|------|------|
| `src/m/m3/m3_decision_engine.py` | GUA-036 实现 |
| `tests/test_m3_gua036.py` | 新增 6 case |
| `tests/test_m3_gua032.py` | 被动夺权 + CALC-M03 flag 单测调整 |
| `docs/guandan-brain/ISSUES.md` | GUA-036 closed |
| `docs/guandan-brain/ITERATIONS.md` | 实施行 |
| `docs/guandan-brain/README.md` | 当前指挥更新 |

**勿混入无关改动**：`.vscode/`、`game_scores_m2.json`、`sync_github_mirror.ps1` 等若非本轮意图，提交前 `git add` 只选上表。

## 数据与产物位置

| 类型 | 路径 |
|------|------|
| 复盘样例 | `replay_word.md` → batch7 round38 |
| 牌谱 | `game_records/20260601191543981195 [yf1_m3]-…-[38]-[4].json`（yf1）；yf2 同批 match_key |
| 24 局批跑台账 | `execution_state.json` start **2026-06-01T19:06:51**；batch7 vn `[1,2,1,2]` |
| 真源 | `docs/guandan-brain/` |

## 相关 commit（已 push 的前序）

```
31328b5 feat(m3): GUA-035 END-M02+ opponent rest filtering
b29854d feat(m3): GUA-034 solo sprint END-M01–M04
```

## 下一步唯一动作

**提交并 push GUA-036**（仅核心文件），建议 commit message：

```text
feat(m3): GUA-036 passive straight seize + team wind guards
```

推送后可选：净盘 `--target-games 9` 填 `ITERATIONS.md` KPI 行（**不要求** batch7 再赢）。

## 不要重做

- 不要用 batch7 round38 逐步复现作 pass/fail 标准
- 不要在 M3 扩 `combine_handcards` 多顺槽 / 整手 222333+顺+炸规划（→ V5+-04）
- 不要重开 GUA-036 登记文档（已完成）；若改行为开 **GUA-037+**

## 新 Agent 第一句（复制）

```text
请先读 docs/governance/分析接续-handoff.md 和
docs/analysis/handoffs/2026-06-01-gua036-control-wind-team.md，
按「下一步唯一动作」提交 GUA-036 并 push；不要从零重做 pytest 已通过的逻辑。
```
