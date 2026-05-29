# 寮鍙戣勮寖涓庤勫垯

## 🔴 核心规则（必须严格遵守）

### 1. 时间处理规则 ⚠️ 强制要求

**所有涉及当前时闂淬佸疄时时间的场景必须调用系统时间API：岀佹使用纭编码时间銆**

#### 规则说明
- 鉁 **必须使用**: `datetime.now()` 获取系统当前时间
- 鉂 **绂佹使用**: 纭编码的时间字符串、固定时间戳
- 鉁 **鍏佽镐娇用**: 固定的历史日期（濡"2025骞10鏈5鏃"这样的具体历史时间）

#### 正确示例

```python
from datetime import datetime, timedelta

# 鉁 获取当前时间
current_time = datetime.now()

# 鉁 获取当前时间鎴
timestamp = datetime.now().timestamp()

# 鉁 格式化当前时闂
formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 鉁 判断鏄否在静默鏃舵
def is_quiet_hours():
    now = datetime.now()  # 必须调用系统时间
    hour = now.hour
    return 0 <= hour < 6

# 鉁 计算涓嬫℃查时闂
def schedule_next_check(interval):
    next_time = datetime.now() + timedelta(seconds=interval)
    return next_time

# 鉁 记录日志时间
log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 鉁 文件命名时间鎴
filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
```

#### 閿欒示例

```python
# 鉂 閿欒：硬编码时间
current_time = "2025-01-01 12:00:00"

# 鉂 閿欒：使用固定时间戳
timestamp = 1704067200

# 鉂 閿欒：在代码涓鍐欐绘椂闂
if hour == 12:  # 搴旇ヤ粠系统时间获取

# 鉂 閿欒：使用固定的时间对象
fixed_time = datetime(2025, 1, 1, 12, 0, 0)  # 除非鏄历史日期
```

#### 适用场景

| 场景 | 必须使用系统时间 | 示例 |
|------|----------------|------|
| 日志时间鎴 | 鉁 鏄 | `datetime.now()` |
| 信息抓取时间 | 鉁 鏄 | `datetime.now()` |
| 静默鏃舵靛垽鏂 | 鉁 鏄 | `datetime.now().hour` |
| 定时任务调度 | 鉁 鏄 | `datetime.now() + timedelta(...)` |
| 数据记录时间 | 鉁 鏄 | `datetime.now()` |
| 文件命名时间鎴 | 鉁 鏄 | `datetime.now().strftime(...)` |
| 历史日期记录 | 鉂 鍚 | 鍙以使用固定日鏈 |

#### 时间处理工具函数

寤鸿在项鐩涓创建统一的时闂村勭悊工具函数：

```python
from datetime import datetime, timedelta
from typing import Optional

class TimeUtils:
    """时间处理工具绫"""
    
    @staticmethod
    def get_current_time() -> datetime:
        """获取当前系统时间"""
        return datetime.now()
    
    @staticmethod
    def get_current_timestamp() -> float:
        """获取当前时间鎴"""
        return datetime.now().timestamp()
    
    @staticmethod
    def format_time(dt: Optional[datetime] = None, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        """格式化时闂"""
        if dt is None:
            dt = datetime.now()  # 榛樿や娇用当前时闂
        return dt.strftime(fmt)
    
    @staticmethod
    def is_quiet_hours(current_time: Optional[datetime] = None) -> bool:
        """判断鏄否在静默鏃舵碉紙0:00-6:00："""
        if current_time is None:
            current_time = datetime.now()  # 必须调用系统时间
        hour = current_time.hour
        return 0 <= hour < 6
    
    @staticmethod
    def schedule_next_check(interval: int, current_time: Optional[datetime] = None) -> datetime:
        """计算涓嬫℃查时间（避开静默鏃舵碉級"""
        if current_time is None:
            current_time = datetime.now()  # 必须调用系统时间
        
        next_check = current_time + timedelta(seconds=interval)
        
        # 如果落在静默鏃舵碉紝延后到静默时段结鏉
        if TimeUtils.is_quiet_hours(next_check):
            next_check = next_check.replace(hour=6, minute=0, second=0)
        
        return next_check
```

