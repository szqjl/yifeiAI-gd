# -*- coding: utf-8 -*-
"""
游戏记录一致性检查工具

功能：
1. 检查游戏记录中的手牌和出牌是否一致
2. 验证每个动作中的卡牌是否在对应时刻的手牌中
3. 检测记录错误和不一致
"""

import json
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple


def check_game_record_consistency(record_file: Path) -> Dict:
    """
    检查游戏记录的一致性
    
    Args:
        record_file: 游戏记录文件路径
        
    Returns:
        检查结果字典，包含：
        - is_consistent: 是否一致
        - errors: 错误列表
        - warnings: 警告列表
        - player_stats: 每个玩家的统计信息
    """
    with open(record_file, 'r', encoding='utf-8') as f:
        game_data = json.load(f)
    
    result = {
        'is_consistent': True,
        'errors': [],
        'warnings': [],
        'player_stats': {}
    }
    
    # 获取初始手牌
    all_players_hands = game_data.get('all_players_hands', {})
    if not all_players_hands:
        # 如果没有all_players_hands，尝试使用initial_hand
        player_id = game_data.get('player_id', 0)
        initial_hand = game_data.get('initial_hand', [])
        if initial_hand:
            all_players_hands[str(player_id)] = initial_hand
    
    # 初始化每个玩家的当前手牌（从初始手牌开始）
    current_hands = {}
    for pos_str, hand in all_players_hands.items():
        if isinstance(hand, list):
            current_hands[int(pos_str)] = hand.copy()
        else:
            current_hands[int(pos_str)] = []
    
    # 获取所有动作
    actions = game_data.get('actions', [])
    
    # 按玩家分组统计
    player_stats = {}
    for pos in range(4):
        player_stats[pos] = {
            'initial_count': len(current_hands.get(pos, [])),
            'actions_count': 0,
            'cards_played': [],
            'errors': [],
            'warnings': []
        }
    
    # 逐个检查动作
    for step, action in enumerate(actions):
        cur_pos = action.get('cur_pos', -1)
        cur_action = action.get('cur_action', [])
        
        if cur_pos < 0 or cur_pos > 3:
            continue
        
        # 解析动作中的卡牌
        action_cards = []
        if isinstance(cur_action, list):
            if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                action_cards = cur_action[2]
            elif len(cur_action) == 2 and isinstance(cur_action[1], list):
                action_cards = cur_action[1]
        
        # 如果是PASS，跳过
        if not action_cards or (isinstance(cur_action, list) and len(cur_action) > 0 and cur_action[0] == 'PASS'):
            continue
        
        player_stats[cur_pos]['actions_count'] += 1
        
        # 获取当前手牌
        current_hand = current_hands.get(cur_pos, [])
        current_hand_counts = Counter(current_hand)
        action_card_counts = Counter(action_cards)
        
        # 检查动作中的卡牌是否在当前手牌中
        missing_cards = []
        insufficient_cards = []
        
        for card, count in action_card_counts.items():
            if card not in current_hand_counts:
                missing_cards.append(f"{card}(需要{count}张)")
            elif current_hand_counts[card] < count:
                insufficient_cards.append(f"{card}(需要{count}张，只有{current_hand_counts[card]}张)")
        
        if missing_cards or insufficient_cards:
            error_msg = f"步骤{step+1}: 玩家{cur_pos}出牌 {cur_action}，但手牌中缺少: {', '.join(missing_cards + insufficient_cards)}"
            result['errors'].append(error_msg)
            player_stats[cur_pos]['errors'].append({
                'step': step + 1,
                'action': cur_action,
                'missing_cards': missing_cards,
                'insufficient_cards': insufficient_cards,
                'current_hand': current_hand.copy()
            })
            result['is_consistent'] = False
        
        # 从当前手牌中移除打出的卡牌
        for card in action_cards:
            if card in current_hands[cur_pos]:
                current_hands[cur_pos].remove(card)
            else:
                # 如果卡牌不在手牌中，记录警告（可能已经被移除过了）
                if step > 0:  # 不是第一步
                    warning_msg = f"步骤{step+1}: 玩家{cur_pos}尝试移除卡牌 {card}，但该卡牌不在当前手牌中"
                    result['warnings'].append(warning_msg)
                    player_stats[cur_pos]['warnings'].append({
                        'step': step + 1,
                        'card': card,
                        'current_hand': current_hand.copy()
                    })
        
        # 记录打出的卡牌
        player_stats[cur_pos]['cards_played'].extend(action_cards)
    
    result['player_stats'] = player_stats
    
    return result


def print_consistency_report(result: Dict, record_file: Path):
    """打印一致性检查报告"""
    print("=" * 80)
    print(f"游戏记录一致性检查报告: {record_file.name}")
    print("=" * 80)
    
    if result['is_consistent']:
        print("✓ 游戏记录一致性检查通过")
    else:
        print("✗ 游戏记录一致性检查失败")
    
    print(f"\n错误数量: {len(result['errors'])}")
    print(f"警告数量: {len(result['warnings'])}")
    
    if result['errors']:
        print("\n【错误详情】")
        for i, error in enumerate(result['errors'][:10], 1):  # 只显示前10个错误
            print(f"  {i}. {error}")
        if len(result['errors']) > 10:
            print(f"  ... 还有 {len(result['errors']) - 10} 个错误")
    
    if result['warnings']:
        print("\n【警告详情】")
        for i, warning in enumerate(result['warnings'][:10], 1):  # 只显示前10个警告
            print(f"  {i}. {warning}")
        if len(result['warnings']) > 10:
            print(f"  ... 还有 {len(result['warnings']) - 10} 个警告")
    
    print("\n【玩家统计】")
    for pos, stats in result['player_stats'].items():
        print(f"\n玩家{pos}:")
        print(f"  初始手牌数: {stats['initial_count']}")
        print(f"  出牌次数: {stats['actions_count']}")
        print(f"  打出卡牌总数: {len(stats['cards_played'])}")
        print(f"  错误数: {len(stats['errors'])}")
        print(f"  警告数: {len(stats['warnings'])}")
        
        if stats['errors']:
            print(f"  错误详情:")
            for error in stats['errors'][:3]:  # 只显示前3个错误
                print(f"    步骤{error['step']}: {error['action']}")
                missing = ', '.join(error['missing_cards'] + error['insufficient_cards'])
                print(f"      缺少卡牌: {missing}")
                print(f"      当前手牌: {error['current_hand']}")
    
    print("\n" + "=" * 80)


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        record_file = Path(sys.argv[1])
    else:
        # 默认检查最新的游戏记录
        record_dir = Path("game_records")
        if not record_dir.exists():
            print(f"错误: 游戏记录目录不存在: {record_dir}")
            return
        
        json_files = list(record_dir.glob("*.json"))
        if not json_files:
            print(f"错误: 游戏记录目录中没有JSON文件: {record_dir}")
            return
        
        # 选择最新的文件
        record_file = max(json_files, key=lambda p: p.stat().st_mtime)
        print(f"自动选择最新的游戏记录: {record_file.name}")
    
    if not record_file.exists():
        print(f"错误: 文件不存在: {record_file}")
        return
    
    # 执行检查
    result = check_game_record_consistency(record_file)
    
    # 打印报告
    print_consistency_report(result, record_file)
    
    # 返回退出码
    return 0 if result['is_consistent'] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

