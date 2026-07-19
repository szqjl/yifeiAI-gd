---
type: source-summary
title: "V8 迁移启动 handoff 摘要（2026-07-14）"
sources:
  - docs/guandan-brain/handoff/2026-07-14-V8-迁移启动-基础设施齐套.md
tags:
  - handoff
  - v8-migration
  - smoke-test
  - infrastructure
status: current
related_gua:
  - GUA-143
  - GUA-144
  - GUA-145
  - GUA-146
date: 2026-07-16
---

# V8 迁移启动 handoff 摘要（2026-07-14）

## 文档定位

本 handoff 是 `v8-migration-init` 迭代的关键状态交接文档，记录 V8 引擎迁移基础设施的齐套状态、V7 链路保护、冒烟测试路径。

## 核心论点

### 1. V8 迁移边界（§背景）
- **仅换通信层**，不改决策管线
- 协议升级：`actIndex` → 完整 `action + type` 包装
- 新增房间模型：`CREATE_ROOM` / `JOIN_ROOM`（V7 无此概念）

### 2. V7 链路零侵入保护（§关键代码改动）
- V7 入口脚本（`v7-launch-*`） + M1/M2/M3 GUI 均不传 `platform` 参数
- BatchExecutor 通过 `platform` 参数区分 v1006 / openguandan
- 默认走 v1006 兼容路径 → **V7 完全不受影响**

### 3. 平台感知启动（§关键代码改动 1.x）
- `restart_manager.py` 启动命令分支：
  - `platform == 'v1006'`：传 `[server_path, str(game_count)]`（V7 旧逻辑）
  - `platform == 'openguandan'`：不传 `game_count`，round 在 CREATE_ROOM 指定
- **疑问**：与 V7 旧逻辑是否完全向后兼容存疑（详见 [[gua-143]] § 兼容性疑虑）

### 4. 实施顺序 §9（冒烟）
- §1 二进制可启动 → 标 ✅（guandan.exe 已就位）
- §2~§8 文件齐套 → 标 ✅（GUA-143~146）
- **§9 冒烟测试 → 未运行**（唯一未完成动作）

## 冒烟测试命令（推测）

```bash
# V8 链路冒烟（未执行）
python scripts/launchers/v8/smoke.py --platform openguandan --rounds 3
```

## 失败诊断点（推测）

1. **端口监听**：8181 (WS) / 3000 (HTTP) 是否被 `guandan.exe` 正确开启
2. **协议字段**：`action + type` 上行格式是否与新平台匹配
3. **上行格式**：JSON 序列化是否包含必要字段
4. **recorder victory 字段**：新平台胜负回报字段名差异

## 关联实体

- [[gua-143]] / [[gua-144]] / [[gua-145]] / [[gua-146]] — V8 基础设施 4 件套
- [[module-v8-communication]] — 通信层 6 文件
- [[engine-v8]] — V8 引擎当前状态
- [[v8-migration-handoff]] — 详细 concept 页

## 已知盲点

1. handoff §V7 链路保护确认未提 GUA-136/137/138 是否在 V8 链路生效（MemoryTracker 是 V7 引擎组件）
2. handoff §关键代码改动 1.2 关于 `restart_manager` 兼容性未给回归测试
3. handoff §1 vs §9 状态描述模糊：「文件齐套 ✅」与「冒烟未跑」并存
