#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看游戏记录的前10个动作
"""

import json
import sys

# 游戏记录文件路径
file_path = "game_records/20251202124331204250 [yf1_v5]-[opponent_1_3].json"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    actions = data['actions']
    print("前10个动作:")
    for i, action in enumerate(actions[:10]):
        print(f"{i+1}. 位置{action['cur_pos']} - {action['cur_action']}")
        print(f"   更大动作: 位置{action['greater_pos']} - {action['greater_action']}")
        print()
        
    print(f"动作总数: {len(actions)}")
except Exception as e:
    print(f"读取文件失败: {e}")
    sys.exit(1)