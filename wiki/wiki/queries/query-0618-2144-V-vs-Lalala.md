---
type: query-answer
title: "V7 vs Lalala"
date: 2026-06-18
sources:
  - queries/query-0618-1734-v-启动脚本-路径-lalala-import-改动.md
  - entities/module-batch-executor.md
  - wiki/wiki-minimax/concepts/batch-evaluation.md
  - sources/v7-system-fixes-summary.md
  - sources/SCRIPT_INDEX-summary.md
  - wiki/wiki-minimax/synthesis/v7-current-state.md
  - entities/module-v7-engine.md
  - concepts/script-directory-layout.md
  - synthesis/synthesis-m3-vs-v7-status.md
  - entities/opponent-lalala.md
---

# V7 vs Lalala

# V7 vs Lalala 综合回答

## 一、启动入口

V7 vs Lalala 批跑主入口：

```bash
python scripts/launchers/v-nn/run_v7_vs_lalala_games.py --config v7_lalala_config.json
```

- **配置**：`v7_lalala_config.json`（与 launcher 同目录）
- **分支**：V7 走 `v7-dev`，**严禁与 M3 混推** 3][5][6
- **替代入口**：GUI 模式 `batch_executor_gui_v7.py` [[2]]

## 二、当前状态

| 维度 | 状态 |
|------|------|
| Wiki 工具链接入 | ✅ v7.2 完成 |
| 分支隔离 | ✅ v7-dev / m-dev 双线并行 |
| 进程管理 | ✅ TrackedClientProcess 已修复（2026-05-22） |
| **V7 当前胜率** | ⚠️ **3.0%**（远低于 30% 门槛） |
| **开放 P0** | GUA-061（模块化架构阻塞） |
| P0 代码改动 | ⏳ 待执行（choose_bomb / context / combine_handcards） |

> **核心张力**：V7 已关 20 个 GUA，但胜率仍 3%——**关单 ≠ 接近达标** [[9]]

## 三、批跑 KPI 与目标

- **当前胜率**：3.0%（vs lalala 副级口径）
- **门槛**：30%
- **目标升级**：从 >50% → **>90%**（PHASE3 2026-05-24 决议） [[6]]
- **核心 KPI 工具**：
  - 局级：`analyze_v7_rounds.py`
  - **副级**（必走）：`analyze_v7_round_levels.py`——**局 ≠ 副** [[3]]

## 四、关键阻碍：GUA-061

- **性质**：V7 模块化架构 P0 阻塞
- **影响**：在 GUA-061 解决前，V7 难以跨越 30% 门槛
- **建议**：集中资源攻克，V7 才有"10 倍增长空间" [[9]]

## 五、相关 GUAs

| GUA | 主题 | 状态 |
|-----|------|------|
| GUA-022 | combine_handcards() 修复 | 根因隔离完成 |
| GUA-014 | choose_bomb() 最小代价炸弹 | 待 P0 改动 |
| GUA-050 | context 字段补全（pass_num 等） | 待 P0 改动 |
| GUA-061 | V7 模块化架构 | **开放 P0** |
| GUA-062 | 消息格式 actionIndex→actIndex | 待补登（早期 fix） |
| GUA-063 | restart_manager 客户端名兼容 | 待补登（早期 fix） |
| GUA-033 | victoryNum 解析路径 | 已关闭（V7 是否沿用待定） |

## 六、信息缺口

Wiki 未直接覆盖：
1. `run_v7_vs_lalala_games.py` 完整 import 列表
2. lalala 对手客户端的引擎归属与版本 [[10]]
3. 最近一次 V7 vs lalala 批跑的具体胜率与局数
4. `victoryNum` 解析路径在 V7 中的选择（标记为"待办"）

## 七、下一步建议

1. **直接读源码**：`scripts/launchers/v-nn/run_v7_vs_lalala_games.py` 确认当前 import 状态
2. **集中攻克 GUA-061**：模块化架构是 V7 突破 30% 的关键瓶颈
3. **建立 M3 vs V7 对照批跑**：追踪 V7 何时跨越门槛 [[9]]
4. **补全 lalala 实体信息**：lalala 的引擎类型、版本、所属团队 Wiki 暂无记录 [[10]]

---

**主要来源**：[1] 启动脚本 import 改动 · [2] 批跑执行器模块 · [3] 批跑评测体系 · [6] V7 当前状态 · [7] V7 引擎模块 · [9] M3 vs V7 状态对比 · [10] 对手 lalala 实体
