#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从对战日志中提取每一局所有玩家的初始手牌信息
"""

import re

def extract_all_hands():
    """提取所有玩家的初始手牌"""
    
    with open('yfscore/yfscore/yfv4_vs_lalala', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 存储每一局的手牌信息
    games = []
    current_game = {}
    
    for i, line in enumerate(lines):
        # 匹配格式: "游戏开始, 我是X号位，手牌：[...]"
        if '游戏开始' in line and '手牌' in line:
            # 提取位置
            pos_match = re.search(r'我是(\d)号位', line)
            if pos_match:
                pos = int(pos_match.group(1))
                
                # 提取手牌部分（从"手牌：["到行末的"]"）
                hand_match = re.search(r'手牌：\[(.*)\]', line)
                if hand_match:
                    cards_str = hand_match.group(1)
                    
                    # 解析手牌
                    cards = []
                    for card_match in re.finditer(r"\['([SHCD])',\s*'([A2-9TJQKBR])'\]", cards_str):
                        cards.append((card_match.group(1), card_match.group(2)))
                    
                    if len(cards) == 27:  # 确保是完整的27张牌
                        current_game[pos] = cards
                        print(f"找到 {pos}号位的手牌（行{i+1}）")
            
            # 如果收集齐4个玩家的手牌，保存这一局
            if len(current_game) == 4:
                games.append(current_game.copy())
                current_game = {}
    
    # 打印结果
    print(f"找到 {len(games)} 局游戏的完整手牌信息\n")
    print("=" * 80)
    
    for game_idx, game in enumerate(games, 1):
        print(f"\n第 {game_idx} 局游戏初始手牌：")
        print("-" * 80)
        
        for pos in sorted(game.keys()):
            cards = game[pos]
            print(f"\n{pos}号位初始手牌（{len(cards)}张）：")
            print(f"  {sorted(cards, key=lambda x: (x[1], x[0]))}")
            
            # 统计牌值分布
            from collections import Counter
            rank_count = Counter([c[1] for c in cards])
            print(f"  牌值统计：{dict(rank_count)}")
    
    # 如果只有部分玩家的手牌（比如只有lalala客户端打印了）
    if current_game:
        print(f"\n未完成的游戏（只有部分玩家手牌）：")
        for pos in sorted(current_game.keys()):
            cards = current_game[pos]
            print(f"  {pos}号位：{len(cards)}张")

if __name__ == '__main__':
    extract_all_hands()

