# 新开 Agent · 第一句（复制即用）

> **你找的就是这个文件。** 新开 Cursor / Opencode 会话时，把下面整句粘贴给 Agent 作为**第一条消息**。

---

## 默认（推荐）

```text
先按 docs/guandan-brain/README.md「Agent 批跑数据入门（5 分钟）」读完并完成自测，再读 ITERATIONS 最新一行，然后等我派任务。
```

---

## 换一句（按场景）

| 场景 | 第一句 |
|------|--------|
| 只分析 log / 胜率 | `先读 README §Agent 批跑数据入门 和 platform-data-interpretation §1～3，自测通过后再解读数据。` |
| 换机接续 | `按 handoff 接续：先 README §Agent 批跑数据入门 自测，再读 ITERATIONS 最新一行 + docs/analysis/handoffs/ 最新一篇。` |
| 只改决策/策略 | `改 M3 决策前先读 ISSUES open（m3 标签）、ITERATIONS 最新一行、PRINCIPLES_MAPPING 相关节、EVAL；M1 frozen 不改策略；局/副口径见 README §Agent 批跑数据入门。` |
| **提交 / 推送** | 见 **[`AGENT_PUSH_CHECKLIST.md`](./AGENT_PUSH_CHECKLIST.md)** 默认第一句 |
| **GUA-033 / vn 对账** | 见下方 **§ GUA-033 定音** 整段复制 |

---

## GUA-033 定音（exe 固定 3 局 + fallback，复制即用）

```text
先读 platform-data-interpretation §2 + §4.3.1，再动批跑/victoryNum 相关代码或报告。

定音五句：
1. 台账 batch_games 真源 = batch_executor/current_batch.json，不是 WebSocket settingTimes。
2. 本包 v1006 offline exe 单次会话固定 3 平台局；argv 1/3/10 实测均无效。
3. gameResult.victoryNum 是会话 3 局合计，禁止裸信；[0]+[1]≠batch_games 时用 gameOver 计数 fallback。
4. batch_games=1 时 fallback 只认领 curTimes=1 → 落盘 [0]+[1]=1；不等于「平台只打 1 局」。
5. 对账看 batch_executor/latest_victory_num.json：victoryNum=采用值，server_vn_raw=WebSocket 原文，vn_source=server|fallback。

自测通过后回复：「已掌握 batch_games vs 平台 3 局 vs fallback，可解译 vn。」
```

---

## Agent 应回复什么

自测通过后应确认一句：**「已掌握局/副/victoryNum 口径，可接任务。」** 再往下派活。

---

## 批跑数据恢复（game_records 丢失/被清时）

> **前提**：`game_records/*.json` 全部丢失，但日志文件还在。**不要重新跑局**，日志足够恢复全部 victoryNum。

### 为什么能恢复——双重数据通道

```
掼蛋服务器 v1006.exe
├─ WebSocket ──→ yf1_m3.py ──→ latest_victory_num.json (覆盖写入，仅最后一批)
│                              game_records/*.json    (被误清 = 丢失)
│
└─ stdout ──→ executor.py read_stdout() ──→ logs/m3_vs_lalala_*.log  (所有行逐行落盘)
                                              game_scores.json        (score tracker)
```

**通道 B（stdout → 日志）与 game_records 生命周期完全解耦**：日志由 `logging.basicConfig` 在进程入口一次性绑定 FileHandler，`executor.py` 后台线程 `read_stdout()` 把服务端 stdout 每一行经 `self.logger.info("[服务器] {line}")` 写入同一个日志文件。清了 `game_records` 不影响日志。

### 三步恢复法（复制即用）

```text
game_records 被清但日志还在 → 按下面三步恢复 victoryNum，禁止重跑局。
```

| 步骤 | 操作 | 命令/文件 |
|------|------|-----------|
| 1 | 读最后一批快照 | `Get-Content batch_executor/latest_victory_num.json` |
| 2 | 搜日志中全部批末 vn | `Select-String -Path "logs/m3_vs_lalala_*.log" -Pattern "vn_source\|server_vn\|批末\|victoryNum"` |
| 3 | 交叉计算队胜率 | 合计各批 `victoryNum[0]+[2]` vs `[1]+[3]` |

**日志关键字**：
- `批末 victoryNum 校验通过:` — executor 每批末对账输出
- `批末对账：采用 vn=` — 含 vn_source + server_vn_raw
- `达到设定场次` — 服务端 stdout 原文（含各位置胜利次数）

### 四层 victoryNum 写入清单

| 序号 | 数据层 | 写入者 | 粒度 | 覆盖/追加 |
|------|--------|--------|------|-----------|
| 1 | `latest_victory_num.json` | `yf1_m3.py`（Player 0） | 最后一批 | **覆盖** |
| 2 | `logs/m3_vs_lalala_*.log` | `executor.py`（stdout 镜像） | 全部批次 | **追加** |
| 3 | `game_scores.json` | `executor.py`（score tracker） | 全部批次 | **覆盖** |
| 4 | `game_records/*.json` | `yf1_m3.py`（game_recorder） | 每副 | **追加** |

**结论**：只要 2 或 3 还在，victoryNum 永不会丢。即使 1+4 全丢，从 2 搜关键行即可完整恢复。详见 [`docs/analysis/数据恢复链分析.md`](../analysis/数据恢复链分析.md)。

---

## 延伸阅读

- 完整 5 分钟路径：[README.md § Agent 批跑数据入门](./README.md#agent-批跑数据入门5-分钟)
- 详版真源：[platform-data-interpretation.md](../knowledge/platform-data-interpretation.md)
- 数据恢复详版：[数据恢复链分析.md](../analysis/数据恢复链分析.md)
