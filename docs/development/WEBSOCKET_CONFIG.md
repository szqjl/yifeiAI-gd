# WebSocket 配置指南

## 概述

yf_v5 客户端现在支持通过配置文件管理 WebSocket 连接，包括自动重连、心跳保活和超时控制等功能。

## 配置文件

WebSocket 配置位于项目根目录的 `config.yaml` 文件中：

```yaml
# WebSocket连接配置
websocket:
  # 本地连接
  local_url: "ws://127.0.0.1:23456/game/{user_info}"
  # 局域网连接（需要时替换IP）
  network_url: "ws://[局域网IP]:23456/game/{user_info}"
  reconnect_interval: 5      # 重连间隔（秒）
  heartbeat_interval: 30      # 心跳间隔（秒）
  timeout: 10                 # 连接超时时间（秒）
```

## 功能特性

### 1. 配置化连接
- 从 `config.yaml` 读取 WebSocket 连接参数
- 支持本地和网络连接切换
- URL 模板支持 `{user_info}` 占位符

### 2. 自动重连
- 连接失败时自动重试
- 可配置重连间隔
- 支持无限重试或限制重试次数

### 3. 心跳保活
- 定期发送 ping 保持连接
- 可配置心跳间隔
- 自动检测连接断开

### 4. 超时控制
- 连接超时保护
- 可配置超时时间
- 避免长时间等待

## 使用方法

### 基本使用

```python
from communication.yf1_v5 import YF1_V5_Client

# 使用本地连接（默认）
client = YF1_V5_Client(player_id=0, use_local_websocket=True)

# 使用网络连接
client = YF1_V5_Client(player_id=0, use_local_websocket=False)

# 连接服务器
await client.connect()
```

### 高级配置

如果需要自定义配置，可以修改 `config.yaml`：

```yaml
websocket:
  local_url: "ws://127.0.0.1:23456/game/{user_info}"
  network_url: "ws://192.168.1.100:23456/game/{user_info}"
  reconnect_interval: 3      # 缩短重连间隔
  heartbeat_interval: 20     # 更频繁的心跳
  timeout: 5                 # 更短的超时时间
```

## WebSocket 管理器 API

### WebSocketManager 类

```python
from communication.websocket_manager import WebSocketManager

# 创建管理器
manager = WebSocketManager(user_info="yf1_v5", use_local=True)

# 连接服务器
connected = await manager.connect(max_retries=-1)  # -1 表示无限重试

# 发送消息
await manager.send_json({"actIndex": 0})

# 接收消息
data = await manager.receive_json()

# 设置消息处理回调
async def handle_message(data: dict):
    print(f"Received: {data}")

manager.set_message_handler(handle_message)
await manager.handle_messages()

# 关闭连接
await manager.close()
```

## 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `local_url` | 本地连接URL模板 | `ws://127.0.0.1:23456/game/{user_info}` |
| `network_url` | 网络连接URL模板 | `ws://[局域网IP]:23456/game/{user_info}` |
| `reconnect_interval` | 重连间隔（秒） | 5 |
| `heartbeat_interval` | 心跳间隔（秒） | 30 |
| `timeout` | 连接超时时间（秒） | 10 |

## 日志记录

WebSocket 管理器会记录详细的连接日志：

- 连接状态
- 重连尝试
- 心跳发送
- 错误信息

日志文件位置：`logs/yf1_v5_YYYYMMDD_HHMMSS.log` 和 `logs/yf2_v5_YYYYMMDD_HHMMSS.log`

## 故障排查

### 连接失败

1. 检查服务器是否运行
2. 验证 URL 配置是否正确
3. 检查防火墙设置
4. 查看日志文件获取详细错误信息

### 频繁断开连接

1. 增加 `heartbeat_interval` 值
2. 检查网络稳定性
3. 调整 `timeout` 值

### 重连失败

1. 检查 `reconnect_interval` 设置
2. 验证服务器是否可访问
3. 查看日志了解重连原因

## 更新记录

- **2025-01-XX**: 初始版本，支持配置化 WebSocket 连接
- 支持自动重连机制
- 支持心跳保活
- 支持超时控制

