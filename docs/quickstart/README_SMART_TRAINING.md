# 智能训练插件快速参考

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 选择训练方式

#### 方式1: 标准训练 + Wandb 监控（推荐新手）

```bash
# 首次使用需要登录
wandb login

# 运行训练
python src/train/stage7_optimized_training.py
```

#### 方式2: Optuna 超参数优化（推荐有经验用户）

```bash
# 运行优化（50次试验）
python src/train/optuna_hyperparameter_optimization.py --n_trials 50

# 查看结果
cat optuna_results/stage7_optimization_*_best_params.json
```

#### 方式3: PyTorch Lightning 训练（推荐高级用户）

```bash
# 运行训练
python src/train/stage7_lightning_training.py --use_wandb
```

### 3. 使用 Windows 快速启动脚本

```bash
START_SMART_TRAINING.bat
```

## 📊 功能对比

| 功能 | 标准训练 | Optuna | PyTorch Lightning |
|------|---------|--------|------------------|
| 训练监控 | ✅ (wandb) | ❌ | ✅ (wandb) |
| 超参数优化 | ❌ | ✅ | ❌ |
| 自动检查点 | ❌ | ❌ | ✅ |
| 早停机制 | ✅ (手动) | ❌ | ✅ (自动) |
| 混合精度 | ❌ | ❌ | ✅ |
| 分布式训练 | ❌ | ❌ | ✅ |
| 代码复杂度 | 中等 | 高 | 低 |

## 📖 详细文档

查看完整使用指南：

```bash
# 打开文档
start docs/training/智能训练插件使用指南.md
```

或访问：`docs/training/智能训练插件使用指南.md`

## 🔧 常见问题

**Q: wandb 登录失败？**  
A: 检查网络，或使用离线模式：`export WANDB_MODE=offline`

**Q: Optuna 优化太慢？**  
A: 减少试验次数：`--n_trials 10`

**Q: 如何查看训练进度？**  
A: 训练开始后会自动打开 wandb 网页，或访问 https://wandb.ai

## 📝 示例命令

```bash
# 标准训练（自定义参数）
python src/train/stage7_optimized_training.py \
    --epochs 100 \
    --batch_size 64 \
    --learning_rate 0.00005 \
    --use_wandb \
    --wandb_project "my-project"

# Optuna 优化（自定义研究名称）
python src/train/optuna_hyperparameter_optimization.py \
    --n_trials 100 \
    --study_name "my_optimization"

# PyTorch Lightning（使用 GPU）
python src/train/stage7_lightning_training.py \
    --max_epochs 100 \
    --accelerator gpu \
    --devices 1 \
    --precision 16 \
    --use_wandb
```
