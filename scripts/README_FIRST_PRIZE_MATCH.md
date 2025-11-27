# Test1、Test2 vs 一等奖代码比赛脚本

## 比赛配置

- **队伍1（知识库增强）**：
  - 座位0：client1 (Test1.py)
  - 座位2：client2 (Test2.py)

- **队伍2（一等奖代码）**：
  - 座位1：client3 (一等奖代码)
  - 座位3：client4 (一等奖代码)

## 使用方法

```powershell
.\scripts\start_match_test12_vs_firstprize34.ps1
```

## 文件位置

- **Test1.py**: `src\communication\Test1.py`
- **Test2.py**: `src\communication\Test2.py`
- **一等奖client3**: `src\communication\first_prize\client3.py`
- **一等奖client4**: `src\communication\first_prize\client4.py`

## 依赖文件

一等奖代码需要以下文件（已复制到 `src\communication\first_prize\`）：
- `state.py` - 状态解析
- `action.py` - 动作决策
- `utils.py` - 工具函数

## 注意事项

1. 确保服务器目录路径正确
2. 确保所有客户端文件存在
3. 首次运行会安装依赖
4. 使用 Alt+Tab 切换窗口查看输出

## 比赛结果

比赛结果会显示在服务器窗口中，包括：
- 每局结束时的顺序
- 最终胜利次数统计

