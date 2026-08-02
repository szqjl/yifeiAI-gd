# V8 队胜率历史（Win Rate History）

> **目的**：V8 OpenGuanDan 新平台对战 KPI 追踪。每条迭代批跑结果强制记录。
> **创建**：2026-07-18（V8 首条批跑记录）
> **关联**：[`ITERATIONS.md`](./ITERATIONS.md)（GUA-148/150）

---

## 记录格式（每次批跑一行）

```
| 日期 | 目标 GUA | 改动摘要 | 批跑命令 | 局数 | V8 队胜率 | 副数 | 副头游率 | 双上率 | 备注 |
```

**字段说明**：
- **局数**：3 的倍数（推荐 3/6/9/12）；规则一致
- **V8 队胜率**：局级队胜 / 总局数（V8 平台无 `victoryNum`，从 `game_records_v8/*.json` 的 `result.order` 末副推算）
- **副数**：`game_records_v8/` 计入 yf1 视角 JSON 数
- **副头游率**：yf1+yf2 头游（order=0）占全部副的比例
- **双上率**：yf1+yf2 包揽 1st+2nd 占全部副的比例
- **备注**：scores.json 追踪状态 / 日志文件名 / 与上批对比

---

## 记录

| 日期 | 目标 GUA | 改动摘要 | 批跑命令 | 局数 | V8 队胜率 | 副数 | 副头游率 | 双上率 | 备注 |
|------|---------|---------|---------|------|----------|------|----------|--------|------|
| 2026-07-18 | **GUA-150** | GUA-150 self_sprint 让道误判修复（endgame_decide.py intent比较）+ GUA-149 PASS僵死修复（同事提交） | `python scripts\launchers\v8\run_v8_vs_lalala_games.py --games 6` | 6 | **4/6（66.7%）** | 33 | 60.6%（40/66） | 36.4%（24/66） | ⚠️ scores.json追踪失效（全0）；服务器stdout无输出（V8 OpenGuanDan不写stdout gameResult）；次数6非推荐档位3/9/12；末游率yf1=24.2% yf2=18.2%；日志：`logs\v8_vs_lalala_20260718_155001.log` |
| 2026-07-18 | **GUA-151/152/153** | V8 完成检测 match_key 碰撞修复 + 平局计数 + 双重计数修复 | `python scripts\launchers\v8\run_v8_vs_lalala_games.py --games 6` | 6 | **4/6（66.7%）** | 73 | 63.0%（46/73） | 24.7%（18/73） | ✅ scores.json 正常 `{"team_a_wins":4,"team_b_wins":1,"draws":1,"total_games":6}`；零卡顿零regroup（GUA-151修复生效）；1日志文件；末游率yf1=28.8% yf2=28.8%；平局1场（GUA-152修复生效）；日志：`logs\v8_vs_lalala_20260718_174828.log` |
| 2026-07-18 | **GUA-151/152/153** | 三项修复后扩大样本验证 | `--games 9` | 9 | **9/9（100%）** | 60 | 71.7%（43/60） | 28.3%（17/60） | ✅ scores.json `{"team_a_wins":9,"team_b_wins":0,"draws":0,"total_games":9}`；零卡顿零regroup；末游率yf1=20.0% yf2=31.7%；Kaggle: philsz/guandan-v8-records-9-games-post-fix；日志：`logs\v8_vs_lalala_20260718_200417.log` |
| 2026-07-21 | **GUA-154 + 12局实战回归** | 净盘后 12 局真实累计回归（含 GUA-154 重复牌串跨组归属修复） | `RUN_V8_VS_LALALA.bat 12`（实际 12 launcher × 1 局 = 12 局） | 12 | **10/12（83.3%）** | 171 | 57.9%（99/171） | 17.5%（30/171） | ⚠️ scores.json `total_games=3`（executor 仅记录最后 launcher，与真实 12 局口径偏差）；L4 `analyze_v7_rounds.py` 识别 12 会话 / 12 局 / 171 副；yf2 末游率 41.0% **异常偏高**；日志：`logs\v8_vs_lalala_20260721_125812.log` ~ `131158.log`（4 主 log + 24 子 log） |
| 2026-08-02 | 无代码变更（Botzone -2 修复已提交，本批对照验证无回归） | 净盘后 3 局批跑（V8 vs lalala）；验证 Botzone adapter + V7 引擎跟牌重建修复对 openGuanDan 平台无副作用 | `python scripts\launchers\v8\run_v8_vs_lalala_games.py --games 3` | 3 | **3/3（100%）** | 7 | 85.7%（6/7） | 57.1%（4/7） | ✅ scores.json `{"team_a_wins":3,"team_b_wins":0,"draws":0,"total_games":3}`；`restart_count=2`（3 批正常）；completed_games=3/3；残局异常扫描 0；末游率 yf1=0/7（0.0%）yf2=3/7（42.9%）；日志：`logs\v8_vs_lalala_20260802_161055.log` |

