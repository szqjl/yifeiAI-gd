"""诊断训练数据问题"""
import sys
sys.path.insert(0, 'src/knowledge_processor')
sys.path.insert(0, 'src/train')

from replay_parser import ReplayParser
from pathlib import Path
import json

print("="*60)
print("诊断训练数据问题")
print("="*60)

# 1. 检查ReplayParser提取的数据
parser = ReplayParser('game_records')
replays = parser.load_replays()[:3]
print(f"\n1. 加载了 {len(replays)} 个replay")

if replays:
    data = parser.extract_training_data(replays)
    print(f"2. 提取了 {len(data)} 个训练样本")
    
    if data:
        sample_state, sample_action = data[0]
        print(f"\n3. 第一个样本:")
        print(f"   状态键: {list(sample_state.keys())[:10]}")
        print(f"   action_cards类型: {type(sample_action)}")
        print(f"   action_cards长度: {len(sample_action) if isinstance(sample_action, list) else 'N/A'}")
        print(f"   action_cards前10个: {sample_action[:10] if isinstance(sample_action, list) and len(sample_action) > 0 else '空'}")
        
        # 检查action_cards是否为空
        if isinstance(sample_action, list) and len(sample_action) == 0:
            print("\n   ⚠️ 问题：action_cards为空！")
            print("   检查更多样本...")
            non_empty_count = 0
            for i, (s, a) in enumerate(data[:100]):
                if isinstance(a, list) and len(a) > 0:
                    non_empty_count += 1
                    if non_empty_count == 1:
                        print(f"   找到非空样本（索引{i}）: {a[:5]}")
            print(f"   前100个样本中非空数量: {non_empty_count}")
        else:
            print("   ✅ action_cards不为空")
    else:
        print("   ❌ 没有提取到训练数据")
else:
    print("   ❌ 没有加载到replay")

# 2. 检查游戏记录格式
print("\n" + "="*60)
print("检查游戏记录格式")
print("="*60)

record_file = list(Path('game_records').glob('*yf1_m1*.json'))[0]
with open(record_file, 'r', encoding='utf-8') as f:
    record = json.load(f)

print(f"记录文件: {record_file.name}")
print(f"记录键: {list(record.keys())}")
print(f"是否有actions: {'actions' in record}")
if 'actions' in record:
    print(f"actions数量: {len(record['actions'])}")
    if len(record['actions']) > 0:
        print(f"第一个action: {record['actions'][0]}")
        print(f"第一个action的cur_action类型: {type(record['actions'][0].get('cur_action'))}")

print("\n" + "="*60)
print("诊断完成")
print("="*60)
