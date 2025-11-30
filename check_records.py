# -*- coding: utf-8 -*-
import json
from pathlib import Path

record_dir = Path('game_records')
games = list(record_dir.glob('*.json'))

print('游戏记录文件:')
for g in games:
    with open(g, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'  {g.name}')
    print(f'    player_id={data.get("player_id")}, player_name={data.get("player_name")}')
    print(f'    初始手牌数量: {len(data.get("initial_hand", []))}')
    print()