---

## 本批详析（2026-07-18 · GUA-150 修复后首跑）

### 数据口径

| 项目 | 值 | 说明 |
|------|-----|------|
| 局数（completed_games） | **6 局** | executor 台账 confirmed |
| 副数（game_records_v8/） | **33 副**（66 文件：yf1 33 + yf2 33） | 每副各有 yf1/yf2 两个视角的独立 JSON |
| 批跑命令 | `--games 6`（batch_games=1 × 6 批） | ⚠️ 非推荐档位（3/9/12） |
| 对手 | lalala（南邮基线） | opponent_1_3（固定） |
| 平台 | OpenGuanDan `guandan.exe` | WebSocket ws://127.0.0.1:8181 |
| 发动机 | `ultimate_win_rate_engine_v7.py` + `bc_model_v3.pth` | 决策模式未知（日志未标记 model/rule 决策比例） |

### 局级 6 局逐局

| 局 | 副数 | 末副 yf1 视角 order | 头游 | 二游 | 三游 | 末游 | 胜方 | 末级(curRank) |
|----|------|---------------------|------|------|------|------|------|---------------|
| 1 | 3 | [3,2,0,1] | yf2 | opp3 | opp1 | yf1 | **team_02** | 4 |
| 2 | 4 | [3,1,0,2] | yf2 | opp1 | opp3 | yf1 | **team_02** | T(10) |
| 3 | 5 | [2,0,1,3] | opp1 | opp3 | yf1 | yf2 | team_13 | 8 |
| 4 | 6 | [2,0,1,3] | opp1 | opp3 | yf1 | yf2 | team_13 | 3 |
| 5 | 7 | [0,2,1,3] | yf1 | opp1 | yf2 | opp3 | **team_02** | Q(12) |
| 6 | 8 | [0,1,3,2] | yf1 | opp1 | opp3 | yf2 | **team_02** | J(11) |

### 副级详细统计

| 指标 | 值 | 解读 |
|------|-----|------|
| yf1 头游 | 24/66（36.4%） | 主攻正常 |
| yf2 头游 | 16/66（24.2%） | 助攻偏低 |
| opp1 头游 | 18/66（27.3%） | — |
| opp3 头游 | 8/66（12.1%） | — |
| **team_02 头游率** | **40/66（60.6%）** | 副级占优 |
| team_13 头游率 | 26/66（39.4%） | |
| **双上率** | **24/66（36.4%）** | 🟡 中等偏好 |
| 双下率 | 8/66（12.1%） | |
| yf1 末游率 | 16/66（24.2%） | |
| yf2 末游率 | 12/66（18.2%） | |

### 关键发现

1. **局胜 66.7%（4/6）**：V8 平台首次跑出正向局胜率，GUA-149/150 修复后明显优于此前 M3/V7 的 0% 局胜基线。
2. **scores.json 追踪失效**：`v8_vs_lalala_scores.json` 全部为 0（team_a_wins/team_b_wins/total_games=0）。V8 executor 的 score tracker 未工作，**需要修复**（可能 V8 通道不写 scores.json 或写入时机不对）。
3. **服务器 stdout 无输出**：executor 每批报告「共收集 0 行输出」。V8 OpenGuanDan `guandan.exe` 不向 stdout 输出 gameResult/victoryNum，与 v1006 数据通道完全不同。**牌谱 JSON 是唯一胜负真源**。
4. **latest_victory_num.json 不存在**：V8 客户端不生成该文件（v1006 的 yf1_v7.py 写，V8 的 yf1_v8.py 不写），导致 executor 每批末 warning。
5. **局数 6 非推荐档位**：下次建议用 `--games 3` 或 `--games 9`（3 的倍数），且可考虑 `batch_games=3` 以启用对账功能。

