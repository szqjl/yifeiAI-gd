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

## 延伸阅读

- 完整 5 分钟路径：[README.md § Agent 批跑数据入门](./README.md#agent-批跑数据入门5-分钟)
- 详版真源：[platform-data-interpretation.md](../knowledge/platform-data-interpretation.md)
