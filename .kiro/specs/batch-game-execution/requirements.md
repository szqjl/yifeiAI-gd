# Requirements Document

## Introduction

本需求文档描述了一个批量游戏执行系统，用于解决掼蛋AI比赛中服务器参数设置与实际执行场数不匹配的问题。根据平台使用说明书v1006，服务器应该支持通过命令行参数指定游戏次数（如 `guandan_offline_v1006.exe 100`），但实际运行中发现服务器只执行3场就停止。本系统需要能够诊断问题根源，并在必要时通过自动重启机制确保完成指定数量的游戏场次。

## Glossary

- **Game Server**: 掼蛋离线服务器程序 (guandan_offline_v1006.exe)，负责管理游戏逻辑和客户端连接
- **Client**: Python客户端程序，连接到Game Server并执行游戏决策
- **Match**: 一场完整的掼蛋游戏对局
- **Batch Execution**: 批量执行多场游戏的过程
- **Score Tracker**: 战绩跟踪器，记录和累计多次运行的游戏结果
- **Auto Restart**: 自动重启机制，当服务器停止后自动重新启动并继续游戏

## Requirements

### Requirement 0

**User Story:** 作为用户，我希望系统能够诊断服务器为何只执行3场游戏，以便找到问题的根本原因。

#### Acceptance Criteria

1. WHEN 系统启动 THEN the Diagnostic System SHALL 检查服务器目录中是否存在配置文件
2. WHEN 发现配置文件 THEN the Diagnostic System SHALL 读取并显示配置文件内容
3. WHEN 服务器启动 THEN the Diagnostic System SHALL 捕获并记录服务器的输出信息
4. WHEN 服务器输出包含游戏次数信息 THEN the Diagnostic System SHALL 提取并显示实际设置的游戏次数
5. WHEN 实际游戏次数与命令行参数不匹配 THEN the Diagnostic System SHALL 报告差异并提示可能的原因

### Requirement 1

**User Story:** 作为用户，我希望能够指定要执行的游戏总场数，以便系统能够完整执行所有场次而不受服务器单次运行限制的影响。

#### Acceptance Criteria

1. WHEN 用户指定目标游戏场数 THEN the Batch Execution System SHALL 接受并存储该目标值
2. WHEN 目标场数大于服务器单次运行限制 THEN the Batch Execution System SHALL 自动计算需要的重启次数
3. WHEN 系统启动 THEN the Batch Execution System SHALL 显示目标场数和预计执行策略
4. WHERE 用户未指定场数 THEN the Batch Execution System SHALL 使用默认值100场
5. WHEN 目标场数为非正整数 THEN the Batch Execution System SHALL 拒绝该输入并提示错误

### Requirement 2

**User Story:** 作为用户，我希望系统能够自动检测服务器何时完成当前批次的游戏，以便及时重启并继续执行剩余场次。

#### Acceptance Criteria

1. WHEN Game Server 正在运行 THEN the Batch Execution System SHALL 持续监控服务器进程状态
2. WHEN Game Server 进程终止 THEN the Batch Execution System SHALL 在3秒内检测到该状态变化
3. WHEN 检测到服务器终止且剩余场数大于零 THEN the Batch Execution System SHALL 自动启动新的服务器实例
4. WHEN 检测到服务器终止且剩余场数为零 THEN the Batch Execution System SHALL 停止监控并生成最终报告
5. WHILE 服务器运行中 THEN the Batch Execution System SHALL 每5秒检查一次进程状态

### Requirement 3

**User Story:** 作为用户，我希望系统能够自动跟踪和累计多次运行的战绩，以便了解整体的胜负情况。

#### Acceptance Criteria

1. WHEN 每场游戏结束 THEN the Score Tracker SHALL 记录该场游戏的结果
2. WHEN 服务器重启 THEN the Score Tracker SHALL 保留之前的战绩数据
3. WHEN 所有游戏完成 THEN the Score Tracker SHALL 生成包含总胜场数、总负场数和胜率的报告
4. WHEN 系统异常终止 THEN the Score Tracker SHALL 将当前战绩持久化到文件
5. WHEN 系统重新启动 THEN the Score Tracker SHALL 从文件中恢复之前的战绩数据

### Requirement 4

**User Story:** 作为用户，我希望系统能够在每次重启时正确管理客户端连接，以便避免连接冲突和资源泄漏。

#### Acceptance Criteria

1. WHEN 准备重启服务器 THEN the Batch Execution System SHALL 先终止所有现有的Client进程
2. WHEN 所有Client进程终止后 THEN the Batch Execution System SHALL 等待3秒以确保资源释放
3. WHEN 启动新的服务器实例后 THEN the Batch Execution System SHALL 等待15秒以确保服务器就绪
4. WHEN 服务器就绪后 THEN the Batch Execution System SHALL 按顺序启动所有Client进程
5. WHEN 启动每个Client后 THEN the Batch Execution System SHALL 等待3秒再启动下一个Client

### Requirement 5

**User Story:** 作为用户，我希望能够实时查看游戏执行进度，以便了解当前状态和预计完成时间。

#### Acceptance Criteria

1. WHEN 系统运行中 THEN the Batch Execution System SHALL 在控制台显示当前已完成场数和剩余场数
2. WHEN 每批次游戏完成 THEN the Batch Execution System SHALL 更新并显示累计战绩
3. WHEN 系统重启服务器 THEN the Batch Execution System SHALL 显示重启次数和原因
4. WHEN 显示进度信息 THEN the Batch Execution System SHALL 包含时间戳
5. WHILE 游戏执行中 THEN the Batch Execution System SHALL 每完成一场游戏更新一次进度显示

### Requirement 6

**User Story:** 作为用户，我希望系统能够处理异常情况，以便在出现错误时不会丢失数据或进入不可恢复状态。

#### Acceptance Criteria

1. WHEN 服务器启动失败 THEN the Batch Execution System SHALL 重试最多3次
2. WHEN 重试3次后仍失败 THEN the Batch Execution System SHALL 记录错误并暂停执行
3. WHEN Client启动失败 THEN the Batch Execution System SHALL 记录错误并继续尝试启动其他Client
4. WHEN 检测到异常终止信号 THEN the Batch Execution System SHALL 保存当前状态并优雅退出
5. IF 系统崩溃 THEN the Score Tracker SHALL 确保战绩数据已持久化到磁盘

### Requirement 7

**User Story:** 作为用户，我希望系统能够生成详细的执行日志，以便在出现问题时进行诊断和分析。

#### Acceptance Criteria

1. WHEN 系统执行任何操作 THEN the Batch Execution System SHALL 将操作记录到日志文件
2. WHEN 记录日志 THEN the Batch Execution System SHALL 包含时间戳、操作类型和详细信息
3. WHEN 发生错误 THEN the Batch Execution System SHALL 记录完整的错误堆栈信息
4. WHEN 所有游戏完成 THEN the Batch Execution System SHALL 生成包含执行摘要的日志报告
5. WHILE 系统运行 THEN the Batch Execution System SHALL 将日志同时输出到控制台和文件
