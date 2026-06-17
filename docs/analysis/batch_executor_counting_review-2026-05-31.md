# batch_executor 计数口径评审报告

| 字段 | 内容 |
|------|------|
| 日期 | 2026-05-31 |
| 评审问题 | `--target-games 10` 在当前实现下究竟表示什么？为何 `completed_games=10` 与仅 1 批平台会话、`victoryNum` 读数矛盾？ |
| 结论 | **问题确认：是**（实现与文档、用户期望、ITERATIONS 口径均不一致） |
| 范围 | `batch_executor/executor.py`、规则文档、`game_recorder`、历史 ITERATIONS 批跑行 |
| 本轮 | **仅评审，不改代码** |

---

## 1. 术语对齐

| 术语 | 平台 / 规则含义 | `game_records` 含义 | `--target-games` **应**指 |
|------|-----------------|---------------------|---------------------------|
| **平台「游戏次数」** | 离线 exe `N` → `settingTimes=N`：**N = 局数**（一次「游戏」= 一方 A 级双上过关，内含多副）；**N ≠ 副数**。见 [platform-data-interpretation.md](../knowledge/platform-data-interpretation.md) §2 实测 | — | 一批平台会话内的 **局数** 上限（≤3） |
| **一副 / episode** | 108 张发完 → 多圈出牌 → `episodeOver` | 客户端每开一新副记录时 `game_counter+=1`，写入文件名 `[game_round]` | **不**等于 executor 的一「场」 |
| **game_id**（文件名前缀） | — | 各客户端 `datetime.now()` 微秒时间戳，**yf1/yf2 几乎永不相等** | 仅当两客户端 id **完全相同**时才算 1 对（M1 历史上偶发；M3 实测 **0 对**） |
| **game_round**（文件名） | — | 进程内单调递增计数，**≠ 平台 curTimes**；一次 3 副会话可产生远多于 3 的 round 文件（多次 save / 多副 / 计数语义混用） | **不应**作为 `target_games` 主计数 |
| **victoryNum** | `gameResult` 四座位**累计胜场**（整段平台会话或更长） | 写入 JSON `result` | **不是**「跑了几局/几副」；`[3,0,3,0]` 表示 0+2 队累计 3 胜，**不能**用 `3` 推断只跑了 3 副 |

**文档口径（设计意图）**：

- `batch_executor/README.md`、`LOCAL_EVAL_CHECKLIST.md`、`EVAL.md`：**一局 = 成对 `game_id`（yf1 + yf2 同 id 各一份 JSON）**。
- `executor.py` 注释（L29–31）写 GUA-022 / ITERATIONS 同口径，但 L75 实现为 `max(成对 game_id, 成对 game_round)`，**与 README 矛盾**。

**用户期望（合理）**：`--target-games 10` = **10 次可评测单元**，且平台单次最多 3 副 → **约 4 批重启**（3+3+3+1），`restart_count≥3`。

**当前实现实际语义**：`--target-games 10` ≈ **「本 Run 新增成对 game_round 数 cap 到 10」**（M3 上 game_id 成对为 0 时完全退化为 round），**不是** 10 次平台会话，也 **不是** 10 个成对 `game_id`。

---

## 2. 计数逻辑审计

### 2.1 `_count_new_paired_games`（`executor.py` L38–75）

```python
return max(len(by_id_p1 & by_id_p2), len(by_round_p1 & by_round_p2))
```

- **game_id 支**：要求 yf1/yf2 **相同时间戳前缀** → M3 实测 **0**。
- **game_round 支**：仅要求 yf1/yf2 文件名中 **`[round]` 字符串相同**（L63–69），**不**校验 opponent/level，**不**使用 GUA-025 的 `opponent+round+level` 匹配键。
- 取 **max** → 任一侧达标即抬高 `session_done`。

### 2.2 `_sync_completed_from_game_records`（L434–455）

- `session_done = _count_new_paired_games(...)`
- `state.completed_games = min(session_done, target_games)` → **累计封顶**，非增量。
- **不区分**本批新增与历史；批间靠 baseline 文件集排除旧文件。

### 2.3 主循环退出（L610、L976–1001）

- 条件：`while state.completed_games < state.target_games`
- 每批结束 `_sync_completed_from_game_records`；若 `completed_games >= target_games` → **不再重启**。
- `restart_count` **仅**在 `completed_games < target_games` 时 +1（L997）→ 第一批 sync 到 10 则 **`restart_count` 永为 0**。

### 2.4 批内提前结束（L833–851）

- 等待循环内再次调用 `_count_new_paired_games`；若 `session_done - batch_start_completed >= batch_games` → 标记批次完成。
- 当 round 对数虚高时，**平台尚未输出「达到设定」** 也可能提前 terminate → 与真实 `settingTimes` 进一步脱钩。

