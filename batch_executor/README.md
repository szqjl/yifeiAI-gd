# 批量游戏执行系统

## 概述

批量游戏执行系统是一个用于解决掼蛋AI比赛中服务器参数设置与实际执行场数不匹配问题的自动化工具。系统提供两大核心功能：

1. **诊断模块**：诊断服务器为何只执行3场游戏的根本原因
2. **自动执行模块**：通过自动重启机制确保完成指定数量的游戏场次

## 功能特性

- ✅ 自动诊断服务器配置问题
- ✅ 智能监控服务器进程状态
- ✅ 自动重启服务器和客户端
- ✅ 累计跟踪多次运行的战绩
- ✅ 实时显示执行进度
- ✅ 详细的日志记录
- ✅ 优雅的异常处理和状态保存
- ✅ 支持中断后查看当前状态

## 系统要求

- Python 3.8 或更高版本
- Windows 操作系统（使用 taskkill 命令）
- 掼蛋离线服务器程序（guandan_offline_v1006.exe）
- 客户端 Python 脚本

## 安装步骤

### 1. 克隆或下载项目

```bash
cd YiFeiAI-GD
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- `psutil>=5.9.0` - 进程监控
- `hypothesis>=6.0.0` - 属性测试
- `pytest>=7.0.0` - 单元测试
- `pytest-cov>=4.0.0` - 测试覆盖率
- `pyyaml>=6.0` - YAML 配置文件支持

### 3. 验证安装

```bash
python -m batch_executor --help
```

如果看到帮助信息，说明安装成功。

## 使用方法

### 方法1: 使用批处理脚本（推荐新手）

#### 诊断服务器问题

双击运行 `DIAGNOSE_SERVER.bat`：

```batch
@echo off
echo ========================================
echo 服务器诊断工具
echo ========================================
python -m batch_executor --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" --diagnose-only
pause
```

系统会：
1. 检查服务器目录中的配置文件
2. 启动服务器并捕获输出
3. 提取实际的游戏次数设置
4. 比较期望值和实际值
5. 报告差异并提供建议

#### 执行批量游戏

双击运行 `START_BATCH_EXECUTOR.bat`：

```batch
@echo off
echo ========================================
echo 批量游戏执行系统
echo ========================================
python -m batch_executor --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" --target-games 100 --clients src\communication\Test1.py src\communication\Test2.py client3.py client4.py
pause
```

### 方法2: 使用命令行（推荐高级用户）

#### 基本用法

```bash
# 执行100场游戏（默认）
python -m batch_executor --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe"

# 执行200场游戏
python -m batch_executor --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" --target-games 200

# 仅运行诊断
python -m batch_executor --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" --diagnose-only
```

#### 指定客户端脚本

```bash
python -m batch_executor ^
    --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" ^
    --target-games 100 ^
    --clients src\communication\Test1.py src\communication\Test2.py client3.py client4.py
```

#### 自定义配置

```bash
python -m batch_executor ^
    --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" ^
    --target-games 100 ^
    --clients client1.py client2.py client3.py client4.py ^
    --log-level DEBUG ^
    --log-dir logs ^
    --state-file my_state.json ^
    --score-file my_scores.json
```

### 命令行参数说明

#### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--server-path` | 服务器可执行文件路径 | `--server-path "D:\server\guandan.exe"` |

#### 可选参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--target-games` | 目标游戏场数 | 100 | `--target-games 200` |
| `--clients` | 客户端脚本路径列表（空格分隔） | [] | `--clients c1.py c2.py c3.py c4.py` |
| `--diagnose-only` | 仅运行诊断，不执行游戏 | False | `--diagnose-only` |
| `--state-file` | 执行状态保存文件路径 | execution_state.json | `--state-file state.json` |
| `--score-file` | 战绩保存文件路径 | game_scores.json | `--score-file scores.json` |
| `--log-dir` | 日志文件目录 | logs | `--log-dir my_logs` |
| `--log-level` | 日志级别 | INFO | `--log-level DEBUG` |

