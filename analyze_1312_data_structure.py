#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析1312数据结构的完整性和转换情况
检查所有字段是否都被正确转换
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# 修复Windows控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def analyze_action_string(action_str):
    """分析action字符串的完整结构"""
    try:
        import ast
        parsed = ast.literal_eval(action_str)
        return {
            'raw': action_str,
            'parsed': parsed,
            'length': len(parsed),
            'elements': {
                'action_type': parsed[0] if len(parsed) > 0 else None,
                'action_type2': parsed[1] if len(parsed) > 1 else None,
                'cards': parsed[2] if len(parsed) > 2 else None,
                'extra': parsed[3:] if len(parsed) > 3 else []
            }
        }
    except Exception as e:
        return {
            'raw': action_str,
            'error': str(e),
            'parsed': None
        }

def analyze_1312_file(file_path):
    """分析单个1312文件的结构"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    analysis = {
        'file': os.path.basename(file_path),
        'fields': {},
        'actions_analysis': [],
        'missing_fields': [],
        'strategy_info': {}
    }
    
    # 检查基本字段
    expected_fields = [
        'player_id', 'initial_hand', 'actions', 
        'all_players_hands', 'game_info'
    ]
    
    for field in expected_fields:
        analysis['fields'][field] = field in data
        if field not in data:
            analysis['missing_fields'].append(field)
    
    # 分析initial_hand
    if 'initial_hand' in data:
        analysis['fields']['initial_hand_count'] = len(data['initial_hand'])
        analysis['fields']['initial_hand_unique'] = len(set(data['initial_hand']))
    
    # 分析game_info
    if 'game_info' in data:
        game_info = data['game_info']
        analysis['fields']['game_info_keys'] = list(game_info.keys())
        analysis['fields']['curRank'] = game_info.get('curRank')
        analysis['fields']['game_result'] = game_info.get('game_result')
    
    # 分析all_players_hands
    if 'all_players_hands' in data:
        all_hands = data['all_players_hands']
        analysis['fields']['all_players_hands_keys'] = list(all_hands.keys())
        analysis['fields']['all_players_hands_non_empty'] = sum(
            1 for v in all_hands.values() if v
        )
    
    # 分析actions
    if 'actions' in data:
        actions = data['actions']
        analysis['fields']['actions_count'] = len(actions)
        
        # 分析每个action
        action_types = defaultdict(int)
        action_lengths = []
        has_strategy_info = False
        
        for i, action in enumerate(actions):
            action_analysis = {
                'index': i,
                'cur_pos': action.get('cur_pos'),
                'cur_action': action.get('cur_action'),
                'parsed': analyze_action_string(action.get('cur_action', ''))
            }
            
            parsed = action_analysis['parsed']
            if parsed.get('parsed'):
                action_type = parsed['elements']['action_type']
                action_types[action_type] += 1
                action_lengths.append(parsed['length'])
                
                # 检查是否有额外信息（策略信息可能在extra中）
                if parsed['elements']['extra']:
                    has_strategy_info = True
                    action_analysis['has_extra_info'] = True
                    action_analysis['extra_info'] = parsed['elements']['extra']
            
            analysis['actions_analysis'].append(action_analysis)
        
        analysis['fields']['action_types'] = dict(action_types)
        analysis['fields']['action_avg_length'] = sum(action_lengths) / len(action_lengths) if action_lengths else 0
        analysis['fields']['has_strategy_info'] = has_strategy_info
    
    # 检查是否有其他字段（可能包含策略信息）
    all_keys = set(data.keys())
    expected_keys_set = set(expected_fields)
    extra_keys = all_keys - expected_keys_set
    if extra_keys:
        analysis['fields']['extra_keys'] = list(extra_keys)
        for key in extra_keys:
            analysis['fields'][f'extra_{key}'] = data[key]
    
    return analysis

def print_analysis(analysis):
    """打印分析结果"""
    print("=" * 80)
    print(f"文件: {analysis['file']}")
    print("=" * 80)
    
    print("\n📋 字段检查:")
    for field, value in analysis['fields'].items():
        if isinstance(value, bool):
            status = "✅" if value else "❌"
            print(f"  {status} {field}: {value}")
        else:
            print(f"  • {field}: {value}")
    
    if analysis['missing_fields']:
        print(f"\n⚠️ 缺失字段: {', '.join(analysis['missing_fields'])}")
    
    print(f"\n🎯 Actions分析:")
    print(f"  • 总数量: {analysis['fields'].get('actions_count', 0)}")
    print(f"  • 动作类型分布: {analysis['fields'].get('action_types', {})}")
    print(f"  • 平均长度: {analysis['fields'].get('action_avg_length', 0):.2f}")
    print(f"  • 包含策略信息: {'是' if analysis['fields'].get('has_strategy_info') else '否'}")
    
    # 检查前几个action的详细信息
    print(f"\n📊 前3个Action详情:")
    for i, action_analysis in enumerate(analysis['actions_analysis'][:3]):
        print(f"\n  Action {i+1}:")
        print(f"    位置: {action_analysis['cur_pos']}")
        parsed = action_analysis['parsed']
        if parsed.get('parsed'):
            elements = parsed['elements']
            print(f"    动作类型: {elements['action_type']}")
            print(f"    动作类型2: {elements['action_type2']}")
            print(f"    卡牌数量: {len(elements['cards']) if elements['cards'] else 0}")
            if elements['extra']:
                print(f"    ⚠️ 额外信息: {elements['extra']}")
        else:
            print(f"    ❌ 解析失败: {parsed.get('error', 'Unknown')}")
    
    if analysis['fields'].get('extra_keys'):
        print(f"\n🔍 额外字段（可能包含策略信息）:")
        for key in analysis['fields']['extra_keys']:
            print(f"  • {key}: {analysis['fields'].get(f'extra_{key}', 'N/A')}")

def main():
    """主函数"""
    # 分析几个1312文件
    data_dir = "game_records"
    
    # 查找1312格式的文件
    files = [
        "replay_player0_szqjl_2023-12-26_13_08_42_.json",
        "replay_player3_szqjl_2024-02-27_16_34_05_.json"
    ]
    
    print("🔍 1312数据结构完整性分析")
    print("=" * 80)
    
    for filename in files:
        file_path = os.path.join(data_dir, filename)
        if os.path.exists(file_path):
            print(f"\n")
            analysis = analyze_1312_file(file_path)
            print_analysis(analysis)
        else:
            print(f"\n⚠️ 文件不存在: {file_path}")
    
    print("\n" + "=" * 80)
    print("📝 总结:")
    print("=" * 80)
    print("""
检查要点：
1. ✅ 基本字段是否完整（player_id, initial_hand, actions等）
2. ✅ action字符串是否包含策略信息（额外字段）
3. ✅ game_info是否包含完整信息（curRank, game_result等）
4. ✅ all_players_hands是否包含所有玩家手牌
5. ⚠️ 策略信息（保护队友、压制对手、出炸策略）是否在数据中
6. ⚠️ 比赛结果是否准确（不是unknown）
    """)

if __name__ == "__main__":
    main()