### 2.5 判断：第一批 3 副会话会否满足 `target_games=10`？

**会。** 用户观测（39 对 round → cap 10）与代码完全吻合：

1. 平台只跑 **batch_games=3** 的一会话；
2. 落盘 78 JSON = **39 对 round**（`max(0, 39)=39`）；
3. `min(39, 10)=10` → `completed_games=10`，循环退出；
4. `restart_count=0`，日志仅「批次 1，游戏场数: 3」。

**2026-05-30 M3 批跑**（ITERATIONS L54–56）同样可疑：~54s 完成「10/10」、仅 batch 1，口径写「成对 round（10）」——与 **未真正跑满 4 批平台会话** 一致。

---

## 3. 与历史 ITERATIONS 的一致性

| 时期 | 计数方式 | 是否可信 |
|------|----------|----------|
| **2026-04-21 M1 GUA-020/022** | 人工统计 **成对 `game_id`（10）**；`completed_games=10` 与 id 列表一致 | **样本量口径可信**；队胜率 0/10 指 **10 个 id 文件内 victoryNum** |
| **2026-05-25** ITERATIONS「成对计数补 **game_round** 口径」 | 引入 `max(id, round)` | M1 若 id 成对≥10，**仍可用**；为 M3 埋下雷 |
| **2026-05-30 M3 GUA-027/028/026 批跑** | 显式「成对 **round**（10）」、32 文件/16 round、54s | **`completed_games=10` / 「10 局」不可信**；实际 ≈ **1 平台会话（3 副）+ 多份 round 落盘** |
| **2026-05-31 用户净盘复现** | 39 round 对、0 game_id 对、restart 0 | **确认缺陷** |

**哪些指标仍可参考？**

| 指标 | 可信度 | 说明 |
|------|--------|------|
| **PASS 率、炸弹 send 次数、ThreeWithTwo 次数** | **中** | 对 **已落盘 JSON 内决策** 的统计仍有效；但样本是「39 副」而非「10 次独立评测」，**方差/独立性被误解** |
| **队胜率「0/10」** | **低** | 分母「10」错误；`victoryNum` 为 **累计胜场**，不是局数 |
| **GUA-029「炸弹已出」** | **高** | 日志 send 计数不依赖 completed_games |
| **pytest（GUA-026/029 等）** | **高** | 与 executor 计数无关 |

**结论**：M3 近期批跑在 ITERATIONS 中写「10/10 完成」的行，**完成度结论应标注无效**；策略类指标需按 **实际 JSON 条数 / 实际平台批次数** 重述，不宜写「10 局样本」。

---

## 4. 修复方案比较

### 方案 A：按平台会话进度计数（推荐为 **executor 台账主口径**）

- **做法**：每批服务器正常结束（「达到设定」或进程退出且非强杀）→ `completed_games += batch_games`（最后一批加剩余）；**不再**用 `max(round,id)` 驱动主循环。
- **game_records**：仅作校验 / 分析，不参与 `completed_games` 封顶。
- **优点**：与用户「3+3+3+1」一致；`restart_count` 自然正确；改动面集中在 `executor.py`。
- **缺点**：若客户端崩溃但服务器跑满，台账与落盘可能不一致（可日志告警）。

### 方案 B：只数成对 `game_id`（文档原意）

- **做法**：删除 round 分支；强制 yf1/yf2 **共享 match_id**（recorder 用平台字段或共享 UUID）。
- **优点**：与 EVAL / GUA-020 完全一致。
- **缺点**：需改 **game_recorder + 客户端**；历史文件名不兼容；M3 当前 0 对会卡死进度。

### 方案 C：成对 match key（GUA-025 键）+ 每平台会话封顶（推荐为 **ITERATIONS 分析口径**）

- **做法**：计数 = 本 Run 新增 **唯一 `(opponent, round, level)` 且 yf1/yf2 各至少一份** 的键数；**可选**每批 sync 增量 ≤ `batch_games`（防止一 session 多副溢出）。
- **优点**：不依赖 game_id 微秒对齐；与 merge 逻辑一致。
- **缺点**：round 仍为客户端计数，**不能**等于平台 settingTimes；需 **方案 A** 配合作为 executor 主计数。

### 方案 D：改 CLI 语义为「成对 round 数」

- **做法**：`--target-games` .rename → `--target-round-pairs`。
- **优点**：诚实反映现状。
- **缺点**：与 EVAL/ISSUES/GUA-020/022 **全面冲突**；不能解决「用户要 10 次平台会话」需求。**不推荐单独采用**。

### 推荐组合

**A（主进度）+ C（落盘校验与 ITERATIONS 统计）+ 文档澄清 victoryNum**

