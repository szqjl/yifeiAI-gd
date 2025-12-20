#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分析位置分配模式"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_position_allocation():
    records_dir = Path('game_records')
    files = sorted(
        [f for f in records_dir.glob('*yf1_v5*.json')],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    print('=' * 80)
    print('位置分配模式分析')
    print('=' * 80)
    print()
    
    position_patterns = defaultdict(int)
    teammate_patterns = defaultdict(int)
    
    for f in files[:20]:  # 分析最近20场
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            
            yf1_pos = data.get('player_id', -1)
            yf1_name = data.get('player_name', '')
            
            # 查找对应的yf2_v5记录
            f2 = f.parent / f.name.replace('yf1_v5', 'yf2_v5')
            if f2.exists():
                with open(f2, 'r', encoding='utf-8') as fp2:
                    data2 = json.load(fp2)
                
                yf2_pos = data2.get('player_id', -1)
                yf2_name = data2.get('player_name', '')
                
                # 检查是否是队友（0和2是队友，1和3是队友）
                is_teammate = ((yf1_pos + 2) % 4 == yf2_pos) or ((yf2_pos + 2) % 4 == yf1_pos)
                
                pattern = f"yf1={yf1_pos}, yf2={yf2_pos}"
                position_patterns[pattern] += 1
                
                if is_teammate:
                    teammate_patterns[f"队友: {pattern}"] += 1
                else:
                    teammate_patterns[f"非队友: {pattern}"] += 1
        except Exception as e:
            print(f'读取 {f.name} 时出错: {e}')
            continue
    
    print('位置分配统计（最近20场）:')
    print('-' * 80)
    for pattern, count in sorted(position_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f'  {pattern}: {count}次')
    
    print()
    print('队友关系统计:')
    print('-' * 80)
    for pattern, count in sorted(teammate_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f'  {pattern}: {count}次')
    
    print()
    print('=' * 80)
    print('结论:')
    print('-' * 80)
    
    # 检查是否总是队友
    teammate_count = sum(1 for p in teammate_patterns.keys() if '队友' in p)
    non_teammate_count = sum(1 for p in teammate_patterns.keys() if '非队友' in p)
    
    if non_teammate_count == 0:
        print('✓ yf1_v5和yf2_v5总是被分配到队友位置')
        print('  可以使用固定队伍关系判断（0和2是队友，1和3是队友）')
    else:
        print('✗ yf1_v5和yf2_v5有时不在同一队！')
        print('  需要根据实际player_id和player_name来判断队伍')
    
    print('=' * 80)

if __name__ == '__main__':
    analyze_position_allocation()