日志级别选项：`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 工作原理

### 诊断模式流程

```
开始
  ↓
检查服务器目录配置文件
  ↓
启动服务器并捕获输出
  ↓
提取实际游戏次数设置
  ↓
比较期望值和实际值
  ↓
生成诊断报告
  ↓
结束
```

### 自动执行模式流程

```
开始
  ↓
运行诊断检查
  ↓
计算需要的重启次数
  ↓
┌─────────────────┐
│ 执行循环开始     │
├─────────────────┤
│ 1. 启动服务器    │
│ 2. 启动客户端    │
│ 3. 监控进程      │
│ 4. 等待完成      │
│ 5. 记录战绩      │
│ 6. 保存状态      │
└─────────────────┘
  ↓
是否还有剩余场次？
  ↓ 是          ↓ 否
  └→ 重启 ←┘   显示最终报告
                ↓
               结束
```

## 输出文件

### 1. 日志文件

**位置**: `logs/batch_executor_YYYYMMDD_HHMMSS.log`

**内容**:
- 所有操作的详细记录
- 诊断结果
- 进度更新
- 错误信息和堆栈跟踪

**示例**:
```
2024-01-15 10:30:00 INFO ============================================================
2024-01-15 10:30:00 INFO 批量游戏执行系统
2024-01-15 10:30:00 INFO ============================================================
2024-01-15 10:30:00 INFO 服务器路径: D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe
2024-01-15 10:30:00 INFO 目标场数: 100
2024-01-15 10:30:01 INFO 启动服务器，本批次场数: 3
2024-01-15 10:30:16 INFO 启动客户端: src\communication\Test1.py
```

### 2. 战绩文件

**位置**: `game_scores.json`

**格式**:
```json
{
  "team_a_wins": 45,
  "team_b_wins": 55,
  "total_games": 100
}
```

**说明**:
- `team_a_wins`: Team A 的胜场数
- `team_b_wins`: Team B 的胜场数
- `total_games`: 总游戏场数

### 3. 状态文件

**位置**: `execution_state.json`

**格式**:
```json
{
  "target_games": 100,
  "completed_games": 30,
  "restart_count": 9,
  "current_batch": 10,
  "start_time": "2024-01-15T10:30:00",
  "last_update": "2024-01-15T10:45:30"
}
```

**用途**: 用于崩溃恢复和状态查询

## 进度显示

执行过程中，系统会实时显示进度信息：

```
============================================================
执行进度
============================================================
目标场数: 100
已完成: 30
剩余: 70
当前批次: 10
重启次数: 9
已运行时间: 0:15:30

战绩报告:
  总场数: 30
  Team A: 15胜 (50.00%)
  Team B: 15胜 (50.00%)
============================================================
```

## 故障排除

### 问题1: 服务器启动失败

**错误信息**:
```
错误: 服务器启动失败，已重试 3 次
```

**可能原因**:
1. 端口被占用
2. 可执行文件不存在或路径错误
3. 权限不足
4. 服务器文件损坏

**解决方案**:
```bash
# 1. 检查服务器路径是否正确
dir "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe"

# 2. 检查端口是否被占用
netstat -ano | findstr :23456

# 3. 终止占用端口的进程
taskkill /F /PID <进程ID>

# 4. 以管理员身份运行
# 右键点击批处理脚本 -> 以管理员身份运行
```

### 问题2: 客户端连接失败

**错误信息**:
```
警告: 客户端启动失败: client1.py
```

**可能原因**:
1. 客户端脚本路径错误
2. Python 环境配置问题
3. 服务器未就绪
4. 脚本语法错误

**解决方案**:
```bash
# 1. 验证客户端脚本路径
dir src\communication\Test1.py

# 2. 手动测试客户端脚本
python src\communication\Test1.py

# 3. 检查 Python 环境
python --version
pip list

# 4. 增加服务器等待时间（修改代码）
# 在 restart_manager.py 中增加 wait_time 参数
```

### 问题3: 进程未正确终止

**症状**:
- 多个服务器进程同时运行
- 端口冲突
- 系统资源占用高

**解决方案**:
```bash
# 手动终止所有相关进程
taskkill /F /IM guandan_offline_v1006.exe
taskkill /F /IM python.exe

