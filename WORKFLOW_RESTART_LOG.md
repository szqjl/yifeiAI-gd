# 工作流重新启动日志

## 重启时间
2026-01-12（使用系统时间API获取）

## 修复内容

### 1. 损失函数修复
- **阈值计算**：从 `adaptive_threshold * sparsity_weight` 改为 `clamp(base_threshold * 0.01, 0.001, 0.1)`
  - 避免预测所有512张卡牌
  - 确保阈值在合理范围（0.001-0.1）
  
- **过度预测惩罚**：从平方惩罚改为对数惩罚
  - 之前：`over_prediction_penalty * (over_prediction ** 2)`（导致1500亿级别惩罚）
  - 现在：`over_prediction_penalty * log(1 + over_prediction)`（更温和）
  
- **稀疏性奖励**：从指数函数改为倒数函数
  - 之前：`sparsity_reward * exp(-pred_count / 10.0)`（预测512时接近0）
  - 现在：`sparsity_reward / (1.0 + pred_count)`（更合理）

- **参数调整**：
  - `over_prediction_penalty`: 576,650.39 → 1000.0
  - `sparsity_reward`: 2,883,251.95 → 100.0
  - `alpha`: 0.093 → 0.05
  - `gamma`: 6.0 → 5.0

### 2. 数据加载器修复
- 已过滤空action_cards样本
- 验证action_vec不为全0
- 真实卡牌数从0.79提升到1.44

### 3. 统计改进
- 只统计非零样本，避免PASS动作影响

## 预期改进

### 修复前
- 损失值：80,168,580,121.39（800亿）
- 预测比例：355.37倍
- 预测卡牌数：512.00/512（所有卡牌）

### 修复后预期
- 损失值：< 1000（合理范围）
- 预测比例：< 10倍
- 预测卡牌数：< 10张（合理范围）

## 监控要点

1. **损失值趋势**：应该大幅下降
2. **预测比例**：应该显著降低
3. **预测卡牌数**：应该从512降至合理范围
4. **真实卡牌数**：应该保持在1.44左右或更高

## 查看方法

1. 工作流状态：
   ```bash
   python check_workflow_status.py
   ```

2. MLflow监控：
   ```bash
   mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns
   ```
   然后浏览器打开 http://localhost:5000

3. 训练效果：
   ```bash
   python view_training_summary.py
   ```
