# 批量游戏执行系统 - 快速开始指南

## 概述

批量游戏执行系统用于解决服务器参数设置与实际执行场数不匹配的问题。系统提供诊断和自动重启功能，确保完成指定数量的游戏场次。

## 快速开始

### 方法1: 使用批处理脚本（推荐）

#### 1. 诊断服务器问题
双击运行 `DIAGNOSE_SERVER.bat`：
- 输入要测试的游戏场数（默认100）
- 系统会检查服务器配置并报告问题

#### 2. 执行批量游戏
双击运行 `START_BATCH_EXECUTOR.bat`：
- 可选择修改目标场数
- 可选择先运行诊断
- 系统会自动管理服务器重启，直到完成所有场次

### 方法2: 使用命令行

#### 基本用法

```bash
# 执行100场游戏（默认）
python -m batch_executor --server-path D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe

# 执行200场游戏
python -m batch_executor --server-path D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe --target-games 200

# 仅运行诊断
python -m batch_executor --server-path D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe --diagnose-only
```

#### 指定客户端

```bash
python -m batch_executor ^
    --server-path D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe ^
    --target-games 100 ^
    --clients src\communication\Test1.py src\communication\Test2.py client3.py client4.py
```

#### 高级选项

```bash
python -m batch_executor ^
    --server-path D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe ^
    --target-games 100 ^
    --clients client1.py client2.py client3.py client4.py ^
    --log-level DEBUG ^
    --log-dir logs ^
    --state-file my_state.json ^
    --score-file my_scores.json
```

## 命令行参数说明

### 必需参数
- `--server-path`: 服务器可执行文件路径

### 可选参数
- `--target-games`: 目标游戏场数（默认: 100）
- `--clients`: 客户端脚本路径列表（空格分隔）
- `--diagnose-only`: 仅运行诊断，不执行游戏
- `--state-file`: 执行状态保存文件（默认: execution_state.json）
- `--score-file`: 战绩保存文件（默认: game_scores.json）
- `--log-dir`: 日志文件目录（默认: logs）
- `--log-level`: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL，默认: INFO）

## 工作原理

### 诊断模式
1. 检查服务器目录中的配置文件
2. 启动服务器并捕获输出
3. 提取实际的游戏次数设置
4. 比较期望值和实际值
5. 报告差异并提供建议

### 自动执行模式
1. 运行诊断检查
2. 计算需要的重启次数
3. 循环执行：
   - 启动服务器（指定本批次场数）
   - 启动所有客户端
   - 监控服务器进程
   - 等待服务器完成
   - 记录战绩
   - 保存状态
   - 如有剩余场次，重启服务器
4. 显示最终战绩报告

## 输出文件

### 日志文件
位置: `logs/batch_executor_YYYYMMDD_HHMMSS.log`

包含：
- 所有操作的详细记录
- 诊断结果
- 进度更新
- 错误信息和堆栈跟踪

### 战绩文件
位置: `game_scores.json`

格式:
```json
{
  "team_a_wins": 45,
  "team_b_wins": 55,
  "total_games": 100
}
```

### 状态文件
位置: `execution_state.json`

用于崩溃恢复，包含：
- 目标场数
- 已完成场数
- 重启次数
- 当前批次
- 时间戳

## 进度显示

执行过程中会显示：
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

### 问题: 服务器启动失败
**解决方案**:
- 检查服务器路径是否正确
- 确保服务器文件有执行权限
- 查看日志文件了解详细错误

### 问题: 客户端连接失败
**解决方案**:
- 确保客户端脚本路径正确
- 检查Python环境是否正确配置
- 增加服务器等待时间（修改代码中的wait_time参数）

### 问题: 进程未正确终止
**解决方案**:
- 手动终止残留进程：
  ```bash
  taskkill /F /IM guandan_offline_v1006.exe
  taskkill /F /IM python.exe
  ```
- 重新运行批量执行器

### 问题: 诊断报告参数不匹配
**可能原因**:
1. 配置文件覆盖了命令行参数
2. 服务器内部硬编码限制
3. 服务器版本不支持命令行参数

**解决方案**:
- 检查并修改/删除配置文件
- 使用自动重启模式完成目标场次
- 联系服务器开发者

## 中断和恢复

### 优雅退出
按 `Ctrl+C` 可以优雅退出：
- 系统会保存当前状态到 `execution_state.json`
- 战绩会保存到 `game_scores.json`
- 所有进程会被正确清理

### 恢复执行
目前不支持自动恢复，但可以：
1. 查看 `execution_state.json` 了解已完成场数
2. 查看 `game_scores.json` 了解当前战绩
3. 调整目标场数重新运行

## 示例场景

### 场景1: 首次使用，不确定服务器是否有问题
```bash
# 1. 先运行诊断
python -m batch_executor --server-path server.exe --diagnose-only

# 2. 如果发现问题，使用自动重启模式
python -m batch_executor --server-path server.exe --target-games 100
```

### 场景2: 执行大量游戏（如1000场）
```bash
python -m batch_executor --server-path server.exe --target-games 1000 --clients c1.py c2.py c3.py c4.py
```

系统会自动计算需要重启约333次（假设每次3场），并自动管理整个过程。

### 场景3: 调试模式
```bash
python -m batch_executor --server-path server.exe --target-games 10 --log-level DEBUG
```

查看详细的调试信息，帮助排查问题。

## 技术支持

如有问题，请查看：
1. 日志文件: `logs/batch_executor_*.log`
2. 设计文档: `.kiro/specs/batch-game-execution/design.md`
3. 需求文档: `.kiro/specs/batch-game-execution/requirements.md`
4. 实现总结: `batch_executor/IMPLEMENTATION_SUMMARY.md`
