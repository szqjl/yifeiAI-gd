# 训练模型与yf_v5关系说明

## 1. 训练模型和yf_v5的关系

### 架构关系

```
yf2_v5 (主客户端)
  ├── HybridDecisionEngineV5 (规则引擎，权重60%)
  ├── RLDecisionEngine (RL引擎，权重15%) ← 使用训练好的模型
  └── 知识库 (权重25%)
```

### 详细说明

**yf2_v5** 是一个**混合决策系统**，它融合了三种决策源：

1. **规则引擎** (HybridDecisionEngineV5)
   - 权重：**60%**（最高优先级）
   - 基于规则和策略的决策
   - 包含：单牌策略、炸弹策略、残局策略等

2. **RL引擎** (RLDecisionEngine) ← **使用训练好的模型**
   - 权重：**15%**
   - 使用训练好的神经网络模型进行决策
   - 模型文件：`models/bc_model_v1.pth`（预训练模型）

3. **知识库**
   - 权重：**25%**
   - 基于历史对局数据的决策建议

### 决策流程

```
1. 规则引擎决策 → 评分 × 0.6
2. RL引擎决策 → 评分 × 0.15  ← 使用训练好的模型
3. 知识库决策 → 评分 × 0.25
4. 融合所有决策 → 选择最高分的动作
```

---

## 2. 训练成功后如何使用

### 当前状态

- **训练好的模型**: `models/bc_model_v1.pth`（预训练模型）
- **RL引擎默认模型**: `models/ppo_model_v1.pth`（强化学习模型）

### 问题

**RLDecisionEngine** 默认加载 `models/ppo_model_v1.pth`，但我们训练的是 `models/bc_model_v1.pth`。

### 解决方案

#### 方案1：修改RL引擎默认模型路径（推荐）

修改 `src/decision/rl_decision_engine.py`：

```python
class RLDecisionEngine:
    def __init__(self, model_path="models/bc_model_v1.pth"):  # 改为bc_model_v1.pth
        # ...
```

#### 方案2：复制模型文件

将训练好的模型复制为默认名称：

```bash
copy models\bc_model_v1.pth models\ppo_model_v1.pth
```

#### 方案3：在yf2_v5中指定模型路径

修改 `src/communication/yf2_v5.py`：

```python
# Initialize RL Engine
try:
    self.rl_engine = RLDecisionEngine(model_path="models/bc_model_v1.pth")  # 指定模型路径
    self.rl_available = True
    self.logger.info("✓ RL Engine initialized")
except Exception as e:
    # ...
```

---

## 3. 使用训练好的模型进行比赛

### 步骤

1. **确保模型文件存在**
   ```bash
   # 检查模型文件
   dir models\bc_model_v1.pth
   ```

2. **修改RL引擎使用训练好的模型**（选择上述方案之一）

3. **启动比赛**
   ```bash
   START_V5_GUI.bat
   ```

4. **yf2_v5会自动使用训练好的模型**
   - RL引擎会加载 `models/bc_model_v1.pth`
   - 在决策时，RL引擎的决策会以15%的权重参与最终决策

### 决策过程

当yf2_v5需要做决策时：

1. **规则引擎** 给出建议（权重60%）
2. **RL引擎** 使用训练好的模型给出建议（权重15%）
3. **知识库** 给出建议（权重25%）
4. **融合所有建议**，选择最高分的动作

---

## 4. 模型效果验证

### 如何验证模型是否生效

1. **查看日志**
   - 启动yf2_v5后，查看日志中是否有：
     ```
     ✓ RL Engine initialized
     RL Engine loaded model from models/bc_model_v1.pth
     ```

2. **观察决策过程**
   - 在日志中查找 `[RL Debug]` 开头的调试信息
   - 这些信息显示RL引擎的决策过程

3. **统计RL决策使用情况**
   - yf2_v5会统计RL决策的使用次数
   - 查看日志中的统计信息

---

## 5. 模型权重调整

### 当前权重设置

在 `src/communication/yf2_v5.py` 中：

```python
self.rl_weight = 0.15  # RL决策权重（15%）
self.knowledge_weight = 0.25  # 知识库权重（25%）
self.rule_weight = 0.6  # 规则引擎权重（60%）
```

### 如何调整权重

如果训练好的模型效果很好，可以增加RL权重：

```python
self.rl_weight = 0.3  # 增加到30%
self.knowledge_weight = 0.2  # 降低到20%
self.rule_weight = 0.5  # 降低到50%
```

**注意**：权重总和应该等于1.0

---

## 6. 总结

### 关系总结

- **训练模型** (`bc_model_v1.pth`) 是 **RL引擎** 的神经网络模型
- **RL引擎** 是 **yf2_v5** 的决策组件之一（权重15%）
- **yf2_v5** 使用混合决策系统，融合规则、RL和知识库

### 使用流程

1. ✅ **训练模型** → `models/bc_model_v1.pth`
2. ✅ **修改RL引擎** → 使用训练好的模型
3. ✅ **启动比赛** → `START_V5_GUI.bat`
4. ✅ **yf2_v5自动使用模型** → 在决策中发挥作用

### 重要提示

- **训练好的模型不会完全替代规则引擎**，而是作为决策的一部分（15%权重）
- **如果模型效果很好**，可以增加RL权重
- **如果模型效果不好**，可以降低RL权重或暂时禁用RL引擎

---

**下一步**：修改RL引擎的默认模型路径，使其使用训练好的 `bc_model_v1.pth`。

