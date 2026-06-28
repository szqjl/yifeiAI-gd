# GUA-085 完成定义（回退 NN actIndex 错位 + 领出保 SF/炸核）

> **登记**：2026-06-01  
> **回放锚点（仅发现用）**：`game_records_v7/20260628091704590941` 步 1/86；WF-12 见仓根 `replay_word.md`  
> **关联**：GUA-075、GUA-084、GUA-064、WF-12

## 禁止伪关单（定音）

掼蛋两次发牌完全相同概率约 **\(10^{-58}\)**（见 `ISSUES.md`「复盘发现 → 实现 → 验收」）。因此：

| ❌ 伪关单 | ✅ 真关单 |
|----------|----------|
| 批跑后再抽到同副 27 张，首出 ≠ TWT/K+拆 H8 | **pytest 构造态**：固定 HAND + 牌谱 `card_mask` / 过滤后 `actionList`，调用 `decide()` |
| 在新 `game_records_v7/` 里搜 game_id `90941` 再现 | **批跑 R-G080-4**：3 局冒烟 **零退化**（scanner/card_mask 降级、副胜率相对 GUA-080 基线） |
| 「步 1 日志必须出现某一行」作为唯一 pass | **原则型断言**：回退路径 `actIndex` 与选中动作**内容一致**；领出不拆 bomb/SF/straight core |

**回放步 1** 只说明 bug 长什么样；**关单不依赖批跑复现该副牌**。

---

## 现象（锚点步）

`group_consistency_filter` 删动作后，`flt_map[model_idx]` 与 `group_actions` 错位 → 内部选 `Pair/2` 却 `return 973`（槽位为 `ThreeWithTwo/K` 含 H8），一步拆 SF 核 + K 炸核。

---

## 关单条件

### A. pytest 构造态（硬门槛，已实施）

```bash
pytest tests/test_gua085_fallback_action_index_mapping.py -v
```

| 用例 | 验证什么 |
|------|----------|
| `test_model_path_does_not_map_to_three_with_two_slot` | 固定 HAND + 牌谱 mask + 模拟 filter 后列表 → `decide()` **不得** return TWT/K 槽 |
| `test_match_chosen_finds_first_identical_action` | 内容回查 `_match_chosen_to_original_action_list` |
| `test_fallback_old_mapping_would_have_hit_973` | 回归：旧 flt_map 会错映到 973 |
| `test_lead_recommends_scatter_not_sf_card` | GUA-084 组牌后领出推荐 **不拆 SF/炸/顺 core**（散牌 DT/HA） |

**可选加强**（非关单阻塞）：在 `test_gua085_*` 增加「领出 `decide()` 全路径不得含 H8 的 TWT」——仍用构造态，非批跑。

### B. 组牌联动（GUA-084，本 GUA 前置）

GUA-085 领出测试依赖 GUA-084 后 `enumerate_groupings(HAND,"8")` 保 SF；GUA-084 关单见 [[GUA-084-completion]]（`check_grouping_engine` + `test_gua084_*`）。

### C. 批跑（仅零退化，非复现副牌）

- [ ] **R-G080-4**：`run_v7_vs_lalala_games.py --games 3`（或 9）— **无** scanner/card_mask 降级回归；副胜率 **不要求**回升（GUA-080 冻结条款）
- [ ] `v7-win-rate-history.md` 追加一行

### D. 中观观测（可选，非关单）

批跑后可在**全体**新牌谱上统计「首出动作 ∩ SF 核牌」比例，作趋势监控；**单副不可达 ≠ 失败**。

---

## 非目标

- 不以「90941 副再赢/再输」验收
- 不要求 NN 主路径命中率（另项 GUA-071/075 观测）

## 关联

- `ultimate_win_rate_engine_v7.py`：`_match_chosen_to_original_action_list`、`_recommend_lead_impl`、回退路径
- `replay_word.md`：WF-12 步 1/9（步 9 为后果，非关单）
