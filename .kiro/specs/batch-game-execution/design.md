# Design Document

## Overview

本设计文档描述了批量游戏执行系统的架构和实现方案。系统分为两个主要模块：

1. **诊断模块**：用于诊断服务器为何只执行3场游戏的根本原因
2. **自动执行模块**：在诊断无法解决问题时，通过自动重启机制确保完成指定场次

系统采用Python实现，使用Windows批处理脚本作为启动入口，通过进程监控和日志分析来实现自动化管理。

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    批量游戏执行系统                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐         ┌──────────────────────────┐  │
│  │  诊断模块     │────────>│  配置文件检测器           │  │
│  │              │         │  服务器输出捕获器         │  │
│  │              │         │  参数验证器               │  │
│  └──────────────┘         └──────────────────────────┘  │
│         │                                                │
│         │ 如果诊断失败                                    │
│         ▼                                                │
│  ┌──────────────┐         ┌──────────────────────────┐  │
│  │  自动执行模块 │────────>│  进程监控器               │  │
│  │              │         │  战绩跟踪器               │  │
│  │              │         │  重启管理器               │  │
│  └──────────────┘         └──────────────────────────┘  │
│         │                                                │
│         ▼                                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │              日志和报告系统                        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 模块职责

1. **诊断模块 (DiagnosticModule)**
   - 检查服务器目录中的配置文件
   - 捕获服务器启动输出
   - 分析参数不匹配的原因
   - 生成诊断报告

2. **自动执行模块 (AutoExecutionModule)**
   - 监控服务器进程状态
   - 管理客户端连接
   - 自动重启服务器和客户端
   - 累计多次运行的战绩

3. **战绩跟踪器 (ScoreTracker)**
   - 记录每场游戏结果
   - 持久化战绩数据
   - 生成统计报告

4. **日志系统 (LoggingSystem)**
   - 记录所有操作
   - 输出到控制台和文件
   - 生成执行摘要

## Components and Interfaces

### 1. 诊断模块

```python
class DiagnosticModule:
    """诊断服务器参数问题的模块"""
    
    def check_config_files(self, server_dir: str) -> List[str]:
        """检查服务器目录中的配置文件"""
        pass
    
    def capture_server_output(self, process) -> str:
        """捕获服务器启动输出"""
        pass
    
    def extract_game_count(self, output: str) -> Optional[int]:
        """从服务器输出中提取游戏次数"""
        pass
    
    def diagnose(self, expected: int, actual: int) -> DiagnosticReport:
        """诊断参数不匹配的原因"""
        pass
```

### 2. 进程监控器

```python
class ProcessMonitor:
    """监控服务器和客户端进程"""
    
    def is_running(self, process_name: str) -> bool:
        """检查进程是否运行"""
        pass
    
    def wait_for_termination(self, process_name: str, timeout: int) -> bool:
        """等待进程终止"""
        pass
    
    def kill_all(self, process_names: List[str]) -> None:
        """终止所有指定进程"""
        pass
```

### 3. 战绩跟踪器

```python
class ScoreTracker:
    """跟踪和累计游戏战绩"""
    
    def __init__(self, save_file: str):
        self.save_file = save_file
        self.scores = {"team_a": 0, "team_b": 0, "total_games": 0}
    
    def record_game(self, winner: str) -> None:
        """记录一场游戏结果"""
        pass
    
    def save(self) -> None:
        """持久化战绩到文件"""
        pass
    
    def load(self) -> None:
        """从文件恢复战绩"""
        pass
    
    def generate_report(self) -> str:
        """生成战绩报告"""
        pass
```

### 4. 重启管理器

```python
class RestartManager:
    """管理服务器和客户端的重启"""
    
    def restart_server(self, game_count: int) -> subprocess.Popen:
        """重启服务器"""
        pass
    
    def restart_clients(self, client_scripts: List[str]) -> List[subprocess.Popen]:
        """重启所有客户端"""
        pass
    
    def cleanup(self) -> None:
        """清理所有进程"""
        pass
```

