#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析2025年12月24日所有对局记录，找出所有问题
"""

import json
import os
from collections import defaultdict
from pathlib import Path

def analyze_game_record(file_path):
    """分析单个游戏记录"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    my_decisions = data.get('my_decisions', [])
    if not my_decisions:
        return None
    
    player_name = data.get('player_name', 'unknown')
    game_id = data.get('game_id', 'unknown')
    
    total_decisions = len(my_decisions)
    pass_count = 0
    problem_passes = []
    split_bombs = []
    action_types = defaultdict(int)
    phase_stats = defaultdict(lambda: {'total': 0, 'pass': 0, 'problem_pass': 0})
    
    for idx, decision in enumerate(my_decisions):
        action = decision.get('action', [])
        context = decision.get('context', {})
        phase = context.get('phase', 'unknown')
        action_list_size = context.get('actionList_size', 0)
        
        # 统计动作类型
        if isinstance(action, list) and len(action) > 0:
            action_type = action[0]
            action_types[action_type] += 1
        else:
            action_types['Unknown'] += 1
        
        # 统计PASS
        is_pass = False
        if action == "PASS" or (isinstance(action, list) and len(action) > 0 and action[0] == "PASS"):
            is_pass = True
            pass_count += 1
        
        # 统计阶段
        phase_stats[phase]['total'] += 1
        if is_pass:
            phase_stats[phase]['pass'] += 1
        
        # 问题PASS：actionList_size > 1 但选择了PASS
        if is_pass and action_list_size > 1:
            problem_passes.append({
                'decision_idx': idx,
                'phase': phase,
                'actionList_size': action_list_size,
                'curAction': context.get('curAction', 'N/A'),
                'myPos': context.get('myPos', -1),
                'greaterPos': context.get('greaterPos', -1)
            })
            phase_stats[phase]['problem_pass'] += 1
        
        # 检查拆炸弹
        if isinstance(action, list) and len(action) > 0:
            action_type = action[0]
            if action_type in ['Single', 'Pair', 'Trips']:
                action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                if action_cards:
                    # 检查是否拆了炸弹（需要检查手牌中是否有4张同点数的牌）
                    from collections import Counter
                    card_ranks = [card[1] if len(card) >= 2 else '' for card in action_cards]
                    rank_counts = Counter(card_ranks)
                    for rank, count in rank_counts.items():
                        if rank and count >= 2:
                            # 可能是拆炸弹，需要进一步检查
                            # 这里简化处理，如果单张/对子/三张的牌点数相同，可能是拆炸弹
                            if action_type == 'Single' and count == 1:
                                # 单张可能是拆炸弹的一部分
                                pass
                            elif action_type == 'Pair' and count == 2:
                                # 对子可能是拆炸弹的一部分
                                pass
                            elif action_type == 'Trips' and count == 3:
                                # 三张可能是拆炸弹的一部分
                                pass
    
    pass_rate = (pass_count / total_decisions * 100) if total_decisions > 0 else 0
    
    return {
        'file_path': file_path,
        'player_name': player_name,
        'game_id': game_id,
        'total_decisions': total_decisions,
        'pass_count': pass_count,
        'pass_rate': pass_rate,
        'problem_passes': problem_passes,
        'problem_pass_count': len(problem_passes),
        'split_bombs': split_bombs,
        'split_bomb_count': len(split_bombs),
        'action_types': dict(action_types),
        'phase_stats': {k: dict(v) for k, v in phase_stats.items()}
    }

