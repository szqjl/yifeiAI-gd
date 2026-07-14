---
type: meta
title: "Wiki 操作日志"
sources: []
tags:
  - log
status: current
date: 2026-06-17
---

# Wiki 操作日志

> 时序记录，按日期倒序

## 2026-06-17

### 摄入批次：GUA-032/033/034 完工记录

**源文件**：
- `docs/guandan-brain/issues/GUA-032-completion.md`（998 chars）
- `docs/guandan-brain/issues/GUA-033-completion.md`（2032 chars）
- `docs/guandan-brain/issues/GUA-034-completion.md`（1146 chars）

**新建页面**：
| 路径 | 类型 | 说明 |
|------|------|------|
| `wiki/sources/GUA-032-completion-summary.md` | source-summary | GUA-032 完工记录摘要 |
| `wiki/sources/GUA-033-completion-summary.md` | source-summary | GUA-033 完工记录摘要 |
| `wiki/sources/GUA-034-completion-summary.md` | source-summary | GUA-034 完工记录摘要 |
| `wiki/entities/gua-032.md` | entity-gua | P0 open，记牌算牌 |
| `wiki/entities/gua-033.md` | entity-gua | closed 2026-05-31，批末校验 |
| `wiki/entities/gua-034.md` | entity-gua | P0 open，残局 guard 切片 |
| `wiki/concepts/card-counting-and-calc.md` | concept | 记牌算牌体系 |
| `wiki/concepts/solo-sprint.md` | concept | 残局单飞冲刺 |
| `wiki/concepts/batch-end-victory-num-validation.md` | concept | 批末 victoryNum 校验 |

**更新页面**：
- `wiki/overview.md` — 补充 GUA 生命周期速览、本次摄入要点
- `wiki/log.md` — 本条记录

**关键定音**：
- GUA-033 平台 exe argv 缺陷已定音：v1006 `settingTimes=3` 固定
- GUA-026 vs GUA-034 边界已划清：常态 vs 1v2 互斥触发
- GUA-034 不在范围：lalala 两手牌枚举留给 V5+
```

## 摄入总结

本次为 3 份 GUA 完工记录生成了 **9 个新页面 + 2 个更新**：

### 核心定音
1. **GUA-033 平台 argv 根因**：v1006 exe 的 `settingTimes` 固定为 3 是离线 exe 实现缺陷，仓库启动脚本无误
2. **GUA-026 vs GUA-034 边界**：常态禁拆 vs 残局 1v2 允许拆，触发条件**互斥**
3. **不在范围**：GUA-034 的 lalala 两手牌枚举留给 V5+

### 页面架构
- **3 个 source-summary**：原始资料的轻量摘要
- **3 个 entity-gua**：正式实体页（2 open + 1 closed）
- **3 个 concept**：可复用的方法论/模式
- **2 个 meta 更新**：overview 增补 + log 新增

### 交叉引用网
```
GUA-032 ←→ card-counting-and-calc
GUA-033 ←→ batch-end-victory-num-validation
GUA-034 ←→ solo-sprint
GUA-034 ↔ GUA-026（互斥边界）
GUA-034 → GUA-029（R3 兜底复用）
GUA-034 ← GUA-031（模式识别后脱离）
