#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析修复效果：对比修复前后的数据
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_game_record(file_path):
    """分析单个游戏记录"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    my_decisions = data.get('my_decisions', [])
    if not my_decisions:
        return None
    
    player_name = data.get('player_name', 'unknown')
    game_id = data.get('game_id', 'unknown')
    
    # 判断是否是修复后的对局（时间戳在22:30之后）
    timestamp = data.get('start_time', '')
    is_after_fix = False
    if timestamp and '22:3' in timestamp or '22:4' in timestamp or '22:5' in timestamp or '22:6' in timestamp or '22:7' in timestamp:
        is_after_fix = True
    
    total_decisions = len(my_decisions)
    pass_count = 0
    problem_passes = []
    phase_stats = defaultdict(lambda: {'total': 0, 'pass': 0, 'problem_pass': 0})
    
    for idx, decision in enumerate(my_decisions):
        action = decision.get('action', [])
        context = decision.get('context', {})
        phase = context.get('phase', 'unknown')
        action_list_size = context.get('actionList_size', 0)
        
        # 统计阶段
        phase_stats[phase]['total'] += 1
        
        # 统计PASS
        is_pass = False
        if action == "PASS" or (isinstance(action, list) and len(action) > 0 and action[0] == "PASS"):
            is_pass = True
            pass_count += 1
            phase_stats[phase]['pass'] += 1
        
        # 问题PASS：actionList_size > 1 但选择了PASS
        if is_pass and action_list_size > 1:
            problem_passes.append({
                'decision_idx': idx,
                'phase': phase,
                'actionList_size': action_list_size
            })
            phase_stats[phase]['problem_pass'] += 1
    
    pass_rate = (pass_count / total_decisions * 100) if total_decisions > 0 else 0
    
    return {
        'file_path': file_path,
        'player_name': player_name,
        'game_id': game_id,
        'is_after_fix': is_after_fix,
        'total_decisions': total_decisions,
        'pass_count': pass_count,
        'pass_rate': pass_rate,
        'problem_passes': problem_passes,
        'problem_pass_count': len(problem_passes),
        'phase_stats': {k: dict(v) for k, v in phase_stats.items()}
    }

def main():
    """主函数"""
    game_records_dir = Path('game_records')
    files = list(game_records_dir.glob('*20251224*.json'))
    
    all_results = []
    before_fix = []
    after_fix = []
    
    for file_path in sorted(files):
        result = analyze_game_record(file_path)
        if result:
            all_results.append(result)
            if result['is_after_fix']:
                after_fix.append(result)
            else:
                before_fix.append(result)
    
    print("=" * 80)
    print("修复效果对比分析")
    print("=" * 80)
    
    # 修复前统计
    if before_fix:
        before_total = len(before_fix)
        before_decisions = sum(r['total_decisions'] for r in before_fix)
        before_pass = sum(r['pass_count'] for r in before_fix)
        before_problem_pass = sum(r['problem_pass_count'] for r in before_fix)
        before_pass_rate = (before_pass / before_decisions * 100) if before_decisions > 0 else 0
        
        print(f"\n修复前（{before_total}局）:")
        print(f"  总决策数: {before_decisions}")
        print(f"  总PASS数: {before_pass}")
        print(f"  平均PASS率: {before_pass_rate:.1f}%")
        print(f"  总问题PASS数: {before_problem_pass}")
        print(f"  平均每局问题PASS: {before_problem_pass/before_total:.1f}个")
    
    # 修复后统计
    if after_fix:
        after_total = len(after_fix)
        after_decisions = sum(r['total_decisions'] for r in after_fix)
        after_pass = sum(r['pass_count'] for r in after_fix)
        after_problem_pass = sum(r['problem_pass_count'] for r in after_fix)
        after_pass_rate = (after_pass / after_decisions * 100) if after_decisions > 0 else 0
        
        print(f"\n修复后（{after_total}局）:")
        print(f"  总决策数: {after_decisions}")
        print(f"  总PASS数: {after_pass}")
        print(f"  平均PASS率: {after_pass_rate:.1f}%")
        print(f"  总问题PASS数: {after_problem_pass}")
        print(f"  平均每局问题PASS: {after_problem_pass/after_total:.1f}个")
        
        # 改善情况
        if before_fix:
            pass_rate_improvement = before_pass_rate - after_pass_rate
            problem_pass_improvement = (before_problem_pass/before_total) - (after_problem_pass/after_total)
            
            print(f"\n改善情况:")
            print(f"  PASS率改善: {pass_rate_improvement:.1f}% ({before_pass_rate:.1f}% → {after_pass_rate:.1f}%)")
            print(f"  问题PASS改善: {problem_pass_improvement:.1f}个/局 ({(before_problem_pass/before_total):.1f} → {(after_problem_pass/after_total):.1f})")
    
    # 按阶段统计
    print(f"\n按阶段统计（修复后）:")
    phase_stats_after = defaultdict(lambda: {'total': 0, 'pass': 0, 'problem_pass': 0})
    for result in after_fix:
        for phase, stats in result['phase_stats'].items():
            phase_stats_after[phase]['total'] += stats['total']
            phase_stats_after[phase]['pass'] += stats['pass']
            phase_stats_after[phase]['problem_pass'] += stats['problem_pass']
    
    for phase in sorted(phase_stats_after.keys()):
        stats = phase_stats_after[phase]
        pass_rate = (stats['pass'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {phase}: 总决策 {stats['total']}, PASS {stats['pass']} ({pass_rate:.1f}%), 问题PASS {stats['problem_pass']}")
    
    # 按玩家统计
    print(f"\n按玩家统计（修复后）:")
    player_stats_after = defaultdict(lambda: {'games': 0, 'total_decisions': 0, 'total_pass': 0, 'total_problem_pass': 0})
    for result in after_fix:
        player = result['player_name']
        player_stats_after[player]['games'] += 1
        player_stats_after[player]['total_decisions'] += result['total_decisions']
        player_stats_after[player]['total_pass'] += result['pass_count']
        player_stats_after[player]['total_problem_pass'] += result['problem_pass_count']
    
    for player, stats in sorted(player_stats_after.items()):
        avg_pass_rate = (stats['total_pass'] / stats['total_decisions'] * 100) if stats['total_decisions'] > 0 else 0
        print(f"  {player}: {stats['games']}局, PASS率 {avg_pass_rate:.1f}%, 问题PASS {stats['total_problem_pass']}个 (平均 {stats['total_problem_pass']/stats['games']:.1f}个/局)")

if __name__ == '__main__':
    main()

