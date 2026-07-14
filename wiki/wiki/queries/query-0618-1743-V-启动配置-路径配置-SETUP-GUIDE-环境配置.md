---
type: query-answer
title: "V7启动配置 路径配置 SETUP_GUIDE 环境配置"
date: 2026-06-18
sources:
  - queries/query-0618-1735-GUA-路径债-清理-完成-closed-v-paths.md
  - sources/SETUP_GUIDE-summary.md
  - sources/v7-infra-gua041-049-summary.md
---

# V7启动配置 路径配置 SETUP_GUIDE 环境配置

# V7 启动配置 / 路径配置 / SETUP_GUIDE / 环境配置

## 核心定位

**SETUP_GUIDE** 是 V7/M3/M1 各引擎的**环境变量配置与批跑候选路径清单**，是离线评测体系的基础设施层 [{2}]。

---

## 路径配置体系（GUA-044）

V7 的路径配置已经统一收敛到 **v7_paths 体系**：

| 组件 | 路径 |
|------|------|
| 配置文件 | `config/v7_paths.yaml` |
| 加载模块 | `v7_paths.py` |
| 优先级 | **环境变量 > yaml > 候选回退** |
| 强约束 | `ultimate_win_rate_engine_v7.py` 启动时**强制走 v7_paths** |

**背景**：73s 卡顿（GUA-041）修复后，历史路径硬编码的混乱暴露出来，作为"路径债"被挂在 **GUA-044** 下清理，状态 **closed** [{1}][{3}]。

---

## V7 基础设施批次（GUA-041 ~ GUA-049）

| GUA | 标题 | 状态 | 要点 |
|-----|------|------|------|
| GUA-041 | WebSocket 73s 卡顿 | closed | `server_stdout_reader.py` 单线程 drain |
| **GUA-044** | **路径配置重构** | **closed** | **v7_paths.yaml + v7_paths.py** |
| GUA-047 | 客户端就绪检测 | closed | `client_ready.py` + Wait-for-all-clients 门闩 |
| GUA-048 | 原子写 | open | `fcntl`/`msvcrt` + temp+rename |
| GUA-049 | game_ready race condition | open (P1) | 60s 超时根因 |

---

## SETUP_GUIDE 当前覆盖范围 [{2}]

- 环境变量优先级表
- 各引擎（V7/M3/M1）候选路径
- ZMQ 端口约定（actor-learner 通信）

> ⚠️ SETUP_GUIDE 的具体环境变量/路径细节**目前 Wiki 中标注为"待维护者从原文摘录"** [{2}]，需要回到 `docs/guandan-brain/SETUP_GUIDE.md` 原文核对。

---

## 关键澄清（避免混淆）

1. **"路径债清理" ≠ GUA-041**：GUA-041 是 73s 卡顿，路径债挂在 **GUA-044** [{1}]
2. **v7_paths 落地是 GUA-044 的修复手段**，不是独立 GUA [{1}]
3. 366 局批跑 100% 门闩生效是 GUA-047 的产物，**不是**路径配置 [{3}]

---

## 引用

- [{1}] GUA-041 路径债查询记录（澄清路径债归属）
- [{2}] SETUP_GUIDE 摘要
- [{3}] V7 基础设施迭代摘要（GUA-041~049）
