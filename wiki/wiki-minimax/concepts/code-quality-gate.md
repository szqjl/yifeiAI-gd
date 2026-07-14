---
type: concept
title: "代码质量门控 (交叉评审)"
sources:
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - quality
  - code-review
  - pre-push
  - gate
status: current
related_gua:
  - GUA-022
date: 2026-06-17
---

# 代码质量门控 (交叉评审)

## 定义
所有代码改动在 push 之前必须经过 **双重交叉评审**（opencode + cursor），是项目级硬规则。

## 评审流程

```
代码改动 → opencode 评审 → cursor 评审 → pre-push hook → 推送
            ↓ 失败            ↓ 失败           ↓ 失败
            退回修改          退回修改          阻止推送
```

## 评审维度

| 维度 | 检查点 |
|------|--------|
| 正确性 | 逻辑错误、边界条件 |
| 兼容性 | 分支隔离、数据目录、客户端 |
| 测试 | P0/T1-T9 测试矩阵 |
| 文档 | Wiki 同步、CHANGELOG |

## 配套工具

- `scripts/hooks/pre_push_validate.py` — pre-push 钩子
- `scripts/hooks/install-hooks.bat` — Windows 安装
- `AGENT_PUSH_CHECKLIST.md` — 人工 checklist

## 测试矩阵（P0/T1-T9）

策略改动必须用测试矩阵验证：

| 测试 | 目的 |
|------|------|
| P0 | 主问题修复 |
| T1-T6 | 单一因素隔离 |
| T7 | 双重 patch 组合 1 |
| T8 | 双重 patch 组合 2 |
| T9 | 全量叠加 |

## 设计动机

- LLM 生成代码存在幻觉风险
- 单一模型评审盲区大
- 双重交叉 + 测试矩阵 = 兜底

## 关联页面
- [[branch-isolation]] — 分支隔离
- [[gua-022]] — 测试矩阵应用案例
- [[AGENT_PUSH_CHECKLIST-summary]] — 源文档
