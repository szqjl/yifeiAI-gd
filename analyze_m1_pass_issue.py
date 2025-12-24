#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析M1对局中yf频繁pass和拆三张打单的问题
"""

import json
from pathlib import Path
from collections import Counter

def analyze_pass_and_split_issue(game_file: str):
    """分析pass和拆牌问题"""
    with open(game_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    player_name = data.get("player_name", "unknown")
    my_decisions = data.get("my_decisions", [])
    actions = data.get("actions", [])
    
    print(f"=== {player_name} 对局分析 ===\n")
    print(f"总决策数: {len(my_decisions)}")
    
    # 1. 分析PASS情况
    print("\n【1. PASS分析】")
    pass_decisions = []
    for i, decision in enumerate(my_decisions):
        action = decision.get('action', [])
        if action and action[0] == 'PASS':
            context = decision.get('context', {})
            # 尝试多种方式获取剩余牌数
            my_remain = context.get('my_remain', context.get('myRemain', 27))
            # 尝试多种方式获取阶段
            game_phase = context.get('game_phase', context.get('phase', 'unknown'))
            # 尝试多种方式获取动作列表长度
            action_list_len = context.get('action_list_len', context.get('actionList_size', 0))
            is_passive = context.get('is_passive', False)
            cur_pos = context.get('curPos', -1)
            greater_pos = context.get('greaterPos', -1)
            
            pass_decisions.append({
                'index': i,
                'my_remain': my_remain,
                'game_phase': game_phase,
                'action_list_len': action_list_len,
                'is_passive': is_passive,
                'cur_pos': cur_pos,
                'greater_pos': greater_pos,
                'context': context
            })
    
    print(f"总PASS次数: {len(pass_decisions)}")
    
    # 按阶段统计PASS
    phase_pass_count = Counter([d['game_phase'] for d in pass_decisions])
    print(f"各阶段PASS次数: {dict(phase_pass_count)}")
    
    # 有可选动作但仍PASS的情况（关键问题！）
    problematic_pass = [d for d in pass_decisions if d['action_list_len'] > 1]
    print(f"\n⚠️ 有可选动作但仍PASS的次数: {len(problematic_pass)}")
    
    if problematic_pass:
        print("\n有可选动作但仍PASS的详情（前10次）:")
        for i, d in enumerate(problematic_pass[:10]):
            print(f"  第{d['index']+1}次决策: 阶段={d['game_phase']}, "
                  f"可选动作数={d['action_list_len']}, 当前玩家={d['cur_pos']}, "
                  f"最大玩家={d['greater_pos']}, 被动={d['is_passive']}")
    
    # 中后期PASS（剩余<=15张）
    mid_late_pass = [d for d in pass_decisions if d['my_remain'] <= 15]
    print(f"\n中后期(<=15张)PASS次数: {len(mid_late_pass)}")
    
    if mid_late_pass:
        print("\n中后期PASS详情（前10次）:")
        for i, d in enumerate(mid_late_pass[:10]):
            print(f"  第{d['index']+1}次决策: 剩余{d['my_remain']}张, 阶段={d['game_phase']}, "
                  f"可选动作数={d['action_list_len']}, 被动={d['is_passive']}")
            if d['action_list_len'] > 1:
                print(f"    ⚠️ 有可选动作但仍PASS！")
    
    # 2. 分析拆三张打单问题
    print("\n【2. 拆三张打单分析】")
    split_trips_decisions = []
    
    for i, decision in enumerate(my_decisions):
        action = decision.get('action', [])
        if not action or action[0] != 'Single':
            continue
        
        context = decision.get('context', {})
        handcards = context.get('handcards', [])
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        
        if not action_cards or not handcards:
            continue
        
        # 检查是否拆三张
        for card in action_cards:
            if len(card) >= 2:
                card_rank = card[1] if len(card) == 2 else card[1:]
                # 统计手牌中该点数的牌数
                rank_count = sum(1 for hc in handcards if len(hc) >= 2 and (hc[1] if len(hc) == 2 else hc[1:]) == card_rank)
                
                if rank_count >= 3:  # 拆三张或拆炸弹
                    my_remain = context.get('my_remain', 27)
                    game_phase = context.get('game_phase', 'unknown')
                    split_trips_decisions.append({
                        'index': i,
                        'card': card,
                        'rank': card_rank,
                        'rank_count': rank_count,
                        'my_remain': my_remain,
                        'game_phase': game_phase,
                        'action': action
                    })
                    break
    
    print(f"拆三张/炸弹打单次数: {len(split_trips_decisions)}")
    
    if split_trips_decisions:
        print("\n拆三张/炸弹打单详情（前10次）:")
        for i, d in enumerate(split_trips_decisions[:10]):
            print(f"  第{d['index']+1}次决策: 剩余{d['my_remain']}张, 阶段={d['game_phase']}, "
                  f"拆牌={d['card']} (该点数有{d['rank_count']}张)")
            print(f"    动作: {d['action']}")
    
    # 3. 分析决策上下文
    print("\n【3. 决策上下文分析】")
    if mid_late_pass:
        print("\n中后期PASS时的上下文（示例）:")
        sample = mid_late_pass[0]
        context = sample['context']
        print(f"  剩余牌数: {context.get('my_remain', '?')}")
        print(f"  游戏阶段: {context.get('game_phase', '?')}")
        print(f"  可选动作数: {context.get('action_list_len', '?')}")
        print(f"  是否被动: {context.get('is_passive', '?')}")
        print(f"  对手剩余牌: {context.get('opponent_rest_cards_list', [])}")
        print(f"  队友剩余牌: {context.get('teammate_rest_cards', '?')}")
        
        # 检查是否有可用的非PASS动作
        if 'action_list' in context:
            action_list = context['action_list']
            non_pass_actions = [a for a in action_list if isinstance(a, list) and len(a) > 0 and a[0] != 'PASS']
            print(f"  非PASS动作数: {len(non_pass_actions)}")
            if non_pass_actions:
                print(f"  可用动作类型: {[a[0] for a in non_pass_actions[:5]]}")
    
    return {
        'total_decisions': len(my_decisions),
        'total_pass': len(pass_decisions),
        'mid_late_pass': len(mid_late_pass),
        'split_trips': len(split_trips_decisions)
    }

if __name__ == "__main__":
    import sys
    
    # 查找最新的游戏记录
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
    for game_file in json_files[:3]:
        print(f"\n{'='*60}")
        print(f"分析文件: {game_file.name}")
        print('='*60)
        try:
            analyze_pass_and_split_issue(str(game_file))
        except Exception as e:
            print(f"分析失败: {e}")
            import traceback
            traceback.print_exc()

