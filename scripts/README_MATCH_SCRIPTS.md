# 比赛脚本使用说明

## 脚本列表

### 1. `start_match.ps1` - 推荐使用（简洁版）
**功能**: 启动client1、2 vs client3、4的比赛

**用法**:
```powershell
.\scripts\start_match.ps1
```

**特点**:
- 简洁清晰
- 自动导航到项目目录
- 自动检查依赖和路径
- 自动启动服务器和4个客户端
- 实时监控进程状态

---

### 2. `start_match_client12_vs_client34.ps1` - 完整版
**功能**: 功能更完整的比赛启动脚本

**用法**:
```powershell
.\scripts\start_match_client12_vs_client34.ps1
```

**特点**:
- 包含窗口激活功能
- 更详细的日志输出
- 更完善的错误处理

---

## 比赛配置

### 队伍分组
- **队伍1** (知识库增强 AI):
  - 座位0: client1 (Test1.py)
  - 座位2: client2 (Test2.py)

- **队伍2** (硬编码规则 AI):
  - 座位1: client3 (client3.py)
  - 座位3: client4 (client4.py)

### 启动顺序
1. client1 (座位0)
2. client3 (座位1)
3. client2 (座位2)
4. client4 (座位3)

---

## 使用步骤

### 1. 准备工作
确保以下路径正确：
- 服务器目录: `D:\guandan_offline_v1006\windows`
- 项目目录: `D:\guandanscore\YiFeiAI-GD`

### 2. 运行脚本
```powershell
# 进入项目目录
cd D:\guandanscore\YiFeiAI-GD

# 运行脚本
.\scripts\start_match.ps1
```

### 3. 观察比赛
- 服务器窗口会显示游戏状态
- 4个客户端窗口会显示各自的决策过程
- 使用 Alt+Tab 切换窗口查看

### 4. 停止比赛
- 按 Ctrl+C 退出监控脚本（进程继续运行）
- 或直接关闭所有PowerShell窗口
- 或使用任务管理器结束进程

---

## 常见问题

### Q: 看不到窗口？
A: 
1. 检查任务栏是否有最小化的窗口
2. 使用 Alt+Tab 切换窗口
3. 使用任务管理器根据PID查找进程

### Q: 客户端连接失败？
A:
1. 检查服务器是否正常启动
2. 检查端口23456是否被占用
3. 查看客户端窗口的错误信息
4. 重启脚本

### Q: 如何修改配置？
A: 编辑脚本文件，修改以下变量：
```powershell
$ServerDir = "服务器目录路径"
$ServerWaitTime = 15  # 服务器等待时间
$ClientStartInterval = 3  # 客户端启动间隔
```

---

## 输出文件

- `match_process_info.json`: 保存进程信息（PID等）

---

## 注意事项

- ?? 确保服务器目录路径正确
- ?? 确保所有客户端文件存在
- ?? 首次运行会安装依赖（ws4py, websockets, pyyaml）
- ? 脚本会自动关闭旧的服务器进程
- ? 脚本会自动导航到项目目录

