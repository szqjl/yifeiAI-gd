# MLflow查看指南

## 问题：MLflow UI看不到内容

如果打开MLflow UI后看不到内容，请按以下步骤检查：

### 1. 确认MLflow UI使用正确的Tracking URI

**重要**：MLflow UI必须使用与训练脚本相同的tracking URI。

#### 启动MLflow UI的正确命令：

```bash
# Windows (Git Bash)
mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns

# 或者使用绝对路径（Windows格式）
mlflow ui --backend-store-uri file:///D:/YiFeiAI-GD/logs/mlruns
```

**注意**：
- 路径必须是绝对路径
- 使用 `file://` 前缀
- 路径分隔符使用 `/`（不是 `\`）

### 2. 检查是否有运行记录

运行以下命令检查：

```bash
python check_mlflow_runs.py
```

这会显示：
- 所有实验列表
- 每个实验的运行数量
- 每个运行的指标和参数

### 3. 在MLflow UI中查看数据

#### 步骤1：打开MLflow UI
```bash
mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns
```

#### 步骤2：在浏览器中打开
```
http://localhost:5000
```

#### 步骤3：查看实验列表
- 左侧边栏会显示所有实验
- 点击实验名称（如 `m1-vs-client`）查看该实验的运行

#### 步骤4：查看运行详情
- 点击运行名称（如 `m1_workflow_iter1_20260110_100325`）
- 查看以下标签页：
  - **Overview**: 运行概览、参数、指标摘要
  - **Metrics**: 指标随时间变化的图表
  - **Params**: 所有训练参数
  - **Artifacts**: 保存的模型文件等

### 4. 常见问题排查

#### 问题1：页面显示"没有运行"
**原因**：MLflow UI的tracking URI与训练时不一致

**解决**：
1. 确认训练脚本使用的tracking URI（查看 `src/train/training_monitor.py`）
2. 使用相同的URI启动MLflow UI

#### 问题2：看到实验但没有运行记录
**原因**：训练可能还在进行中，或者训练失败

**解决**：
1. 检查训练日志确认训练状态
2. 运行 `python check_mlflow_runs.py` 查看实际运行记录

#### 问题3：有运行记录但看不到指标
**原因**：指标可能还在写入中，或者指标名称有问题

**解决**：
1. 刷新页面（F5）
2. 检查运行状态是否为 `FINISHED`
3. 查看运行详情页面的 `Metrics` 标签

### 5. 实时监控训练

#### 方法1：在训练过程中查看
1. 启动训练（使用MLflow backend）
2. 在另一个终端启动MLflow UI
3. 在浏览器中打开 `http://localhost:5000`
4. 实时刷新查看最新指标

#### 方法2：使用检查脚本
```bash
# 持续监控最新运行
python check_mlflow_runs.py
```

### 6. 当前实验信息

根据检查结果，当前有以下实验：

1. **m1-vs-client** (ID: 148326867361846751)
   - 运行数量: 1
   - 最新运行: `m1_workflow_iter1_20260110_100325`
   - 状态: FINISHED
   - 指标: 15个
   - 参数: 12个

2. **yifei-ai-gd** (ID: 463419311776901645)
   - 运行数量: 3
   - 包含多个历史训练运行

### 7. 快速查看命令

```bash
# 检查运行记录
python check_mlflow_runs.py

# 启动MLflow UI
mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns

# 在浏览器打开
# http://localhost:5000
```

### 8. 查看特定指标

在MLflow UI中：
1. 进入实验页面
2. 点击运行名称
3. 切换到 `Metrics` 标签
4. 选择要查看的指标（如 `best/prediction_quality_score`）

### 9. 比较多个运行

1. 在实验页面勾选多个运行
2. 点击 "Compare" 按钮
3. 对比不同运行的指标和参数

---

**提示**：如果仍然看不到内容，请：
1. 确认MLflow UI的tracking URI正确
2. 刷新浏览器页面（F5）
3. 检查 `logs/mlruns` 目录是否存在且有数据
4. 运行 `python check_mlflow_runs.py` 确认数据存在
