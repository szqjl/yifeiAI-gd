#!/usr/bin/env python3
"""
M1 vs lalala 对局逐局、逐副分析脚本
目标：找出为何M1胜率始终为0的根本原因
"""

import json
import glob
import os
from collections import defaultdict, Counter
from datetime import datetime

def load_game_record(filepath):
    """加载单个对局记录"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR loading {filepath}: {e}")
        return None

def extract_game_id(filepath):
    """从文件路径提取 game_id"""
    # 格式: 20260217094055405181 [yf2_m1]-[opponent_1_3]-[1]-[None].json
    filename = os.path.basename(filepath)
    parts = filename.split('[')
    game_id = parts[0].strip()
    player_info = filename.split('[')[1].split(']')[0]  # yf2_m1 or yf1_m1
    return game_id, player_info

def group_records_by_game(record_files):
    """将成对的yf1/yf2记录按game_id分组"""
    games = defaultdict(dict)

    for record_file in record_files:
        game_id, player_info = extract_game_id(record_file)
        data = load_game_record(record_file)
        if data:
            games[game_id][player_info] = data

    return games

def analyze_single_round(round_data, player_pos, player_name):
    """分析单副的M1决策"""
    actions = round_data.get('play_sequence', [])

    # 找出该玩家的所有决策
    decisions = []
    pass_count = 0

    for action in actions:
        if action.get('cur_pos') == player_pos:
            action_type = action.get('cur_action', [None])[0]
            decision = {
                'action_type': action_type,
                'full_action': action.get('cur_action'),
                'greater_action': action.get('greater_action'),
                'is_pass': action_type == 'Pass',
                'timestamp': action.get('timestamp'),
            }
            decisions.append(decision)
            if action_type == 'Pass':
                pass_count += 1

    return {
        'decisions': decisions,
        'pass_count': pass_count,
        'total_decisions': len(decisions),
        'pass_rate': pass_count / len(decisions) if decisions else 0,
    }

def get_round_result(round_data):
    """获取副级结果"""
    # episodeOver 包含名次信息
    episode_over = round_data.get('episodeOver')
    if episode_over:
        order = episode_over.get('order', [])  # [head, second, third, last]
        return order
    return None

def analyze_game_pair(game_data_m1, game_data_yf2, game_id):
    """分析一对yf1/yf2的M1对局"""

    # 基本信息
    yf1_player_id = 0
    yf2_player_id = 2

    results = {
        'game_id': game_id,
        'rounds': [],
        'total_pass_rate_yf1': 0,
        'total_pass_rate_yf2': 0,
        'yf1_victories': 0,
        'yf2_victories': 0,
        'lalala_victories': 0,
        'm1_team_victories': 0,
    }

    # 分析每一副
    rounds_yf1 = game_data_m1.get('rounds', [])
    rounds_yf2 = game_data_yf2.get('rounds', [])

    # 配对分析
    for idx, (round_m1, round_m2) in enumerate(zip(rounds_yf1, rounds_yf2)):
        round_analysis = analyze_single_round(round_m1, yf1_player_id, "yf1_m1")
        yf2_analysis = analyze_single_round(round_m2, yf2_player_id, "yf2_m1")

        # 获取副级结果
        round_order = get_round_result(round_m1)
        yf2_order = get_round_result(round_m2)

        # 计算胜负（0位和2位是一队）
        m1_team_positions = {0, 2}

        round_result = {
            'round_num': idx + 1,
            'yf1_m1': round_analysis,
            'yf2_m1': yf2_analysis,
            'yf1_order': round_order,
            'yf2_order': yf2_order,
        }

        if round_order:
            # order = [head_pos, second_pos, third_pos, last_pos]
            # 检查我们队是否获胜
            first_pos = round_order[0]
            second_pos = round_order[1]

            if first_pos in m1_team_positions and second_pos in m1_team_positions:
                results['m1_team_victories'] += 1
                round_result['m1_team_victory'] = True
            else:
                round_result['m1_team_victory'] = False
                if first_pos not in m1_team_positions:
                    results['lalala_victories'] += 1

        results['rounds'].append(round_result)

    # 统计
    if results['rounds']:
        total_pass_yf1 = sum(r['yf1_m1']['pass_rate'] for r in results['rounds'])
        total_pass_yf2 = sum(r['yf2_m1']['pass_rate'] for r in results['rounds'])
        results['total_pass_rate_yf1'] = total_pass_yf1 / len(results['rounds'])
        results['total_pass_rate_yf2'] = total_pass_yf2 / len(results['rounds'])

    return results

def main():
    print("="*80)
    print("M1 vs lalala 逐局、逐副分析")
    print("="*80)
    print()

    # 获取所有记录文件
    record_files = sorted(glob.glob("game_records/*[yf?_m1]*.json"))
    print(f"找到 {len(record_files)} 个M1对局记录")
    print()

    # 按game_id分组
    games = group_records_by_game(record_files)
    print(f"找到 {len(games)} 对完整的yf1/yf2配对对局")
    print()

    # 分析每一对
    all_results = []

    for game_id, records in sorted(games.items()):
        if 'yf1_m1' in records and 'yf2_m1' in records:
            result = analyze_game_pair(records['yf1_m1'], records['yf2_m1'], game_id)
            all_results.append(result)

    # 打印详细分析结果
    print("逐局分析结果（最近的10对）:")
    print("-"*80)

    for result in all_results[-10:]:
        print(f"\n对局 {result['game_id']}")
        print(f"  yf1_m1 平均PASS率: {result['total_pass_rate_yf1']:.2%}")
        print(f"  yf2_m1 平均PASS率: {result['total_pass_rate_yf2']:.2%}")
        print(f"  M1队胜场数: {result['m1_team_victories']}")
        print(f"  lalala队胜场数: {result['lalala_victories']}")

        # 逐副详细
        print(f"  副级详情:")
        for round_info in result['rounds']:
            round_num = round_info['round_num']
            yf1_pass = round_info['yf1_m1']['pass_rate']
            yf2_pass = round_info['yf2_m1']['pass_rate']
            m1_win = round_info['m1_team_victory']

            result_str = "✓M1胜" if m1_win else "✗lalala胜"
            print(f"    副{round_num}: yf1 PASS {yf1_pass:.0%} | yf2 PASS {yf2_pass:.0%} | {result_str}")

    # 汇总统计
    print("\n" + "="*80)
    print("总体统计:")
    print("-"*80)

    total_m1_victories = sum(r['m1_team_victories'] for r in all_results)
    total_lalala_victories = sum(r['lalala_victories'] for r in all_results)
    total_rounds = sum(len(r['rounds']) for r in all_results)

    print(f"总对局数: {len(all_results)}")
    print(f"总副数: {total_rounds}")
    print(f"M1队总胜场: {total_m1_victories}")
    print(f"lalala队总胜场: {total_lalala_victories}")
    print(f"M1队胜率: {total_m1_victories}/{total_rounds} = {total_m1_victories/total_rounds if total_rounds > 0 else 0:.2%}")

    avg_pass_yf1 = sum(r['total_pass_rate_yf1'] for r in all_results) / len(all_results) if all_results else 0
    avg_pass_yf2 = sum(r['total_pass_rate_yf2'] for r in all_results) / len(all_results) if all_results else 0

    print(f"\n平均PASS率:")
    print(f"  yf1_m1: {avg_pass_yf1:.2%}")
    print(f"  yf2_m1: {avg_pass_yf2:.2%}")

    # 生成分析报告
    generate_detailed_report(all_results)

def generate_detailed_report(all_results):
    """生成详细分析报告"""
    print("\n" + "="*80)
    print("深度分析: 为什么M1胜率始终为0%")
    print("="*80)

    # 分析副数分布
    print("\n1. 副数级别分析:")
    print("-"*80)

    round_stats = defaultdict(lambda: {'m1_wins': 0, 'total': 0})

    for game_result in all_results:
        for round_info in game_result['rounds']:
            round_num = round_info['round_num']
            round_stats[round_num]['total'] += 1
            if round_info['m1_team_victory']:
                round_stats[round_num]['m1_wins'] += 1

    print("\n  按副数编号的M1胜率:")
    for round_num in sorted(round_stats.keys()):
        stats = round_stats[round_num]
        win_rate = stats['m1_wins'] / stats['total'] if stats['total'] > 0 else 0
        print(f"    副{round_num}: {stats['m1_wins']}/{stats['total']} = {win_rate:.0%}")

    # PASS率与胜负的关联分析
    print("\n2. PASS率与胜负的关联:")
    print("-"*80)

    m1_wins_rounds = []
    m1_loss_rounds = []

    for game_result in all_results:
        for round_info in game_result['rounds']:
            yf1_pass = round_info['yf1_m1']['pass_rate']
            yf2_pass = round_info['yf2_m1']['pass_rate']
            avg_pass = (yf1_pass + yf2_pass) / 2

            if round_info['m1_team_victory']:
                m1_wins_rounds.append(avg_pass)
            else:
                m1_loss_rounds.append(avg_pass)

    if m1_wins_rounds:
        print(f"  M1胜场 平均PASS率: {sum(m1_wins_rounds)/len(m1_wins_rounds):.2%}")
    else:
        print(f"  M1胜场: 0场 (无数据)")

    print(f"  M1负场 平均PASS率: {sum(m1_loss_rounds)/len(m1_loss_rounds):.2%}")

    # 分析yf1 vs yf2的差异
    print("\n3. yf1_m1 vs yf2_m1 的性能差异:")
    print("-"*80)

    for game_result in all_results[-5:]:  # 最后5对
        print(f"\n  对局 {game_result['game_id'][:10]}...")

        yf1_passes = []
        yf2_passes = []

        for round_info in game_result['rounds']:
            yf1_passes.append(round_info['yf1_m1']['pass_rate'])
            yf2_passes.append(round_info['yf2_m1']['pass_rate'])

        print(f"    yf1平均PASS: {sum(yf1_passes)/len(yf1_passes):.2%} (范围 {min(yf1_passes):.0%}-{max(yf1_passes):.0%})")
        print(f"    yf2平均PASS: {sum(yf2_passes)/len(yf2_passes):.2%} (范围 {min(yf2_passes):.0%}-{max(yf2_passes):.0%})")

if __name__ == '__main__':
    main()