# 或使用任务管理器
# Ctrl+Shift+Esc -> 详细信息 -> 结束任务
```

### 问题4: 诊断报告参数不匹配

**诊断输出**:
```
诊断报告:
  期望游戏次数: 100
  实际游戏次数: 3
  检测到不匹配: 是
```

**可能原因**:
1. 配置文件覆盖了命令行参数
2. 服务器内部硬编码限制
3. 服务器版本不支持命令行参数

**解决方案**:
```bash
# 1. 检查并删除配置文件
dir D:\guandan_offline_v1006\windows\*.ini
dir D:\guandan_offline_v1006\windows\*.json
dir D:\guandan_offline_v1006\windows\*.txt

# 2. 使用自动重启模式完成目标场次
python -m batch_executor --server-path server.exe --target-games 100

# 3. 联系服务器开发者确认参数支持
```

### 问题5: 日志文件过大

**症状**:
- 日志文件占用大量磁盘空间
- 系统运行变慢

**解决方案**:
```bash
# 1. 降低日志级别
python -m batch_executor --server-path server.exe --log-level WARNING

# 2. 定期清理旧日志
del logs\*.log

# 3. 使用日志轮转（已内置）
# 系统会自动限制单个日志文件大小为 10MB
```

### 问题6: 战绩数据丢失

**症状**:
- game_scores.json 文件不存在或为空
- 战绩统计不准确

**解决方案**:
```bash
# 1. 检查文件是否存在
dir game_scores.json

# 2. 查看日志了解保存情况
type logs\batch_executor_*.log | findstr "保存战绩"

# 3. 手动创建初始文件
echo {"team_a_wins": 0, "team_b_wins": 0, "total_games": 0} > game_scores.json
```

## 中断和恢复

### 优雅退出

按 `Ctrl+C` 可以优雅退出系统：

1. 系统捕获中断信号
2. 保存当前状态到 `execution_state.json`
3. 保存战绩到 `game_scores.json`
4. 终止所有服务器和客户端进程
5. 清理资源
6. 退出程序

### 查看当前状态

```bash
# 查看执行状态
type execution_state.json

# 查看战绩
type game_scores.json

# 查看最新日志
type logs\batch_executor_*.log
```

### 恢复执行

目前系统不支持自动恢复，但可以手动恢复：

1. 查看 `execution_state.json` 了解已完成场数
2. 查看 `game_scores.json` 了解当前战绩
3. 计算剩余场数：`剩余 = 目标 - 已完成`
4. 重新运行系统，调整目标场数

**示例**:
```bash
# 假设目标 100 场，已完成 30 场
# 重新运行剩余 70 场
python -m batch_executor --server-path server.exe --target-games 70
```

## 使用场景示例

### 场景1: 首次使用，不确定服务器是否有问题

```bash
# 步骤1: 运行诊断
python -m batch_executor --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" --diagnose-only

# 步骤2: 查看诊断结果
# 如果发现参数不匹配，使用自动重启模式

# 步骤3: 执行批量游戏
python -m batch_executor --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" --target-games 100
```

### 场景2: 执行大量游戏（如1000场）

```bash
python -m batch_executor ^
    --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" ^
    --target-games 1000 ^
    --clients src\communication\Test1.py src\communication\Test2.py client3.py client4.py
```

系统会自动计算需要重启约 333 次（假设每次 3 场），并自动管理整个过程。

### 场景3: 调试模式

```bash
python -m batch_executor ^
    --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" ^
    --target-games 10 ^
    --log-level DEBUG
```

查看详细的调试信息，帮助排查问题。

### 场景4: 测试新客户端

```bash
# 使用少量场次测试
python -m batch_executor ^
    --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" ^
    --target-games 10 ^
    --clients new_client.py client2.py client3.py client4.py ^
    --log-level DEBUG
