# 指挥官工作笔记

> 本文件是指挥官（Hermes CLI）的内部思考记录，供跨会话使用。不维护合并稿，每次开工前独立撰写或更新。

更新时间：2026-07-14

---

## 分支现状速览（2026-07-14）

| 分支 | 定位 | 离线平台 |
|------|------|----------|
| `m-dev` | M3 硬编码规则引擎（当前开发） | v1006 `guandan_offline_v1006.exe` |
| `v7-dev` | V7 神经网络引擎（**回退基线**） | v1006 `guandan_offline_v1006.exe`（TCP Socket） |
| `v8-dev` | V8 分支（从 v7-dev 复制，commit `2904c08`） | 新版 `guandan.exe`（WebSocket `ws://127.0.0.1:8181`） |

> v8-dev 代码与 v7-dev 一致，正等待 OpenGuanDan 新版服务器对接指令。新平台资源：`offline_platform/openguandan_latest/`。

---

## 下一步开发启动前待完成的 6 件事

### #1 ✅ 架构规则分析.md review 完成
- **状态**：2026-05-21 完成，修订了3个⚠️问题
  - "更优"绝对化 → 改为"精确 if-then 维度 lalala 更优，M1 有阶段细分优势"
  - M1 "7-10层" → 修正为"6-8层"
  - P0 任务出处 → 补充源码引用（`utils.py:13` / `utils.py:297-367`）
- **文件**：`docs/guandan-brain/架构规则分析.md`
- **评审文件**：`reviews/架构规则分析_OPENCODE.md`（171行）、`reviews/架构规则分析_CURSOR.md`

### #2 ✅ M1_ARCHITECTURE.md 事实核查完成
- **状态**：2026-05-21 完成，修复2个错误
  - L216 继承关系（MidLatePassiveHandler → BasePhaseHandler）
  - L176 strategy_engine 行号（588→589）
- **文件**：`docs/guandan-brain/M1_ARCHITECTURE.md`

### #3 ✅ 测试计划
- **状态**：T7（禁用 should_protect）→ 0%，T8（lalala combine_handcards）→ 0%，T9（双重patch）→ 0%
- **结论**：两个单一因素及其组合均非 GUA-022 根因

### #4 ✅ GUA-022 根因隔离完成
- **状态**：T7（禁用 should_protect）→ 0%，T8（lalala combine_handcards）→ 0%，T9（双重patch）→ 0%
- **结论**：两个单一因素及其组合均非 GUA-022 根因
- **下一步**：进入P0代码改动阶段（T1+T2+T3）

### #5 ✅ 开发目标已量化
- **目标**：M1 对 lalala >50% 队胜率
- **基线**：victoryNum=[0,3,0,3] = 0%
- **测试量**：16局/次

### #6 ⏳ M1 和 V 系列集成节点
- **状态**：待良总讨论

### #7 ⏳ P0代码改动阶段（新增）
- **状态**：准备开始
- **触发条件**：T9测试完成（2026-05-22，0%胜率确认）
- **执行顺序**：
  1. P0代码改动（T1: choose_bomb优化, T2: context补全, T3: combine_handcards修复）
  2. Cursor交叉评审代码
  3. 跑T4测试（16局对lala）
  4. 评审结果
  5. 决定下一步（T5/T6或收尾）
- **质量门控**：代码改动必须经过交叉评审才能执行

---

## ⚠️ 游戏服务器/客户端自启动问题（2026-05-22）

### 症状
- 关掉客户端 CMD 窗口后，游戏服务器和 batch_executor 总是自动重启
- 服务器反复出现，`execution_state.json` 持续更新

### 根因
1. **正常流程**：`test_t9.py` 调用 `batch_executor -m`，batch_executor 内置自动重启机制（每3场重启一次，直到跑完 16 场）
2. **异常触发**：用户关掉客户端 CMD 窗口 → batch_executor 的 `process_monitor` 检测到客户端进程消失 → `should_restart()` 返回 True（remaining_games > 0）→ 立刻重启服务器

### 当前进程链路（已清理）
```
hermes kanban worker (t_dec4aac3)
  └── python exec(open('test_t9.py').read())  [PID 9676, 13:09:33]
        └── python -m batch_executor            [PID 2592]
              ├── guandan_offline_v1006.exe     [服务器]
              └── python src/communication/*.py  [4个客户端]
```

### 已修复（2026-05-22 代码）
- `TrackedClientProcess`：按脚本名解析真实 Python PID，不再误跟踪 `start` 壳进程
- 客户端监控增加 **60s 宽限期** + **连续 2 次**不足才终止本批（`BATCH_EXECUTOR_CLIENT_MONITOR_GRACE`）
- **连续 3 次无进度**熔断 + **总重启次数上限**（`BATCH_EXECUTOR_MAX_TOTAL_RESTARTS`）
- 单实例锁 `tmp/.batch_executor.lock` 防止多个 batch_executor 互杀端口

### 处理步骤
1. 杀掉所有相关进程：
   ```
   powershell Get-Process guandan_offline_v1006 -ErrorAction SilentlyContinue | Stop-Process -Force
   powershell Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -match 'batch_executor|test_t9'} | Stop-Process -Force
   ```
2. 删除 `execution_state.json`（重置状态）
3. 如需停止 Kanban worker：`hermes kanban list` 查任务状态

