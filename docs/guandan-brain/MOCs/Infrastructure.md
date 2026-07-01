---
tags: [MOC, infrastructure, batch-executor, governance]
created: 2026-06-17
topic: 基础设施与治理索引
---

# 基础设施与治理

## 迭代文件

- [[phase5-infra]] — Phase 5 仓库治理（5a~5g + M2/M3 物理迁入）
- [[batch-executor]] — 批跑器改进与 victoryNum 链路（GUA-033）
- [[governance-docs]] — 治理文档、回放工具、录牌、handoff

## 环境与文档

- [[SETUP_GUIDE]]（`docs/guandan-brain/SETUP_GUIDE.md`）— 新电脑首次拉取环境搭建
- [[ISSUES]]（`docs/guandan-brain/ISSUES.md`）— 缺陷登记簿入口；完成定义见 `issues/` 目录

## GUA 索引

| GUA | 状态 | 文件 |
|-----|------|------|
| GUA-033 | closed | [[batch-executor]] |

## 关键约定

### 批跑
- `--target-games` 须为 **3 的倍数**（推荐 3/9/12，勿用 10）
- v1006 exe 单次会话固定 3 局
- 队胜看 `victoryNum[0] vs [1]`（0+2 一队，1+3 一队）
- 禁止裸信 `gameResult.victoryNum`

### Git
- 日常开发分支 m-dev（Gitee 真源 origin/m-dev）
- GitHub 仅 main 与 m-dev（default m-dev）
- **禁止 push main**

### 仓库
- M1 frozen；M3 主交付；组牌/牌力走 V5+
- 离线 exe：`offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe`
- lalala：`reference/lalala/`（纯 ASCII 路径）

## 常用回放命令

- `python scripts/tools/yf_replay.py`
- `YF_REPLAY.bat`