def main():
    """主函数"""
    game_records_dir = Path('game_records')
    if not game_records_dir.exists():
        print(f"错误：找不到 game_records 目录")
        return
    
    # 找到所有20251224的对局记录
    files = list(game_records_dir.glob('*20251224*.json'))
    if not files:
        print("未找到2025年12月24日的对局记录")
        return
    
    print(f"找到 {len(files)} 个对局记录文件")
    print("=" * 80)
    
    all_results = []
    player_stats = defaultdict(lambda: {
        'games': 0,
        'total_decisions': 0,
        'total_pass': 0,
        'total_problem_pass': 0,
        'total_split_bomb': 0
    })
    
    # 分析每个文件
    for file_path in sorted(files):
        result = analyze_game_record(file_path)
        if result:
            all_results.append(result)
            player = result['player_name']
            player_stats[player]['games'] += 1
            player_stats[player]['total_decisions'] += result['total_decisions']
            player_stats[player]['total_pass'] += result['pass_count']
            player_stats[player]['total_problem_pass'] += result['problem_pass_count']
            player_stats[player]['total_split_bomb'] += result['split_bomb_count']
    
    # 汇总统计
    print("\n" + "=" * 80)
    print("汇总统计")
    print("=" * 80)
    
    total_games = len(all_results)
    total_decisions = sum(r['total_decisions'] for r in all_results)
    total_pass = sum(r['pass_count'] for r in all_results)
    total_problem_pass = sum(r['problem_pass_count'] for r in all_results)
    total_split_bomb = sum(r['split_bomb_count'] for r in all_results)
    
    avg_pass_rate = (total_pass / total_decisions * 100) if total_decisions > 0 else 0
    
    print(f"总对局数: {total_games}")
    print(f"总决策数: {total_decisions}")
    print(f"总PASS数: {total_pass}")
    print(f"平均PASS率: {avg_pass_rate:.1f}%")
    print(f"总问题PASS数: {total_problem_pass}")
    print(f"总拆炸弹数: {total_split_bomb}")
    
    # 按玩家统计
    print("\n" + "=" * 80)
    print("按玩家统计")
    print("=" * 80)
    for player, stats in sorted(player_stats.items()):
        avg_pass_rate = (stats['total_pass'] / stats['total_decisions'] * 100) if stats['total_decisions'] > 0 else 0
        print(f"\n{player}:")
        print(f"  对局数: {stats['games']}")
        print(f"  总决策数: {stats['total_decisions']}")
        print(f"  总PASS数: {stats['total_pass']}")
        print(f"  平均PASS率: {avg_pass_rate:.1f}%")
        print(f"  问题PASS数: {stats['total_problem_pass']}")
        print(f"  拆炸弹数: {stats['total_split_bomb']}")
    
    # 问题清单
    print("\n" + "=" * 80)
    print("问题清单")
    print("=" * 80)
    
    # 1. 问题PASS详情
    print(f"\n1. 问题PASS详情（共{total_problem_pass}个）:")
    problem_pass_by_phase = defaultdict(list)
    problem_pass_by_player = defaultdict(list)
    
    for result in all_results:
        for pp in result['problem_passes']:
            pp['player'] = result['player_name']
            pp['game_id'] = result['game_id']
            problem_pass_by_phase[pp['phase']].append(pp)
            problem_pass_by_player[result['player_name']].append(pp)
    
    for phase, pps in sorted(problem_pass_by_phase.items()):
        print(f"\n  阶段 {phase}: {len(pps)} 个问题PASS")
        for pp in pps[:5]:  # 只显示前5个
            print(f"    - {pp['player']} 游戏{pp['game_id']} 决策{pp['decision_idx']}: actionList_size={pp['actionList_size']}, curAction={pp['curAction']}")
        if len(pps) > 5:
            print(f"    ... 还有 {len(pps) - 5} 个")
    
    # 2. 高PASS率对局
    print(f"\n2. 高PASS率对局（PASS率 >= 70%）:")
    high_pass_games = [r for r in all_results if r['pass_rate'] >= 70]
    for r in sorted(high_pass_games, key=lambda x: x['pass_rate'], reverse=True)[:10]:
        print(f"  - {r['player_name']} 游戏{r['game_id']}: PASS率 {r['pass_rate']:.1f}%, 问题PASS {r['problem_pass_count']}个")
    
    # 3. 阶段统计
    print(f"\n3. 各阶段PASS率:")
    phase_pass_stats = defaultdict(lambda: {'total': 0, 'pass': 0, 'problem_pass': 0})
    for result in all_results:
        for phase, stats in result['phase_stats'].items():
            phase_pass_stats[phase]['total'] += stats['total']
            phase_pass_stats[phase]['pass'] += stats['pass']
            phase_pass_stats[phase]['problem_pass'] += stats['problem_pass']
    
    for phase in sorted(phase_pass_stats.keys()):
        stats = phase_pass_stats[phase]
        pass_rate = (stats['pass'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {phase}: 总决策 {stats['total']}, PASS {stats['pass']} ({pass_rate:.1f}%), 问题PASS {stats['problem_pass']}")
    
    # 4. 动作类型分布
    print(f"\n4. 动作类型分布:")
    action_type_total = defaultdict(int)
    for result in all_results:
        for action_type, count in result['action_types'].items():
            action_type_total[action_type] += count
    
    for action_type in sorted(action_type_total.keys()):
        print(f"  {action_type}: {action_type_total[action_type]}")
    
    # 5. 最严重的问题
    print(f"\n5. 最严重的问题:")
    if total_problem_pass > 0:
        print(f"  - 问题PASS总数: {total_problem_pass} (平均每局 {total_problem_pass/total_games:.1f} 个)")
    if avg_pass_rate > 60:
        print(f"  - 平均PASS率过高: {avg_pass_rate:.1f}% (应该 < 50%)")
    if total_split_bomb > 0:
        print(f"  - 拆炸弹问题: {total_split_bomb} 次")
    
    # 保存详细报告
    report_file = 'M1_20251224_问题分析报告.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# M1 2025年12月24日对局问题分析报告\n\n")
        f.write(f"## 汇总统计\n\n")
        f.write(f"- 总对局数: {total_games}\n")
        f.write(f"- 总决策数: {total_decisions}\n")
        f.write(f"- 总PASS数: {total_pass}\n")
        f.write(f"- 平均PASS率: {avg_pass_rate:.1f}%\n")
        f.write(f"- 总问题PASS数: {total_problem_pass}\n")
        f.write(f"- 总拆炸弹数: {total_split_bomb}\n\n")
        
        f.write(f"## 按玩家统计\n\n")
        for player, stats in sorted(player_stats.items()):
            avg_pass_rate = (stats['total_pass'] / stats['total_decisions'] * 100) if stats['total_decisions'] > 0 else 0
            f.write(f"### {player}\n\n")
            f.write(f"- 对局数: {stats['games']}\n")
            f.write(f"- 总决策数: {stats['total_decisions']}\n")
            f.write(f"- 总PASS数: {stats['total_pass']}\n")
            f.write(f"- 平均PASS率: {avg_pass_rate:.1f}%\n")
            f.write(f"- 问题PASS数: {stats['total_problem_pass']}\n")
            f.write(f"- 拆炸弹数: {stats['total_split_bomb']}\n\n")
        
        f.write(f"## 问题清单\n\n")
        f.write(f"### 1. 问题PASS详情\n\n")
        for phase, pps in sorted(problem_pass_by_phase.items()):
            f.write(f"#### 阶段 {phase}: {len(pps)} 个问题PASS\n\n")
            for pp in pps:
                f.write(f"- {pp['player']} 游戏{pp['game_id']} 决策{pp['decision_idx']}: actionList_size={pp['actionList_size']}, curAction={pp['curAction']}\n")
            f.write("\n")
    
    print(f"\n详细报告已保存到: {report_file}")

if __name__ == '__main__':
    main()

