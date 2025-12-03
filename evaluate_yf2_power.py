#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估yf2_v5的手牌牌力
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.decision.card_power_evaluator import calculate_card_power

def evaluate_yf2_power():
    """评估yf2_v5的手牌牌力"""
    # yf2_v5的手牌
    yf2_hand = [
        "C2", "D2", "D2", "D3", "H4", "H4", "S5", "S5", "C6", 
        "S7", "D7", "S8", "H8", "H8", "C8", "D8", "S9", "H9", 
        "CT", "DT", "SJ", "SJ", "CQ", "HK", "DK", "CA", "HR"
    ]
    
    # 调用牌力计算函数
    result = calculate_card_power(
        hand_cards=yf2_hand,
        game_phase='opening',  # 开局阶段
        cur_level_rank=10,      # 默认级牌
        opponent_rest_cards=27  # 开局阶段对手剩余牌数
    )
    
    print("yf2_v5手牌牌力评估结果:")
    print("=" * 60)
    print(f"总牌力: {result['total_power']}")
    print(f"牌力等级: {result['grade']}")
    print(f"建议角色: {result['suggested_role']}")
    print("=" * 60)
    print("牌力详情:")
    for key, value in result['details'].items():
        print(f"  {key}: {value}")
    print("=" * 60)
    
    return result

if __name__ == "__main__":
    evaluate_yf2_power()