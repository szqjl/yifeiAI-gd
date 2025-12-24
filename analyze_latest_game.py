#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析最新对局记录，评估修复效果"""

import json
import glob
import os
from pathlib import Path
from collections import Counter

def analyze_game_record(game_file):
    """分析单个游戏记录"""
    with open(game_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    decisions = data.get('my_decisions', [])
    actions = data.get('actions', [])
    
    print(f"\n{'='*60}")
    print(f"游戏记录: {Path(game_file).name}")
    print(f"{'='*60}")
    print(f"总决策数: {len(decisions)}")
    
    # 统计PASS
    pass_count = 0
    problem_passes = []  # actionList_size > 1 时的PASS
    
    for i, dec in enumerate(decisions):
        action = dec.get('action', [])
        if isinstance(action, list) and len(action) > 0:
            if action[0] == 'PASS':
                pass_count += 1
                ctx = dec.get('context', {})
                action_list_size = ctx.get('actionList_size', 0)
                if action_list_size > 1:
                    problem_passes.append({
                        'idx': i,
                        'actionList_size': action_list_size,
                        'curAction': ctx.get('curAction', 'N/A'),
                        'phase': ctx.get('phase', 'N/A')
                    })
    
    print(f"PASS总数: {pass_count}/{len(decisions)} ({pass_count/len(decisions)*100:.1f}%)")
    print(f"问题PASS (actionList_size>1): {len(problem_passes)}")
    
    if problem_passes:
        print("\n问题PASS详情（前5个）:")
        for pp in problem_passes[:5]:
            print(f"  决策{pp['idx']}: phase={pp['phase']}, actionList_size={pp['actionList_size']}, curAction={pp['curAction']}")
    
    # 统计动作类型
    action_types = Counter()
    for dec in decisions:
        action = dec.get('action', [])
        if isinstance(action, list) and len(action) > 0:
            action_types[action[0]] += 1
    
    print(f"\n动作类型统计:")
    for act_type, count in action_types.most_common():
        print(f"  {act_type}: {count}")
    
    # 检查是否有拆炸弹的情况（通过检查Single动作是否来自炸弹）
    bomb_splits = []
    for i, dec in enumerate(decisions):
        action = dec.get('action', [])
        if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
            action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
            if action_cards:
                # 检查手牌中是否有4张相同点数的牌（可能是炸弹）
                initial_hand = data.get('initial_hand', [])
                if initial_hand:
                    card_rank = action_cards[0][1] if len(action_cards[0]) >= 2 else ""
                    if card_rank:
                        rank_count = sum(1 for card in initial_hand if len(card) >= 2 and card[1] == card_rank)
                        if rank_count >= 4:
                            bomb_splits.append({
                                'idx': i,
                                'card': action_cards[0],
                                'rank_count': rank_count
                            })
    
    if bomb_splits:
        print(f"\n⚠️ 可能的拆炸弹情况: {len(bomb_splits)}")
        for bs in bomb_splits[:3]:
            print(f"  决策{bs['idx']}: 出单张{bs['card']}, 手牌中有{bs['rank_count']}张相同点数")
    else:
        print(f"\n✓ 未发现拆炸弹情况")
    
    return {
        'total': len(decisions),
        'pass_count': pass_count,
        'pass_rate': pass_count/len(decisions)*100 if decisions else 0,
        'problem_passes': len(problem_passes),
        'bomb_splits': len(bomb_splits)
    }

def main():
    # 找到最新的游戏记录
    game_files = sorted(glob.glob("game_records/*.json"), key=os.path.getmtime, reverse=True)
    
    if not game_files:
        print("未找到游戏记录文件")
        return
    
    # 分析最新的3个游戏
    results = []
    for game_file in game_files[:3]:
        if 'yf1_m1' in game_file or 'yf2_m1' in game_file:
            result = analyze_game_record(game_file)
            results.append(result)
    
    # 汇总
    if results:
        print(f"\n{'='*60}")
        print("汇总统计")
        print(f"{'='*60}")
        avg_pass_rate = sum(r['pass_rate'] for r in results) / len(results)
        total_problem_passes = sum(r['problem_passes'] for r in results)
        total_bomb_splits = sum(r['bomb_splits'] for r in results)
        
        print(f"平均PASS率: {avg_pass_rate:.1f}%")
        print(f"总问题PASS数: {total_problem_passes}")
        print(f"总拆炸弹数: {total_bomb_splits}")
        
        if total_bomb_splits == 0:
            print("✓ 修复成功：未发现拆炸弹")
        else:
            print(f"⚠️ 仍有拆炸弹问题: {total_bomb_splits}次")

if __name__ == "__main__":
    main()

