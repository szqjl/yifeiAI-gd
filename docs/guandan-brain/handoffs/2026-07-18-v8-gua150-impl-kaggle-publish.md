# Handoff: GUA-150 实施 + Kaggle 公开 KPI（2026-07-18）

> **下次接续入口**：读完本文件即可继续工作，无需重读全部上下文
> **生成时间**：2026-07-18（周六）
> **会话主线**：WF-12 复盘 → GUA-150 登记 → 实施 → commit → Kaggle 公开

---

## 1. 一句话总结

完成了 GUA-150（R-D09 self_sprint 让道误判）**全链路闭环**：复盘 → 5 问准入 → 代码修复 → pytest 验证 → commit+push。**额外达成 V8 项目里程碑**：首次将 184 副牌谱 + 完整 KPI 量化数据**公开发布到 Kaggle**，为后续 BC → Self-play RL 范式切换建立基线。

---

## 2. 已完成的工作（按时间顺序）

### 2.1 WF-12 决策链路复盘
- **牌谱**：`game_records_v8/20260716222448436062 [yf1_v8]-[opponent_1_3]-[12]-[2].json`
- **步 35/79**：yf1 持 7 张 `[H8,S8,D8,H8,D8,CT,SB]`（5 星 8 炸+CT+SB），平台 actionList 6 项含 `Single/B[SB]`（idx=1），3 手可清牌。但引擎 GUA-135 self_sprint 让道 PASS
- **错误** Q0（workbuddy 写的）+ **正确** Q1（你写我分析）报告：`docs/analysis/WF-12-20260716222448436062-副12-yf1-Q1让道决策分析.md`

### 2.2 GUA-150 登记 + 5 问准入
- 5 问全通过（一类局面 / 可沉意图层 / P0 止血 / pytest+trace+批跑闭环 / 迁移出口=GUA-091）
- ISSUES.md：GUA-150 行 + 交叉引用表 + 当前活跃

### 2.3 GUA-150 实施
- `src/v/nn/endgame/endgame_decide.py`：
  - 新增 `_find_min_non_bomb_lead_action()` — 找最小非炸非 PASS 动作（按型优先级）
  - 新增 `_estimate_self_num_rounds()` — 基于 `game_state["handCards"]` 直接算 self 冲刺手数
  - 情形 2 改 intent 比较（`self_hands ≤ teammate_hands` → 选 TWT/最小非炸非 PASS 夺权）
- `tests/test_gua150_self_sprint_short_path.py`：**6/6 ✅**
- GUA-135 原 28/28 ✅ 未破坏
- GUA-137/138/142 全部通过（**GUA-136 2 failed 预先存在**，stash 后仍失败，与本修复无关）

### 2.4 Commit + Push
- Commit `ad52a50` → `origin/v8-dev`（Gitee）
- 8 文件：endgame_decide.py + test_gua150 + 文档 + 之前未提交的 V8 scores.json 修复 + v8-win-rate-history.md

### 2.5 🆕 Kaggle 公开里程碑（项目历史首次）
- **账号**：`philsz`（Kaggle 用户名 `guandanny`）
- **Dataset**：`guandanny/guandan-v8-game-records-184-episodes`（184 副牌谱，830KB zip，**重命名去 `[]` 字符**）
- **Notebook**：`philsz/guandan-v8-data-exploration-184-episodes-31-5`（V8 项目历史首份公开 KPI）
- **V8 牌谱真实 schema**（与 V7 不同）：
  - 顶层字段：`game_id, start_time, player_id, player_name, initial_hand, all_players_hands, game_info, actions, my_decisions, result, game_round, end_time, duration`
  - **名次字段**：`result.order` = `[头游座位, 二游, 三游, 末游]`（**不是** V7 的 `episodeOver`）
  - **没有** `gameResult.victoryNum`（V8 用 `result.game_count` 累计）

### 2.6 公开 KPI 量化基线（**V8 项目历史首份**）

| 指标 | V8 队 | 评级 |
|------|:---:|:---:|
| 头游率 | 35.3% | 🟡 偏低 |
| 末游率 | 32.1% | 🔴 偏高 |
| 双上率 | **31.5%** | 🟡 中等 |
| 平均决策 | 25.5 手/副 | ✅ |
| 决策速度 | 0.62s/副 | ✅ |

**核心结论**：头游率与末游率双高 → **决策两极分化**，单靠规则补丁无法收敛。

---

## 3. 关键文档改动汇总

| 文件 | 改动 |
|------|------|
| `docs/guandan-brain/ISSUES.md` | GUA-150 行 + 交叉引用 + 当前活跃 P0 |
| `docs/guandan-brain/ITERATIONS.md` | ① 迭代行 `v8-gua150-self-sprint-yield-misjudge`（登记）<br>② 迭代行 `v8-gua150-impl + kaggle-publish`（实施+Kaggle）<br>③ 顶部"当前活跃"追加 GUA-150 实施完成 |
| `docs/analysis/WF-12-20260716222448436062-副12-yf1-Q1让道决策分析.md` | WF-12 报告（含 5 问审查表 + 实施清单） |
| `src/v/nn/endgame/endgame_decide.py` | GUA-150 实施（+106 行） |
| `tests/test_gua150_self_sprint_short_path.py` | 新增 6 条 pytest |
| `game_records_v8_kaggle/` | 184 个 JSON（重命名去 `[]`） |
| `kaggle_upload.zip` | 830KB（**上传后已删**，数据在 Kaggle） |

---

## 4. 下一步建议（按优先级）

### 4.1 净盘 + 跑批验证 GUA-150 效果（**最该做**）

