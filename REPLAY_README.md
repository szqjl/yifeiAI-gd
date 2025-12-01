# 游戏回放工具使用说明

## 文件说明

1. **REPLAY_GAME.ps1** - PowerShell脚本（推荐使用）
2. **REPLAY_GAME.bat** - 批处理脚本（调用PowerShell脚本）
3. **src/communication/replay_select.py** - Python选择脚本

## 使用方法

### 方法1：使用批处理脚本（最简单）

直接双击运行 `REPLAY_GAME.bat`

### 方法2：使用PowerShell脚本

```powershell
.\REPLAY_GAME.ps1
```

### 方法3：直接使用Python脚本

```powershell
# 设置环境变量
$env:PYTHONPATH="D:\guandanscore\YiFeiAI-GD\src"

# 基础回放
python src\communication\replay_select.py

# 交互式回放
python src\communication\replay_select.py --interactive
```

## 功能特点

### 基础回放模式
- 快速查看完整游戏回放
- 显示所有出牌步骤
- 自动分析规则使用情况

### 交互式回放模式（推荐）
- **上一步/下一步**：逐步查看游戏过程
- **自动播放**：自动按步骤回放
- **实时规则分析**：显示当前步骤的规则违反情况
- **控制键**：
  - `1` - 开始自动播放
  - `2` - 停止自动播放
  - `3` - 下一步
  - `4` - 上一步
  - `q` - 退出
  - 回车 - 默认下一步

## 游戏记录位置

游戏记录保存在：`game_records/` 目录下

文件格式：`YYYYMMDDHHMMSSffffff [player_name]-[opponent_name].json`

## 测试

运行测试脚本验证工具是否正常：

```powershell
.\test_replay.ps1
```

## 注意事项

1. 确保Python环境已正确安装
2. 确保所有依赖包已安装：`pip install -r requirements.txt`
3. 如果遇到编码问题，使用PowerShell脚本而不是批处理脚本
4. 游戏记录需要先运行游戏并保存后才能回放

## 故障排除

### 问题：找不到模块 'communication'
**解决**：确保设置了PYTHONPATH环境变量，或使用提供的脚本（已自动设置）

### 问题：未找到游戏记录
**解决**：先运行游戏以生成记录文件，记录会自动保存在 `game_records/` 目录

### 问题：PowerShell执行策略错误
**解决**：运行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

