---
type: query-answer
title: "GUA-041 路径债 清理 完成 closed v7_paths"
date: 2026-06-18
sources:
  - synthesis/m1-p0-iteration-story.md
  - wiki/wiki-minimax/sources/GUA-033-completion-summary.md
  - sources/m3-guards-gua031-036-summary.md
  - sources/v7-infra-gua041-049-summary.md
  - wiki/wiki-minimax/sources/GUA-030-completion-summary.md
  - wiki/wiki-minimax/sources/GUA-031-completion-summary.md
  - sources/ISSUES-summary.md
  - sources/p0_implementation_reports-summary.md
  - synthesis/m3-batch-infra-closure.md
  - wiki/wiki-minimax/sources/GUA-029-completion-summary.md
---

# GUA-041 路径债 清理 完成 closed v7_paths

# GUA-041 路径债清理 — 状态确认

## 结论

**GUA-041 在当前 Wiki 中没有独立的"路径债清理"记录**。Wiki 中关于 GUA-041 的内容是 **WebSocket 73s 卡顿**（属于 V7 基础设施层），与"路径债清理 + v7_paths"无直接对应。

---

## Wiki 中 GUA-041 的实际定义

根据 [4] `v7-infra-gua041-049-summary.md`：

| 字段 | 值 |
|------|-----|
| 编号 | GUA-041 |
| 标题 | **WebSocket 73s 卡顿** |
| 根因 | `async for` 在迭代服务端 stdout 时被长行阻塞 |
| 修复 | 引入 module-server-stdout-reader（`server_stdout_reader.py`）单线程 drain |
| 范围 | infra / V7 |

**注意**：[4] 中确实提到了 `v7_paths.yaml` + `v7_paths.py`，但那是 **GUA-044（路径配置重构）** 的产物，不是 GUA-041。

---

## 与"路径债 + v7_paths"最接近的 GUA

**GUA-044 — 路径配置重构**（同属 V7 基础设施批）：
- 新文件：`config/v7_paths.yaml` + `v7_paths.py`
- 优先级：环境变量 > yaml > 候选回退
- 关联：`ultimate_win_rate_engine_v7.py` 启动时强制走 v7_paths
- 状态：closed

**v7_paths 体系** 的关键点：
- 73s 卡顿问题**修复后**才暴露路径混乱（路径债）
- 路径债清理（即"v7_paths 落地"）被挂在 GUA-044 下，作为其修复手段

---

## 当前活跃 P0（参考）

来自 [7] `ISSUES-summary.md`：

- **GUA-059**（open, P0）— BC v2 退化根因定位，所有 P1 GUA 的硬前置
- **GUA-048**（open）— 73s 卡顿双根因
- **GUA-049**（open, P1）— mark_game_ready race condition

GUA-041 本身**未出现在 open 列表**中，参照 [4] 的描述应已 closed。

---

## 建议

如果"路径债清理"是**新工作项**或**新近完成的 GUA**，目前 Wiki 中没有对应记录，可能需要：

1. 确认"路径债"是指 **GUA-044（路径配置重构）** 的口语化称呼 → 详见 [[gua-044]]
2. 如果这是 **GUA-041~049 批次之后**的新动作（例如清理历史路径硬编码），需新建 GUA 编号并补充完成报告
3. 检查 `docs/guandan-brain/ISSUES.md` 最新版是否有 063+ 编号的"路径债清理"条目

---

## 引用

- [4] V7 基础设施迭代摘要（GUA-041 = 73s 卡顿，GUA-044 = 路径配置）
- [7] ISSUES.md 摘要（当前 open 列表）