## Data Models

### DiagnosticReport

```python
@dataclass
class DiagnosticReport:
    """诊断报告"""
    config_files_found: List[str]
    server_output: str
    expected_count: int
    actual_count: Optional[int]
    mismatch_detected: bool
    possible_causes: List[str]
    recommendations: List[str]
```

### GameScore

```python
@dataclass
class GameScore:
    """游戏战绩"""
    team_a_wins: int
    team_b_wins: int
    total_games: int
    timestamp: datetime
    
    def win_rate(self, team: str) -> float:
        """计算胜率"""
        if self.total_games == 0:
            return 0.0
        wins = self.team_a_wins if team == "team_a" else self.team_b_wins
        return wins / self.total_games
```

### ExecutionState

```python
@dataclass
class ExecutionState:
    """执行状态"""
    target_games: int
    completed_games: int
    restart_count: int
    current_batch: int
    start_time: datetime
    last_update: datetime
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 配置文件检测完整性
*For any* 服务器目录，如果目录中存在配置文件（config.ini, config.json, settings.txt等），系统应该能够检测到所有这些文件
**Validates: Requirements 0.1**

### Property 2: 输出捕获完整性
*For any* 服务器进程输出，系统应该能够捕获并记录所有输出内容
**Validates: Requirements 0.3**

### Property 3: 游戏次数提取准确性
*For any* 包含游戏次数信息的服务器输出，系统应该能够正确提取数值
**Validates: Requirements 0.4**

### Property 4: 参数不匹配检测
*For any* 命令行参数和实际游戏次数的组合，当两者不相等时，系统应该能够检测到差异
**Validates: Requirements 0.5**

### Property 5: 目标场数验证
*For any* 正整数输入，系统应该接受并正确存储该值作为目标场数
**Validates: Requirements 1.1**

### Property 6: 重启次数计算
*For any* 目标场数和单次限制，重启次数应该等于 ceil(目标场数 / 单次限制) - 1
**Validates: Requirements 1.2**

### Property 7: 无效输入拒绝
*For any* 非正整数输入（负数、零、非数字），系统应该拒绝该输入
**Validates: Requirements 1.5**

### Property 8: 进程状态监控
*For any* 正在运行的服务器进程，监控器应该能够检测到其运行状态
**Validates: Requirements 2.1**

### Property 9: 重启决策
*For any* 剩余场数大于零的情况，当服务器终止时，系统应该决定重启
**Validates: Requirements 2.3**

### Property 10: 游戏结果记录
*For any* 游戏结果（team_a或team_b获胜），战绩跟踪器应该正确增加对应队伍的胜场数
**Validates: Requirements 3.1**

### Property 11: 战绩持久化
*For any* 战绩数据，保存后重新加载应该得到相同的数据（round trip）
**Validates: Requirements 3.2, 3.5**

### Property 12: 战绩报告计算
*For any* 战绩数据，生成的报告应该包含正确的总胜场数、总负场数和胜率
**Validates: Requirements 3.3**

### Property 13: 进程终止完整性
*For any* 客户端进程列表，终止操作后所有进程都应该不再运行
**Validates: Requirements 4.1**

### Property 14: 客户端启动顺序
*For any* 客户端脚本列表，启动顺序应该与列表顺序一致
**Validates: Requirements 4.4**

### Property 15: 错误处理继续性
*For any* 客户端启动失败的情况，系统应该继续尝试启动其他客户端
**Validates: Requirements 6.3**

### Property 16: 状态保存完整性
*For any* 执行状态，在接收到终止信号时，状态应该被保存到文件
**Validates: Requirements 6.4**

### Property 17: 日志记录完整性
*For any* 系统操作，该操作应该被记录到日志文件中
**Validates: Requirements 7.1**

### Property 18: 日志格式正确性
*For any* 日志条目，应该包含时间戳、操作类型和详细信息
**Validates: Requirements 7.2**

### Property 19: 错误日志堆栈信息
*For any* 错误，日志应该包含完整的堆栈跟踪信息
**Validates: Requirements 7.3**

### Property 20: 日志双输出
*For any* 日志条目，应该同时出现在控制台和日志文件中
**Validates: Requirements 7.5**

## Error Handling

### 错误类型

1. **服务器启动失败**
   - 端口被占用
   - 可执行文件不存在
   - 权限不足
   - 处理：重试最多3次，记录错误，提示用户

2. **客户端连接失败**
   - 服务器未就绪
   - 网络问题
   - 脚本错误
   - 处理：记录错误，继续启动其他客户端

3. **进程监控失败**
   - 权限不足
   - 系统资源不足
   - 处理：记录错误，尝试降级监控

4. **文件操作失败**
   - 磁盘空间不足
   - 权限不足
   - 文件损坏
   - 处理：记录错误，尝试备用位置

### 异常处理策略

```python
try:
    # 执行操作
    pass
