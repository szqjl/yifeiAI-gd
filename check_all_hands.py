# -*- coding: utf-8 -*-
"""
检查所有玩家的初始手牌
"""

import json
import sys
from pathlib import Path

# 设置路径
script_dir = Path(__file__).parent.absolute()
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

# 获取最新的游戏记录文件
record_dir = script_dir / "game_records"
games = list(record_dir.glob("*.json"))
if not games:
    print("未找到游戏记录文件")
    sys.exit(1)

# 使用最新的文件
latest_game = max(games, key=lambda x: x.stat().st_mtime)

print(f"检查游戏记录: {latest_game.name}")
print("=" * 80)

# 加载游戏记录
with open(latest_game, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n【记录信息】")
print(f"玩家ID: {data.get('player_id')}")
print(f"玩家名称: {data.get('player_name')}")
print(f"初始手牌数量: {len(data.get('initial_hand', []))}")
print(f"初始手牌: {data.get('initial_hand', [])}")

# 检查第一个动作的context，看是否有其他玩家的信息
print(f"\n【第一个动作的Context】")
first_action = data.get('actions', [])[0] if data.get('actions') else None
if first_action:
    context = first_action.get('context', {})
    print(f"Context keys: {list(context.keys())}")
    
    public_info = context.get('publicInfo', [])
    print(f"\npublicInfo 长度: {len(public_info)}")
    if public_info:
        for i, info in enumerate(public_info):
            print(f"  玩家{i}的publicInfo: {info}")
    
    # 检查是否有restCards信息
    if 'restCards' in context:
        print(f"\nrestCards: {context.get('restCards')}")

# 检查所有动作，看能否推断出其他玩家的手牌
print(f"\n【分析所有玩家的出牌】")
player_cards_played = {0: [], 1: [], 2: [], 3: []}
actions = data.get('actions', [])

for action in actions:
    cur_pos = action.get('cur_pos', -1)
    cur_action = action.get('cur_action', [])
    
    # 解析cur_action
    if isinstance(cur_action, str):
        try:
            import ast
            cur_action = ast.literal_eval(cur_action)
        except:
            continue
    
    if not cur_action or (isinstance(cur_action, list) and len(cur_action) == 0):
        continue
    
    if isinstance(cur_action, list) and cur_action[0] == "PASS":
        continue
    
    # 提取出的牌
    if isinstance(cur_action, list) and len(cur_action) > 2:
        cards = cur_action[2]
        if cards:
            if isinstance(cards, list):
                for c in cards:
                    if isinstance(c, str):
                        player_cards_played[cur_pos].append(c)
                    elif isinstance(c, list) and len(c) >= 2:
                        player_cards_played[cur_pos].append(f"{c[0]}{c[1]}")
            elif isinstance(cards, str):
                player_cards_played[cur_pos].append(cards)

print(f"\n【各玩家出的牌统计】")
for pos in range(4):
    cards = player_cards_played[pos]
    from collections import Counter
    card_counts = Counter(cards)
    print(f"\n{pos}号位出了 {len(cards)} 张牌:")
    print(f"  牌型统计: {dict(card_counts)}")
    if 'D6' in cards:
        print(f"  ⚠ 包含D6！")

print(f"\n【2号位初始手牌 vs 出的牌】")
initial_hand = set(data.get('initial_hand', []))
played_cards = set(player_cards_played[2])
print(f"初始手牌: {sorted(initial_hand)}")
print(f"出的牌: {sorted(played_cards)}")
print(f"交集: {sorted(initial_hand & played_cards)}")
print(f"初始手牌中但没出的: {sorted(initial_hand - played_cards)}")
print(f"出了但不在初始手牌的: {sorted(played_cards - initial_hand)}")

