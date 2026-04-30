# M1完整训练工作流

## 🎯 唯一目标
**M1战胜client（胜率 > 50%）**

## ✨ 完整功能

### 1. ✅ 自动运行M1与client对战生成记录
- 自动检查游戏记录数量
- 记录不足时自动运行M1客户端与client对战
- 生成足够的游戏记录用于评估

### 2. ✅ MLflow实时监控训练指标
- 训练过程中实时记录指标到MLflow
- 自动从MLflow读取实时训练指标
- 分析预测比例、损失趋势、预测质量等

### 3. ✅ 根据MLflow指标自动优化训练代码
- 根据实时指标分析结果
- 自动调整训练代码中的参数：
  - `over_prediction_penalty` - 过度预测惩罚
  - `loss_alpha` - 正样本权重
  - `sparsity_reward` - 稀疏性奖励
  - `learning_rate` - 学习率
- 自动备份原代码，确保可回滚

### 4. ✅ 迭代训练直到M1战胜client
- 自动评估胜率
- 如果胜率 < 50%，自动优化并重新训练
- 直到胜率 ≥ 50% 自动停止

## 🚀 快速开始

### 一键启动完整工作流

```bash
START_M1_WORKFLOW_FULL.bat
```

### 或使用Python命令

```bash
python src/train/m1_training_workflow.py \
    --max_iterations 10 \
    --target_win_rate 0.50 \
    --min_games 50
```

## 📊 实时监控

### 启动MLflow UI（推荐）

工作流运行期间，在新终端运行：

```bash
mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns
```

然后在浏览器打开：**http://localhost:5000**

### 查看的指标

- **Loss指标**: `loss/total`, `loss/action`, `loss/strategy`
- **预测指标**: `metrics/predicted_cards`, `metrics/true_cards`, `metrics/prediction_ratio`
- **质量指标**: `quality/prediction_quality_score`, `best/combined_score`

## 🔄 工作流程

```
开始
  ↓
[0] 检查/生成游戏记录（自动运行M1与client对战）
  ↓
[1] 训练模型（MLflow实时监控）
  ↓
[1.5] 从MLflow读取实时指标
  ↓
[2] 分析训练结果
  ↓
[3] 评估M1 vs Client胜率
  ↓
[4] 检查目标
  ├─ 胜率 ≥ 50% → ✅ 成功，停止
  └─ 胜率 < 50% → 继续
  ↓
[5] 根据MLflow指标自动优化训练代码
  ↓
[迭代] 重复步骤0-5
  ↓
结束（达到目标或最大迭代次数）
```

## 🛠️ 自动优化机制

### 根据MLflow指标自动优化

工作流会根据MLflow实时指标自动优化训练代码：

| 问题 | MLflow指标 | 自动优化动作 |
|------|-----------|-------------|
| 预测过度 | `prediction_ratio > 2.0` | 增加 `over_prediction_penalty` (x1.5)<br>降低 `loss_alpha` (x0.8) |
| 预测不足 | `prediction_ratio < 0.5` | 降低 `over_prediction_penalty` (x0.7)<br>增加 `loss_alpha` (x1.2) |
| 损失上升 | `loss_trend = increasing` | 降低 `learning_rate` (x0.5) |
| 预测质量低 | `quality_score < 0.3` | 增加 `sparsity_reward` (x1.5) |

### 代码备份

每次优化前自动备份：
- 原文件: `src/train/stage7_optimized_training.py`
- 备份文件: `src/train/stage7_optimized_training.py.backup`

## 📁 相关文件

### 核心组件
- `src/train/m1_training_workflow.py` - 主工作流脚本
- `src/train/mlflow_monitor.py` - MLflow实时监控器
- `src/train/auto_game_runner.py` - 自动游戏运行器
- `src/train/code_optimizer.py` - 代码自动优化器
- `src/train/m1_vs_client_evaluator.py` - 胜率评估器

### 启动脚本
- `START_M1_WORKFLOW_FULL.bat` - 完整工作流启动脚本（推荐）

### 文档
- `docs/training/M1完整工作流说明.md` - 详细说明文档

## 📈 工作流历史

工作流历史保存在：
```
models/m1_training_workflow_history.json
```

包含每次迭代的：
- 胜率
- MLflow分析结果
- 训练分析结果
- 时间戳
- 最终状态

## ⚠️ 注意事项

1. **游戏服务器路径**: 如果未自动找到，需要手动指定 `--server_path`
2. **训练时间**: 每次迭代可能需要10-30分钟
3. **MLflow UI**: 建议保持打开，实时查看训练指标
4. **代码备份**: 自动优化前会备份，可随时回滚

## 🎯 成功标准

工作流在以下情况停止：

1. **✅ 成功**: 胜率 ≥ 50%（自动停止）
2. **⚠️ 未达标**: 达到最大迭代次数但未达标
3. **❌ 失败**: 某次迭代训练失败

## 📖 详细文档

- [M1完整工作流说明](docs/training/M1完整工作流说明.md)
- [M1训练优化指南](docs/training/M1训练优化指南.md)
- [M1训练工作流使用指南](docs/training/M1训练工作流使用指南.md)

---

**创建时间**: 2025-01-10  
**目标**: M1战胜client（胜率 > 50%）