### 预防
- 不要再手动关客户端窗口来停止测试
- 用 Ctrl+C 或发信号停止 batch_executor 主进程
- 下次跑测试前确认 `execution_state.json` 已清空

---

## 代码质量门控（强制）
- 涉及代码的任务：开始前必须交叉评审通过
- 不赶时间，只看质量
- 目标：赢

---

## 当前分支：m-dev
- **现状**：已知 M1（规则）和 V4/V5/V6（神经网络）是两条独立线
- **未决**：两条线在什么节点汇合？决策层集成？还是出牌时才合并？
- **影响**：架构选择会影响后续代码改动方向
- **行动**：需和良总或架构负责人讨论

---

## 指挥官每日快扫（开工前必读）

- [ ] TASKS.md 有无新任务？
- [ ] ISSUES.md 有无新 open 的 GUA？
- [ ] 本文件 7 项待办有无推进？（新增#7 P0代码改动阶段）
- [ ] 上一轮代码改动是否已 commit 并 push？
- [ ] P0任务是否按计划执行？（choose_bomb优化 → context补全 → combine_handcards修复）
- [ ] 每个代码改动是否经过交叉评审？

---

## 项目当前关键状态

|| 指标 | 当前值 | 备注 |
|------|--------|------|
| M1 对 lalala 胜率 | 0% (0/88)，T7禁用should_protect: 0%(0/308)，T8 lalala combine_handcards: 0%(0/48)，T9双重patch: 0%(0/16) | GUA-022 open |
| 当前阶段 | T9测试完成，进入P0代码改动阶段 | 根因隔离完成 |
| 下一步行动 | P0代码改动：choose_bomb优化 → context补全 → combine_handcards修复 | 按优先级执行 |

> 基线说明：`victoryNum=[p0胜, p1胜, p2胜, p3胜]` = 队伍维度。队伍0（pos 0+2）胜0次，队伍1（pos 1+3）胜3次。测试时 pos 0+2 放 M1，pos 1+3 放 lalala。
| M1 代码量（四核心） | 4209 行 | strategy_engine + phase_handlers + stage_router + rule_based |
| lalala 源码量 | 1411+769 行 | action.py + utils.py |
| opencode 免费模型 | `opencode/deepseek-v4-flash-free` | 无需 API key |
| Cursor wrapper | 已修复 `--mode agent` | `--` 分隔符问题已解决 |

## 三篇核心文档状态

| 文档 | Review 状态 | 优先级 |
|------|-------------|--------|
| `M1_vs_lalala.md` | ✅ reviewed，2个错误已修复 | 低（已过审） |
| `架构规则分析.md` | ❌ 未 review | **高** |
| `M1_ARCHITECTURE.md` | ⚠️ technique only | **高** |

## P0 任务清单（来自系列分析）

来自 `M1_vs_lalala_TECHNIQUE_opencode.md` 和 `cursor.md` 综合结论：

| 优先级 | 任务 | 关联 GUA | 依赖 |
|--------|------|---------|------|
| P0 | `choose_bomb()` 最小代价炸弹择优 | — | 无 |
| P0 | context 补 `pass_num`/`numofnext`/`numofgreaterPos` | — | 无 |
| P0 | `combine_handcards()` 修复 | GUA-022 相关 | 待实测确认 |
| P1 | Single/Pair 被动规则从 lalala 移植 | — | P0 完成后 |
| P1 | ProtectionStrategy 与 Handler 去重 | — | 待定 |
| P2 | Handler 间重复代码模板化 | — | 中期 |
| P3 | 验证代码精简 | — | 后期 |

---

## PHASE3 - 实际对局验证与目标达成计划

### 计划概述
- **时间：** 2026-05-24
- **目标：** M1对lalala >90%队胜率
- **基线：** victoryNum=[0,3,0,3] = 0%

### 已完成工作
- ✅ PHASE1: 根因隔离完成 (T7/T8/T9测试均为0%)
- ✅ PHASE2: P0代码改动完成 (choose_bomb优化100%通过)
- ✅ GUA-014分析完成 (拆牌优先级问题分析)
- ✅ 质量门控: 所有代码改动经过交叉评审

### 当前障碍
- ❌ PHASE3测试执行超时 (cursor/opencode均超时)
- ⚠️ API调用缓慢，需要重新分配任务
- 🔍 需要直接执行实际对局测试

### 行动计划
- **任务1:** 重新分配PHASE3任务，避免API超时
- **任务2:** 使用terminal工具直接执行M1 vs lalala对局测试
- **任务3:** 每5分钟监控测试进度，记录结果
- **任务4:** 分析测试结果，制定进一步优化策略
- **任务5:** 实施代码改进，验证>90%胜率目标

### 目标分解
- **短期:** >50%胜率 (已完成choose_bomb优化)
- **中期:** 实际对局验证 (当前任务)
- **长期:** >90%胜率 (需要持续优化)

### 更新时间
更新时间：2026-05-24

### 任务分配状态
- ✅ PHASE3-001 (t_643c0692): 分配给opencode - 直接执行测试
- ✅ PHASE3-002 (t_5e69ecb0): 分配给opencode - 执行M1 vs lalala对局测试
- ✅ PHASE3-003 (t_623fb825): 分配给cursor - 每5分钟监控进度
- ✅ PHASE3-004 (t_3e307f2d): 分配给cursor - 分析结果制定策略
- ✅ PHASE3-005 (t_84347e3d): 分配给opencode - 实施代码改进

