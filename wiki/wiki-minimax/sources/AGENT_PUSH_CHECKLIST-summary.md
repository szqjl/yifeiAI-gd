---
type: source-summary
title: "Agent Push Checklist（摘要）"
sources:
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
tags:
  - workflow
  - quality-gate
  - push
  - pre-commit
status: current
related_gua: []
date: 2026-06-17
---

# Agent Push Checklist（摘要）

## 来源
- 原始文件：`docs/guandan-brain/AGENT_PUSH_CHECKLIST.md`（1435 字符）
- 类型：推送前质量门控

## 核心内容
推送代码前的强制检查清单（pre_push_validate 流程）：

1. **代码改动交叉评审**：opencode + cursor 双重评审通过
2. **本地测试通过**：相关 GUA 的测试矩阵 (P0/T1-T9) 全部跑通
3. **批跑验证**：策略类改动必须经过离线批跑
4. **数据目录分离**：M3 → `game_records/`，V7 → `game_records_v7/`
5. **Wiki 同步**：重大决策必须先更新 Wiki

## 关键工具
- `scripts/hooks/pre_push_validate.py`：pre-push hook
- `scripts/hooks/install-hooks.bat`：Windows 安装脚本

## 关联页面
- [[code-quality-gate]] — 交叉评审门控
- [[branch-isolation]] — 分支隔离
