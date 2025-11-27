# 配置文件使用指南

## 概述

批量游戏执行系统支持通过 JSON 配置文件进行详细配置。虽然命令行参数可以满足大多数使用场景，但配置文件提供了更多高级选项和更好的可维护性。

## 快速开始

### 1. 创建配置文件

```bash
# 复制示例配置文件
copy batch_executor\config.example.json batch_executor\config.json
```

### 2. 编辑配置文件

使用文本编辑器打开 `config.json`，根据需要修改配置项。

### 3. 使用配置文件

```bash
# 注意：当前版本主要通过命令行参数使用
# 配置文件为未来版本预留，提供配置参考
python -m batch_executor --server-path "D:\server\guandan.exe" --target-games 100
```

## 配置项详解

### 服务器配置 (server)

```json
{
  "server": {
    "path": "D:\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe",
    "wait_time": 15,
    "max_retries": 3
  }
}
```

#### path
- **类型**: 字符串
- **必需**: 是
- **说明**: 服务器可执行文件的完整路径
- **示例**: `"D:\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe"`
- **注意**: Windows 路径中的反斜杠需要转义（使用 `\\`）

#### wait_time
- **类型**: 整数
- **默认值**: 15
- **单位**: 秒
- **说明**: 启动服务器后等待就绪的时间
- **调整建议**: 
  - 如果客户端经常连接失败，增加此值（如 20 或 30）
  - 如果服务器启动很快，可以减少此值（如 10）

#### max_retries
- **类型**: 整数
- **默认值**: 3
- **说明**: 服务器启动失败时的最大重试次数
- **建议**: 保持默认值，除非网络或系统不稳定

### 客户端配置 (clients)

```json
{
  "clients": {
    "scripts": [
      "src\\communication\\Test1.py",
      "src\\communication\\Test2.py",
      "client3.py",
      "client4.py"
    ],
    "wait_between": 3,
    "continue_on_error": true
  }
}
```

#### scripts
- **类型**: 字符串数组
- **必需**: 否（可以为空）
- **说明**: 客户端脚本路径列表，按顺序启动
- **示例**: 
  ```json
  [
    "src\\communication\\Test1.py",
    "src\\communication\\Test2.py",
    "client3.py",
    "client4.py"
  ]
  ```
- **注意**: 
  - 路径相对于项目根目录
  - 确保所有脚本文件存在且可执行

#### wait_between
- **类型**: 整数
- **默认值**: 3
- **单位**: 秒
- **说明**: 启动每个客户端之间的等待时间
- **建议**: 保持默认值，避免客户端同时连接导致冲突

#### continue_on_error
- **类型**: 布尔值
- **默认值**: true
- **说明**: 如果某个客户端启动失败，是否继续启动其他客户端
- **建议**: 
  - 设为 `true`：即使部分客户端失败，游戏仍可能继续
  - 设为 `false`：任何客户端失败都会停止整个流程

### 执行配置 (execution)

```json
{
  "execution": {
    "target_games": 100,
    "games_per_batch": 3,
    "diagnose_first": true
  }
}
```

#### target_games
- **类型**: 整数
- **默认值**: 100
- **说明**: 目标游戏场数
- **示例**: `100`, `200`, `1000`
- **注意**: 必须是正整数

#### games_per_batch
- **类型**: 整数
- **默认值**: 3
- **说明**: 服务器单次运行的游戏场数
- **注意**: 
  - 此值通常由服务器限制决定
  - 如果服务器实际执行场数不同，系统会自动调整

#### diagnose_first
- **类型**: 布尔值
- **默认值**: true
- **说明**: 执行前是否先运行诊断
- **建议**: 
  - 首次使用时设为 `true`
  - 确认服务器正常后可设为 `false` 以节省时间

### 监控配置 (monitoring)

```json
{
  "monitoring": {
    "check_interval": 5,
    "process_names": {
      "server": "guandan_offline_v1006.exe",
      "client": "python.exe"
    }
  }
}
```

#### check_interval
- **类型**: 整数
- **默认值**: 5
- **单位**: 秒
- **说明**: 检查服务器进程状态的间隔时间
- **性能影响**: 
  - 值越小，响应越快，但 CPU 占用越高
  - 值越大，响应越慢，但 CPU 占用越低
- **建议**: 保持默认值 5 秒

#### process_names
- **类型**: 对象
- **说明**: 要监控的进程名称
- **server**: 服务器进程名称
- **client**: 客户端进程名称
- **注意**: 根据实际使用的服务器和客户端修改

### 文件路径配置 (files)

```json
{
  "files": {
    "state_file": "execution_state.json",
    "score_file": "game_scores.json",
    "log_dir": "logs"
  }
}
```

#### state_file
- **类型**: 字符串
- **默认值**: `"execution_state.json"`
- **说明**: 执行状态保存文件路径
- **用途**: 用于崩溃恢复和状态查询

#### score_file
- **类型**: 字符串
- **默认值**: `"game_scores.json"`
- **说明**: 战绩保存文件路径
- **用途**: 持久化游戏战绩数据

