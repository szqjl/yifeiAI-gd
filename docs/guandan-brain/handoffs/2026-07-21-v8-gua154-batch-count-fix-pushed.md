# Handoff: V8 GUA-154 与批跑口径修复已推送

| 字段 | 内容 |
|------|------|
| 日期 | 2026-07-21 |
| 分支 | `v8-dev @ 3a747dc` |
| 远端 | `origin/v8-dev @ 3a747dc`，已对齐 |
| 状态 | 代码已提交推送；待净盘实跑验收 V8 真实局数累计 |

## 背景

本轮从牌谱 `20260721070501773000 [yf1_v8]-[opponent_1_3]-[6]-[2].json` 的第 17/81 步出发，修复重复牌串跨组归属被单值 `card_mask` 覆盖，导致 `Trips/3` 误拆 `StraightFlush` 的 GUA-154。随后完成净盘批跑解读，并修复 V8 launcher/executor 与分析器的两个局数口径缺陷。

代码、测试、WF-12 报告和台账已合并为提交 `3a747dc [V-nn-v8] 修复跨组牌归属与批跑口径`，并推送到 `origin/v8-dev`。

## 已完成

- [x] GUA-154 根因修复：保留兼容 `card_mask`，新增同牌串多实例 memberships 与最小拆核 allocation。
- [x] 拆核过滤、复合组检查、heuristic 一致性与扣分统一消费实例分配结果。
- [x] 锚点回归：`Trips/3 broken=StraightFlush`，完整 `StraightFlush broken=None`，错误 `+10000` 奖励消失。
- [x] 实战灵活性验证：`Trips/7 [H7,C7,D7]` 消费重复 `D7` 后，下一次组牌仍保留 `StraightFlush D3-D7`。
- [x] V8 启动修复：`InputValidator` 接受并校验 `platform="openguandan"`。
- [x] 净盘批跑解读：3 个 OpenGuanDan 会话、3 局、145 副、290 文件；L3 局胜 TeamA 3:0。
- [x] V8 executor 计数修复：OpenGuanDan 每个服务器会话固定承载 1 局，`completed_games` 改由新增牌谱重建的真实 `(team_a, team_b, draw)` 增量推进。
- [x] V8 分析器修复：按会话内 TeamA/TeamB 头游副数判定真实局胜，`victoryNum` 仅作升级值诊断。
- [x] 145 副重放输出修正为 `V8 3/3 (100.0%)、Lalala 0/3、平局 0/3`，不再显示 `1366.7%/766.7%`。
- [x] WF-08 治理提交：Layer 1 共 15 个文件已提交推送；3 个运行态 JSON 未进入提交。

## 验证结果

| 验证 | 结果 |
|------|------|
| GUA-154 / GUA-085 / 组牌 / executor / analyzer 综合功能集 | `104 passed, 2 deselected` |
| card mask / grouping bridge / 主攻领出 | `54 passed` |
| 10ms 组牌性能项单独复测 | `2 passed` |
| 当前批跑与分析器关联集 | `35 passed` |
| `py_compile` | 通过 |
| `git diff --check` | 通过 |
| `scripts/hooks/pre_push_validate.py` | 通过 |

两项 10ms 性能测试在并发跑验证时曾抖动到约 11ms，单独复测均通过；本轮未修改 `grouping_engine.py`，不要为该环境噪声改组牌算法。

## 关键结论

1. **GUA-154 实战回归通过**：6 个 yf 客户端日志有 898 条实例分配、146 条跨组归属；2 个 `Trips` 正确识别拆 `StraightFlush`，33 个跨组完整 `StraightFlush` 均 `broken=[]`。
2. **V8 的 `victoryNum` 是累计升级值，不是局胜数**：真实局胜应按一个 OpenGuanDan 会话的 TeamA/TeamB 头游副数判定。
3. **OpenGuanDan 一次服务器房间实际只完成 1 局**：`RUN_V8_VS_LALALA.bat 3` 必须由 executor 连续运行 3 个服务器会话，不能一会话后直接把 `completed_games` 记成 3。
4. **当前 3:0 KPI 可靠**：L3 `scores.json`、L4 三会话检测与逐会话头游副数判定一致；旧分析器的超 100% 数值已修复。

