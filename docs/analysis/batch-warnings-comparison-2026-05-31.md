# 批跑 WARNING 对照表（M3 10 局 vs M1 12 局）

**生成时间**：2026-05-31 22:09:16

## 来源

| 批跑 | batch_executor 日志 | 客户端 | ITERATIONS |
|------|---------------------|--------|------------|
| **M3 净盘 10 局** | `logs/batch_executor_20260531_201339.log` | `yf1_m3`/`yf2_m3` ×4 批 | GUA-022/026 M3 净盘批跑 |
| **M1 净盘 12 局** | `logs/batch_executor_20260531_204844.log` | `yf1_m1`/`yf2_m1` ×4 批 | GUA-022 M1 净盘 12 局 |

## 数量总览

| 来源 | M3 10 局 | M1 12 局 |
|------|----------|----------|
| batch_executor WARNING | 5 | 7 |
| 客户端 WARNING（yf1+yf2 合计） | 210 | 10427 |

**完整客户端 WARNING 原文**（逐行、未去重）见：

- [`batch-warnings-m3-10-full.txt`](./batch-warnings-m3-10-full.txt)
- [`batch-warnings-m1-12-full.txt`](./batch-warnings-m1-12-full.txt)

## 分类对照（客户端）

| 分类 | M3 10 局 | M1 12 局 | 说明 |
|------|----------|----------|------|
| GUA-033：gameResult fallback | 2 | 0 | batch_games=1；服务器 vn 为 3 局合计 |
| GameRecorder：卡牌验证 | 208 | 79 | 出牌与初始手牌快照校验 |
| GameRecorder：手牌扣减 | 0 | 48 | 期望移除张数与实际不符 |
| M1：PASS 强制改出 | 0 | 141 | StageRouter coerce 非 PASS |
| M1：actIndex 越界兜底 | 0 | 281 | 决策 index 非法 → 0(PASS) |
| M1：保护组合跳过 | 0 | 9260 | OpeningActive 拆结构保护 |
| M1：待回填 victoryNum | 0 | 222 | episodeOver 先落盘、gameResult 后回填 |
| M1：抗贡通知未识别 | 0 | 44 | stage=anti-tribute |
| M1：阶段 handler fallback | 0 | 194 | Endgame 等分支 fallback |
| 其他 | 0 | 158 | 见完整原文文件 |

---

## batch_executor WARNING 完整原文

### M3 净盘 10 局（5 条）

```text
2026-05-31 20:13:59 - WARNING - 检测到参数不匹配!
2026-05-31 20:15:22 - WARNING - 本批 match_key 增量(58) 远大于 batch_games(3)；落盘副数不等于平台批次数，分析 PASS/胜率时请区分口径。
2026-05-31 20:16:44 - WARNING - 本批 match_key 增量(49) 远大于 batch_games(3)；落盘副数不等于平台批次数，分析 PASS/胜率时请区分口径。
2026-05-31 20:17:57 - WARNING - 本批 match_key 增量(30) 远大于 batch_games(3)；落盘副数不等于平台批次数，分析 PASS/胜率时请区分口径。
2026-05-31 20:19:14 - WARNING - 本批 match_key 增量(34) 远大于 batch_games(1)；落盘副数不等于平台批次数，分析 PASS/胜率时请区分口径。
```

### M1 净盘 12 局（7 条）

```text
2026-05-31 20:49:04 - WARNING - 检测到参数不匹配!
2026-05-31 20:50:17 - WARNING - 本批 match_key 增量(27) 远大于 batch_games(3)；落盘副数不等于平台批次数，分析 PASS/胜率时请区分口径。
2026-05-31 20:50:17 - WARNING - 批末未找到 latest_victory_num.json，无法交叉验证 victoryNum（batch_games=3）
2026-05-31 20:51:34 - WARNING - 本批 match_key 增量(19) 远大于 batch_games(3)；落盘副数不等于平台批次数，分析 PASS/胜率时请区分口径。
2026-05-31 20:51:34 - WARNING - 批末未找到 latest_victory_num.json，无法交叉验证 victoryNum（batch_games=3）
2026-05-31 20:52:42 - WARNING - 批末未找到 latest_victory_num.json，无法交叉验证 victoryNum（batch_games=3）
2026-05-31 20:53:51 - WARNING - 批末未找到 latest_victory_num.json，无法交叉验证 victoryNum（batch_games=3）
```

---

## 客户端 WARNING 按文件对照

| 文件 | M3 WARNING 数 | M1 WARNING 数 |
|------|---------------|---------------|
| 批1 `yf1_m3_20260531_201407.log` | 25 | — |
| 批1 `yf1_m1_20260531_204913.log` | — | 1531 |
| 批1 `yf2_m3_20260531_201414.log` | 31 | — |
| 批1 `yf2_m1_20260531_204920.log` | — | 280 |
| 批2 `yf1_m3_20260531_201530.log` | 33 | — |
| 批2 `yf1_m1_20260531_205025.log` | — | 2975 |
| 批2 `yf2_m3_20260531_201537.log` | 32 | — |
| 批2 `yf2_m1_20260531_205033.log` | — | 2229 |
| 批3 `yf1_m3_20260531_201652.log` | 20 | — |
| 批3 `yf1_m1_20260531_205143.log` | — | 254 |
| 批3 `yf2_m3_20260531_201700.log` | 21 | — |
| 批3 `yf2_m1_20260531_205150.log` | — | 792 |
| 批4 `yf1_m3_20260531_201805.log` | 22 | — |
| 批4 `yf1_m1_20260531_205251.log` | — | 96 |
| 批4 `yf2_m3_20260531_201812.log` | 26 | — |
| 批4 `yf2_m1_20260531_205258.log` | — | 2270 |

---

## 批末对账（M3 第 4 批，INFO 非 WARNING，供对照）

```text
2026-05-31 20:15:22 - INFO - 批末 victoryNum 校验通过: vn=[1, 2, 1, 2], batch_games=3, Team0=1 Team1=2
2026-05-31 20:16:44 - INFO - 批末 victoryNum 校验通过: vn=[2, 1, 2, 1], batch_games=3, Team0=2 Team1=1
2026-05-31 20:17:57 - INFO - 批末 victoryNum 校验通过: vn=[3, 0, 3, 0], batch_games=3, Team0=3 Team1=0
2026-05-31 20:19:14 - INFO - 批末对账：采用 vn=[1, 0, 1, 0] (vn_source=fallback)，服务器 RAW=[3, 0, 3, 0]
2026-05-31 20:19:14 - INFO - 批末 victoryNum 校验通过: vn=[1, 0, 1, 0], batch_games=1, Team0=1 Team1=0
```

---

## 解读要点

1. **「检测到参数不匹配」**：两次均有；根因是 v1006 exe 不在 stdout 打印 argv 局数，非批跑失败。
2. **「match_key 增量 >> batch_games」**：副（episodeOver）≠ 局（gameOver）；分析 PASS 用牌谱，队胜用批末 vn。
3. **M1 四次「未找到 latest_victory_num.json」**：M1 客户端未写该文件；M3 由 `yf1_m3` 写入。
4. **M3 批 4 gameResult fallback**：见 `yf1_m3_20260531_201805.log` 与 platform-data-interpretation §4.3.1。
5. **M1 客户端 WARNING 远多于 M3**：大量 OpeningActive 保护组合、actIndex 越界；M3 以 GameRecorder 卡牌校验为主。

## 再生成

```bash
python scripts/tools/export_batch_warnings_comparison.py
```