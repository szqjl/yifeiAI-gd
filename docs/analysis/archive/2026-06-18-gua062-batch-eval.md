# Handoff: GUA-062 批跑验证 — 组牌引擎 v2 实战评估

| 字段 | 内容 |
|------|------|
| 日期 | 2026-06-18 |
| 分支 | v7-dev |
| 状态 | 已结论，待根因定位 |
| 负责人 | — |

## 背景
GUA-062 关闭后（P0-A/B/C + P1/P2 全部完成，49 pytest passed），需要实战验证 v2 分组引擎是否提升了 V7 对 lalala 的竞争力。执行了 V7 vs Lalala 9 局批跑。

## 已完成
- [x] 净盘（清空 game_records、scores.json、state.json、replay_word.md）
- [x] 执行 `python -m scripts.launchers.v7.run_v7_vs_lalala_games --games 9`（3 批次 × 3 局/会话，重启 2 次）
- [x] 副级统计：79 副（158 条记录 = 每副 yf1+yf2 双文件）
- [x] 更新 ISSUES.md、ITERATIONS.md、kpi-observations.md

## 关键结论

### 局级
- **V7 队胜 0/9 (0%)**，Lalala 完封
- `victoryNum`: `[0,3,0,3]` → pos0+2（V7）0 胜

### 副级
- V7 赢副：**8/79 (10.1%)**
- Lalala 赢副：**71/79 (89.9%)**
- V7 达 A 级副：**12/79 (15.2%)**

### V7 末级分布（两极化）
```
2:  ████████████████ 12副    3:  ██ 2副     4:  ██ 2副
5:  █████████████ 13副     6:  ██████ 6副    7:  ██ 2副
8:  █████████ 9副         9:  ███ 3副       T:  ██ 2副
J:  █████████ 9副         Q:  ████ 4副      K:  ███ 3副
A:  ████████████ 12副
```
→ 2/A 双峰凸起：要么卡在 2 级，要么被一路推到 A。中间等级（5-8-J）堆积表明 V7 能爬升但很快被压回。

### 结论
**GUA-062 分组引擎 v2 未转化为对局竞争力。** ptest 全过但实战副胜率仅 10.1%，与 GUA-061（M3 原始组牌提取）无显著区别。

## 数据与产物位置
| 类型 | 路径 |
|------|------|
| 批跑记录 | `game_records_v7/`（158 条 JSON） |
| 批跑日志 | `v7_batch_output.txt` |
| 得分文件 | `v7_vs_lalala_scores.json`、`v7_vs_lalala_state.json` |
| victoryNum 真源 | `batch_executor/latest_victory_num.json` |

## 下一步唯一动作
**根因定位**：检查 V7 出牌决策链是否真正使用了 v2 分组引擎评分输出，还是仍然走 BC 模型 argmax / guard 壳 PASS 回退路径。
（具体：`UltimateWinRateEngineV7.decide()` 中 `grouping_engine` 的调用链路 → `filter_action_list` → 最终 action 选择逻辑）

## 不要重做
- 不要再调 GUA-062 的组牌评分参数（49 pytest 已证明代码正确，问题在决策链接入）
- 不要再跑 BC 重训对比（GUA-060 已证 BC argmax collapse 理论必然）
- 不要再跑 GUA-061 批跑（M3 提取的弱组牌，已覆盖）
