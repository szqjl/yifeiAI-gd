# V7系统问题修复报告

## 问题概述

在V7系统测试中发现两个关键问题：
1. **服务器端KeyError: 'actIndex'错误** - V7客户端消息格式不匹配
2. **客户端启动顺序错误** - 连接顺序不符合预期

## 问题1: 服务器端KeyError: 'actIndex'错误

### 错误信息
```
[服务器] Traceback (most recent call last):
[服务器] File "site-packages\tornado\websocket.py", line 649, in _run_callback
[服务器] File "server.py", line 96, in on_message
[服务器] KeyError: 'actIndex'
```

### 根本原因
V7客户端发送的消息使用了错误的字段名：
- **V7客户端使用**: `actionIndex`
- **服务器期望**: `actIndex`

### 对比分析
检查其他客户端的消息格式：
```python
# lalala客户端 (正确)
self.send(json.dumps({"actIndex": act_index}))

# V7客户端 (错误)
"data": {"actionIndex": action_index}
```

### 修复方案
修改V7客户端的消息发送格式：

**修复前 (yf1_v7.py, yf2_v7.py):**
```python
message = {
    "type": "action",
    "data": {
        "actionIndex": action_index  # 错误字段名
    }
}
```

**修复后:**
```python
message = {
    "type": "action",
    "data": {
        "actIndex": action_index  # 正确字段名
    }
}
```

## 问题2: 客户端启动顺序错误

### 错误现象
实际连接顺序：
```
[服务器] [I 260120 12:14:00] 101 GET /game/yf1_v7 (127.0.0.1) 0.99ms
[服务器] [I 260120 12:14:03] 101 GET /game/client3 (127.0.0.1) 0.00ms
[服务器] [I 260120 12:14:22] 101 GET /game/client4 (127.0.0.1) 0.00ms  # 错误：client4在yf2_v7之前
[服务器] [I 260120 12:14:26] 101 GET /game/yf2_v7 (127.0.0.1) 0.00ms
```

期望连接顺序：
```
yf1_v7 -> client3 -> yf2_v7 -> client4
```

### 根本原因
`restart_manager.py`中的等待逻辑使用了旧的客户端名称：
- 代码中检查的是 `yf1_m1`, `yf2_m1`
- 实际使用的是 `yf1_v7`, `yf2_v7`

### 客户端延迟分析
```python
# V7客户端内部延迟
yf1_v7: DELAY_BEFORE_CONNECT = 3  # 3秒
yf2_v7: DELAY_BEFORE_CONNECT = 9  # 9秒

# lalala客户端延迟（固定）
client3: 10秒
client4: 20秒
```

### 修复方案
更新`restart_manager.py`中的等待逻辑：

**修复前:**
```python
if 'yf1_m1' in current_script:
    wait_time = 6  # 基于旧的5秒延迟
elif 'yf2_m1' in current_script:
    wait_time = 16  # 基于旧的15秒延迟
```

**修复后:**
```python
if 'yf1_v7' in current_script or 'yf1_m1' in current_script:
    wait_time = 4  # 基于新的3秒延迟 + 1秒缓冲
elif 'yf2_v7' in current_script or 'yf2_m1' in current_script:
    wait_time = 10  # 基于新的9秒延迟 + 1秒缓冲
```

## 修复后的时序分析

### 启动时序
```
T+0s:  启动yf1_v7
T+4s:  启动client3 (等待yf1_v7的3秒延迟+1秒缓冲)
T+15s: 启动yf2_v7 (等待client3的10秒延迟+1秒缓冲)
T+25s: 启动client4 (等待yf2_v7的9秒延迟+1秒缓冲)
```

### 连接时序
```
T+3s:  yf1_v7连接到服务器
T+14s: client3连接到服务器
T+24s: yf2_v7连接到服务器
T+45s: client4连接到服务器
```

### 最终连接顺序
```
✓ yf1_v7 -> client3 -> yf2_v7 -> client4
```

## 修复文件清单

### 1. src/communication/yf1_v7.py
- 修复消息字段名：`actionIndex` -> `actIndex`

### 2. src/communication/yf2_v7.py
- 修复消息字段名：`actionIndex` -> `actIndex`

### 3. batch_executor/restart_manager.py
- 更新客户端名称检测逻辑
- 调整等待时间以匹配V7客户端的实际延迟

## 验证测试

### 消息格式测试
```python
# 修复后的V7消息格式
{
  "type": "action",
  "data": {
    "actIndex": 2  # 正确字段名
  }
}
```

### 启动顺序测试
运行V7 GUI后，服务器日志应显示：
```
[服务器] 101 GET /game/yf1_v7
[服务器] 101 GET /game/client3
[服务器] 101 GET /game/yf2_v7
[服务器] 101 GET /game/client4
```

## 使用说明

修复后的V7系统：
1. 不再出现`KeyError: 'actIndex'`错误
2. 客户端按正确顺序连接
3. 游戏可以正常进行

启动方式：
```bash
# 方式1：使用GUI
python scripts/v7/start_v7_gui.py

# 方式2：使用批处理
START_V7_GUI.bat
```

## 技术要点

1. **消息格式一致性**：确保所有客户端使用相同的字段名
2. **启动时序控制**：基于实际的客户端内部延迟调整等待时间
3. **向后兼容性**：同时支持新旧客户端名称检测
4. **错误处理**：保持原有的错误处理和重试机制

## 后续建议

1. **标准化消息格式**：建立统一的消息格式规范
2. **配置化延迟时间**：将客户端延迟时间配置化，便于调整
3. **自动化测试**：添加启动顺序和消息格式的自动化测试
4. **监控和日志**：增强连接状态监控和错误日志记录