# Stage 7: 鲁棒性增强训练

## 概述

Stage 7 是基于 Stage 6 评估结果的问题修复和优化版本，专门解决模型稳定性和预测准确性问题。

## 问题分析

### Stage 6 存在的问题

1. **严重的稳定性问题**
   - 前3轮胜率50-60%，但第4-10轮全部为0%
   - 模型在连续对战中出现崩溃或严重性能下降

2. **预测过度问题**
   - 预测卡牌数平均28-35张，真实只有3张左右
   - 预测准确率仅6.2%，远低于期望

3. **数据质量问题**
   - 429个维度始终为0，信息利用不充分
   - 策略效果评估匹配率仅16.3%

## 解决方案

### 1. 模型架构改进

#### RobustGuandanNet 特性
- **残差连接**: 防止梯度消失，提升训练稳定性
- **BatchNorm**: 标准化中间层输出，加速收敛
- **多尺度特征提取**: 更好地捕获不同层次的特征
- **自适应阈值机制**: 动态调整预测阈值，减少过度预测

```python
class RobustGuandanNet(nn.Module):
    def __init__(self, input_dim=512, output_dim=512, dropout_rate=0.3):
        # 特征提取层（多尺度）
        self.feature_extractor = nn.Sequential(...)
        
        # 残差连接层
        self.residual_block = nn.Sequential(...)
        
        # 自适应阈值预测器
        self.threshold_predictor = nn.Sequential(...)
```

### 2. 损失函数优化

#### AdaptiveFocalLoss 特性
- **动态权重调整**: 根据样本难度自动调整权重
- **过度预测惩罚**: 直接惩罚预测过多卡牌的行为
- **自适应阈值**: 每个样本使用不同的预测阈值

```python
class AdaptiveFocalLoss(nn.Module):
    def forward(self, pred_logits, target, adaptive_threshold):
        # 使用自适应阈值进行预测
        # 计算过度预测惩罚
        # 组合焦点损失和惩罚项
```

### 3. 数据处理增强

#### EnhancedGuandanDataset 特性
- **数据标准化**: 基于统计信息的特征标准化
- **数据增强**: 噪声注入、特征dropout等技术
- **平衡采样**: 确保不同策略类型的样本均衡分布
- **异常值处理**: 自动过滤和清洗异常样本

### 4. 训练策略优化

#### 训练配置
- **优化器**: AdamW (更好的权重衰减)
- **学习率调度**: 余弦退火 (CosineAnnealingWarmRestarts)
- **梯度裁剪**: 防止梯度爆炸
- **早停机制**: 防止过拟合

## 使用方法

### 1. 启动训练

```bash
# Windows
START_STAGE7_TRAINING.bat

# 或直接运行Python脚本
cd src/train
python stage7_robust_training.py
```

### 2. 评估模型

```bash
cd src/train
python stage7_evaluation.py
```

### 3. 参数配置

```python
# 训练参数
train_stage7_robust_model(
    data_dir="game_records",
    model_save_path="models/bc_model_stage7_robust.pth",
    epochs=200,
    batch_size=32,
    learning_rate=0.0001,
    device="cpu"
)
```

## 评估指标

### 1. 预测准确性
- **完全匹配率**: 预测动作与真实动作完全一致的比例
- **卡牌级准确率**: 单个卡牌预测正确的比例
- **阈值准确性**: 自适应阈值的准确程度

### 2. 稳定性评估
- **多轮一致性**: 连续多轮测试的性能稳定性
- **变异系数**: 性能指标的变异程度
- **最小性能保证**: 最差情况下的性能下限

### 3. 综合评分
```
综合评分 = 准确性权重(40%) + 稳定性权重(30%) + 预测质量权重(30%)
```

## 预期改进

### 1. 稳定性提升
- 连续对战中性能不再崩溃
- 变异系数 < 0.05 (Stage 6: 1.535)
- 最低胜率 > 40% (Stage 6: 0%)

### 2. 预测准确性提升
- 完全匹配率 > 30% (Stage 6: 6.2%)
- 平均预测卡牌数 < 8张 (Stage 6: 28-35张)
- 过度预测比例 < 20%

### 3. 整体性能提升
- 综合评分 > 0.6
- 通过稳定性测试
- 适应不同对手策略

## 文件结构

```
src/train/
├── stage7_robust_training.py      # 主训练脚本
├── stage7_evaluation.py           # 评估脚本
└── enhanced_data_loader.py        # 增强数据加载器

models/
├── bc_model_stage7_robust.pth     # 训练好的模型
└── bc_model_stage7_robust_training_history.json  # 训练历史

training_logs/
└── stage7_evaluation_*.json       # 评估结果

START_STAGE7_TRAINING.bat          # Windows启动脚本
```

## 技术细节

### 1. 残差连接
```python
# 残差连接防止梯度消失
residual = self.residual_block(features)
features = features + residual  # 残差连接
features = torch.relu(features)
```

### 2. 自适应阈值
```python
# 每个样本预测自己的最优阈值
adaptive_threshold = self.threshold_predictor(features)
predicted_actions = (pred_probs > threshold.unsqueeze(1)).float()
```

### 3. 数据增强
```python
# 随机噪声增强
if random.random() < 0.3:
    noise = np.random.normal(0, 0.01, state_vec.shape)
    state_vec = state_vec + noise

# 特征dropout
if random.random() < 0.2:
    dropout_mask = np.random.random(state_vec.shape) > 0.05
    state_vec = state_vec * dropout_mask
```

## 监控和调试

### 1. 训练监控
- 实时损失曲线
- 学习率变化
- 梯度范数监控

### 2. 评估监控
- 多轮稳定性测试
- 预测分布分析
- 阈值准确性跟踪

### 3. 异常检测
- 梯度爆炸检测
- 性能突然下降检测
- 预测异常检测

## 故障排除

### 1. 训练不收敛
- 检查学习率设置
- 验证数据质量
- 调整损失函数权重

### 2. 预测过度
- 增加过度预测惩罚权重
- 调整自适应阈值范围
- 检查数据标注质量

### 3. 稳定性问题
- 增加Dropout比例
- 使用更强的正则化
- 减小学习率

## 后续优化方向

1. **模型压缩**: 减少模型大小，提升推理速度
2. **在线学习**: 支持增量学习和在线适应
3. **多任务学习**: 集成更多辅助任务
4. **对抗训练**: 提升模型鲁棒性
5. **知识蒸馏**: 从大模型向小模型转移知识