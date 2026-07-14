---
type: concept
title: "GUA 缺陷生命周期"
sources:
  - docs/guandan-brain/ISSUES.md
  - docs/guandan-brain/issues/GUA-080-completion.md
tags:
  - gua
  - lifecycle
  - process
status: current
date: 2026-06-29
---

# GUA 缺陷生命周期

## 定义
GUA（Guandan AI Issue）编号体系是本项目追踪缺陷、迭代、任务的唯一脊柱编号。每条 GUA 经历以下生命周期：

```
open → in-progress → in-review → closed
                ↓
            blocked / deferred
```

## 关键状态
| 状态 | 含义 |
|------|------|
| `open` | 已登记，未分配 |
| `in-progress` | 责任人正在处理 |
| `in-review` | 等待评审/批跑验证 |
| `closed` | 完成并有证据（如 GUA-080-completion） |
| `blocked` | 等待外部依赖 |

## 完成标准
参照 [[GUA-080-completion-summary]] 模式，需包含：
1. 根因分析
2. 修复方案
3. 验证证据（批跑结果 / 单元测试）
4. 关闭责任人 + 日期

## 关联
- [[ISSUES-summary]] — 总索引
- [[batch-evaluation]] — 验证手段
```

---
