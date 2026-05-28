#!/usr/bin/env python3
"""
简化版数据加载器测试
用于验证Stage 7训练系统的数据格式兼容性
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'knowledge_processor'))

from src.knowledge_processor.replay_parser import ReplayParser
import json
import numpy as np
from pathlib import Path

def test_simple_data_loading():
    """测试简化版数据加载"""
    print("=== 简化版数据加载器测试 ===")
    
    # 1. 测试ReplayParser
    print("\n1. 测试ReplayParser...")
    parser = ReplayParser("game_records")
    
    # 加载少量游戏记录进行测试
    replays = []
    json_files = list(Path("game_records").glob("*.json"))[:5]  # 只测试前5个文件
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'player_id' in data and 'actions' in data:
                replays.append(data)
                print(f"  加载游戏记录: {json_file.name}")
        except Exception as e:
            print(f"  跳过文件 {json_file}: {e}")
    
    print(f"  总共加载了 {len(replays)} 个游戏记录")
    
    # 2. 提取训练数据
    print("\n2. 提取训练数据...")
    training_data = parser.extract_training_data(replays)
    print(f"  提取了 {len(training_data)} 个训练样本")
    
    if len(training_data) > 0:
        # 检查前几个样本
        print("\n3. 检查样本格式...")
        for i, (state_dict, action_cards) in enumerate(training_data[:3]):
            print(f"  样本 {i+1}:")
            print(f"    状态字典键: {list(state_dict.keys())}")
            print(f"    动作卡牌: {action_cards}")
            print(f"    策略类型: {state_dict.get('strategy_type', 'N/A')}")
            
            # 尝试转换为向量
            try:
                state_vec = simple_state_to_vector(state_dict)
                action_vec = simple_action_to_vector(action_cards)
                print(f"    状态向量长度: {len(state_vec)}")
                print(f"    动作向量长度: {len(action_vec)}, 动作数量: {sum(action_vec)}")
            except Exception as e:
                print(f"    向量转换失败: {e}")
    
    return len(training_data) > 0

def simple_state_to_vector(state_dict):
    """简化版状态向量转换"""
    # 创建512维向量
    vector = [0.0] * 512
    
    # 手牌信息（前54维）
    hand_cards = state_dict.get('hand', [])
    card_mapping = get_simple_card_mapping()
    
    for card in hand_cards:
        if card in card_mapping:
            idx = card_mapping[card]
            if idx < 54:
                vector[idx] = 1.0
    
    # 游戏阶段
    game_phase = state_dict.get('game_phase', 1)
    if 54 + game_phase < 512:
        vector[54 + game_phase] = 1.0
    
    return vector

def simple_action_to_vector(action_cards):
    """简化版动作向量转换"""
    # 创建512维向量
    vector = [0] * 512
    
    card_mapping = get_simple_card_mapping()
    
    for card in action_cards:
        if card in card_mapping:
            idx = card_mapping[card]
            if idx < 512:
                vector[idx] = 1
    
    return vector

def get_simple_card_mapping():
    """获取简化版卡牌映射"""
    cards = []
    
    # 标准52张牌
    suits = ['C', 'D', 'H', 'S']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    
    for suit in suits:
        for rank in ranks:
            cards.append(suit + rank)
    
    # 大小王
    cards.extend(['HR', 'BR'])
    
    return {card: idx for idx, card in enumerate(cards)}

if __name__ == "__main__":
    success = test_simple_data_loading()
    if success:
        print("\n✅ 简化版数据加载测试成功！")
        print("可以继续进行Stage 7训练系统的开发。")
    else:
        print("\n❌ 简化版数据加载测试失败！")
        print("需要进一步调试数据格式问题。")