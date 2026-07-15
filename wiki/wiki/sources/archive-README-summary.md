---
type: source-summary
title: "archive 目录说明"
sources:
  - docs/analysis/archive/README.md
tags:
  - archive
  - meta
status: current
date: 2026-06-21
---

# archive 目录说明

## 来源
- 原始文件：`docs/analysis/archive/README.md`
- 字数：约 900 字

## 目录用途
`docs/analysis/archive/` 用于存放已过期、已合并、已证伪的分析文档。

## 当前归档清单
| 文件 | 归档原因 | 替代页面 |
|------|---------|---------|
| `2026-06-21-cardmask-dict-collision.md` | 单点排查 handoff | [[cardmask-multiset-fix]] |
| `level2-root-cause.md` | 子集证据 | [[bc-argmax-collapse]] |
| `南邮离线平台-actionList候选缺失观测报告.md` | 双版本并存 | [[GUA-124]] 可发送版 |
| `批跑cmd窗口观察.md` | 单次观察 | [[synthesis-m3-vs-v7-status]] 性能章 |

## 归档原则
1. 结论已被新文档覆盖
2. 单点 handoff 文档（任务完成后归档）
3. 存在双版本且旧版本已证伪（保留旧版本但禁止外发）
4. 单次观察记录（结论已合并到综合页）

## 严禁行为
- ❌ 引用归档文档作为对外口径
- ❌ 修改归档文档（应为只读）
- ❌ 删除归档文档（保留历史轨迹）
