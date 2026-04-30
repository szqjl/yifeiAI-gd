# M1训练工作流快速指南

## 🎯 目标
训练模型帮助M1战胜client，胜率目标 > 50%

## 🚀 快速开始

### 一键启动工作流

```bash
# Windows
START_M1_WORKFLOW_FULL.bat

# Linux/Mac
python src/train/m1_training_workflow.py --max_iterations 10 --target_win_rate 0.50
```

## 📊 工作流说明

### 自动化流程

工作流会自动执行以下步骤，直到达到目标胜率：

1. **训练模型** - 使用优化后的Stage7训练框架
2. **分析结果** - 自动分析训练效果和问题
3. **评估胜率** - 评估M1 vs Client的胜率
4. **优化参数** - 根据结果自动调整训练参数
5. **迭代训练** - 重复上述步骤直到胜率 > 50%

### 监控训练

训练期间查看MLflow UI：

```bash
mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns
```

浏览器打开：http://localhost:5000

### 检查状态

```bash
python check_workflow_status.py
```

## 📁 相关文件

- **工作流脚本**: `src/train/m1_training_workflow.py`
- **训练框架**: `src/train/stage7_optimized_training.py`
- **结果分析**: `src/train/training_optimizer.py`
- **胜率评估**: `src/train/m1_vs_client_evaluator.py`
- **工作流历史**: `models/m1_training_workflow_history.json`

## 📖 详细文档

- [M1训练工作流使用指南](docs/training/M1训练工作流使用指南.md)
- [M1训练优化指南](docs/training/M1训练优化指南.md)
- [历次训练效果汇总](docs/training/历次训练效果汇总.md)

## ⚠️ 注意事项

1. **需要游戏记录**: 评估胜率需要M1与client的对战记录
2. **训练时间**: 每次迭代可能需要10-30分钟
3. **资源消耗**: 确保有足够的CPU/GPU和磁盘空间

## 🔄 工作流已启动

工作流正在后台运行，会自动迭代训练直到M1战胜client。

查看状态：
```bash
python check_workflow_status.py
```

---

**创建时间**: 2025-01-10