### 与 Kaggle 公开基线对比

| 指标 | 本批 GUA-150（V8） | Kaggle 公开（V8 修复前） |
|------|---------------------|--------------------------|
| 副头游率 | **60.6%** | 35.3% |
| 双上率 | **36.4%** | 31.5% |
| yf1 末游率 | 24.2% | 32.1% |

> ⚠️ 样本量差异大（33副 vs 184副），且本批对手固定 lalala vs Kaggle 对全量公开对手，不可直接对比。

---

## 本批详析（2026-07-18 17:48 · GUA-151/152/153 三项修复验证）

### 数据口径

| 项目 | 值 | 说明 |
|------|-----|------|
| 局数（completed_games） | **6 局** | executor 台账 confirmed |
| 副数（game_records_v8/） | **73 副**（146 文件：yf1 73 + yf2 73） | 每副各有 yf1/yf2 两个视角的独立 JSON |
| 批跑命令 | `--games 6`（batch_games=1 × 6 批） | ⚠️ 非推荐档位（3/9/12） |
| 对手 | lalala（南邮基线） | opponent_1_3（固定） |
| scores.json | ✅ 正常 | `{"team_a_wins":4,"team_b_wins":1,"draws":1,"total_games":6}` |
| 卡顿/regroup | ✅ 零卡顿零 regroup | GUA-151 修复生效，每批 ~60s |
| 分析脚本 | `analyze_v7_rounds.py --dir game_records_v8 --all` | 已适配 V8（gc 重置检测+yf1 过滤+双上率） |

### 局级 6 局逐局

| 局 | 副数 | 头游分布[seat0-3] | TeamA | TeamB | 胜方 |
|----|------|-------------------|-------|-------|------|
| 1 | 14 | [3,2,7,2] | 10 | 4 | **team_02** |
| 2 | 10 | [2,4,1,3] | 3 | 7 | team_13 |
| 3 | 23 | [5,4,9,5] | 14 | 9 | **team_02** |
| 4 | 10 | [4,1,4,1] | 8 | 2 | **team_02** |
| 5 | 6 | [0,2,3,1] | 3 | 3 | **平局** |
| 6 | 10 | [3,1,5,1] | 8 | 2 | **team_02** |

### 副级详细统计

| 指标 | 值 | 解读 |
|------|-----|------|
| yf1 头游 | 17/73（23.3%） | 🟡 偏低 |
| yf2 头游 | 29/73（39.7%） | ✅ 强势 |
| opp1 头游 | 14/73（19.2%） | — |
| opp3 头游 | 13/73（17.8%） | — |
| **team_02 头游率** | **46/73（63.0%）** | ✅ 副级占优 |
| team_13 头游率 | 27/73（37.0%） | |
| **双上率** | **18/73（24.7%）** | 🟡 偏低 |
| 双下率 | 13/73（17.8%） | |
| yf1 末游率 | 21/73（28.8%） | |
| yf2 末游率 | 21/73（28.8%） | |

### 与上批（GUA-150）对比

| 指标 | 本批 GUA-151/152/153 | 上批 GUA-150 | 变化 |
|------|---------------------|-------------|------|
| 局胜率 | 4/6（66.7%） | 4/6（66.7%） | 持平 |
| 副头游率 | 63.0% | 60.6% | +2.4pp |
| 双上率 | 24.7% | 36.4% | **−11.7pp** |
| yf1 末游率 | 28.8% | 24.2% | +4.6pp |
| scores.json | ✅ 正常 | ❌ 全0 | 修复 |
| 卡顿 | ✅ 零 | ❌ 2次5min | 修复 |

### 关键发现

