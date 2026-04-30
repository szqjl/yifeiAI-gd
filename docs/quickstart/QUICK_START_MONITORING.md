# 训练监控快速开始指南

## 🚀 30秒快速开始

### 方案1: TensorBoard（推荐，最简单）

```bash
# 1. 安装
pip install tensorboard

# 2. 训练（默认使用 TensorBoard）
python src/train/stage7_optimized_training.py

# 3. 查看结果（新终端）
tensorboard --logdir logs/tensorboard
# 然后浏览器打开 http://localhost:6006
```

### 方案2: MLflow（功能强大）

```bash
# 1. 安装
pip install mlflow

# 2. 训练（指定使用 MLflow）
python src/train/stage7_optimized_training.py --monitor_backend mlflow

# 3. 查看结果（新终端）
mlflow ui
# 然后浏览器打开 http://localhost:5000
```

---

## 📊 工具对比

| 工具 | 安装 | 登录 | 推荐度 |
|------|------|------|--------|
| **TensorBoard** | `pip install tensorboard` | ❌ 不需要 | ⭐⭐⭐⭐⭐ |
| **MLflow** | `pip install mlflow` | ❌ 不需要 | ⭐⭐⭐⭐ |
| **wandb** | `pip install wandb` | ✅ 需要 | ⭐⭐⭐ |

---

## 💡 推荐选择

- **无法登录 wandb？** → **TensorBoard**（默认，最简单）
- **需要实验管理？** → **MLflow**（功能强大）
- **wandb 可用？** → **wandb**（功能最全）

---

## 📖 详细文档

- [训练监控工具替代方案](docs/training/训练监控工具替代方案.md)
- [智能训练插件使用指南](docs/training/智能训练插件使用指南.md)
