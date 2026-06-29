# GUA-098 · 决策溯源日志模块（DecisionTracer）

> **状态**：open 🟢 (P0 — 实施 2026-06-29)
> **严重级别**：P0（治理层护栏，机械化 "决策是兜底没人发现" 教训）
> **标签**：v7, infra, tracing, observability
> **触发**：v4v5v6 教训 §4.1 + §8.1 红字第 2 条

---

## 1. 现象

`v4v5v6-lessons-2026-06.md` §4.1 + §8.1：
> V5 因 lalala 路径错**静默退到兜底**——代码都在，决策是兜底，没人发现
> 失败是静默的：V5 因 lalala 路径错静默退到兜底——错误处理吃掉异常，没人发现

V7 三层架构（§七.9）的"运维基础"第三条：决策链路**必须**可观测。

## 2. 修复（旁路日志模块）

新增 `src/v/nn/tracing/decision_trace.py`：

**类 DecisionTracer**：
- 构造：`DecisionTracer(my_pos, game_id, enable=True)`
- `begin_step(hand_size, cur_rank, stage, cur_pos, greater_pos)`：开一步
- `record_layer1(source, payload)`：Layer 1 记忆命中
- `record_layer2(ip_id, delta, oppo, comment)`：Layer 2 IP-XX 推断
- `record_guard(rule_id, filtered_count, reason)`：Layer 3 Guard RXX 过滤
- `end_step(actIndex, chosen_action)`：结一步（自动算 decision_ms）
- `flush_to_jsonl()`：每局结束写 `game_decision_traces/{game_id}.jsonl`
- `get_summary()`：返回 `{steps, stages, ip_counter, guard_counter, avg_ms}`

**约束**：
- `enable=False` 时全部方法 no-op（pytest 验证过）
- 不阻塞主决策路径（纯旁路记录）
- `flush` 失败不抛异常

**未来接入 V7 决策入口**（GUA-089/090/091/092 落地时）：
```python
tracer = DecisionTracer(my_pos=my_pos, game_id=game_id, enable=True)
tracer.begin_step(hand_size=len(hand), cur_rank=cur_rank, stage=stage, ...)
# ... 跑 Layer 1/2/3 ...
tracer.end_step(actIndex=chosen_idx, chosen_action=action_list[chosen_idx])
# 每局结束
tracer.flush_to_jsonl()
```

## 3. 验收

- [x] `src/v/nn/tracing/decision_trace.py` 创建
- [x] `src/v/nn/tracing/__init__.py` 目录创建
- [x] `python -m pytest tests/test_gua096_097_098_v7_infra.py -v` → 7/7 PASS
  - `test_gua098_decision_tracer_basic` PASSED
  - `test_gua098_decision_tracer_multi_step` PASSED
  - `test_gua098_decision_tracer_disabled` PASSED
  - `test_gua098_decision_tracer_flush` PASSED

## 4. 关联

- **GUA-089/090/091/092**：阶段化状态机决策入口（GUA-098 接入点）
- **GUA-094**：IP 规则实现（GUA-098 通过 `record_layer2` 记录每条 IP 触发）
- **GUA-013**：手牌跟踪修复（Layer 1 输入可信 = tracer 数据可信）
- **§七.11.3 反推 2**：决策链路加 _decision_trace() 日志 = 机械化 V5 静默失败教训

## 5. 文件清单

| 文件 | 状态 |
|------|------|
| `src/v/nn/tracing/decision_trace.py` | 新建 ✅ |
| `src/v/nn/tracing/__init__.py` | 新建 ✅（目录建） |
| `game_decision_traces/` | 待首次 flush 建（Layer 2 数据落盘点） |
| `tests/test_gua096_097_098_v7_infra.py::test_gua098_*` | 4 PASS ✅ |
