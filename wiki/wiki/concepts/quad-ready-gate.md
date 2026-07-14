---
type: concept
title: "四席就绪门闩（GUA-044）"
sources:
  - docs/guandan-brain/issues/GUA-044-completion.md
tags:
  - concept
  - batch
  - infra
  - gate
  - websocket
status: current
related_gua:
  - GUA-044
  - GUA-033
date: 2026-06-17
---

# 四席就绪门闩（GUA-044）

## 定义

批跑开局前，确保 **4 个客户端席位**全部连入并发送就绪信号的同步门闩，定义于 [[GUA-044]]。

## 门闩机制

### 状态文件

- `batch_executor/clients_ready.json`
- 记录每个席位的 `_peers_ready` 状态

### 同步顺序

- `CONNECT_ORDER_INDEX`（按席位索引顺序）
- 逐席等待 `wait_for_connect_turn` 完成
- 全部就绪后清空（`clear_all_ready`）进入对局

## 时间参数（最新）

| 参数 | 值 | 调整日期 |
|------|-----|----------|
| client4 延迟 | **11s** | 2026-06-06 |
| 末席稳定窗口 | **7s** | 2026-06-06 |

> 旧参数（2s + 5s）在网络抖动下偶发半连接，已硬化。

## 调试旁路

```bash
YF_SKIP_CONNECT_GATE=1  # 跳过门闩（仅调试用）
```

## 排查指南

单席长时间无 act 时：
1. **先查他席回包**（可能是被卡住）
2. 再判定本席断连
3. 必要时重启该席

## 关联

- [[gua-044]] - GUA-044 实体
- 批跑评测体系 - 批跑体系总览
- [[m3-batch-infra-closure]] - M3 批跑基建关闭综合
- wiki-minimax/entities/gua-033.md - 批跑基建历史
