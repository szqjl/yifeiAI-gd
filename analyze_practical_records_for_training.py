"""分析实战记录是否可用于改善M1训练"""
import json
from pathlib import Path
from typing import List, Dict, Any

print("="*60)
print("实战记录训练可行性分析")
print("="*60)

# 1. 检查实战记录
game_records_dir = Path("game_records")
all_records = list(game_records_dir.glob("*.json"))
m1_records = [r for r in all_records if "yf1_m1" in r.name or "yf2_m1" in r.name]
replay_records = [r for r in all_records if r.name.startswith("replay")]

print(f"\n1. 记录统计:")
print(f"   总记录数: {len(all_records)}")
print(f"   M1实战记录: {len(m1_records)}")
print(f"   Replay记录: {len(replay_records)}")

# 2. 分析M1实战记录格式
if m1_records:
    print(f"\n2. 分析M1实战记录格式:")
    latest_m1 = max(m1_records, key=lambda p: p.stat().st_mtime)
    
    with open(latest_m1, 'r', encoding='utf-8') as f:
        m1_data = json.load(f)
    
    print(f"   最新记录: {latest_m1.name}")
    print(f"   顶层键: {list(m1_data.keys())[:15]}")
    
    # 检查关键字段
    has_actions = 'actions' in m1_data
    has_game_info = 'game_info' in m1_data
    has_states = 'states' in m1_data or 'game_states' in m1_data
    has_result = 'result' in m1_data
    
    print(f"\n   关键字段:")
    print(f"     - actions: {'[OK]' if has_actions else '[NO]'}")
    print(f"     - game_info: {'[OK]' if has_game_info else '[NO]'}")
    print(f"     - states: {'[OK]' if has_states else '[NO]'}")
    print(f"     - result: {'[OK]' if has_result else '[NO]'}")
    
    # 分析actions
    if has_actions:
        actions = m1_data.get('actions', [])
        print(f"\n   Actions分析:")
        print(f"     - 数量: {len(actions)}")
        if actions:
            print(f"     - 示例（前3个）:")
            for i, action in enumerate(actions[:3], 1):
                print(f"       {i}. {str(action)[:100]}...")
    
    # 分析game_info
    if has_game_info:
        game_info = m1_data.get('game_info', {})
        print(f"\n   Game Info分析:")
        print(f"     - 键: {list(game_info.keys())[:10]}")
        if 'game_result' in game_info:
            print(f"     - 游戏结果: {game_info.get('game_result')}")
        if 'team_result' in game_info:
            print(f"     - 队伍结果: {game_info.get('team_result')}")

# 3. 分析Replay记录格式
if replay_records:
    print(f"\n3. 分析Replay记录格式:")
    latest_replay = max(replay_records, key=lambda p: p.stat().st_mtime)
    
    with open(latest_replay, 'r', encoding='utf-8') as f:
        replay_data = json.load(f)
    
    print(f"   最新记录: {latest_replay.name}")
    print(f"   顶层键: {list(replay_data.keys())[:15]}")
    
    # 检查是否包含出牌记录
    has_actions = 'actions' in replay_data or 'moves' in replay_data
    has_states = 'states' in replay_data or 'game_states' in replay_data
    
    print(f"\n   关键字段:")
    print(f"     - actions/moves: {'✓' if has_actions else '✗'}")
    print(f"     - states: {'✓' if has_states else '✗'}")

# 4. 检查数据加载器支持
print(f"\n4. 检查数据加载器支持:")
try:
    from src.train.simple_data_loader import create_simple_dataloader
    print("   [OK] simple_data_loader 可用")
except ImportError as e:
    print(f"   [NO] simple_data_loader 导入失败: {e}")

try:
    from src.knowledge_processor.replay_parser import ReplayParser
    print("   [OK] ReplayParser 可用")
except ImportError as e:
    print(f"   [NO] ReplayParser 导入失败: {e}")

# 5. 可行性分析
print(f"\n5. 可行性分析:")
print(f"\n   [优势]")
print(f"   - M1实战记录包含真实的出牌决策")
print(f"   - 可以学习M1在实战中的策略选择")
print(f"   - 包含胜负信息，可以区分好决策和坏决策")
print(f"   - 数据格式与现有训练流程兼容")

print(f"\n   [挑战]")
print(f"   - 需要确保记录格式与ReplayParser兼容")
print(f"   - 需要验证actions格式是否正确")
print(f"   - 可能需要调整数据加载器以支持新格式")

print(f"\n   [建议]")
print(f"   1. 检查M1记录的actions格式是否与replay格式一致")
print(f"   2. 如果格式不同，需要编写转换函数")
print(f"   3. 可以将M1实战记录与replay记录混合训练")
print(f"   4. 根据胜负结果，可以给M1的决策加权（胜利的决策权重更高）")

# 6. 测试数据加载
print(f"\n6. 测试数据加载:")
if m1_records:
    try:
        from src.knowledge_processor.replay_parser import ReplayParser
        
        parser = ReplayParser()
        test_record = max(m1_records, key=lambda p: p.stat().st_mtime)
        
        print(f"   测试记录: {test_record.name}")
        
        # 尝试解析
        with open(test_record, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # 检查是否可以提取训练数据
        if 'actions' in test_data:
            print(f"   [OK] 包含actions字段")
            print(f"   [OK] 可以尝试提取训练数据")
        else:
            print(f"   [NO] 缺少actions字段，可能需要格式转换")
            
    except Exception as e:
        print(f"   ✗ 测试失败: {e}")

print("\n" + "="*60)
print("结论:")
print("  实战记录可以用于改善M1训练，但需要：")
print("  1. 确保记录格式兼容")
print("  2. 可能需要格式转换")
print("  3. 可以混合实战记录和replay记录训练")
print("  4. 根据胜负结果给决策加权")
print("="*60)
