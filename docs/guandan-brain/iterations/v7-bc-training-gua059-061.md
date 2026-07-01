---
tags: [V7, BC-training, GUA-059, GUA-060, GUA-061, argmax-collapse]
created: 2026-06-17
topic: V7 BC 训练诊断与模块化架构
related: [[V7-Development]], [[v7-features-gua037-038]]
---

# V7 BC 训练诊断与模块化架构（GUA-059 ~ GUA-061）

> 来源：[[ITERATIONS]] 2026-06-17（6 条迭代）

## GUA-059：action_head 修复 + Guard 接入

| 日期 | 阶段 | 内容 |
|------|------|------|
| 2026-06-17 | 阶段 1 | action_head 2048→512；Guard 接入；grouping_score 9 维串联 |
| 2026-06-17 | 阶段 2 重训 | 5541 样本 val_acc=**36.46%**（6 epoch 锁死） |

**关键信号**：val_acc 锁死现象提示非"训练不足"，而是模型 collapse 到固定预测。

## GUA-060：argmax collapse 诊断

| 日期 | 迭代 | 内容 |
|------|------|------|
| 2026-06-17 | A 诊断 | `tmp_action_dist_diag.py`：top1=35.75% ≈ val_acc 36.46% → **模型 argmax collapse 到 top1（强证据）**；唯一 action 166/512（67.6% 未用）；罕见 action（<5 样本）121/166（72.9%）；归一化熵 0.489 |
| 2026-06-17 | B-α 失败 | label_smoothing=0.1 引爆 loss 9.12e7 → **val_acc 仍锁死 36.46%**；关键发现：val_acc 锁死与 loss 完全解耦 |

### C 方向（待交接）

| 方向 | 内容 | 推荐度 |
|------|------|--------|
| C-α | class_weight=1/sqrt(count) 反比加权 | ⭐⭐⭐ 推荐 |
| C-β | focal loss γ=2.0 | ⭐⭐ 备选 |
| C-γ | dropout 0.2→0.5 + wd 1e-4→1e-3 | ⭐ 备选 |

**关单硬条件**：val_acc>50% + 12 局副胜率≥11.8% + ≥30 局 vs lalala 队胜率不下降。

## GUA-060 关单 + GUA-061 立项

| 日期 | 迭代 | 内容 |
|------|------|------|
| 2026-06-17 | GUA-060 closed | BC 调参路线终止；argmax collapse 在掼蛋动态贝叶斯决策中是**理论必然**——同一手牌不同圈数/角色出不同动作，BC 只能学平均值；V2-V7 六个版本端到端 BC/RL 全部 ≤3% 队胜率佐证 |
| 2026-06-17 | **GUA-061 open** | 模块化架构：M3 组牌逻辑提取 + GroupingEngine 独立模块 |

**正确路径**：组牌（算法）→ 角色定位 → 记忆追踪 → 动态调整 → 动作选择（模块化分阶段训练，套路七 Week 1-5）

**GUA-061 路线**：
1. P0 ①：从 M3 `enumerate_groupings` 提取组牌核心逻辑，封装为 V7-internal `GroupingEngine`（纯函数 + pytest ≥8 case）
2. P0 ②：接入 V7 引擎特征管线，替换当前 grouping_scanner 9 维软信号
3. P1 ③：组牌增强 BC 重训对比基线 36.46%
4. P1 ④：若不生效→正式启动模块化分阶段训练

### 交接材料

- `ISSUES.md` GUA-060 完整 C 方向完成定义
- `tmp_action_dist_diag.py` 诊断脚本
- `bc_model_v2_PRE_RETRAIN_20260617.pth`（1.19MB，2048 维退化）
- `bc_model_v2_GUA060_20260617_36pct.pth`（640KB，36.46% 当前）
- `v4v5v6-lessons-2026-06.md` §0 红线
