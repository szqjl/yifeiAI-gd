#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析M1对局行为是否合理
"""

import json
from pathlib import Path
from collections import Counter

def analyze_m1_behavior(game_file: str):
    """分析M1行为是否合理"""
    with open(game_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    player_name = data.get("player_name", "unknown")
    player_id = data.get("player_id", 0)
    my_decisions = data.get("my_decisions", [])
    actions = data.get("actions", [])
    initial_hand = data.get("initial_hand", [])
    
    print(f"=== {player_name} 对局行为分析 ===\n")
    print(f"玩家ID: {player_id}")
    print(f"初始手牌数: {len(initial_hand)}")
    print(f"初始手牌: {initial_hand}\n")
    
    print(f"总决策数: {len(my_decisions)}")
    print(f"总动作数: {len(actions)}\n")
    
    # 1. 分析决策类型分布
    print("【1. 决策类型分布】")
    from collections import Counter
    decision_types = Counter()
    for decision in my_decisions:
        action = decision.get('action', [])
        if action and len(action) > 0:
            action_type = action[0]
            decision_types[action_type] += 1
    
    print(f"决策类型统计: {dict(decision_types)}")
    pass_count = decision_types.get('PASS', 0)
    print(f"PASS占比: {pass_count}/{len(my_decisions)} = {pass_count/len(my_decisions)*100:.1f}%\n")
    
    # 2. 分析被动出牌时的PASS情况
    print("【2. 被动出牌PASS分析】")
    passive_pass_decisions = []
    for i, decision in enumerate(my_decisions):
        action = decision.get('action', [])
        context = decision.get('context', {})
        
        if action and action[0] == 'PASS':
            cur_pos = context.get('curPos', -1)
            greater_pos = context.get('greaterPos', -1)
            action_list_size = context.get('actionList_size', 0)
            phase = context.get('phase', 'unknown')
            
            # 判断是否是被动出牌（curPos != myPos 或 greaterPos != myPos）
            my_pos = context.get('myPos', player_id)
            is_passive = (cur_pos != my_pos) or (greater_pos != my_pos and greater_pos != -1)
            
            if is_passive:
                passive_pass_decisions.append({
                    'index': i,
                    'cur_pos': cur_pos,
                    'greater_pos': greater_pos,
                    'action_list_size': action_list_size,
                    'phase': phase,
                    'context': context
                })
    
    print(f"被动出牌时PASS次数: {len(passive_pass_decisions)}")
    
    # 分析有可选动作但仍PASS的情况
    problematic_passive_pass = [d for d in passive_pass_decisions if d['action_list_size'] > 1]
    print(f"⚠️ 被动出牌时有可选动作但仍PASS: {len(problematic_passive_pass)}次\n")
    
    if problematic_passive_pass:
        print("被动出牌时有可选动作但仍PASS的详情:")
        for d in problematic_passive_pass[:10]:
            print(f"  第{d['index']+1}次决策: 阶段={d['phase']}, "
                  f"当前玩家={d['cur_pos']}, 最大玩家={d['greater_pos']}, "
                  f"可选动作数={d['action_list_size']}")
            
            # 查找对应的action，看看对手/队友在出什么
            decision_timestamp = my_decisions[d['index']].get('timestamp', '')
            matching_action = None
            for action in actions:
                if action.get('timestamp') == decision_timestamp or abs(
                    (action.get('timestamp', '') if isinstance(action.get('timestamp'), str) else '') == decision_timestamp
                ):
                    matching_action = action
                    break
            
            # 或者通过cur_pos和greater_pos查找
            if not matching_action:
                for action in actions:
                    if action.get('cur_pos') == d['cur_pos'] and action.get('greater_pos') == d['greater_pos']:
                        matching_action = action
                        break
            
            if matching_action:
                greater_action = matching_action.get('greater_action', [])
                if greater_action:
                    print(f"    对手/队友出牌: {greater_action[0]} {greater_action[1] if len(greater_action) > 1 else ''}")
            print()
    
    # 3. 分析主动出牌情况
    print("【3. 主动出牌分析】")
    active_decisions = []
    for i, decision in enumerate(my_decisions):
        action = decision.get('action', [])
        context = decision.get('context', {})
        
        if action and action[0] != 'PASS':
            cur_pos = context.get('curPos', -1)
            greater_pos = context.get('greaterPos', -1)
            my_pos = context.get('myPos', player_id)
            
            # 判断是否是主动出牌
            is_active = (cur_pos == -1 and greater_pos == -1) or (cur_pos == my_pos)
            
            if is_active:
                active_decisions.append({
                    'index': i,
                    'action': action,
                    'phase': context.get('phase', 'unknown')
                })
    
    print(f"主动出牌次数: {len(active_decisions)}")
    for d in active_decisions:
        action = d['action']
        print(f"  第{d['index']+1}次: {action[0]} {action[1] if len(action) > 1 else ''} (阶段={d['phase']})")
    
    # 4. 分析手牌变化（如果有记录）
    print("\n【4. 手牌变化分析】")
    if initial_hand:
        # 统计初始手牌中的牌型
        initial_rank_counts = Counter()
        for card in initial_hand:
            if len(card) >= 2:
                rank = card[1] if len(card) == 2 else card[1:]
                initial_rank_counts[rank] += 1
        
        print(f"初始手牌点数分布: {dict(initial_rank_counts)}")
        
        # 统计已出的牌
        played_cards = []
        for decision in my_decisions:
            action = decision.get('action', [])
            if action and len(action) > 2 and isinstance(action[2], list):
                played_cards.extend(action[2])
        
        print(f"已出牌数: {len(played_cards)}")
        if played_cards:
            print(f"已出牌: {played_cards}")
    
    # 5. 分析拆牌行为
    print("\n【5. 拆牌行为分析】")
    split_decisions = []
    for i, decision in enumerate(my_decisions):
        action = decision.get('action', [])
        if not action or action[0] != 'Single':
            continue
        
        # 需要检查是否拆牌，但这需要知道当时的手牌状态
        # 简化：检查是否出单张，且该点数在手牌中有多张
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        if action_cards:
            card = action_cards[0]
            if len(card) >= 2:
                rank = card[1] if len(card) == 2 else card[1:]
                # 检查初始手牌中该点数的数量
                rank_count = sum(1 for c in initial_hand if len(c) >= 2 and (c[1] if len(c) == 2 else c[1:]) == rank)
                if rank_count >= 3:
                    split_decisions.append({
                        'index': i,
                        'card': card,
                        'rank': rank,
                        'initial_count': rank_count
                    })
    
    print(f"可能的拆牌行为: {len(split_decisions)}次")
    if split_decisions:
        for d in split_decisions:
            print(f"  第{d['index']+1}次: 出单张 {d['card']} (该点数初始有{d['initial_count']}张)")
    
    # 6. 总结
    print("\n【6. 行为合理性总结】")
    issues = []
    
    if len(problematic_passive_pass) > 0:
        issues.append(f"⚠️ 被动出牌时有可选动作但仍PASS {len(problematic_passive_pass)}次")
    
    if len(split_decisions) > 0:
        issues.append(f"⚠️ 可能的拆牌行为 {len(split_decisions)}次")
    
    if len(active_decisions) < len(my_decisions) * 0.3:
        issues.append(f"⚠️ 主动出牌次数过少 ({len(active_decisions)}/{len(my_decisions)})")
    
    if issues:
        print("发现的问题:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✓ 未发现明显问题")
    
    return {
        'total_decisions': len(my_decisions),
        'pass_count': pass_count,
        'problematic_passive_pass': len(problematic_passive_pass),
        'split_decisions': len(split_decisions),
        'active_decisions': len(active_decisions)
    }

if __name__ == "__main__":
    import sys
    
    # 查找最新的M1对局记录
    game_records_dir = Path("game_records")
    if not game_records_dir.exists():
        print("game_records目录不存在！")
        sys.exit(1)
    
    # 获取最新的yf1_m1或yf2_m1记录
    json_files = list(game_records_dir.glob("*yf*_m1*.json"))
    if not json_files:
        print("未找到M1对局记录！")
        sys.exit(1)
    
    # 按修改时间排序
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # 分析最新的几个文件
    print("="*60)
    print("分析最新的M1对局记录（修复后）")
    print("="*60)
    
    for game_file in json_files[:3]:
        print(f"\n{'='*60}")
        print(f"分析文件: {game_file.name}")
        print('='*60)
        try:
            result = analyze_m1_behavior(str(game_file))
            print(f"\n统计: 总决策={result['total_decisions']}, PASS={result['pass_count']}, "
                  f"问题PASS={result['problematic_passive_pass']}, 主动出牌={result['active_decisions']}")
        except Exception as e:
            print(f"分析失败: {e}")
            import traceback
            traceback.print_exc()

