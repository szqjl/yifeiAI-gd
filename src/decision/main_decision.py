import sys
sys.path.append('D:\\guandanscore\\YiFeiAI-GD\\src\\decision')
from typing import Dict, List
from card_power_evaluator import calculate_card_power
from single_card_strategy import single_card_strategy
from bomb_strategy import bomb_strategy
from endgame_strategy import endgame_strategy

def main_decision(
    hand_cards: List[str],
    game_phase: str = 'mid',
    current_round: int = 1,
    opponent_rest_cards: int = 27,
    # ... other params from sub-functions
) -> Dict[str, any]:
    """
    主决策函数
    整合所有策略，返回综合建议。
    """
    # 计算牌力
    power_result = calculate_card_power(hand_cards, game_phase=game_phase, opponent_rest_cards=opponent_rest_cards)
    power = power_result['total_power']

    # 调用子策略
    single_sugg = single_card_strategy(game_phase=game_phase, power=power, opponent_rest_cards=opponent_rest_cards)  # pass relevant
    bomb_sugg = bomb_strategy(game_phase=game_phase, power=power, opponent_rest_cards=opponent_rest_cards)  # pass relevant
    has_bomb = power_result['details']['bomb_super_high'] + power_result['details']['bomb_mid'] + power_result['details']['bomb_normal'] > 0
    endgame_sugg = endgame_strategy(opponent_rest_cards=opponent_rest_cards, power=power, has_bomb=has_bomb)  # pass relevant

    return {
        'power': power_result,
        'single': single_sugg,
        'bomb': bomb_sugg,
        'endgame': endgame_sugg
    }

if __name__ == "__main__":
    test_hand = ["H3", "H4"]  # 简化
    result = main_decision(test_hand, game_phase='endgame', opponent_rest_cards=7)
    print(result)
