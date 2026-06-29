# GUA-096 · 净盘后强制写入 v7-win-rate-history.md

> **状态**：open 🟢 (P0 — 实施 2026-06-29)
> **严重级别**：P0（治理层护栏，对应 §七.11 第 5 项可反驳预测）
> **标签**：v7, infra, governance, kpi
> **触发**：v4v5v6 教训 §0 "跑过 ≠ 记录过 ≠ 可分析过" + §7.11.3 反推 1

---

## 1. 现象

V 系列 6 个月历史从未认真跑过对战 KPI（`v4v5v6-lessons-2026-06.md` §0）：
- 训练指标（loss / 准确率 / 收敛速度）= 完整
- 对战胜率 = **0 数据**

`v4v5v6-lessons-2026-06.md` §0.2 用户口述：手动跑过对战训练，但 5 个文档里找不到对战 KPI——手动跑过但**没沉淀数据 = 等于没跑**。

## 2. 修复（机械化 — 不靠用户记得）

新增 `scripts/hooks/post_batch_log.py`：

**功能**：
- 读 `batch_executor/latest_victory_num.json` (vn 真源)
- 算 0+2 vs 1+3 队胜率（按 AGENTS.md 三句数据口径）
- 数 `game_records_v7/*.json` 副数
- 追加一行到 `docs/guandan-brain/v7-win-rate-history.md` (markdown 表格行)

**调用入口**：
```bash
python scripts/hooks/post_batch_log.py --gua-id "GUA-097" --change "..." \
    --cmd "python scripts/launchers/v7/run_v7_vs_lalala_games.py --games 3" \
    --games 3 --note "(auto-logged)"
```

**约束**：
- 失败不抛异常（避免阻塞批跑）
- 静默 (`--quiet`) 或 verbose (默认)
- vn 真源不可读 → 退出码 1（强制人工补登）

## 3. 验收

- [x] `scripts/hooks/post_batch_log.py` 创建
- [x] `python -m pytest tests/test_gua096_097_098_v7_infra.py -v` → 7/7 PASS
  - `test_gua096_post_batch_log_syntax` PASSED

## 4. 关联

- **GUA-097**：IP 规则上线前对照批跑 helper（强制联动 GUA-096）
- **GUA-098**：决策溯源日志模块（每步可观测）
- **§七.11 第 5 项可反驳预测**：未来 4 周 `v7-win-rate-history.md` 总共只跑 ≤3 次 = 治理失败
- **§七.9.5 落地路径**：GUA-096 是 §七.9 三层架构的"运维基础"第一条

## 5. 文件清单

| 文件 | 状态 |
|------|------|
| `scripts/hooks/post_batch_log.py` | 新建 ✅ |
| `tests/test_gua096_097_098_v7_infra.py::test_gua096_post_batch_log_syntax` | PASS ✅ |
| `docs/guandan-brain/v7-win-rate-history.md` | 待第 1 次自动追加（手动跑或批跑后） |