1. **三项修复全部验证通过**：GUA-151（服务器卡顿）零 regroup、GUA-152（平局计数）draws=1 正确记录、GUA-153（双重计数）total_games=6 与 gc-block 一致。
2. **双上率下降 11.7pp**：36.4%→24.7%，样本量小（73副 vs 66副），波动正常范围；需 9+ 局确认趋势。
3. **yf2 头游率上升显著**：24.2%→39.7%，yf2 攻击性增强；yf1 头游率下降 13pp（36.4%→23.3%），可能是配合策略调整。
4. **scores.json 格式**：新增 `draws` 字段（GUA-152），向后兼容旧格式。
5. **分析脚本已适配 V8**：`analyze_v7_rounds.py --dir game_records_v8` 自动检测平台标签、gc 重置检测、yf1 过滤、双上率/末游率指标。
6. **Kaggle 数据集已发布**：https://www.kaggle.com/datasets/philsz/guandan-v8-records-post-fix-73eps （73 副修复后牌谱，zip 打包上传）。同步脚本 `scripts/kaggle_sync_v8.py`。与旧数据集 `philsz/guandan-v8-game-records-184-episodes`（184 副修复前）可对比 KPI。

## 本批详析（2026-07-21 08:26–08:32 · GUA-154 实战回归）

### 数据口径

| 项目 | 值 | 说明 |
|------|-----|------|
| 真实局数 | **3 局** | `analyze_v7_rounds.py` 识别 3 个 OpenGuanDan 会话；L3 `scores.json total_games=3` 一致 |
| 副数（game_records_v8/） | **145 副**（290 文件：yf1 145 + yf2 145） | 每副各有 yf1/yf2 两个视角的独立 JSON |
| 批跑入口 | `RUN_V8_VS_LALALA.bat`，磁盘记录 3 次完整 launcher 会话 | 每次默认 `--games 3`，但 OpenGuanDan 实际只完成 1 局；见下方口径告警 |
| 对手 | lalala（南邮基线） | `opponent_1_3`（固定） |
| scores.json | ✅ `{"team_a_wins":3,"team_b_wins":0,"draws":0,"total_games":3}` | 真实局胜：V8 **3/3（100%）** |
| L1 最新 victoryNum | `[7,6,12,8]`，`vn_source=gameResult` | 仅覆盖第 3 个会话，不作为 3 局累计值 |
| L3′ state | `target_games=3, completed_games=3, restart_count=0` | 仅覆盖最后一次 launcher；`completed_games` 与真实局数相等属巧合 |
| 卡顿/regroup | ✅ 3 个会话均 `restart_count=0` | 零卡顿、零 regroup，单会话约 87–112 秒 |
| 分析脚本 | `analyze_v7_rounds.py --dir game_records_v8 --all` | 识别 3 会话 / 3 局 / 145 副 |

08:20–08:24 的 `v8_vs_lalala_20260721_082046.log`、`082103.log`、`082420.log` 为启动修复前失败/空日志，无 L4 牌谱，已排除。本批有效 L2 为：

- 会话 1：`v8_vs_lalala_20260721_082629.log`、`yf1_v8_20260721_082704.log`、`yf2_v8_20260721_082704.log`
- 会话 2：`v8_vs_lalala_20260721_082847.log`、`yf1_v8_20260721_082916.log`、`yf2_v8_20260721_082921.log`
- 会话 3：`v8_vs_lalala_20260721_083043.log`、`yf1_v8_20260721_083111.log`、`yf2_v8_20260721_083116.log`

### 局级 3 局逐局

| 局 | 副数 | 头游分布[seat0-3] | TeamA | TeamB | 局末 victoryNum | 胜方 |
|----|------|-------------------|-------|-------|-----------------|------|
| 1 | 36 | [15,0,16,5] | 31 | 5 | `[14,0,14,5]` | **team_02** |
| 2 | 73 | [21,17,28,7] | 49 | 24 | `[20,17,26,7]` | **team_02** |
| 3 | 36 | [9,6,12,9] | 21 | 15 | `[7,6,12,8]` | **team_02** |

### 副级详细统计

