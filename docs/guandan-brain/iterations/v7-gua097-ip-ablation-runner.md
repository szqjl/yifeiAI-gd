# GUA-097 · IP 规则对照批跑 helper

> **状态**：open 🟢 (P0 — 实施 2026-06-29)
> **严重级别**：P0（治理层护栏，机械化 "加规则不测" 教训）
> **标签**：v7, infra, ablation, ip-rule
> **触发**：v4v5v6 教训 §4.1 "失败是静默的" + §6.2 "加规则有负收益"

---

## 1. 现象

V 系列历史教训（`v4v5v6-lessons-2026-06.md` §4.1）：
- 加规则不测 → 叠加崩（M3 GUA-036 教训：副胜率从 78.8% 跌到 52.2%）
- v5 路径错 → 静默退兜底 → 没人发现

V7 阶段化方案 §7.2.4.1 设计了 IP-01~IP-13（相生相克）+ §7.9.2 计划补 IP-14~IP-21（算牌）= **共 21 条 IP 规则**。

**风险**：21 条规则如果直接堆叠 → V 老路。

## 2. 修复（机械化对照批跑）

新增 `scripts/hooks/ip_ablation_runner.py`：

**功能**：
- 注册表 IP_REGISTRY（21 条 IP 规则描述）
- 3 模式：
  - `baseline`：全部 IP 关闭 → 跑 GUA-096 落盘
  - `enable --ip-id IP-07`：启用单条 → 跑 GUA-096 落盘
  - `diff --ip-id IP-07`：对比 baseline + enable 两行 win_rate
  - `list`：打印 21 条注册表

**调用入口**：
```bash
# 基线 (全部 IP 关闭)
python scripts/hooks/ip_ablation_runner.py --mode baseline --games 3

# 启用 IP-07
python scripts/hooks/ip_ablation_runner.py --mode enable --ip-id IP-07 --games 3

# 查注册表
python scripts/hooks/ip_ablation_runner.py --mode list

# 对比
python scripts/hooks/ip_ablation_runner.py --mode diff --ip-id IP-07
```

**联动 GUA-096**：每次跑完自动调 `post_batch_log.py` 写 win-rate-history。

**Ablation log 落盘**：`docs/guandan-brain/iterations/v7-gua097-ablation-log.md`
- 表头：`date | mode | ip_id | description | win_rate | delta_vs_baseline | 备注`
- 每次跑追加一行

## 3. 验收

- [x] `scripts/hooks/ip_ablation_runner.py` 创建
- [x] `python -m pytest tests/test_gua096_097_098_v7_infra.py -v` → 7/7 PASS
  - `test_gua097_ip_registry_complete` PASSED（验证 IP-01~IP-21 全部注册）
  - `test_gua097_list_mode_runs` PASSED（验证 --mode list 跑通）
- [ ] **未来 4 周**：21 条 IP 至少跑 5 条 baseline + enable 双跑（GUA-094 落地前提）

## 4. 关联

- **GUA-094**：`_inference_phase_relation` + IP-01~IP-21 实现
- **GUA-096**：净盘后强制写 win-rate-history（本 GUA 联动）
- **§七.11.3 反推 1**：每条 IP 规则上线前必须跑 baseline + enable 双跑
- **§七.6 预测 2**：阶段 2 副胜率 < 25% = Guard 全开帮倒忙

## 5. 文件清单

| 文件 | 状态 |
|------|------|
| `scripts/hooks/ip_ablation_runner.py` | 新建 ✅ |
| `docs/guandan-brain/iterations/v7-gua097-ablation-log.md` | 待首次 baseline 跑后建 |
| `tests/test_gua096_097_098_v7_infra.py::test_gua097_*` | 2 PASS ✅ |
