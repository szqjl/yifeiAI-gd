# 1312掼蛋数据集成使用指南

## 📋 概述

本指南说明如何将1312掼蛋平台的真实比赛记录数据集成到训练流程中。

## 🔍 数据格式

### 1312原始格式

```json
{
  "player_id": 0,
  "initial_hand": ["D9", "C2", "C3", ...],
  "actions": [
    {
      "cur_pos": 0,
      "cur_action": "['Discard', 'Discard', ['C4', 'DA']]"
    }
  ]
}
```

### 转换后格式（训练格式）

```json
{
  "player_id": 0,
  "initial_hand": ["D9", "C2", ...],
  "all_players_hands": {
    "0": ["D9", "C2", ...],
    "1": [],
    "2": [],
    "3": []
  },
  "game_info": {
    "curRank": "2",
    "game_result": "unknown"
  },
  "actions": [...]
}
```

## 🚀 使用方法

### 方法1: 使用训练GUI自动转换

1. 启动训练GUI：
```bash
python run_stage6_training_gui.py
```

2. 选择包含1312格式数据的目录（如`game_records`）

3. 点击"开始阶段6训练"

4. GUI会自动检测并转换1312格式的数据

### 方法2: 手动转换单个文件

```python
from src.knowledge_processor.replay_1312_converter import convert_1312_replay

# 转换单个文件
convert_1312_replay(
    input_path="game_records/replay_player0_szqjl_2023-12-26_13_08_42_.json",
    output_path="game_records/replay_player0_szqjl_2023-12-26_13_08_42_converted.json"
)
```

### 方法3: 批量转换目录

```python
from src.knowledge_processor.replay_1312_converter import convert_1312_directory

# 批量转换
convert_1312_directory(
    input_dir="game_records",
    output_dir="game_records_converted"
)
```

### 方法4: 使用命令行测试

```bash
python test_1312_converter.py
```

## 📊 转换功能说明

### 自动补充的字段

1. **all_players_hands**: 从initial_hand和actions序列推断所有玩家的手牌
2. **game_info.curRank**: 从文件名提取或使用默认值"2"
3. **game_info.game_result**: 从数据中提取或标记为"unknown"

### 数据验证

转换器会自动验证：
- ✅ 初始手牌数量（应为26张）
- ✅ 动作序列格式
- ✅ 卡牌编码格式

## 🎯 训练流程集成

转换后的数据可以直接用于训练：

1. **数据加载**: `ReplayParser`会自动识别转换后的格式
2. **训练**: 使用`train_bc`函数进行训练
3. **评估**: 使用`GameOrientedEvaluator`进行评估

## ⚠️ 注意事项

1. **级牌等级**: 如果数据中没有级牌信息，默认使用"2"
2. **游戏结果**: 如果无法确定结果，标记为"unknown"
3. **其他玩家手牌**: 只能准确知道Hero的手牌，其他玩家手牌通过动作序列估算

## 📝 示例

### 转换示例

```python
from src.knowledge_processor.replay_1312_converter import Replay1312Converter

converter = Replay1312Converter()

# 转换单个文件
result = converter.convert_file(
    "game_records/replay_player0_szqjl_2023-12-26_13_08_42_.json",
    "game_records/converted/replay_player0_szqjl_2023-12-26_13_08_42_.json"
)

print(f"转换完成:")
print(f"  玩家ID: {result['player_id']}")
print(f"  级牌等级: {result['game_info']['curRank']}")
print(f"  游戏结果: {result['game_info']['game_result']}")
```

## 🔧 故障排除

### 问题1: 导入错误

**错误**: `ModuleNotFoundError: No module named 'replay_1312_converter'`

**解决**: 使用动态导入（已在GUI中实现）

### 问题2: 数据格式错误

**错误**: `初始手牌数量不正确`

**解决**: 检查原始数据文件，确保手牌数量为26张

### 问题3: 转换失败

**错误**: `转换失败: ...`

**解决**: 检查JSON文件格式是否正确，确保编码为UTF-8

## 📚 相关文档

- [1312数据格式分析](../analysis/1312_data_format_analysis.md)
- [训练流程文档](../training/历次训练效果汇总.md)