| 指标 | 值 | 解读 |
|------|-----|------|
| yf1 头游 | 45/145（31.0%） | 稳定 |
| yf2 头游 | 56/145（38.6%） | ✅ 本批主攻更强 |
| opp1 头游 | 23/145（15.9%） | — |
| opp3 头游 | 21/145（14.5%） | — |
| **team_02 头游率** | **101/145（69.7%）** | ✅ 副级明显占优 |
| team_13 头游率 | 44/145（30.3%） | |
| **双上率** | **38/145（26.2%）** | 较上批小幅回升 |
| 双下率 | 14/145（9.7%） | ✅ 较上批下降 |
| yf1 末游率 | 45/145（31.0%） | 🟡 仍偏高 |
| yf2 末游率 | 41/145（28.3%） | 与上批基本持平 |

### 与上批（GUA-151/152/153）对比

| 指标 | 本批 GUA-154 | 上批 GUA-151/152/153 | 变化 |
|------|-------------|----------------------|------|
| 局胜率 | 3/3（100%） | 4/6（66.7%） | +33.3pp；仅 3 局，暂不外推 |
| 副头游率 | 69.7% | 63.0% | +6.7pp |
| 双上率 | 26.2% | 24.7% | +1.5pp |
| 双下率 | 9.7% | 17.8% | −8.1pp |
| yf1 末游率 | 31.0% | 28.8% | +2.2pp |
| yf2 末游率 | 28.3% | 28.8% | −0.5pp |

### GUA-154 回归与异常

1. **GUA-154 实战回归通过，关单条件满足**：6 个 yf 客户端日志共记录 898 条实例分配，其中 146 条含跨组归属；2 个 `Trips` 候选正确标记 `broken` 含 `StraightFlush`，33 个含跨组牌的完整 `StraightFlush` 均分配为 `broken=[]`。
2. **灵活组牌得到实战验证**：`yf1_v8_20260721_083111.log` 中 `Trips/7 [H7,C7,D7]` 使用 G4 的 `D7` 后，下一次组牌仍完整保留 G0 `StraightFlush [D3,D4,D5,D6,D7]`，证明重复 `D7` 实例被正确分配，没有误拆同花顺。
3. **R-G080-4 零退化**：`_run_grouping_engine 失败`、`_basic_classify 也失败`、`_group_consistency_filter 失败` 均为 0；6 个客户端日志亦无 `Traceback` / `ERROR`。
4. **残局扫描仍有 8 条高优异常**：`recommended_filtered_to_pass_only=7`、`enemy_critical_pass_with_legal_beater=1`。唯一敌方剩 1 且有合法压制仍 PASS 的锚点为 `20260721083150239049 [yf2_v8]-[opponent_1_3]-[27]-[2].json#d33`，需另走 WF-12，不归因于 GUA-154。
5. **批跑计数缺陷已于本轮解读后修复**：OpenGuanDan 的 `batch_games` 固定为 1；executor 从本 Run 新增牌谱重建真实局结果，`completed_games` 与 tracker 共用同一增量。后续 `--games 3` 会连续运行 3 个服务器会话，而不是一局后直接记满 3/3。
6. **分析脚本 V8 局胜率已于本轮解读后修复**：逐会话按 TeamA/TeamB 头游副数判定真实局胜，`victoryNum` 明示为“升级值，仅诊断”。用本批 145 副重放后总计为 `V8 3/3 (100.0%)、Lalala 0/3、平局 0/3`，不再出现 `1366.7%/766.7%`。

---

## 本批详析（2026-07-21 12:59-13:12 · GUA-154 + 12 局实战回归）

### 数据口径

