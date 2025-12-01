from typing import Dict

def endgame_strategy(
    opponent_rest_cards: int = 27,
    power: float = 5.0,
    has_pair: bool = False,
    has_trips: bool = False,
    has_straight: bool = False,
    has_three_with_two: bool = False,
    has_bomb: bool = False,
    can_press: bool = True  # 是否能压
) -> Dict[str, str]:
    """
    残局技巧决策函数
    根据对手剩牌数返回建议。
    """
    action = "未知"
    reason = ""

    if opponent_rest_cards <= 4:
        action = "不出/不炸"
        reason = "火不打四，观察或放给对家。"
    elif opponent_rest_cards == 5:
        action = "出两张"
        reason = "出对试探。"
        if not can_press:
            action = "放过给对家"
            reason = "不能压，放给对家。"
    elif opponent_rest_cards == 6:
        action = "打三张"
        reason = "剩6出三张拆牌。"
    elif opponent_rest_cards in [7, 8]:
        action = "打顺或三带二"
        reason = "剩7-8出顺/三带二。"
        if has_bomb and opponent_rest_cards == 7:
            action += " 或炸"
            reason += " 炸7不炸8，该炸还要炸。"
    elif opponent_rest_cards == 9:
        action = "打一张"
        reason = "剩9出单。"
    elif opponent_rest_cards == 10:
        action = "打两张"
        reason = "剩10出对。"
    else:
        action = "正常出牌"
        reason = "非残局，按牌力正常。"

    if power < 5:
        reason += " 牌力弱，优先放给对家。"

    return {'action': action, 'reason': reason}

if __name__ == "__main__":
    result = endgame_strategy(opponent_rest_cards=7, has_bomb=True)
    print(result)
