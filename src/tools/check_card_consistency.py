#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
卡牌一致性检查工具
检查游戏记录中卡牌的一致性，特别是：
1. 初始手牌中的卡牌
2. 出牌动作中的卡牌
3. 回放系统显示的卡牌
"""

import json
import sys
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple

def check_card_consistency(game_file: str):
    """检查游戏记录中的卡牌一致性"""
    with open(game_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 获取初始手牌
    initial_hand = data.get("initial_hand", [])
    all_players_hands = data.get("all_players_hands", {})
    player_id = data.get("player_id", 2)
    
    print(f"=== 卡牌一致性检查 ===")
    print(f"游戏ID: {data.get('game_id', 'unknown')}")
    print(f"玩家ID: {player_id}")
    print(f"\n初始手牌 ({len(initial_hand)}张):")
    initial_counts = Counter(initial_hand)
    for card, count in sorted(initial_counts.items()):
        print(f"  {card}: {count}张")
    
    # 检查所有动作
    actions = data.get("actions", [])
    print(f"\n=== 检查所有动作 ===")
    
    # 跟踪当前手牌（从初始手牌开始）
    current_hand = initial_hand.copy()
    current_hand_counts = Counter(current_hand)
    
    issues = []
    
    for i, action in enumerate(actions):
        cur_pos = action.get("cur_pos", -1)
        cur_action = action.get("cur_action", [])
        
        # 只检查yf玩家的动作
        if cur_pos != player_id:
            continue
        
        # 提取动作中的卡牌
        action_cards = []
        if isinstance(cur_action, list):
            if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                action_cards = cur_action[2]
            elif all(isinstance(card, str) for card in cur_action):
                action_cards = cur_action
        
        if not action_cards or cur_action[0] == "PASS":
            continue
        
        # 检查卡牌一致性
        action_counts = Counter(action_cards)
        
        # 检查每张卡牌是否在当前手牌中
        for card, count in action_counts.items():
            if card not in current_hand_counts:
                issues.append({
                    "step": i + 1,
                    "action": cur_action,
                    "card": card,
                    "count": count,
                    "issue": f"卡牌 {card} 不在当前手牌中",
                    "current_hand": current_hand.copy()
                })
            elif current_hand_counts[card] < count:
                issues.append({
                    "step": i + 1,
                    "action": cur_action,
                    "card": card,
                    "count": count,
                    "available": current_hand_counts[card],
                    "issue": f"卡牌 {card} 需要 {count} 张，但手牌中只有 {current_hand_counts[card]} 张",
                    "current_hand": current_hand.copy()
                })
        
        # 更新当前手牌（移除已出的卡牌）
        for card in action_cards:
            if card in current_hand:
                current_hand.remove(card)
        current_hand_counts = Counter(current_hand)
        
        print(f"\n步骤 {i + 1}: 位置{cur_pos} 打出 {cur_action[0]} {cur_action[1] if len(cur_action) > 1 else ''}")
        print(f"  卡牌: {action_cards}")
        print(f"  剩余手牌数: {len(current_hand)}")
    
    # 报告问题
    if issues:
        print(f"\n=== 发现 {len(issues)} 个卡牌一致性问题 ===")
        for issue in issues:
            print(f"\n步骤 {issue['step']}:")
            print(f"  动作: {issue['action']}")
            print(f"  问题: {issue['issue']}")
            print(f"  当前手牌: {sorted(issue['current_hand'])}")
    else:
        print(f"\n[OK] 未发现卡牌一致性问题")
    
    # 检查初始手牌中的8
    print(f"\n=== 检查8的分布 ===")
    eights = [card for card in initial_hand if card.endswith('8')]
    print(f"初始手牌中的8: {sorted(eights)}")
    print(f"  S8: {eights.count('S8')}张")
    print(f"  H8: {eights.count('H8')}张")
    print(f"  C8: {eights.count('C8')}张")
    print(f"  D8: {eights.count('D8')}张")
    
    # 检查所有动作中的8
    print(f"\n=== 检查所有动作中的8 ===")
    for i, action in enumerate(actions):
        cur_pos = action.get("cur_pos", -1)
        cur_action = action.get("cur_action", [])
        
        if cur_pos != player_id:
            continue
        
        action_cards = []
        if isinstance(cur_action, list):
            if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                action_cards = cur_action[2]
        
        eights_in_action = [card for card in action_cards if card.endswith('8')]
        if eights_in_action:
            print(f"步骤 {i + 1}: 位置{cur_pos} 打出8: {eights_in_action}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python check_card_consistency.py <game_record_file>")
        sys.exit(1)
    
    game_file = sys.argv[1]
    check_card_consistency(game_file)

