# -*- coding: utf-8 -*-
"""
分析M1开局炸弹问题
"""

import json
from pathlib import Path

# 加载游戏记录
record_file = Path("game_records/20251222205430146644 [yf2_m1]-[opponent_1_3]-[15]-[None].json")
with open(record_file, 'r', encoding='utf-8') as f:
    game_data = json.load(f)

print("="*60)
print("M1开局炸弹问题分析")
print("="*60)

# 初始手牌
initial_hand = game_data.get("initial_hand", [])
print(f"\n初始手牌（27张）: {initial_hand}")
print(f"初始手牌数量: {len(initial_hand)}")

# 分析前3个动作（都是炸弹）
actions = game_data.get("actions", [])
print(f"\n前3个动作（都是yf2_m1的炸弹）:")

for i, action in enumerate(actions[:3]):
    if action.get("cur_pos") == 2:  # yf2_m1是2号位
        cur_action = action.get("cur_action", [])
        if len(cur_action) >= 3:
            action_type = cur_action[0]
            rank = cur_action[1]
            cards = cur_action[2]
            print(f"\n动作{i+1}: {action_type} {rank}")
            print(f"  使用的牌: {cards}")
            
            # 检查这些牌是否在初始手牌中
            missing_cards = []
            for card in cards:
                if card not in initial_hand:
                    missing_cards.append(card)
            
            if missing_cards:
                print(f"  ⚠️  警告：以下牌不在初始手牌中: {missing_cards}")
                print(f"  可能原因：拆了其他牌来组成炸弹")
            else:
                print(f"  ✓ 所有牌都在初始手牌中")

# 分析初始手牌中的炸弹组合
print(f"\n初始手牌中的炸弹组合分析:")
from collections import Counter

# 按牌值分组
rank_counts = Counter()
for card in initial_hand:
    rank = card[1:] if len(card) > 1 else card
    rank_counts[rank] += 1

print(f"牌值分布: {dict(rank_counts)}")

# 找出可能的炸弹组合
possible_bombs = []
for rank, count in rank_counts.items():
    if count >= 4:
        possible_bombs.append((rank, count))
        print(f"  ⚠️  发现{count}张{rank}，可以组成炸弹")

if not possible_bombs:
    print("  ✓ 初始手牌中没有完整的炸弹组合")

# 分析第一个炸弹为什么用了HA
print(f"\n第一个炸弹分析:")
first_bomb = actions[0].get("cur_action", [])
if len(first_bomb) >= 3:
    bomb_cards = first_bomb[2]
    print(f"  炸弹牌: {bomb_cards}")
    print(f"  炸弹类型: {first_bomb[0]} {first_bomb[1]}")
    
    # 检查是否拆了牌
    for card in bomb_cards:
        if card not in initial_hand:
            print(f"  ⚠️  {card}不在初始手牌中，说明拆了其他牌")
        else:
            print(f"  ✓ {card}在初始手牌中")

print("\n" + "="*60)
print("分析完成")
print("="*60)

