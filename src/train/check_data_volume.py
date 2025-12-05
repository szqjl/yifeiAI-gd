# -*- coding: utf-8 -*-
"""
检查训练数据量
统计当前训练数据是否达到目标
"""

import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.knowledge_processor.replay_parser import ReplayParser


def check_data_volume():
    """检查训练数据量"""
    print("="*60)
    print("训练数据量检查")
    print("="*60)
    
    # 1. 使用ReplayParser统计
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    print(f"\n[ReplayParser统计]")
    print(f"  对局文件数: {len(replays)} 个")
    print(f"  训练样本数: {len(raw_data)} 个")
    
    # 2. 直接统计JSON文件
    game_records_dir = "game_records"
    json_files = [f for f in os.listdir(game_records_dir) 
                  if f.endswith('.json') and 'replay_player' in f]
    
    total_actions = 0
    player_stats = {}
    
    for f in json_files:
        path = os.path.join(game_records_dir, f)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                player_id = data.get('player_id', 'unknown')
                actions = data.get('actions', [])
                action_count = len(actions)
                total_actions += action_count
                
                if player_id not in player_stats:
                    player_stats[player_id] = {'files': 0, 'actions': 0}
                player_stats[player_id]['files'] += 1
                player_stats[player_id]['actions'] += action_count
        except Exception as e:
            print(f"  警告: 无法读取 {f}: {e}")
    
    print(f"\n[JSON文件统计]")
    print(f"  JSON文件数: {len(json_files)} 个")
    print(f"  总动作数: {total_actions} 个")
    
    # 3. 各玩家数据分布
    print(f"\n[各玩家数据分布]")
    for player_id in sorted(player_stats.keys(), key=lambda x: (isinstance(x, str), x)):
        stats = player_stats[player_id]
        print(f"  玩家 {player_id}: {stats['files']} 个对局, {stats['actions']} 个动作")
    
    # 4. 目标对比
    target_samples = 500
    current_samples = len(raw_data)
    
    print(f"\n" + "="*60)
    print("目标对比")
    print("="*60)
    print(f"当前训练样本数: {current_samples} 个")
    print(f"目标训练样本数: {target_samples} 个")
    
    if current_samples >= target_samples:
        print(f"[OK] 已达到目标！超出 {current_samples - target_samples} 个样本")
    else:
        remaining = target_samples - current_samples
        print(f"[WARNING] 未达到目标，还差 {remaining} 个样本")
        print(f"   还需要约 {remaining // 10} - {remaining // 5} 个对局")
        print(f"   (假设每个对局5-10个训练样本)")
    
    # 5. 数据质量评估
    print(f"\n" + "="*60)
    print("数据质量评估")
    print("="*60)
    
    if current_samples < 200:
        print("[WARNING] 数据量较少，建议继续收集")
    elif current_samples < 500:
        print("[OK] 数据量中等，可以开始训练，但建议继续收集")
    elif current_samples < 1000:
        print("[OK] 数据量充足，适合训练")
    else:
        print("[OK] 数据量丰富，非常适合训练")
    
    # 6. 建议
    print(f"\n" + "="*60)
    print("建议")
    print("="*60)
    
    if current_samples < 500:
        print(f"1. 继续收集数据（目标500+个样本）")
        print(f"2. 当前可以使用现有数据训练，但效果可能有限")
        print(f"3. 建议收集更多对局（至少50-100个对局）")
    else:
        print(f"1. [OK] 数据量充足，可以开始正式训练")
        print(f"2. 建议使用学习率 0.0003-0.0005")
        print(f"3. 建议训练轮数 30-50轮")
        print(f"4. 可以考虑使用学习率衰减")
    
    print(f"\n" + "="*60)


if __name__ == "__main__":
    check_data_volume()