except SpecificException as e:
    logger.error(f"操作失败: {e}", exc_info=True)
    # 尝试恢复或降级
except Exception as e:
    logger.critical(f"未预期的错误: {e}", exc_info=True)
    # 保存状态并退出
```

## Testing Strategy

### 单元测试

使用 `pytest` 框架进行单元测试：

1. **诊断模块测试**
   - 测试配置文件检测
   - 测试输出解析
   - 测试参数验证

2. **进程监控测试**
   - 使用模拟进程测试监控逻辑
   - 测试进程终止检测

3. **战绩跟踪测试**
   - 测试战绩记录
   - 测试文件保存和加载
   - 测试报告生成

4. **重启管理测试**
   - 使用模拟进程测试重启逻辑
   - 测试清理操作

### 属性测试

使用 `hypothesis` 库进行属性测试：

1. **输入验证属性**
   - 生成随机有效/无效输入
   - 验证接受/拒绝逻辑

2. **计算属性**
   - 生成随机场数和限制
   - 验证重启次数计算

3. **数据持久化属性**
   - 生成随机战绩数据
   - 验证保存/加载round trip

4. **日志属性**
   - 生成随机操作
   - 验证日志记录完整性

### 集成测试

1. **端到端测试**
   - 使用模拟服务器测试完整流程
   - 验证多次重启场景

2. **错误恢复测试**
   - 模拟各种失败场景
   - 验证系统恢复能力

### 测试配置

```python
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short

# hypothesis配置
from hypothesis import settings
settings.register_profile("default", max_examples=100)
settings.load_profile("default")
```

## Implementation Notes

### 技术选择

1. **Python 3.8+**：主要实现语言
2. **psutil**：进程监控
3. **subprocess**：进程管理
4. **json**：数据序列化
5. **logging**：日志系统
6. **hypothesis**：属性测试

### 关键实现细节

1. **服务器输出捕获**
   - 使用 `subprocess.Popen` 启动服务器
   - 通过 `stdout=subprocess.PIPE` 捕获输出
   - 使用单独线程读取输出避免阻塞

2. **进程监控**
   - 使用 `psutil.process_iter()` 遍历进程
   - 定期检查进程状态（每5秒）
   - 使用进程名称和PID双重验证

3. **战绩持久化**
   - 使用JSON格式存储
   - 每次更新后立即保存
   - 使用临时文件+原子重命名确保数据安全

4. **日志系统**
   - 使用Python标准logging模块
   - 配置多个handler（控制台+文件）
   - 使用RotatingFileHandler避免日志文件过大

### 性能考虑

1. **进程监控频率**：每5秒检查一次，平衡响应速度和CPU占用
2. **日志缓冲**：使用缓冲写入减少磁盘IO
3. **内存管理**：及时清理已终止进程的引用

### 安全考虑

1. **路径验证**：验证所有文件路径，防止路径遍历攻击
2. **进程隔离**：使用独立进程运行服务器和客户端
3. **错误信息**：避免在日志中泄露敏感信息
