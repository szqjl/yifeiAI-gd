# 使用实战记录改善M1训练指南

## ✅ 可行性分析

### 当前状态

**记录统计**:
- 总记录数: 366条
- M1实战记录: 2条
- Replay记录: 364条

**M1实战记录格式**:
- ✅ 包含 `actions` 字段（出牌记录）
- ✅ 包含 `player_id` 字段（玩家ID）
- ✅ 包含 `game_info` 字段（游戏信息）
- ✅ 包含 `result` 字段（胜负结果）
- ✅ 包含 `initial_hand` 字段（初始手牌）

**格式兼容性**:
- ✅ M1记录格式与 `ReplayParser` 兼容
- ✅ 数据加载器可以处理M1记录
- ✅ 可以提取训练数据

## 🎯 优势

### 1. 真实决策数据
- M1实战记录包含真实的出牌决策
- 可以学习M1在实战中的策略选择
- 包含完整的游戏状态信息

### 2. 胜负信息
- 可以根据胜负结果区分好决策和坏决策
- 胜利的决策可以给予更高权重
- 失败的决策可以分析问题所在

### 3. 数据兼容性
- M1记录格式与现有训练流程兼容
- 可以直接使用 `ReplayParser` 解析
- 可以与replay记录混合训练

## 🔧 实施方法

### 方法1: 直接使用（推荐）

M1实战记录已经包含所有必需字段，可以直接用于训练：

```python
# 数据加载器会自动加载所有包含 player_id 和 actions 的记录
# 包括M1实战记录和replay记录
dataloader = create_simple_dataloader(
    data_dir="game_records",
    batch_size=32,
    max_samples=5000
)
```

**优点**:
- 无需修改代码
- 自动混合实战记录和replay记录
- 简单直接

### 方法2: 根据胜负结果加权

可以根据胜负结果给M1的决策加权：

```python
# 在数据加载器中添加权重
def _get_sample_weight(self, record):
    """根据胜负结果计算样本权重"""
    result = record.get('result', {})
    victory_num = result.get('victoryNum', [])
    player_id = record.get('player_id', 0)
    
    if victory_num and len(victory_num) > player_id:
        wins = victory_num[player_id]
        # 胜利的决策权重更高
        return 1.0 + wins * 0.5  # 每胜一次增加0.5权重
    
    return 1.0  # 默认权重
```

**优点**:
- 更关注胜利的决策
- 提高训练效果
- 可以区分好决策和坏决策

### 方法3: 只使用胜利记录

可以只使用M1胜利的记录进行训练：

```python
def filter_winning_records(records):
    """只保留M1胜利的记录"""
    winning_records = []
    
    for record in records:
        result = record.get('result', {})
        victory_num = result.get('victoryNum', [])
        player_id = record.get('player_id', 0)
        
        if victory_num and len(victory_num) > player_id:
            if victory_num[player_id] > 0:
                winning_records.append(record)
    
    return winning_records
```

**优点**:
- 只学习胜利的决策
- 避免学习失败的策略
- 提高训练质量

## 📊 当前训练数据来源

### 数据加载器逻辑

`simple_data_loader.py` 的加载逻辑：

1. **扫描所有JSON文件**:
   ```python
   json_files = list(self.data_dir.glob("*.json"))
   ```

2. **检查记录格式**:
   ```python
   if 'player_id' in data and 'actions' in data:
       replays.append(data)
   ```

3. **提取训练数据**:
   ```python
   training_data = parser.extract_training_data(replays)
   ```

**结论**: M1实战记录已经可以被自动加载和使用！

## 🚀 改进建议

### 1. 增加实战记录数量

当前只有2条M1实战记录，建议：
- 运行更多M1对战测试
- 收集更多实战记录
- 目标：至少50-100条实战记录

### 2. 根据胜负结果加权

可以修改数据加载器，根据胜负结果给样本加权：

```python
# 在 SimpleGuandanDataset 中添加权重计算
def _calculate_sample_weight(self, record, state_dict):
    """根据胜负结果计算样本权重"""
    result = record.get('result', {})
    victory_num = result.get('victoryNum', [])
    player_id = record.get('player_id', 0)
    
    if victory_num and len(victory_num) > player_id:
        wins = victory_num[player_id]
        # 胜利的决策权重更高
        return 1.0 + wins * 0.3
    elif result.get('game_result') == 'win':
        return 1.5  # 胜利记录权重更高
    
    return 1.0  # 默认权重
```

### 3. 混合训练策略

可以混合使用：
- **Replay记录**（364条）: 提供基础策略
- **M1实战记录**（2条）: 提供实战经验
- **胜利记录优先**: 更关注胜利的决策

### 4. 数据增强

可以基于实战记录进行数据增强：
- 镜像对称（左右对称）
- 牌面替换（保持牌型不变）
- 时间序列增强

## 📝 实施步骤

### 步骤1: 验证数据加载

```bash
# 测试数据加载器是否能加载M1记录
python -c "from src.train.simple_data_loader import create_simple_dataloader; loader = create_simple_dataloader('game_records', max_samples=100); print(f'加载了 {len(loader.dataset)} 个样本')"
```

### 步骤2: 检查样本分布

```bash
# 检查M1记录是否被加载
python -c "from pathlib import Path; import json; m1_records = [r for r in Path('game_records').glob('*.json') if 'yf1_m1' in r.name]; print(f'M1记录数: {len(m1_records)}')"
```

### 步骤3: 开始训练

```bash
# 使用包含M1实战记录的数据进行训练
python src/train/stage7_optimized_training.py --epochs 100
```

## ✅ 结论

**可以使用实战记录改善M1训练！**

1. ✅ **格式兼容**: M1记录格式与训练流程完全兼容
2. ✅ **自动加载**: 数据加载器会自动加载M1记录
3. ✅ **可以加权**: 可以根据胜负结果给决策加权
4. ✅ **混合训练**: 可以与replay记录混合训练

**建议**:
- 运行更多M1对战测试，收集更多实战记录
- 可以考虑根据胜负结果给样本加权
- 当前2条记录已经可以被使用，但建议增加到50-100条

---

**分析时间**: 2026-01-13  
**状态**: ✅ 可以使用实战记录改善训练  
**下一步**: 运行更多对战测试，收集更多实战记录
