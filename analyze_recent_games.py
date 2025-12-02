#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析最近的比赛结果"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_recent_games():
    records_dir = Path('game_records')
    files = sorted(
        [f for f in records_dir.glob('*yf1_v5*.json')],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    print('=' * 80)
    print('最近10场V5比赛结果')
    print('=' * 80)
    print()
    
    team_a_wins = 0
    team_b_wins = 0
    total = 0
    
    for i, f in enumerate(files[:10], 1):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            
            result = data.get('result', {})
            vn = result.get('victoryNum', [0, 0, 0, 0])
            team_a = vn[0] + vn[2]
            team_b = vn[1] + vn[3]
            
            team_a_wins += team_a
            team_b_wins += team_b
            total += 1
            
            game_id = data.get('game_id', f.name[:20])
            start_time = data.get('start_time', '')[:19] if data.get('start_time') else ''
            
            print(f'{i}. {game_id} ({start_time})')
            print(f'   队伍A (0号+2号): {team_a} 胜 | 队伍B (1号+3号): {team_b} 胜')
            print(f'   决策统计: RL={result.get("rl_decisions", 0)}, '
                  f'知识库={result.get("knowledge_decisions", 0)}, '
                  f'策略={result.get("strategy_decisions", 0)}')
            print()
        except Exception as e:
            print(f'读取 {f.name} 时出错: {e}')
            print()
    
    print('-' * 80)
    print(f'总计 ({total}场):')
    print(f'  队伍A (yf1_v5 + yf2_v5): {team_a_wins} 胜')
    print(f'  队伍B (对手): {team_b_wins} 胜')
    
    if total > 0 and (team_a_wins + team_b_wins) > 0:
        rate_a = team_a_wins / (team_a_wins + team_b_wins) * 100
        rate_b = team_b_wins / (team_a_wins + team_b_wins) * 100
        print(f'  队伍A胜率: {rate_a:.1f}%')
        print(f'  队伍B胜率: {rate_b:.1f}%')
    
    print('=' * 80)
    
    # 分析最新一场比赛的详细情况
    if files:
        latest_file = files[0]
        print()
        print('最新比赛详情:')
        print('=' * 80)
        try:
            with open(latest_file, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            
            result = data.get('result', {})
            vn = result.get('victoryNum', [0, 0, 0, 0])
            
            print(f'比赛ID: {data.get("game_id", "N/A")}')
            print(f'开始时间: {data.get("start_time", "N/A")}')
            print(f'玩家: {data.get("player_name", "N/A")} (位置 {data.get("player_id", "N/A")})')
            print()
            print('各位置胜场:')
            print(f'  0号位 (yf1_v5): {vn[0]} 胜')
            print(f'  1号位 (对手): {vn[1]} 胜')
            print(f'  2号位 (yf2_v5): {vn[2]} 胜')
            print(f'  3号位 (对手): {vn[3]} 胜')
            print()
            print(f'队伍A (0+2号): {vn[0] + vn[2]} 胜')
            print(f'队伍B (1+3号): {vn[1] + vn[3]} 胜')
            print()
            print('决策统计:')
            print(f'  总决策数: {result.get("total_decisions", 0)}')
            print(f'  RL决策: {result.get("rl_decisions", 0)}')
            print(f'  知识库决策: {result.get("knowledge_decisions", 0)}')
            print(f'  策略决策: {result.get("strategy_decisions", 0)}')
            print()
            print('=' * 80)
        except Exception as e:
            print(f'读取最新比赛详情时出错: {e}')

if __name__ == '__main__':
    analyze_recent_games()