### 2. JSON格式规则

- **严格遵循平台JSON格式要求**
- 所有消息必须符合平台规范
- 消息格式验证必须通过
- 绂佹㈤殢意修改JSON结构

### 3. 组队规则

- **绗1涓鍜岀3涓连接**的AI自动为涓闃
- **绗2涓鍜岀4涓连接**的AI自动为涓闃
- 必须正确识别队友并配鍚
- 组队关系在连接时纭定，不可更改

### 4. 响应时间规则

- 决策响应时间寤鸿 < 1绉
- 避免超时导致判负
- 优化算法纭保及时响搴

### 5. 信息监控规则

- 妫查间闅 鈮 6小时
- 每日 0:00-6:00 为静默时段，不进琛屾鏌
- 遵守网站使用鏉℃撅紝涓嶉犳垚服务器压鍔
- 使用系统时间判断静默鏃舵

## 📝 代码规范

### Python代码规范

- 遵循 PEP 8 Python代码规范
- 使用类型提示（Type Hints：
- 编写清晰的注释和文档瀛楃︿覆
- 函数和类要有清晰的命鍚

### 文档规范

- **文档尽量绠娲**：避免一娆℃х敓成过长文妗ｅ艰嚧超时
- **先列提纲再填鍏**：先创建文档框架和提纲并保存，再閫愭ュ～充内瀹
- **定期保存**：每3分钟保存涓次，避免长时间编杈戝艰嚧鍐呭逛涪澶
- **遵守时间规范**：文档中的时间信鎭应使用系统时间API：岀佹㈢‖编码时间

### 时间处理规范

#### 必须使用系统时间API

```python
# 鉁 正确
from datetime import datetime
current_time = datetime.now()

# 鉂 閿欒
current_time = "2025-01-01 12:00:00"
```

#### 时间处理工具函数

寤鸿使用统一的时闂村勭悊工具函数，避免在代码涓直接调用 `datetime.now()`，便于测试和维护銆

### 閿欒处理规范

- 所有可能失败的操作閮借佹湁异常处理
- 记录详细的错璇日志
- 提供有意义的閿欒信息

### 日志规范

- 使用统一的日志格寮
- 日志时间戳必须使用系统时闂
- 区分不同级别的日志（DEBUG/INFO/WARNING/ERROR：

## 🧪 测试规范

### 单元测试

- 所有核心功能都要有单元测试
- 测试时间相关功能时，鍙以使用mock时间
- 纭保测试的鍙閲嶅嶆

### 时间测试示例

```python
from unittest.mock import patch
from datetime import datetime

def test_is_quiet_hours():
    """测试静默鏃舵靛垽鏂"""
    # 测试凌晨3点（在静默时段）
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 1, 3, 0, 0)
        assert is_quiet_hours() == True
    
    # 测试上午10点（不在静默鏃舵碉級
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 1, 10, 0, 0)
        assert is_quiet_hours() == False
```

## ⚠️ 甯歌侀敊璇

### 时间处理閿欒

1. **纭编码时间**
   ```python
   # 鉂 閿欒
   if datetime.now().hour == 12:
       do_something()
   ```

2. **使用固定时间鎴**
   ```python
   # 鉂 閿欒
   timestamp = 1704067200
   ```

3. **蹇樿拌皟用系统时闂**
   ```python
   # 鉂 閿欒
   def get_time():
       return "2025-01-01 12:00:00"  # 搴旇ヨ繑回datetime.now()
   ```

## 鉁 妫查清鍗

开发时请确保：
- [ ] 所有时间相关代码都使用 `datetime.now()`
- [ ] 没有纭编码的时间字符串
- [ ] 没有使用固定的时间戳
- [ ] 时间处理函数都有适当的测璇
- [ ] 日志时间戳使用系统时闂
- [ ] 定时任务基于系统时间计算

## 📚 相关文档

- [README.md](../README.md) - 项目主文档（包含时间处理规则：
- [架构方案圿(掼蛋AI客户端架构方案.md) - 详细鎶本文档

---

**閲嶈佹彁閱**: 时间处理规则鏄项目的核蹇冭勫垯之一，所有开鍙戣呭繀须严格遵守！

