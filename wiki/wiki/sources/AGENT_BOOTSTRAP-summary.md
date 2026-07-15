---
type: source-summary
title: "V7/V8 Agent 启动指南"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
tags:
  - source-summary
  - agent
  - workflow
  - bootstrap
status: current
related_gua:
  - GUA-033
date: 2026-07-15
---

# V7/V8 Agent 启动指南

## 资料元信息

| 字段 | 值 |
|------|-----|
| 路径 | `docs/guandan-brain/AGENT_BOOTSTRAP.md` |
| 字符数 | 9,943 |
| 类型 | Agent 工作流真源 |
| 状态 | 与 [[AGENT_FIRST_MESSAGE]] / [[AGENT_PUSH_CHECKLIST]] 配套使用 |

## 章节结构

### §1 项目身份与边界
掼蛋 AI 项目定位、计分规则、双上计分王定义。

### §2 V7 引擎配置（详见 [[engine-v7]]）
- `ultimate_win_rate_engine_v7.py`
- 客户端：`yf1_v7` / `yf2_v7`
- 批跑命令模板

### §3 关键定音（详见 [[recursion-game-round]]）
- §3.1 局 vs 副区别（[[gua-033]] 定音）
- §3.2 出牌顺序 0→1→2→3 顺时针
- §3.3 队胜分布 `[0,3,0,3]` 解释
- §3.4 四层 victoryNum 写入
- §3.5 LLM Wiki 已初始化并摄入 107 个源文件

### §4 V8 平台迁移（详见 [[v8-openguandan-protocol]]）
- OpenGuanDan 新平台
- WebSocket `ws://127.0.0.1:8181`
- v8-dev 分支开发

### §5 引擎对照表
M 系列 vs V 系列，共用层与差异层。

### §7 批跑命令（详见 [[batch-evaluation]]）
- M3 批跑命令
- V7 批跑命令
- game_records vs game_records_v7 目录分离
- `--target-games` 须为 3 的倍数

## 工作流编号

文档定义 12 个 Agent 工作流（WF-01 ~ WF-12），覆盖从开发到批跑到复核的全流程。

## 关联页面

- [[agent-bootstrap-workflow]] —— Agent 工作流概念
- [[batch-evaluation]] —— 批跑评测
- [[engine-v7]] / [[engine-m3]] —— 引擎实体
