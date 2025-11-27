# 启动脚本说明

本文档说明批量游戏执行系统的启动脚本使用方法。

## 文件列表

### 1. batch_executor.py
**位置**: `YiFeiAI-GD/batch_executor.py`

**说明**: Python主启动脚本，作为批量执行系统的主入口点。

**使用方法**:
```bash
# 基本用法
python batch_executor.py --server-path <服务器路径>

# 指定目标场数
python batch_executor.py --server-path server.exe --target-games 200

# 仅运行诊断
python batch_executor.py --server-path server.exe --diagnose-only

# 指定客户端脚本
python batch_executor.py --server-path server.exe --clients client1.py client2.py client3.py client4.py

# 完整示例
python batch_executor.py \
    --server-path guandan_offline_v1006.exe \
    --target-games 100 \
    --clients Test1.py Test2.py client3.py client4.py \
    --log-level INFO \
    --log-dir logs
```

**命令行参数**:
- `--server-path`: 服务器可执行文件路径（必需）
- `--target-games`: 目标游戏场数（默认: 100）
- `--clients`: 客户端脚本路径列表（空格分隔）
- `--diagnose-only`: 仅运行诊断，不执行游戏
- `--state-file`: 执行状态保存文件路径（默认: execution_state.json）
- `--score-file`: 战绩保存文件路径（默认: game_scores.json）
- `--log-dir`: 日志文件目录（默认: logs）
- `--log-level`: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）

### 2. START_BATCH_100.bat
**位置**: `YiFeiAI-GD/START_BATCH_100.bat`

**说明**: Windows批处理脚本，用于快速启动批量游戏执行系统，执行100场游戏。

**使用方法**:
1. 双击运行此脚本
2. 或在命令行中运行: `START_BATCH_100.bat`

**配置说明**:

在使用前，请编辑脚本中的以下变量：

```batch
REM 设置服务器路径（请根据实际情况修改）
set SERVER_PATH=D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe

REM 设置客户端脚本路径（请根据实际情况修改）
set CLIENT1=src\communication\Test1.py
set CLIENT2=src\communication\Test2.py
set CLIENT3=D:\掼蛋算法大赛选手人工智能代码\一等奖-东南大学-李菁-lalala-人机大赛\client3.py
set CLIENT4=D:\掼蛋算法大赛选手人工智能代码\一等奖-东南大学-李菁-lalala-人机大赛\client4.py

REM 设置目标场数
set TARGET_GAMES=100
```

**功能特性**:
- 自动检查Python环境
- 验证服务器文件是否存在
- 检查客户端脚本（警告但不阻止执行）
- 显示配置信息
- 用户确认后启动
- 执行完成后显示结果和相关文件位置
- 可选查看战绩

**环境变量**:
- `PYTHONIOENCODING=utf-8`: 设置Python编码为UTF-8
- `LOG_LEVEL`: 日志级别（默认: INFO）
- `LOG_DIR`: 日志目录（默认: logs）
- `STATE_FILE`: 状态文件（默认: execution_state.json）
- `SCORE_FILE`: 战绩文件（默认: game_scores.json）

## 执行流程

### Python脚本执行流程
1. 解析命令行参数
2. 验证参数有效性
3. 初始化日志系统
4. 创建BatchExecutor实例
5. 运行诊断（可选）
6. 执行批量游戏
7. 显示最终结果

### 批处理脚本执行流程
1. 检查Python环境
2. 验证服务器文件存在
3. 检查客户端脚本
4. 显示配置信息
5. 用户确认
6. 调用Python启动脚本
7. 显示执行结果
8. 可选查看战绩

## 输出文件

执行完成后，系统会生成以下文件：

1. **日志文件**: `logs/batch_executor_YYYYMMDD_HHMMSS.log`
   - 包含详细的执行日志
   - 记录所有操作和错误信息

2. **战绩文件**: `game_scores.json`
   - 记录累计战绩
   - 包含team_a和team_b的胜场数

3. **状态文件**: `execution_state.json`
   - 保存当前执行状态
   - 用于异常恢复

## 故障排除

### 问题1: 找不到Python
**错误**: `未找到Python，请先安装Python 3.8或更高版本`

**解决方法**:
1. 安装Python 3.8或更高版本
2. 确保Python已添加到系统PATH环境变量

### 问题2: 服务器文件不存在
**错误**: `服务器文件不存在`

**解决方法**:
1. 检查SERVER_PATH变量设置是否正确
2. 确认服务器文件路径存在

### 问题3: 客户端脚本不存在
**警告**: `只找到 X 个客户端脚本`

**解决方法**:
1. 检查CLIENT1-CLIENT4变量设置
2. 确认客户端脚本路径正确
3. 如果不需要4个客户端，可以忽略此警告

### 问题4: 目标场数验证失败
**错误**: `目标场数必须是正整数`

**解决方法**:
1. 确保TARGET_GAMES设置为正整数
2. 不要使用负数或零

## 高级用法

### 自定义日志级别
```bash
python batch_executor.py --server-path server.exe --log-level DEBUG
```

### 指定自定义文件路径
```bash
python batch_executor.py \
    --server-path server.exe \
    --state-file my_state.json \
    --score-file my_scores.json \
    --log-dir my_logs
```

### 仅诊断模式
```bash
python batch_executor.py --server-path server.exe --diagnose-only
```

## 注意事项

1. **编码问题**: 批处理脚本已设置`PYTHONIOENCODING=utf-8`，确保中文正常显示
2. **路径空格**: 如果路径包含空格，请使用引号括起来
3. **权限问题**: 确保有足够权限访问服务器和客户端文件
4. **进程清理**: 系统会自动清理进程，但异常退出时可能需要手动终止
5. **状态恢复**: 如果执行中断，下次启动会尝试从状态文件恢复

## 相关文档

- [批量执行系统README](README.md) - 系统整体说明
- [实现总结](IMPLEMENTATION_SUMMARY.md) - 实现细节
- [需求文档](../.kiro/specs/batch-game-execution/requirements.md) - 需求规格
- [设计文档](../.kiro/specs/batch-game-execution/design.md) - 设计规格
