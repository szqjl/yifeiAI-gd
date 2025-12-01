# YF_V5 升级指南

## 概述

YF_V5 是在 YF_V4 基础上的升级版本，保留了 V4 的所有功能，同时增加了以下增强特性：

### V5 新增特性

1. **智能混合决策** (Hybrid Decision Fusion)
   - 融合 RL 决策、知识库决策和规则引擎决策
   - 可配置的权重系统

2. **增强的 RL 集成**
   - 更智能的 RL 引擎调用
   - 自动降级机制（RL 不可用时回退到 V4）

3. **改进的统计追踪**
   - 分别追踪 RL 决策和知识库决策的使用情况
   - 更详细的性能分析

## 文件结构

### V4 文件（保留）

- `src/communication/yf1_v4.py` - V4 客户端（Player 0）
- `src/communication/yf2_v4.py` - V4 客户端（Player 2）
- `src/decision/hybrid_decision_engine_v4.py` - V4 决策引擎

### V5 文件（新增）

- `src/communication/yf1_v5.py` - V5 客户端（Player 0）
- `src/communication/yf2_v5.py` - V5 客户端（Player 2）

## 版本对比

| 特性 | V4 | V5 |
|------|----|----|
| **基础决策引擎** | ✅ HybridDecisionEngineV4 | ✅ HybridDecisionEngineV4 |
| **知识库集成** | ✅ 已集成 | ✅ 已集成（增强） |
| **RL 集成** | ⚠️ 部分集成 | ✅ 完整集成 |
| **决策融合** | ❌ 无 | ✅ 智能融合 |
| **权重配置** | ❌ 无 | ✅ 可配置 |
| **统计追踪** | ✅ 基础统计 | ✅ 增强统计 |

## V5 核心改进

### 1. 智能混合决策

V5 实现了多源决策融合：

```python
# V5 决策流程
1. 知识库增强决策（权重 50%）
   └─ HybridDecisionEngineV4（包含知识库规则）
   
2. RL 决策（权重 30%）
   └─ RLDecisionEngine（如果可用）
   
3. 规则引擎决策（权重 20%）
   └─ 基础规则和关键规则

4. 选择最优动作（按加权评分）
```

### 2. 自动降级机制

- **RL 不可用**：自动回退到知识库决策
- **知识库失败**：自动回退到规则引擎
- **所有失败**：回退到 V4 的 decide 方法

### 3. 增强的统计追踪

V5 提供更详细的统计信息：

```python
{
    "total_decisions": 100,
    "rl_decisions": 30,        # RL决策次数
    "knowledge_decisions": 50,  # 知识库决策次数
    "layer_stats": {...}       # 各层使用统计
}
```

## 使用方法

### 启动 V5 客户端

```bash
# Player 0
python src/communication/yf1_v5.py

# Player 2
python src/communication/yf2_v5.py
```

### 配置决策权重

在 `yf1_v5.py` 或 `yf2_v5.py` 中修改：

```python
self.rl_weight = 0.3          # RL决策权重
self.knowledge_weight = 0.5   # 知识库权重
self.rule_weight = 0.2        # 规则引擎权重
```

### 启用/禁用混合决策

```python
self.use_hybrid_decision = True   # 启用混合决策
self.use_hybrid_decision = False  # 禁用（回退到V4）
```

## 兼容性

### ✅ 完全兼容

- V4 和 V5 可以同时运行
- V4 和 V5 可以互相配合（同一队伍）
- 共享相同的决策引擎（HybridDecisionEngineV4）
- 共享相同的知识库

### 📋 日志区分

- V4 日志：`logs/yf1_v4_*.log`
- V5 日志：`logs/yf1_v5_*.log`

## 性能对比

### 预期改进

- **决策质量**：+5-10%（通过多源融合）
- **决策速度**：-0.01-0.02秒（RL调用开销）
- **胜率提升**：+2-5%（通过智能融合）

### 实际效果

需要实际测试验证，建议：
1. 运行 V4 和 V5 各 100 场
2. 对比胜率和决策质量
3. 根据结果调整权重

## 迁移建议

### 从 V4 迁移到 V5

1. **保留 V4**：V4 作为稳定版本保留
2. **测试 V5**：在测试环境验证 V5 性能
3. **逐步切换**：先在一个玩家使用 V5，另一个使用 V4
4. **全面切换**：验证无误后全面切换到 V5

### 回退方案

如果 V5 出现问题，可以：
1. 设置 `use_hybrid_decision = False`（回退到 V4 逻辑）
2. 直接使用 V4 客户端

## 总结

✅ **V4 已保留**：所有 V4 文件保持不变

✅ **V5 已创建**：新增 V5 客户端文件

✅ **完全兼容**：两个版本可以共存

✅ **向后兼容**：V5 可以回退到 V4 逻辑

现在可以同时使用 V4 和 V5 进行对比测试！