```powershell
# V8 净盘
Get-Process guandan_offline_v1006 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item tmp\.batch_executor.lock -ErrorAction SilentlyContinue
Get-ChildItem game_records_v8 -Filter *.json | Remove-Item -Force
Remove-Item v8_vs_lalala_scores.json, v8_vs_lalala_state.json -ErrorAction SilentlyContinue
Remove-Item batch_executor\latest_victory_num.json, batch_executor\current_batch.json -ErrorAction SilentlyContinue
Get-ChildItem logs -File -ErrorAction SilentlyContinue | Remove-Item -Force

# 跑批（建议 6 局 = 180+ 副）
.\RUN_V8_VS_LALALA.bat --target-games 6
```

- **预期**：GUA-150 修复后头游率应上升、末游率应下降、双上率应改善
- **trace 验证**：日志搜 `GUA-150 self_sprint_priority` 看是否触发 + self 多手绕路是否消失

### 4.2 Kaggle notebook 更新 KPI 对比
- 跑批结束后，在 Kaggle notebook 上**更新数据**（用新批次的 184+ 副覆盖）
- 标题加 v2 后缀：`Guandan V8: Data Exploration v2 (post GUA-150)`
- 关键对比：修复前 35.3% / 32.1% / 31.5% vs 修复后 X% / Y% / Z%

### 4.3 BC 预训练 notebook（**真正的破局**）
- 在 Kaggle 上做第 3 个 notebook：`Guandan V8: BC Pretraining Demo`
- 从 `guandan-v8-game-records-184-episodes` 读牌谱
- 用 PyTorch Lightning 训练一个简单模型（输入：牌局状态 → 输出：每个候选动作的分数）
- 哪怕只跑 5 epoch，**这是 V8 项目从"规则补丁"切换到"训练管线"的第一个里程碑**

### 4.4 收尾：清 `game_records_v8_kaggle/` 与 `kaggle_upload.zip`
- 当前状态：`game_records_v8_kaggle/` 184 文件还在（**Layer 2**，禁止 commit）；`kaggle_upload.zip` 已删
- 跑批完成后**新一批牌谱需要重新走重命名+打包流程**上传到 Kaggle
- **建议**：保留 `game_records_v8_kaggle/` 作为 Kaggle 同步备份目录，写个 `tools/kaggle_sync.ps1` 自动化

---

## 5. 已知的非阻塞问题

| # | 问题 | 影响 | 处理 |
|---|------|------|------|
| 1 | `tests/test_gua136_player_remaining_enhance.py` 2 failed | 预先存在，与 GUA-150 无关 | 暂搁置，下次专查 |
| 2 | `kaggle_upload.zip` 上传后被 Kaggle 处理，文件本地状态可能变化 | 仅影响下次同步 | 跑批后重做 |
| 3 | Kaggle notebook `ConcurrencyViolation Sequence number` 保存错误 | UI bug | 等 2 分钟重试或 Quick Save |
| 4 | Lightning AI Studio "点了没反应" | 平台问题 | 改用 Kaggle 跑（已达成） |

---

## 6. 关键文件路径速查

```
# 代码
src/v/nn/endgame/endgame_decide.py            # GUA-150 实施点 L3416-3424
tests/test_gua150_self_sprint_short_path.py   # 6/6 pytest

# 文档
docs/guandan-brain/ISSUES.md                  # GUA-150 行
docs/guandan-brain/ITERATIONS.md              # v8-gua150-impl 迭代行
docs/analysis/WF-12-20260716222448436062-副12-yf1-Q1让道决策分析.md
docs/guandan-brain/handoffs/2026-07-18-v8-gua150-impl-kaggle-publish.md  # 本文件

# 数据
game_records_v8/                              # 原始牌谱（184 副）
game_records_v8_kaggle/                       # Kaggle 同步副本（重命名去 []）
batch_executor/v8_vs_lalala_scores.json       # 跑批战绩

# Kaggle
https://www.kaggle.com/datasets/philsz/guandan-v8-game-records-184-episodes
https://www.kaggle.com/code/philsz/guandan-v8-data-exploration-184-episodes-31-5
```

---

## 7. 用户的"补丁螺旋"痛苦（重要上下文）

- 用户在 7/18 早些时候说："我现在痛苦的是，还是在为 v8 一条一条补写规则，相当于缝合怪"
- 诊断：用户在阶段 A（补丁主脑）螺旋，治理文档三年前就预警过
- 出路：
  1. **停止补丁膨胀**：每条新 GUA 严格过 5 问，第 2 问不过就驳回
  2. **中期启动训练管线**：用现有 184 副牌谱跑 BC 预训练
  3. **长期降级规则**：把 Q1/stage_2/heuristic 全部降为 safety constraint
- **今天做的就是**：
  - GUA-150 已严格按 5 问准入实施（**不是又一条补丁，是一次架构收敛**）
  - Kaggle 公开是**训练管线启动的第一块基石**（数据有了，且公开可访问）
  - **下一步就是 BC 预训练 notebook**（破补丁螺旋的真正起点）

---

## 8. 复盘：今天最有价值的 3 件事

1. **GUA-150 全链路闭环**（5 问准入 + 实施 + pytest + commit）—— 这是项目第一次**不补一条规则，而是沉一个状态**
2. **V8 牌谱真实 schema 揭示**（`result.order` vs V7 `episodeOver`）—— 给后续 BC 数据加载铺平路
3. **Kaggle 公开首份 KPI**（184 副 / 头游 35.3% / 末游 32.1% / 双上 31.5%）—— 把"感觉"变成"数据"

---

**接续方式**：下次开会读本文件 → 看 §4 下一步 → 选 4.1（净盘跑批）or 4.3（BC 训练）开工。
