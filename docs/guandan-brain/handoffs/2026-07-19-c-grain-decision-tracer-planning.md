# Handoff: DecisionTracer C 粒度对齐（2026-07-19）

> **下次接续入口**：读完本文件即可直接进入 C 粒度实施，无需重读上下文
> **生成时间**：2026-07-19（周日）
> **会话主线**：WF-01 → C 粒度缺口梳理 → 挂载点定位 → 接口对齐（待确认）→ 写 handoff + commit（无代码）
> **状态更新（2026-07-19）**：✅ 用户定音改为 `YF_REPLAY` 离线 A/B/C 完整分析；实时只保存平台原始输入，C 粒度不再放入实战模型计算。§4 的三问已由离线架构取代。

---

## 1. 一句话总结

**DecisionTracer（B 粒度）602 个 jsonl 已在生产落地；C 粒度 = 候选评分排序 + MemoryV2 快照 + GUA trace 三块缺口确认。** 唯一定位到生产挂载点 `src/v/nn/ultimate_win_rate_engine_v7.py:173-310`，三块 C 粒度的插入点已提议并发起对齐问；本 handoff 提交时**用户尚未点确定稿**，留作下一会话首句。

---

## 2. 背景

### 2.1 B 粒度现状 = 已落地

文件：`src/v/nn/tracing/decision_trace.py`（GUA-098 实施）。

| 接口 | 行为 | 字段 |
|---|---|---|
| `begin_step(hand_size,cur_rank,stage,cur_pos,greater_pos)` | 开步 | ts_start_ms, hand_size, cur_rank, stage, cur_pos, greater_pos |
| `record_layer1(source,payload)` | L1 命中 | layer1_hits[]（source+payload 截断 200） |
| `record_layer2(ip_id,delta,oppo,comment)` | L2 IP 触发 | layer2_ips[] |
| `record_guard(rule_id,filtered_count,reason)` | L3 guard 过滤 | layer3_guards[] |
| `record_joker_signal(joker_signal)` | 王记牌 | joker_signal |
| `record_decision_intent(intent,payload)` | 阶段意图 | decision_intent |
| `end_step(actIndex,chosen_action)` | 步终 | ts_end_ms, decision_ms, chosen_action 截断 200 |
| `flush_to_jsonl()` | 局末落盘 | `game_decision_traces/{game_id}.jsonl` |

落地数：**602 个 jsonl**（`game_decision_traces/`）。

### 2.2 C 粒度缺口 = 用户提出

| # | 缺口 | 含义 |
|---|---|---|
| **C1** | 候选评分排序 | 每步候选 `actionList` + 评分排序（被 filter 前的全量 / 之后的留存 / top-K） |
| **C2** | MemoryV2 快照 | 每步：`hand / curRank / role / phase / teammate_hands_est / opponent_sprint_capable` |
| **C3** | GUA trace 字段 | 决策触发的 GUA 标号 + payload（区别于 IP-XX、Guard R-XX 的更高层语义） |

---

## 3. 挂载点定位（唯一定位）

**生产唯一实例化**：`src/v/nn/ultimate_win_rate_engine_v7.py:173-180`（`__init__` 末段，按 `V7_ENABLE_DECISION_TRACE` 启用）。

| 阶段 | 代码行 | B 粒度现状 | C 粒度提议插入 |
|---|---|---|---|
| init | 173-180 | 实例化 | （不变） |
| 局末 flush | 186-199 | `flush_to_jsonl` | （不变） |
| 步起 `_trace_begin_step` | 219-291 | 已开步 + 3 个 record_* | C2 紧接 `belief` record 后追加 `record_memory_snapshot` |
| 残局 decider 命中/未命中 | 479, 482, 518 | 无 trace | C3 增加 `record_gua("GUA-XXX", triggered, payload)` |
| `_recommend_play` 推荐 | 520 | 无 trace | C1 在 L520 旁捕 `recommendation + scores` |
| `filter_action_list` (V7-native guard) | 605 | 无 trace | C1/C3 在 605 后捕 filter 前后 |
| `_run_grouping_engine` + NN | 646 起 | 无 trace | C3 在 guard/heuristic 命中点 |
| `_match_chosen_to_original_action_list` | 741, 762 | 无 trace | （不变，回退路径） |
| `_trace_finalize` end_step | 293-313 | end_step + decision_intent | C1/C3 汇总在 end_step 前 |

---

## 4. 原接口提议（已被 YF_REPLAY 离线架构取代）

### 4.1 C1 候选评分

```python
def record_candidates(self, scored_entries: List[Dict[str, Any]]) -> None:
    """每项: {actIndex, score, type, rank, kept}"""
```

**待 Q1**：`_recommend_play` 返回的 `recommendation` 长啥样？
- 选项 A：单 `actIndex`（仅指向最优）→ 在 `_recommend_play` 旁加一次排序捕快照
- 选项 B：已排好序 `List[(actIndex,score)]` → 直接用

### 4.2 C2 MemoryV2 快照