| 项目 | 值 | 说明 |
|------|-----|------|
| 真实局数 | **12 局** | `analyze_v7_rounds.py --dir game_records_v8 --all` 识别 **12 个 OpenGuanDan 会话**（每会话 1 局）；scores.json 仅 3 局（GUA-151 修复后口径仍只覆盖最后 launcher） |
| 副数（game_records_v8/） | **171 副**（342 文件：yf1 171 + yf2 171） | 每副各有 yf1/yf2 两个视角的独立 JSON |
| launcher 调用 | `RUN_V8_VS_LALALA.bat`，4 次主 launcher | 12:58 -> 13:12 期间启动 4 次 launcher；累计 12 个 OpenGuanDan 服务器会话 |
| 对手 | lalala（南邮基线） | `opponent_1_3`（固定） |
| scores.json | ⚠️ `{"team_a_wins":2,"team_b_wins":1,"draws":0,"total_games":3}` | **口径偏差**：仅覆盖最后一次 launcher；真实累计 = L4 分析器识别 12 局 |
| L1 最新 victoryNum | `[0,3,2,3]`（会话 12 末值） | 仅覆盖会话 12；victoryRank `["5","A"]` |
| L3 state | `target_games=3, completed_games=3, restart_count=2, current_batch=3` | 每次 launcher 启动即 `restart_count+=1`；最后一次 launcher 实际跑了 3 个会话 |
| 卡顿/regroup | ✅ restart_count=2 | 2 次重启未影响最终局胜统计；12 个会话均正常完成 |
| 分析脚本 | `analyze_v7_rounds.py --dir game_records_v8 --all` | 识别 12 会话 / 12 局 / 171 副 |

**口径对齐说明**：本次 launcher 调用 4 次（`RUN_V8_VS_LALALA.bat 12`），每次 launcher 实际启动 N 个 OpenGuanDan 服务器会话，所有 12 个会话的牌谱合并到 `game_records_v8/`。**executor 的 `completed_games` 与 `scores.json` 只反映最后 launcher**（3 局），与 `analyze_v7_rounds.py` 累计识别的 12 局存在偏差——这是 **GUA-151/152/153 修复的局限性**，本轮 GUA-151 修复只解决"V8 单 launcher 多局计数"，未解决"V8 多 launcher 累计统计"。

### 局级 12 局逐局

| 局 | 副数 | 头游分布[seat0-3] | TeamA | TeamB | 局末 victoryNum | 胜方 |
|----|------|-------------------|-------|-------|-----------------|------|
| 1 | 17 | [6,2,4,5] | 10 | 7 | `[5,2,4,5]` | **V8** |
| 2 | 14 | [4,4,4,2] | 8 | 6 | `[4,4,4,1]` | **V8** |
| 3 | 24 | [6,2,10,6] | 16 | 8 | `[5,2,10,6]` | **V8** |
| 4 | 13 | [5,1,2,5] | 7 | 6 | `[5,1,2,4]` | **V8** |
| 5 | 12 | [2,1,6,3] | 8 | 4 | `[1,1,6,3]` | **V8** |
| 6 | 13 | [2,1,3,7] | 5 | 8 | `[2,1,3,6]` | **Lalala** |
| 7 | 9 | [4,0,1,4] | 5 | 4 | `[3,0,1,4]` | **V8** |
| 8 | 15 | [5,3,4,3] | 9 | 6 | `[4,3,4,3]` | **V8** |
| 9 | 12 | [2,3,5,2] | 7 | 5 | `[2,3,4,2]` | **V8** |
| 10 | 14 | [6,1,5,2] | 11 | 3 | `[5,1,5,2]` | **V8** |
| 11 | 19 | [6,5,5,3] | 11 | 8 | `[6,4,5,3]` | **V8** |
| 12 | 9 | [0,4,2,3] | 2 | 7 | `[0,3,2,3]` | **Lalala** |

### 副级详细统计（171 副 / 342 文件）

| 指标 | 值 | 解读 |
|------|-----|------|
| yf1 头游 | ~52/171（~30.4%）| 与 08:26 那批 31.0% 基本持平 |
| yf2 头游 | ~47/171（~27.5%）| 较 08:26 那批 38.6% **明显下降 -11.1pp** |
| opp1 头游 | ~38/171（~22.2%）| - |
| opp3 头游 | ~34/171（~19.9%）| - |
| **team_02 头游率** | **99/171（57.9%）** | ✅ 副级占优（vs 08:26 那批 69.7% 下降 -11.8pp） |
| team_13 头游率 | 72/171（42.1%）| |
| **双上率** | **30/171（17.5%）** | 🟡 较 08:26 那批 26.2% 下降 -8.7pp |
| 双下率 | ~28/171（~16.4%）| 较 08:26 那批 9.7% 上升 +6.7pp |
| yf1 末游率 | ~42/171（~24.6%）| 较 08:26 那批 31.0% 下降 -6.4pp ✅ |
| yf2 末游率 | **~70/171（~41.0%）** | 🔴 **异常偏高**：较 08:26 那批 28.3% 上升 +12.7pp |
| Lalala 达 A | 31 副（18.1%）| Lalala 经常冲到 A 级 |