1. 主循环：`completed_games` 按 **累计 batch_games**（强杀批次不加）。
2. `_sync_completed_from_game_records`：改为 **日志报告** `paired_id / paired_match_key / round` 三指标，**不 cap 主进度**（或仅作异常检测：单批 match_key 增量 ≫ batch_games 时 WARN）。
3. 删除 L833–851 用 round 对数 **提前结束批次** 的逻辑，或改为仅识别平台 stdout。
4. 文档：`README.md`、`EVAL.md`、`LOCAL_EVAL_CHECKLIST.md` 各加 **victoryNum 释义** 与 **双指标**（平台批次数 vs 落盘副数）。

---

## 5. 验收标准（修复后）

| # | 标准 |
|---|------|
| 1 | 净盘 + `--target-games 10` + `single_run_limit=3` → **`restart_count >= 3`**，**`current_batch >= 4`**（或日志 4 次「开始批次」） |
| 2 | `completed_games == 10` **且** 累计 `batch_games` 之和为 10（与平台 settingTimes 累计一致） |
| 3 | 日志每批打印：`batch_games`、`completed_games`（台账）、`new_match_keys`（落盘，可选） |
| 4 | 文档明确：`victoryNum[i]` = 座位 i **累计胜场**，不是副数/批次数 |

**复现命令（修复前/后对比）**：

```powershell
Remove-Item game_records\*.json -Force -ErrorAction SilentlyContinue
python -m batch_executor --target-games 10 `
  --server-path "offline_platform\guandan_offline_v1006\windows\guandan_offline_v1006.exe" `
  --clients src/communication/yf1_m3.py src/communication/run_lalala_client3.py `
            src/communication/yf2_m3.py src/communication/run_lalala_client4.py
```

**修复前预期**：`restart_count=0`，round 对 >> 10，`completed_games=10`。  
**修复后预期**：`restart_count=3`，4 批；落盘副数可 >10，但台账 `completed_games` 仅随平台批次数增长。

---

## 6. 测试建议

| 项 | 建议 |
|----|------|
| **新增** `tests/test_batch_executor_counting.py` | **需要**。用 `tmp_path` 伪造 `game_records` 文件名，覆盖：仅 round 无 id、39 round cap 10、M1 式同 id 等；**不启真实 exe**。 |
| **`tests/test_game_recorder_merge.py`** | **相关**：提供 `(opponent, round, level)` 配对范例；可抽 **共享 match_key 计数函数** 与 merge 同源。 |
| **`tests/test_batch_executor_integration.py`** | 仅测初始化，**不覆盖**计数；保留。 |

---

## 7. 根因链（摘要）

```
平台 1 会话 settingTimes=3（3 副）
  → 客户端多次落盘，game_id 不对齐，game_round 同步递增至 39 对
  → _count_new_paired_games = max(0, 39) = 39
  → _sync_completed_from_game_records: min(39, 10) = 10
  → while 条件失败，restart_count 不递增
  → 用户见 completed_games=10 但仅 1 批、victoryNum 像「3」的累计胜场
```

**引入点**：2026-05-25 ITERATIONS「成对计数补 game_round 口径」+ `max()` 逻辑（L75）+ M3 无成对 game_id。

---

## 8. 给用户的三句话

1. **`victoryNum` 是四个座位从开始到当前的累计胜场**，例如 `[3,0,3,0]` 表示 0 号和 2 号队各赢了 3 次，**不是**「只打了 3 副或 3 局」。  
2. **`completed_games=10` 在当前代码里往往表示「落盘成对 round 编号凑满 10」**，一次平台「3 副」会话就可能因 39 对 round 被 cap 成 10，**所以不会重启第 2～4 批**。  
3. **ITERATIONS 里 M1 的「10 个 game_id」口径是对的**；M3 近期写「10/10 完成」的批跑行应视为 **计数 bug 下的 Premature stop**，策略数字需按实际 JSON 重新解读，**本轮不关 GUA-022/031 等台账**。

---

## 9. 关键文件

- `batch_executor/executor.py` — `_count_new_paired_games`、`_sync_completed_from_game_records`、L833–851
- `batch_executor/input_validator.py` — `single_run_limit=3`、`calculate_restart_count`
- `batch_executor/README.md` — 与实现不一致的 game_id 说明
- `src/communication/game_recorder.py` — `game_counter`、`RECORD_FILENAME_RE`
- `docs/knowledge/rules/01_basic_rules/06_game_flow.md`、`08_basic_concepts.md` — 副 / gameOver / victoryNum

**评审问题一句话答案**：当前 `--target-games` **名义上**是「成对评测局数（文档写 game_id）」，**实际上**是「成对 game_round 数 cap 到 target」；应改为 **按平台会话 batch 累计（方案 A）**，分析层用 **match key（方案 C）**，并 **文档澄清 victoryNum**。