```

### 场景5: 夜间批量执行

```bash
# 创建批处理脚本 night_run.bat
@echo off
echo 开始夜间批量执行...
python -m batch_executor ^
    --server-path "D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe" ^
    --target-games 1000 ^
    --clients src\communication\Test1.py src\communication\Test2.py client3.py client4.py ^
    --log-level INFO
echo 执行完成！
pause
```

## 模块结构

```
batch_executor/
├── __init__.py              # 包初始化
├── diagnostic.py            # 诊断模块
├── process_monitor.py       # 进程监控模块
├── tracker.py               # 战绩跟踪模块
├── restart_manager.py       # 重启管理模块
├── executor.py              # 主执行器
├── input_validator.py       # 输入验证模块
├── logging_config.py        # 日志配置
├── main.py                  # 主入口
└── README.md               # 本文档
```

### 模块说明

#### 1. diagnostic.py - 诊断模块
- 检查服务器配置文件
- 捕获服务器输出
- 分析参数不匹配原因
- 生成诊断报告

#### 2. process_monitor.py - 进程监控模块
- 监控服务器和客户端进程状态
- 检测进程终止
- 管理进程生命周期

#### 3. tracker.py - 战绩跟踪模块
- 记录游戏结果
- 持久化战绩数据
- 生成统计报告

#### 4. restart_manager.py - 重启管理模块
- 管理服务器重启
- 管理客户端重启
- 清理进程资源

#### 5. executor.py - 主执行器
- 整合所有模块
- 实现主控制逻辑
- 协调执行流程

#### 6. input_validator.py - 输入验证模块
- 验证目标场数
- 计算重启次数
- 处理无效输入

#### 7. logging_config.py - 日志配置
- 配置日志系统
- 支持控制台和文件双输出
- 日志轮转管理

#### 8. main.py - 主入口
- 解析命令行参数
- 验证参数
- 启动执行器

## 测试

### 运行所有测试

```bash
pytest
```

### 运行特定类型的测试

```bash
# 单元测试
pytest -m unit

# 属性测试
pytest -m property

# 集成测试
pytest -m integration
```

### 查看测试覆盖率

```bash
pytest --cov=batch_executor --cov-report=html
```

然后打开 `htmlcov/index.html` 查看详细报告。

### 运行特定测试文件

```bash
pytest tests/test_diagnostic.py
pytest tests/test_tracker.py
pytest tests/test_executor.py
```

## 技术支持

### 文档资源

1. **快速开始指南**: `batch_executor/QUICK_START.md`
2. **设计文档**: `.kiro/specs/batch-game-execution/design.md`
3. **需求文档**: `.kiro/specs/batch-game-execution/requirements.md`
4. **实现总结**: `batch_executor/IMPLEMENTATION_SUMMARY.md`
5. **启动脚本说明**: `batch_executor/STARTUP_SCRIPTS_README.md`

### 日志分析

查看日志文件了解详细执行情况：

```bash
# 查看最新日志
type logs\batch_executor_*.log

# 搜索错误信息
findstr /i "error" logs\batch_executor_*.log

# 搜索警告信息
findstr /i "warning" logs\batch_executor_*.log
```

### 常见问题

如果遇到问题，请按以下步骤排查：

1. 查看日志文件中的错误信息
2. 运行诊断模式检查服务器配置
3. 验证所有文件路径是否正确
4. 检查 Python 环境和依赖是否安装完整
5. 查看本文档的"故障排除"部分

### 联系方式

如需进一步帮助，请查看项目文档或联系开发团队。

## 许可证

本项目用于掼蛋AI比赛，请遵守相关比赛规则和要求。

## 更新日志

### v1.0.0 (2024-01-15)
- ✅ 初始版本发布
- ✅ 实现诊断模块
- ✅ 实现自动执行模块
- ✅ 实现战绩跟踪
- ✅ 实现进程监控
- ✅ 实现日志系统
- ✅ 完整的测试覆盖

## 致谢

感谢南京邮电大学游戏AI平台提供的比赛环境和技术支持。