#### log_dir
- **类型**: 字符串
- **默认值**: `"logs"`
- **说明**: 日志文件目录
- **注意**: 目录会自动创建

### 日志配置 (logging)

```json
{
  "logging": {
    "level": "INFO",
    "console": true,
    "file": true,
    "max_file_size": 10485760,
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

#### level
- **类型**: 字符串
- **默认值**: `"INFO"`
- **可选值**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **说明**: 日志级别
- **级别说明**:
  - `DEBUG`: 详细的调试信息
  - `INFO`: 一般信息
  - `WARNING`: 警告信息
  - `ERROR`: 错误信息
  - `CRITICAL`: 严重错误
- **建议**: 
  - 正常使用：`INFO`
  - 调试问题：`DEBUG`
  - 生产环境：`WARNING`

#### console
- **类型**: 布尔值
- **默认值**: true
- **说明**: 是否输出到控制台

#### file
- **类型**: 布尔值
- **默认值**: true
- **说明**: 是否输出到文件

#### max_file_size
- **类型**: 整数
- **默认值**: 10485760 (10MB)
- **单位**: 字节
- **说明**: 单个日志文件最大大小
- **注意**: 超过此大小会自动轮转

#### backup_count
- **类型**: 整数
- **默认值**: 5
- **说明**: 保留的日志文件备份数量

#### format
- **类型**: 字符串
- **默认值**: `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
- **说明**: 日志格式
- **格式说明**:
  - `%(asctime)s`: 时间戳
  - `%(name)s`: 日志记录器名称
  - `%(levelname)s`: 日志级别
  - `%(message)s`: 日志消息

### 诊断配置 (diagnostic)

```json
{
  "diagnostic": {
    "config_file_patterns": [
      "*.ini",
      "*.json",
      "*.txt",
      "*.cfg",
      "config*",
      "settings*"
    ],
    "output_capture_timeout": 30,
    "game_count_patterns": [
      "Game count:\\s*(\\d+)",
      "游戏次数:\\s*(\\d+)",
      "场数:\\s*(\\d+)",
      "games?:\\s*(\\d+)"
    ]
  }
}
```

#### config_file_patterns
- **类型**: 字符串数组
- **说明**: 要检查的配置文件模式
- **用途**: 诊断时扫描服务器目录中的配置文件

#### output_capture_timeout
- **类型**: 整数
- **默认值**: 30
- **单位**: 秒
- **说明**: 捕获服务器输出的超时时间

#### game_count_patterns
- **类型**: 字符串数组
- **说明**: 从服务器输出中提取游戏次数的正则表达式模式
- **注意**: 如果服务器输出格式不同，可以添加新的模式

### 战绩跟踪配置 (tracker)

```json
{
  "tracker": {
    "auto_save": true,
    "save_format": "json",
    "backup_on_save": false
  }
}
```

#### auto_save
- **类型**: 布尔值
- **默认值**: true
- **说明**: 是否在每次更新后自动保存战绩
- **建议**: 保持 `true` 以防数据丢失

#### save_format
- **类型**: 字符串
- **默认值**: `"json"`
- **可选值**: `json`（目前仅支持 JSON）
- **说明**: 战绩保存格式

#### backup_on_save
- **类型**: 布尔值
- **默认值**: false
- **说明**: 保存时是否创建备份文件
- **注意**: 启用后会创建 `.bak` 备份文件

### 高级配置 (advanced)

```json
{
  "advanced": {
    "cleanup_on_exit": true,
    "force_kill_timeout": 5,
    "state_save_interval": 60,
    "enable_signal_handlers": true
  }
}
```

#### cleanup_on_exit
- **类型**: 布尔值
- **默认值**: true
- **说明**: 退出时是否清理所有进程
- **警告**: 设为 `false` 可能导致进程残留

#### force_kill_timeout
- **类型**: 整数
- **默认值**: 5
- **单位**: 秒
- **说明**: 强制终止进程前的等待时间

#### state_save_interval
- **类型**: 整数
- **默认值**: 60
- **单位**: 秒
- **说明**: 自动保存状态的间隔时间
- **注意**: 0 表示仅在重启时保存

#### enable_signal_handlers
- **类型**: 布尔值
- **默认值**: true
- **说明**: 是否启用信号处理器（Ctrl+C 优雅退出）
- **建议**: 保持 `true`

### 用户界面配置 (ui)

```json
{
  "ui": {
    "show_progress": true,
    "progress_update_interval": 10,
    "show_banner": true,
    "color_output": false
  }
}
```

#### show_progress
- **类型**: 布尔值
- **默认值**: true
- **说明**: 是否显示进度信息

#### progress_update_interval
- **类型**: 整数
- **默认值**: 10
- **单位**: 秒
- **说明**: 更新进度显示的间隔时间

#### show_banner
- **类型**: 布尔值
- **默认值**: true
- **说明**: 是否显示启动横幅

