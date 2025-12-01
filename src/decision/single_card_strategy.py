from typing import Dict

def single_card_strategy(
    game_phase: str = 'mid',  # opening, mid, endgame
    power: float = 5.0,
    opponent_rest_cards: int = 27,
    has_bomb: bool = False,
    has_king: bool = False,
    has_level_card: bool = False,
    has_pair_above_q: bool = False,
    has_straight: bool = False,
    is_double_tribute: bool = False,
    teammate_needs_single: bool = False,
    opponent_needs_single: bool = False,
    just_bombed: bool = False
) -> Dict[str, str]:
    """
    单张技巧决策函数
    根据牌局情况返回出单建议
    """
    action = "未知"
    reason = ""

    # 残局优先 (opponent_rest_cards <=10)
    if game_phase == 'endgame' or opponent_rest_cards <= 10:
        if opponent_rest_cards <= 4:
            action = "不出（火不打四）"
            reason = "对手剩<=4张，一般不炸/出单，观察或放给对家。"
        elif opponent_rest_cards == 5:
            if not has_pair_above_q:
                action = "放过给对家"
                reason = "不能压，放给对家处理。"
            else:
                action = "出两张（对子）"
                reason = "出对试探，若不能压放给对家。"
        elif opponent_rest_cards == 6:
            action = "打三张"
            reason = "剩6可出三张拆牌型。"
        elif opponent_rest_cards in [7, 8]:
            if has_straight:
                action = "打顺"
                reason = "剩7-8出顺或三带二。"
            elif has_bomb and opponent_rest_cards == 7:
                action = "考虑炸"
                reason = "炸7不炸8，但该炸还要炸。"
            else:
                action = "打三带二"
                reason = "剩7-8出三带二。"
        elif opponent_rest_cards == 9:
            action = "打一张（单张）"
            reason = "剩9出单。"
        elif opponent_rest_cards == 10:
            action = "打两张（对子）"
            reason = "剩10出对。"
        return {'action': action, 'reason': reason}

    # 开局/中期
    if game_phase == 'opening':
        if has_king or has_level_card:
            action = "起始出单（有保护）"
            reason = "有王/级牌保护，能回手。"
        elif has_bomb and power >= 5:
            action = "出单（多炸保护）"
            reason = "有两个+炸弹，单张难处理，先出。"
        elif is_double_tribute and has_king:
            action = "出单（进贡大王）"
            reason = "进贡大王，对家可接。"
        else:
            action = "不出单"
            reason = "双贡不出单，暂缓走。"

    elif game_phase == 'mid':
        if just_bombed:
            action = "不出小单"
            reason = "前期炸后不立刻出小单，等于送对手一炸。"
        elif opponent_needs_single:
            action = "控下家单（卡小）"
            reason = "卡下家小单，防顺/过牌。"
        elif teammate_needs_single:
            action = "让对家出单（送小单）"
            reason = "对家需要，送小单让他出尽。"
        elif has_straight:
            action = "顺子出中间"
            reason = "出顺中间单，减少轮次。"
        elif not has_pair_above_q:
            action = "不出（无单拆大对）"
            reason = "无单拆大对，下家无套牌机会。"
        else:
            action = "拆大对出单"
            reason = "无单时拆大对（如Q+）出，卡下家小单。"

    # 通用：去单化、算单
    if power < 5:
        action = "不出小单（牌力差）"
        reason = "牌力差，留小单耗下家牌力，保对家。"
    
    return {'action': action, 'reason': reason}

if __name__ == "__main__":
    # 测试示例
    result = single_card_strategy(game_phase='endgame', opponent_rest_cards=5, has_pair_above_q=False)
    print(result)
