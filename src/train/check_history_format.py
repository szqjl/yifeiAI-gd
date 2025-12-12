# -*- coding: utf-8 -*-
"""检查history数据格式"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset

# 加载数据
parser = ReplayParser("game_records")
replays = parser.load_replays()
raw_data = parser.extract_training_data(replays)

if len(raw_data) == 0:
    print("没有数据")
    exit(1)

dataset = GuandanDataset(raw_data)

# 找到有history的样本
for i in range(min(100, len(dataset))):
    state_dict, action_cards = dataset.data[i]
    if 'history' in state_dict and state_dict['history']:
        print(f"\n样本 {i}:")
        print(f"  history长度: {len(state_dict['history'])}")
        print(f"  第一个历史动作: {state_dict['history'][0]}")
        if len(state_dict['history']) > 1:
            print(f"  第二个历史动作: {state_dict['history'][1]}")
        break