#### color_output
- **类型**: 布尔值
- **默认值**: false
- **说明**: 是否使用彩色输出
- **注意**: 需要终端支持 ANSI 颜色代码

### 性能配置 (performance)

```json
{
  "performance": {
    "max_concurrent_clients": 4,
    "memory_limit_mb": 1024,
    "cpu_affinity": []
  }
}
```

#### max_concurrent_clients
- **类型**: 整数
- **默认值**: 4
- **说明**: 最大并发客户端数量
- **注意**: 根据游戏规则，通常为 4

#### memory_limit_mb
- **类型**: 整数
- **默认值**: 1024
- **单位**: MB
- **说明**: 内存使用限制
- **注意**: 0 表示无限制

#### cpu_affinity
- **类型**: 整数数组
- **默认值**: []
- **说明**: CPU 亲和性设置
- **示例**: `[0, 1]` 表示仅使用 CPU 0 和 1
- **注意**: 空数组表示使用所有 CPU

### 测试配置 (testing)

```json
{
  "testing": {
    "mock_mode": false,
    "test_game_duration": 60,
    "inject_errors": false
  }
}
```

#### mock_mode
- **类型**: 布尔值
- **默认值**: false
- **说明**: 是否启用模拟模式
- **用途**: 用于测试，不实际启动进程

#### test_game_duration
- **类型**: 整数
- **默认值**: 60
- **单位**: 秒
- **说明**: 模拟模式下每场游戏的持续时间

#### inject_errors
- **类型**: 布尔值
- **默认值**: false
- **说明**: 是否注入错误
- **用途**: 用于测试错误处理逻辑

## 配置文件示例

### 示例1: 基本配置

```json
{
  "server": {
    "path": "D:\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe",
    "wait_time": 15
  },
  "clients": {
    "scripts": [
      "src\\communication\\Test1.py",
      "src\\communication\\Test2.py",
      "client3.py",
      "client4.py"
    ]
  },
  "execution": {
    "target_games": 100
  }
}
```

### 示例2: 调试配置

```json
{
  "server": {
    "path": "D:\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe",
    "wait_time": 20
  },
  "execution": {
    "target_games": 10,
    "diagnose_first": true
  },
  "logging": {
    "level": "DEBUG",
    "console": true,
    "file": true
  }
}
```

### 示例3: 生产配置

```json
{
  "server": {
    "path": "D:\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe",
    "wait_time": 15,
    "max_retries": 5
  },
  "clients": {
    "scripts": [
      "src\\communication\\Test1.py",
      "src\\communication\\Test2.py",
      "client3.py",
      "client4.py"
    ],
    "continue_on_error": true
  },
  "execution": {
    "target_games": 1000,
    "diagnose_first": false
  },
  "logging": {
    "level": "WARNING",
    "console": false,
    "file": true
  }
}
```

## 配置优先级

当同时使用配置文件和命令行参数时，优先级如下：

1. **命令行参数**（最高优先级）
2. **配置文件**
3. **默认值**（最低优先级）

示例：
```bash
# 配置文件中 target_games = 100
# 命令行参数 --target-games 200
# 实际使用: 200（命令行参数优先）
python -m batch_executor --server-path server.exe --target-games 200
```

## 配置验证

系统启动时会自动验证配置：

- 检查必需字段是否存在
- 验证数据类型是否正确
- 验证文件路径是否存在
- 验证数值范围是否合理

如果配置无效，系统会显示错误信息并退出。

## 最佳实践

1. **备份配置文件**: 修改前先备份
   ```bash
   copy config.json config.json.bak
   ```

2. **使用注释**: JSON 不支持注释，但可以使用 `_comment` 字段
   ```json
   {
     "_comment": "这是一个注释",
     "setting": "value"
   }
   ```

3. **分环境配置**: 为不同环境创建不同配置文件
   ```
   config.dev.json    # 开发环境
   config.test.json   # 测试环境
   config.prod.json   # 生产环境
   ```

4. **版本控制**: 将 `config.example.json` 加入版本控制，但不要提交实际的 `config.json`

5. **定期检查**: 定期检查配置是否需要更新

## 故障排除

### 配置文件无法加载

**错误**: `无法加载配置文件`

**解决方案**:
1. 检查文件是否存在
2. 检查 JSON 格式是否正确（使用 JSON 验证工具）
3. 检查文件编码（应为 UTF-8）

### 配置项无效

**错误**: `配置项 xxx 无效`

**解决方案**:
1. 参考本文档检查配置项名称和类型
2. 检查拼写错误
3. 使用 `config.example.json` 作为参考

### 路径错误

**错误**: `文件不存在: xxx`

**解决方案**:
1. 使用绝对路径
2. Windows 路径使用双反斜杠 `\\`
3. 检查文件是否确实存在

## 相关文档

- [README.md](README.md) - 系统使用文档
- [QUICK_START.md](QUICK_START.md) - 快速开始指南
- [设计文档](../.kiro/specs/batch-game-execution/design.md) - 系统设计文档

## 技术支持

如有配置相关问题，请查看日志文件或联系技术支持。
