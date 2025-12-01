from typing import Dict, List

def bomb_strategy(
    game_phase: str = 'mid',
    power: float = 5.0,
    opponent_rest_cards: int = 27,
    opponent_action_type: str = 'none',  # e.g., 'trips', 'pair', 'straight', 'three_head'
    opponent_action_rank: int = 0,  # 牌点，如10 for 10以上
    has_better_combo: bool = False,  # 有更好牌型压
    teammate_needs_help: bool = False,
    is_critical_moment: bool = False,
    bomb_quality: str = 'normal',  # small, mid, high
    is_teammate_action: bool = False
) -> Dict[str, List[Dict[str, str]]]:
    """
    出炸弹要领决策函数
    收集匹配建议，覆盖8点要领。
    """
    suggestions = []

    # 1. 贵在及时
    if is_critical_moment:
        suggestions.append({'action': '炸（及时）', 'reason': '关键时刻炸，扭转局面。'})

    # 2. 贵在准确
    if opponent_action_type in ['straight', 'three_with_two'] and opponent_action_rank >= 10:
        suggestions.append({'action': '炸（准确）', 'reason': '针对高牌型准确炸。'})

    # 3. 贵在经济
    if has_better_combo:
        suggestions.append({'action': '不炸（经济）', 'reason': '有更好牌型压，节省炸弹。'})

    # 4. 贵在价值
    if teammate_needs_help:
        suggestions.append({'action': '炸（价值）', 'reason': '帮助队友，掩护头游。'})

    # 5. 贵在隐蔽
    if game_phase == 'opening':
        suggestions.append({'action': '不炸（隐蔽）', 'reason': '开局隐蔽实力，后发制人。'})

    # 6. 贵在顺序
    if bomb_quality == 'small':
        suggestions.append({'action': '先小后大', 'reason': '小炸先出，诱大炸。'})

    # 7. 贵在配合
    if is_teammate_action:
        suggestions.append({'action': '不炸（配合）', 'reason': '队友行动，不干扰。'})

    # 8. 盲目轻动 匹夫之勇
    if opponent_action_type == 'three_head' and opponent_action_rank < 10:
        suggestions.append({'action': '不炸（慎动）', 'reason': '对手三头间隔近，可能烂牌或管不了，等10+再炸。'})

    # 通用：牌力弱不炸
    if power < 5:
        suggestions.append({'action': '不炸（牌力弱）', 'reason': '牌力差，保留炸弹关键用。'})

    return {'suggestions': suggestions}

if __name__ == "__main__":
    result = bomb_strategy(opponent_action_type='three_head', opponent_action_rank=8)
    print(result)
