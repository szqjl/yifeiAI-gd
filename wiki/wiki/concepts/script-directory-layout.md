---
type: concept
title: "脚本目录布局"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - concept
  - directory-layout
  - phase-5
  - organization
status: current
related_gua: []
date: 2026-06-20
---

# 脚本目录布局

## 概述

项目脚本遵循 **Phase 5 目录迁移**后的分层布局：根目录保留 Windows/Linux 兼容的 stub，**真源全部位于 `scripts/` 子目录**。

## 完整目录树

```
project-root/
├── *.bat / *.py            # Phase 5 stub（兼容入口）
│
├── scripts/
│   ├── launchers/          # 启动器（按引擎族/功能域）
│   │   ├── v7/             # V7 NN 引擎
│   │   ├── v-learn/        # V4-V6 学习引擎
│   │   ├── m/              # M 系列规则引擎
│   │   ├── training/       # 训练流水线
│   │   └── tools/          # 辅助工具
│   │
│   ├── training/           # Stage 5-8 训练脚本
│   ├── analysis/           # 分析工具（analyze_v7_rounds.py 等）
│   ├── gui/                # 通用 GUI（batch_executor_gui*.py）
│   ├── hooks/              # Git hooks（pre_push_validate.py）
│   ├── checks/             # 推送前检查（verify_gitignore.py）
│   ├── cos/                # COS 云端同步
│   ├── lark/               # 飞书 Bot
│   ├── sdk/                # Qoder Agent SDK
│   ├── clients/            # 标准测试客户端
│   ├── shell/              # 公共 shell 工具
│   └── v7/                 # V7 专用脚本（run_bc_training.py）
│
└── docs/
    └── guandan-brain/
        └── SCRIPT_INDEX.md # 唯一真源索引
```

## 设计原则

### 1. 真源-引用分离

- **真源（authoritative）**：`scripts/` 下文件为**唯一修改目标**
- **引用（stub）**：根目录 `.bat`/`.py` 仅作历史兼容，**不应被修改**

### 2. 引擎族隔离

`scripts/launchers/` 下按引擎族分子目录（v7/v-learn/m），避免跨引擎代码污染。

### 3. 功能域横切

非引擎专属功能（cos/lark/sdk/checks/hooks）置于 `scripts/` 顶级子目录，便于复用。

### 4. 双平台兼容

每个常用脚本提供：
- `.bat`（Windows CMD）
- `.py`（跨平台 Python）
- 可选 `.ps1`（Windows PowerShell）

## 治理规则

1. **新增脚本**：必须放入对应 `scripts/` 子目录，禁止直接在根目录创建
2. **删除脚本**：同步更新 [[SCRIPT_INDEX-summary]]
3. **修改脚本**：优先修改 `scripts/` 下真源，根目录 stub 通过符号链接或转发实现
4. **文档引用**：所有 GUA、Wiki、文档必须引用 `scripts/` 下真源路径

## 关联页面

- [[SCRIPT_INDEX-summary]] — 完整脚本索引
- [[module-script-launchers]] — 启动器分层
- [[script-launcher-hierarchy]] — 启动器分层概念
- phase-5-migration — Phase 5 迁移
