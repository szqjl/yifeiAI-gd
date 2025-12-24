#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析回放系统问题
检查回放系统是否正确加载和显示卡牌
"""

import json
import sys
from pathlib import Path

def analyze_replay_issue(game_file: str):
    """分析回放系统问题"""
    with open(game_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    player_id = data.get("player_id", 2)
    initial_hand = data.get("initial_hand", [])
    all_players_hands = data.get("all_players_hands", {})
    
    print(f"=== 回放系统问题分析 ===")
    print(f"玩家ID: {player_id}")
    print(f"\n1. initial_hand (当前玩家初始手牌):")
    print(f"   数量: {len(initial_hand)}")
    print(f"   8的分布: S8={initial_hand.count('S8')}, H8={initial_hand.count('H8')}, C8={initial_hand.count('C8')}, D8={initial_hand.count('D8')}")
    print(f"   所有8: {[c for c in initial_hand if c.endswith('8')]}")
    
    print(f"\n2. all_players_hands (所有玩家手牌):")
    print(f"   包含的玩家: {list(all_players_hands.keys())}")
    
    for pos, hand in all_players_hands.items():
        print(f"\n   玩家 {pos}:")
        print(f"     数量: {len(hand)}")
        print(f"     8的分布: S8={hand.count('S8')}, H8={hand.count('H8')}, C8={hand.count('C8')}, D8={hand.count('D8')}")
        print(f"     所有8: {[c for c in hand if c.endswith('8')]}")
    
    # 检查回放系统可能的问题
    print(f"\n3. 回放系统可能的问题:")
    
    # 问题1: all_players_hands是否包含所有玩家
    if len(all_players_hands) < 4:
        print(f"   [问题1] all_players_hands只包含{len(all_players_hands)}个玩家，回放系统可能无法正确显示其他玩家的手牌")
    
    # 问题2: 检查当前玩家的手牌是否一致
    player_id_str = str(player_id)
    if player_id_str in all_players_hands:
        recorded_hand = all_players_hands[player_id_str]
        if sorted(initial_hand) != sorted(recorded_hand):
            print(f"   [问题2] initial_hand和all_players_hands[{player_id_str}]不一致！")
            print(f"      initial_hand: {sorted(initial_hand)}")
            print(f"      all_players_hands[{player_id_str}]: {sorted(recorded_hand)}")
        else:
            print(f"   [OK] initial_hand和all_players_hands[{player_id_str}]一致")
    
    # 问题3: 检查第二步动作
    actions = data.get("actions", [])
    print(f"\n4. 检查第二步动作（yf2的首发）:")
    for i, action in enumerate(actions):
        cur_pos = action.get("cur_pos", -1)
        if cur_pos == player_id and i == 1:  # 第二步（索引1）
            cur_action = action.get("cur_action", [])
            print(f"   步骤 {i+1}: 位置{cur_pos} 打出 {cur_action}")
            if isinstance(cur_action, list) and len(cur_action) >= 3:
                action_cards = cur_action[2]
                print(f"   动作中的卡牌: {action_cards}")
                print(f"   8的分布: S8={action_cards.count('S8')}, H8={action_cards.count('H8')}, C8={action_cards.count('C8')}, D8={action_cards.count('D8')}")
                if 'D8' in action_cards:
                    print(f"   [ERROR] 动作中包含D8，但初始手牌中没有D8！")
                elif 'C8' in action_cards:
                    print(f"   [OK] 动作中包含C8，初始手牌中有C8")
            break
    
    # 问题4: 检查回放系统如何加载初始手牌
    print(f"\n5. 回放系统加载逻辑分析:")
    print(f"   回放系统会从以下来源加载初始手牌:")
    print(f"   a) initial_hand -> initial_hands[str(player_id)]")
    print(f"   b) all_players_hands -> initial_hands[str(pos)] for each pos")
    print(f"   如果all_players_hands中缺少某个玩家，回放系统会使用空列表")
    print(f"   这可能导致回放系统显示的手牌与实际不符")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python analyze_replay_issue.py <game_record_file>")
        sys.exit(1)
    
    game_file = sys.argv[1]
    analyze_replay_issue(game_file)

