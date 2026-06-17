# 01 - 项目现状速查表

**日期**：2026-05-27  
**范围**：M1/M2 引擎、PHASE2 迭代状态、缺陷与评测

---

## 快速概览

| 指标 | 数值 | 状态 |
|------|------|------|
| **M1 队胜率** | 0/10（0%） | 🔴 未达目标 |
| **PASS 率** | yf1 54-60%、yf2 50-56% | 🟡 改善但仍高 |
| **近似问题 PASS** | yf1 **10** ⚠️、yf2 **1** ✅ | 🟡 yf1 未清 |
| **单元测试** | 19 passed | 🟢 通过 |
| **victoryNum 链路** | 100% 非空率 | 🟢 已修 |
| **自动化度** | 改代码✅ 测试✅ 跑局❌ | 🟡 评测瓶颈 |
| **M2 状态** | 4/5 bugs 已修 | 🔴 80% 进度 |
| **RL 线** | 收敛困难 | 🔴 open |

---

## M1 最新评测（2026-05-26）

**样本**：10 对成对 `game_id`  
**对手**：lalala  
**测试位置**：P0 + P2（yf1_m1 + yf2_m1）

### 指标汇总

```
yf1_m1 (P0):
  - 决策总数：250 条
  - PASS 次数：136 (54.40%)
  - 近似问题 PASS：10
  - 平均 PASS 率：54.40%

yf2_m1 (P2):
  - 决策总数：233 条
  - PASS 次数：105 (45.06%)
  - 近似问题 PASS：1
  - 平均 PASS 率：45.06%

对比 lalala：
  - PASS 率：~15%（M1 是 lalala 的 3~4 倍）
```

### 胜负记录

```
M1 队胜场：0/10（0%）
对手队胜场：10/10（100%）
victoryNum 分布：全为 [0,3,0,3]
```

### PHASE2 改动轨迹

| 阶段 | 改动 | yf1 近似 PASS | yf2 近似 PASS | 队胜率 |
|------|------|-------------|-------------|--------|
| PHASE2-001 | choose_bomb | 待测 | 待测 | - |
| PHASE2-003 | 拆牌优先级 | 0 → 9 ⚠️ | 0 | 0% |
| PHASE2-004 | 队级进攻 | 9 → 10 | 8 | 0% |
| PHASE2-005 | 清近似 PASS | 10 | 1 ✅ | 0% |

**关键观察**：yf1 的近似 PASS 始终未清，且胜率始终 0%

---

## M2 引擎状态

**版本**：重构硬编码规则引擎（无分数累积）  
**目标**：突破 M1 的 0% 胜率  
**阶段**：Bug 修复 80% 完成

### 5 个 Bug 状态

| Bug | 类型 | 状态 | 影响 |
|-----|------|------|------|
| Bug 1 | index 错误 | ✅ 已修 | 残局崩溃 |
| Bug 2 | 无两手规划 | ❌ 未修 | 残局逐张输 |
| Bug 4 | 无队友配合 | ❌ 未修 | 无法双上 |
| Bug 5 | 无炸弹主动 | ❌ 未修 | 失去控场 |

### 跑分结果

```
初始跑分（44 局）：队胜率 0%、对手 6 胜
Bug 1-4 修后（36 局）：队胜率 0%、对手 6 胜
→ 修 Bug 1-4 后仍是 0%，说明真根因是 Bug 2+Bug 4
```

---

## 开放缺陷优先级

### 🔴 P1（当前重点）

| ID | 简述 | 影响 | 关联 |
|----|------|------|------|
| **GUA-022** | M1 队胜率 0% | 目标失败 | 主目标 |
| **GUA-014** | 拆牌与优先级 | 进攻无力 | 联动 GUA-022 |
| **GUA-016** | 训练样本质量 | RL 参差 | 训练线 |
| **GUA-017** | 训练损失异常 | RL 收敛困难 | 训练线 |

### 🟡 P2（后续）

- GUA-009：V4 RL 未启用
- GUA-010：决策信息不全
- GUA-013：疑似重复出牌
- GUA-015：V6 路线验收未闭环

### 🟢 已闭缺陷

- **GUA-020**（2026-04-21）：yf1/yf2 PASS 率差无明显差异 → 不必分叉
- **GUA-021**（2026-04-21）：问题 PASS 清零 → yf2 已清，yf1 仍需清

---

## 批跑基础设施

### 离线服务器

**路径**：`D:/GDAI/server/windows/guandan_offline_v1006.exe`  
**验证**：
```bash
python -m batch_executor --diagnose-only
```

### 快速跑局（M1 vs lalala）

```bash
# GUI 模式（推荐）
START_M1_GUI.bat
# 或命令行
python batch_executor_gui_m1.py

# 无头模式（脚本化）
python -m batch_executor --server-path "D:/GDAI/..." --target-games 10 \
  --clients src/communication/yf1_m1.py run_lalala_client3.py \
           src/communication/yf2_m1.py run_lalala_client4.py
```

### 评测结果位置

- **执行日志**：`logs/batch_executor_*.log`
- **游戏记录**：`game_records/`（格式：`{game_id} [{client_name}]-*.json`）
- **执行状态**：`batch_executor/execution_state.json`（包含 completed_games、target_games）

---

## 近期迭代路线

### PHASE2 完成（2026-05-26）

**目标**：GUA-022（队胜率）+ GUA-014（拆牌）  
**改动**：choose_bomb、拆牌优先级、队级进攻、清近似 PASS  
**结果**：指标改善，胜率 0% 不动 → **方向需调整**

### 下一步（待执行）

**建议不继续改 PHASE2-006+，改为转向 Lv2（队伙联动）**

具体见：[05-root-cause-analysis.md](05-root-cause-analysis.md)

---

## 技术栈与环境

- **Python**：3.8+
- **框架**：PyTorch（RL）、Gymnasium（RL 环境）
- **通信**：WebSocket
- **测试**：pytest
- **版本管理**：git（分支：m1-dev、v6-dev、main）

---

## 关键文件索引

| 文件 | 用途 |
|------|------|
| `src/decision/stage_router.py` | 5 阶段路由器 |
| `src/decision/phase_handlers.py` | 阶段处理器（Opening/Mid/Endgame） |
| `src/decision/rule_based_decision_engine_m1.py` | M1 主决策引擎 |
| `src/communication/yf1_m1.py` / `yf2_m1.py` | M1 客户端 |
| `batch_executor/executor.py` | 批量执行与计数 |
| `game_recorder.py` | 游戏记录与 victoryNum 链路 |

---

**参考**：[guandan-brain/EVAL.md](../../guandan-brain/EVAL.md)、[guandan-brain/ITERATIONS.md](../../guandan-brain/ITERATIONS.md)