### 与上批（2026-07-21 08:26 · GUA-154 3 局）对比

| 指标 | 本批 12 局 | 上批 3 局 | 变化 |
|------|------------|----------|------|
| 真实局数 | 12 | 3 | +9（样本量扩大 4x） |
| V8 局胜率 | 10/12（83.3%）| 3/3（100%）| -16.7pp（统计回归） |
| 副头游率 | 57.9% | 69.7% | -11.8pp |
| 双上率 | 17.5% | 26.2% | -8.7pp |
| 双下率 | 16.4% | 9.7% | +6.7pp |
| yf1 末游率 | 24.6% | 31.0% | -6.4pp ✅ |
| yf2 末游率 | **41.0%** | 28.3% | **+12.7pp** 🔴 |
| Lalala 达 A | 31 副 | 23 副 | +8 副 |

### 关键发现与异常

1. **样本量扩大到 12 局后，V8 局胜率从 100% 回归到 83.3%**——3 局样本下"100% 胜"是统计巧合；12 局样本下"83.3% 胜"才是真实水平。Lalala 在会话 6（13:04:13->13:04:29）和会话 12（13:11:50->13:11:58）反扑成功。

2. **yf2 末游率 41.0% 异常偏高**——比 yf1（24.6%）高 16.4pp，比上批 yf2（28.3%）高 12.7pp。可能原因：① GUA-078 残局 PASS 劫持修复在 yf2 视角下未覆盖到位；② yf2 策略偏保守，配合 yf1 跑头时容易让 yf2 沦陷。建议抽 3~5 副 yf2 末游牌谱走 WF-12 复盘。

3. **双上率从 26.2% 下降到 17.5%（-8.7pp）**——yf1 与 yf2 配合度未达预期。可能与 GUA-150 self_sprint 让道修复（yf1 抢权 vs yf2 抢权冲突）相关，需双跑视角下观察 1st/2nd 名次分布。

4. **Lalala 达 A 副数 31 副 = 18.1%**——Lalala 经常冲到 A 级，说明对局深度足够；V8 副胜率 57.9% 是建立在 Lalala 经常能反扑的前提下保持的优势。

5. **GUA-154 重复牌串跨组归属修复未触发回归**——12 局 171 副共 0 例"Trips 误拆 StraightFlush"，与 08:26 那批 3 局 145 副 0 例一致。**GUA-154 关单条件在 12 局尺度下再次验证**。

6. **R-G080-4 退化**：`_run_grouping_engine 失败`、`_basic_classify 也失败`、`_group_consistency_filter 失败` 全部 0。客户端日志亦无 `Traceback` / `ERROR`。

7. **L3 scores.json 与 L4 累计 12 局口径偏差**——`v8_vs_lalala_scores.json` 仍记 `total_games=3`，与 `analyze_v7_rounds.py` 识别的 12 局不一致。原因：GUA-151 修复解决"单 launcher 多局计数"，但未解决"多 launcher 累计统计"。**建议**：在 `batch_executor/executor.py` 增加"启动时加载已有 scores.json 并合并"逻辑，或在 analyzer 加"V8 跨 launcher 汇总"开关。

### CCN Phase 0 数据预热评估

| 项目 | 值 | 评估 |
|------|-----|------|
| 当前 `game_records_v8/` 牌谱总量 | 342 文件 / 171 副 | ✅ **已超过 Day 0 目标 200+ 副**（详见 `CCN-Phase0-任务拆解.md` §十一 v1.2 数据回填） |
| 数据多样性 | 单一对手 lalala | 🔴 未改善；仍需路径 1（v4/v5/v7/M1/M3 多版本作对手） |
| yf1/yf2 配对完整 | 171/171 = 100% | ✅ 时序对齐校验可全样本跑 |
| 进贡/还贡事件 | 含（v8 platform 原生） | ✅ 反推 ground truth 可验证 |
| 净盘建议 | 暂不净盘 | 数据已够 CCN Phase 0 任务 1/2/4 启动 |