```python
def record_memory_snapshot(self, snapshot: Dict[str, Any]) -> None:
    """键: hand/curRank/role/phase/teammate_hands_est/opponent_sprint_capable"""
```

**待 Q2**：`opponent_sprint_capable` 真源在哪儿？
- 选项 A：`_phase_relation["sprint_fire_ready"]`（已存在 belief 子字段）
- 选项 B：`memory_v2.py` 内属性（需 import + 暴露）
- 选项 C：本轮新增 `_sprint_capable_seats()` 工具函数

### 4.3 C3 GUA trace

```python
def record_gua(self, gua_id: str, triggered: bool, payload: Dict[str, Any] = None) -> None:
    """GUA-075 / GUA-135 / GUA-150 等高语义层触发"""
```

**待 Q3**：现有硬编码 `record_layer2("GUA-094.phase_relation", ...)` 是否本轮统一迁移到新 `record_gua`？
- 选项 A：本轮只增接口，旧硬编码保留，下次治理合并
- 选项 B：本轮一并迁移，影响 ISSUES / ITERATIONS 治理 + 测试 4 条同步修

---

## 5. 提交规范预备

### 5.1 提交消息（prefix `[V-nn-v8]`，等用户确认后复用）

```
[V-nn-v8] GUA-098-ext C 粒度：候选评分 + MemoryV2 快照 + GUA trace

src/v/nn/tracing/decision_trace.py
  - record_candidates(scored_entries)
  - record_memory_snapshot(snapshot)
  - record_gua(gua_id, triggered, payload)

src/v/nn/ultimate_win_rate_engine_v7.py
  - _trace_begin_step  L226 追加 record_memory_snapshot
  - L520 旁捕 recommend 评分 + record_candidates
  - L479/L482/L518/L605  GUA hit/miss 触发 record_gua
  - L611 后捕 filter 前后 action_list diff
  - _trace_finalize  end_step 前汇总 C1/C3

tests/test_gua098_c_grain.py  新增（pytest ≥6 条）
docs/guandan-brain/ISSUES.md  GUA-098-ext 行 + 5 问准入
docs/guandan-brain/ITERATIONS.md  追加迭代行
```

### 5.2 不入库的文件

| 路径 | 原因 |
|---|---|
| `batch_executor/clients_ready.json` | Layer 2 运行时状态（AGENTS.md § 6） |
| `batch_executor/game_ready.json` | 同上 |
| `batch_executor/latest_victory_num.json` | 同上 |

本次 commit **仅 stage** `docs/guandan-brain/handoffs/2026-07-19-c-grain-decision-tracer-planning.md`。

---

## 6. 验证（实施后必跑）

```powershell
cd <repo_root>

# ① C 粒度接口 unit（pytest）
python -m pytest tests/test_gua098_c_grain.py -v

# ② B 粒度回归（不影响现状）
python -m pytest tests/test_gua096_097_098_v7_infra.py -v

# ③ 注入式 trace 实验（构造态 1 副）
# （留待实施）

# ④ R-G080-4 净盘批跑
Get-Process guandan_offline_v1006 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item tmp\.batch_executor.lock -ErrorAction SilentlyContinue
Get-ChildItem game_records_v7 -Filter *.json -ErrorAction SilentlyContinue | Remove-Item -Force
Remove-Item v7_vs_lalala_scores.json, v7_vs_lalala_state.json -ErrorAction SilentlyContinue
Remove-Item batch_executor\latest_victory_num.json, batch_executor\current_batch.json -ErrorAction SilentlyContinue
Remove-Item execution_state.json -ErrorAction SilentlyContinue
Get-ChildItem logs -File -ErrorAction SilentlyContinue | Remove-Item -Force
python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3
python scripts/analysis/analyze_v7_rounds.py --all
rg "_run_grouping_engine\s*失败|_basic_classify\s*也失败|_group_consistency_filter\s*失败" logs/yf*_v7_*.log logs/v7_vs_lalala_*.log
```

预期：C 粒度 jsonl 字段含 `candidates/memory_snapshot/gua_traces`；B 粒度不变；副胜率不回归（R-G080-4 零退化）。

---

## 7. 下次会话第一句（建议给 Agent）

```text
接续 handoff docs/guandan-brain/handoffs/2026-07-19-c-grain-tracer-planning.md 的 C 粒度接口对齐：
Q1 candidates 数据形态；Q2 opponent_sprint_capable 真源；Q3 旧 record_layer2('GUA-094.phase_relation') 是否同步迁移 record_gua。
按用户回复先确认 4.1/4.2/4.3 三块接口，再实施。
```

---

## 8. 一次一句

已实施 `YF_REPLAY` A/B/C：A=平台输入与实际动作；B=Layer/Guard/Intent；C=候选逐层去留、Memory/信念、GUA。新牌谱通过 `my_decisions.context.replay_state` 保存完整 `actionList` 等平台输入；旧牌谱自动降级。实时 `DecisionTracer` 默认关闭，显式 `V7_ENABLE_DECISION_TRACE=1` 才开启。
