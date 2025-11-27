# 掼蛋AI对战系统

## 快速开始

### 图形界面（推荐）
```bash
START_GUI.bat          # 正式运行
START_GUI_TEST.bat     # 测试运行（带详细日志）
```

### 命令行
```bash
START_100_GAMES.bat    # 执行100场对战
START_MATCH.bat        # 单场对战
```

## 核心文件

```
启动脚本:
  START_GUI.bat              # GUI启动
  START_100_GAMES.bat        # 批量执行
  START_MATCH.bat            # 单场对战

源代码:
  src/communication/         # AI客户端
    ├── Test1.py            # 客户端1
    └── Test2.py            # 客户端2（知识增强）
  src/game_logic/           # 游戏逻辑
  src/knowledge/            # 知识库

批量执行:
  batch_executor/           # 自动重启系统
  batch_executor_gui.py     # GUI界面

配置:
  config.yaml               # AI参数配置

文档:
  GUI使用指南.md            # GUI操作说明
  修复说明.md               # 最新修复内容
```

## 配置说明

编辑 `config.yaml` 调整AI行为：
- `decision.max_decision_time`: 决策超时（秒）
- `evaluation.weights`: 评估权重
- `cooperation.support_threshold`: 合作阈值

## 常见问题

**只运行3场就停止？**
- 已修复，系统会自动重启完成目标场数

**GUI不显示状态？**
- 已修复，使用 `START_GUI_TEST.bat` 查看详细日志

**如何修改对战场数？**
- GUI模式：在界面输入目标场数
- 命令行：编辑 `.bat` 文件中的数字参数

## 联系

- 研究: chenxg@njupt.edu.cn
- 反馈: wuguduofeng@gmail.com