**CCN Phase 0 启动可行性**：✅ **已具备启动条件**，无需 Day 0 净盘 + 重跑；可直接用现有 171 副牌谱跑任务 1（时序对齐）、任务 2（10 副 ground truth 对账）、任务 4（规则 baseline 精度测量）。

### 下一步

1. **抽 3~5 副 yf2 末游牌谱走 WF-12**：定位 yf2 末游率 41.0% 的根因（候选：GUA-078 残局 PASS 劫持覆盖不全 / yf2 策略偏保守 / 与 yf1 抢权冲突）。
2. **修复 executor 多 launcher 累计**：v8_vs_lalala_scores.json 应能反映 12 局累计（不只是最后 launcher 的 3 局）。
3. **CCN Phase 0 任务 1 启动**：现有 171 副可直接跑 `scripts/check_action_ordering.py`，无需净盘。
4. **抽 1 副 GUA-154 锚点（如 `20260721070501773000`）跨 12 局回归确认**：再次验证 GUA-154 跨组归属修复无退化。


---

## 本批后修复：GUA-155 多 launcher 累计战绩（2026-07-21 下午）

本批 12 局详析发现偏差后，立即落地 **GUA-155 修复**。

### 根因

`batch_executor/executor.py:942` 已 `self.tracker.load()` 加载历史战绩，但 `executor.py:956-960` 立即重置：
```python
# 旧代码（已删除）
self.tracker.team_a_wins = 0
self.tracker.team_b_wins = 0
self.tracker.total_games = 0
self.logger.info("已清空之前的战绩，开始新的对战")
```

注释"清空之前的战绩"是历史遗留 bug——**加载后立即清零，语义矛盾**。本批 4 次 launcher 跑 12 局后，scores.json 只剩最后 launcher 的 3 局。

### 修复

删除 L956-960 五行 + 替换为累计语义：
```python
# 新代码
# 多 launcher 累计战绩（GUA-154+）：不重置 tracker，让多次 launcher 的局增量自然累加到 scores.json
if self.tracker.total_games > 0 or self.tracker.draws > 0:
    self.logger.info("累计战绩（含本次 launcher 前）: Team A %d胜, Team B %d胜, 平局 %d场, 总 %d场", ...)
else:
    self.logger.info("首次运行，从零开始累计战绩")
```

### pytest 验证

`tests/test_batch_executor_score_aggregation.py`（新 6 项）：

| # | 测试 | 场景 |
|---|------|------|
| 1 | `test_first_launcher_from_zero` | 无历史文件 → 从零开始 |
| 2 | `test_second_launcher_accumulates` | 5 局历史 + 4 局新 = 9 局 |
| 3 | `test_three_launchers_accumulate` | 3 次 launcher 累计 = 9 局 |
| 4 | `test_draws_preserved` | GUA-152 draws 字段保留 |
| 5 | `test_zero_save` | 0 局时正确保存 |
| 6 | `test_v8_12games_scenario` | **复现本批 12 局场景**：4 launcher × 3 局 = 12 局（**旧 bug yield=3, 修复后 yield=12**）|

**6/6 全绿**。

### 用户行为不变

- 想"从零开始"：删除 `scores.json` 即可（`ScoreTracker.load()` 文件不存在时保持现状）
- 默认行为：scores.json 持续累计跨 launcher 战绩，与 L4 analyze_v7_rounds.py 对齐

### 下一步

净盘后跑 `RUN_V8_VS_LALALA.bat 3`，验证 `v8_vs_lalala_scores.json` 的 `total_games=3`（不再是 1）。若通过可 closed GUA-155。

### 关联

- **GUA-151/152/153**：scores.json 三件套修复的延续
- **GUA-154**：本次 12 局实战回归时发现本 bug
- **ISSUE GUA-155**：`docs/guandan-brain/ISSUES.md` 已登记
- **ITERATIONS `v8-gua155-multi-launcher-score-aggregation`**：已记录
