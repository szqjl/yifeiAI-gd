#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看增强回放文件的前15个动作
"""

import json
import sys

# 增强回放文件路径
file_path = "game_records/enhanced_20251124T224003.json"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    actions = data['actions']
    print("前15个动作:")
    for i, action in enumerate(actions[:15]):
        cur_pos = action.get('cur_pos', -1)
        cur_action = action.get('cur_action', '[]')
        greater_pos = action.get('greater_pos', -1)
        greater_action = action.get('greater_action', '[]')
        print(f"{i+1}. 位置{cur_pos} - {cur_action}")
        print(f"   更大动作: 位置{greater_pos} - {greater_action}")
        print()
        
    print(f"动作总数: {len(actions)}")
except Exception as e:
    print(f"读取文件失败: {e}")
    sys.exit(1)