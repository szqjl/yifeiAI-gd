---
type: source-summary
title: "V7 基础设施迭代摘要"
sources:
  - docs/guandan-brain/iterations/v7-infra-gua041-049.md
tags:
  - v7
  - infrastructure
  - webserver
  - 73s-card
status: current
related_gua:
  - GUA-041
  - GUA-044
  - GUA-047
  - GUA-048
  - GUA-049
date: 2026-06-17
---

# V7 基础设施迭代摘要

## 范围

GUA-041 ~ GUA-049，覆盖 V7 引擎的**底层基础设施层**：服务端、WebSocket、客户端联动、路径配置、race condition 修复。

## 关键 GUA

### GUA-041 — WebSocket 73s 卡顿
- **根因**：`async for` 在迭代服务端 stdout 时被长行阻塞
- **修复**：引入 module-server-stdout-reader（`server_stdout_reader.py`）单线程 drain
- **佐证**：双读者场景下出现 73s 延迟

### GUA-044 — 路径配置重构
- **新文件**：`config/v7_paths.yaml` + `v7_paths.py`
- **优先级**：环境变量 > yaml > 候选回退
- **关联**：`ultimate_win_rate_engine_v7.py` 启动时强制走 v7_paths

### GUA-047 — 客户端就绪检测
- **实现**：`client_ready.py`（module-client-ready）
- **机制**：Wait-for-all-clients 门闩（`clients_ready.json` + 顺位）

### GUA-048 — 原子写
- **目的**：避免多进程写模型/状态文件时的部分写入
- **实现**：`fcntl`（Linux）/ `msvcrt`（Windows）文件锁 + temp+rename

### GUA-049 — game_ready race condition
- **症状**：客户端竞争 game_ready 信号导致 60s 超时
- **修复**：见 [[gua-049]] 独立实体页

## 关键 KPI

- **73s 卡顿** → 修复后消除
- **60s 超时** → GUA-049 关闭后稳定
- **Wait-for-all-clients** 门闩在 366 局批跑中 100% 生效（V7 队胜 366/366 即为该门闩保护下的产物）

## 关联

- wiki/entities/engine-v7.md
- [[gua-045]]
- [[gua-049]]
- wiki/synthesis/synthesis-v7-current-state.md