## 数据与产物位置

| 类型 | 路径 |
|------|------|
| WF-12 报告 | `docs/analysis/WF-12-20260721070501773000-副6-yf1-重复C3拆同花顺分析.md` |
| GUA-154 完成定义 | `docs/guandan-brain/issues/GUA-154-completion.md` |
| 批跑历史 | `docs/guandan-brain/v8-win-rate-history.md` 最新块 |
| 迭代记录 | `docs/guandan-brain/ITERATIONS.md` 最新两行 |
| GUA-154 专项测试 | `tests/test_gua154_duplicate_card_cross_group.py` |
| 批跑计数测试 | `tests/test_batch_executor_counting.py` |
| 分析器测试 | `tests/test_analyze_v7_rounds_dedup.py` |
| 本轮牌谱 | `game_records_v8/`：145 副、290 文件（Layer 2） |
| 本轮日志 | `logs/v8_vs_lalala_20260721_082629.log`、`082847.log`、`083043.log` 及对应 yf 日志（Layer 2） |
| 远端提交 | `3a747dc44da0ae2aaa90b548d53ae9685166c0b3` |

## 当前工作区

提交历史已与远端对齐，但以下 3 个 Layer 2 运行态文件仍有本地修改，**禁止提交**：

- `batch_executor/clients_ready.json`
- `batch_executor/game_ready.json`
- `batch_executor/latest_victory_num.json`

本 handoff 文件在提交 `3a747dc` 之后创建，当前尚未 commit/push。

## 未完成 / 后续

- [ ] post-fix executor 尚未实际跑一轮；当前 145 副来自计数修复前的 3 次独立 launcher 会话，只能验证 GUA-154 与分析器，不能验证新 executor 的 1/3→2/3→3/3 进度。
- [ ] `ISSUES.md` 中 GUA-154 仍标为 `open`；批跑关单证据已经满足，完成 post-fix 计数实跑后可一并改为 `closed`。
- [ ] 残局扫描仍有 8 条 high：`recommended_filtered_to_pass_only=7`、`enemy_critical_pass_with_legal_beater=1`。敌剩 1 仍 PASS 的锚点为 `20260721083150239049 [yf2_v8]-[opponent_1_3]-[27]-[2].json#d33`，后续单独走 WF-12。

## 下一步唯一动作

**净盘后只运行一次 `RUN_V8_VS_LALALA.bat 3`，验收同一个 executor 是否连续完成 3 个 OpenGuanDan 会话，并在主日志中依次出现 `completed_games=1/3`、`2/3`、`3/3`。**

验收时同时确认：

1. `v8_vs_lalala_state.json` 最终为 `completed_games=3`、`current_batch=3`、`restart_count=2`。
2. `v8_vs_lalala_scores.json total_games=3`。
3. 主日志有 3 条 `V8 台账`，每条 `真实新增局=1`。
4. `python scripts/analysis/analyze_v7_rounds.py --dir game_records_v8 --all` 的局胜率不超过 100%。

## 不要重做

- 不要重新调查 GUA-154 的 `C3` 单值覆盖根因；WF-12、专项测试和实战日志证据已齐。
- 不要恢复“按新增副数截断 target”的 V8 `completed_games` 逻辑；副数不等于局数。
- 不要再用 `victoryNum[0]/[1]` 直接计算 V8 局胜率。
- 不要提交上述 3 个运行态 JSON，也不要把 `game_records_v8/`、`logs/` 纳入 Git。
- 不要在 post-fix 实跑前使用现有 145 副声称 executor 计数已完成实战验收。
- 不要因并发环境中的 10ms 阈值抖动修改 `grouping_engine.py`；先单独复测性能项。
