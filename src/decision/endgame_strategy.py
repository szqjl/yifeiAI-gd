from typing import Dict, List

def check_one_hand_finish(
    my_rest_cards: int,
    action_list: List,
    hand_cards: List,
    sorted_cards: Dict = None,
    bomb_info: Dict = None,
    rank_card: str = "H2"
) -> Dict[str, any]:
    """
    判断能否一手出完（one_hand函数逻辑）
    当剩余牌 <= 10 时，优先考虑能否一手出完
    
    返回：
    {
        'can_finish': bool,  # 能否一手出完
        'best_action_index': int,  # 最佳动作索引
        'action_type': str,  # 动作类型
        'reason': str  # 原因
    }
    """
    if my_rest_cards > 10:
        return {'can_finish': False, 'best_action_index': -1, 'action_type': '', 'reason': '剩余牌数>10，不考虑一手出完'}
    
    # 检查是否有能一手出完的动作
    for idx, action in enumerate(action_list):
        if len(action) < 3:
            continue
        
        action_type = action[0] if isinstance(action, list) else str(action)
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        
        # 如果动作牌数等于剩余牌数，说明可以一手出完
        if len(action_cards) == my_rest_cards:
            # 如果是炸弹，需要额外判断
            if action_type in ["Bomb", "BOMB", "StraightFlush"]:
                # 炸弹一手出完需要谨慎，这里先返回可以
                return {
                    'can_finish': True,
                    'best_action_index': idx,
                    'action_type': action_type,
                    'reason': f'剩余{my_rest_cards}张，可用{action_type}一手出完'
                }
            else:
                # 非炸弹一手出完，优先选择
                return {
                    'can_finish': True,
                    'best_action_index': idx,
                    'action_type': action_type,
                    'reason': f'剩余{my_rest_cards}张，可用{action_type}一手出完'
                }
    
    return {'can_finish': False, 'best_action_index': -1, 'action_type': '', 'reason': '没有能一手出完的动作'}

def endgame_strategy(
    opponent_rest_cards: int = 27,
    power: float = 5.0,
    has_pair: bool = False,
    has_trips: bool = False,
    has_straight: bool = False,
    has_three_with_two: bool = False,
    has_bomb: bool = False,
    can_press: bool = True,  # 是否能压
    opponent_rest_cards_list: list = None,  # 对手剩余牌数列表 [上家, 下家, 对家]
    is_reported_double: bool = False,  # 是否报双
    is_reported_single: bool = False,  # 是否报单
    is_first_place_finished: bool = False,  # 头游是否已跑
    my_rest_cards: int = 27,  # 自己剩余牌数
    lower_hand_rest_cards: int = 27,  # 下家剩余牌数
    action_list: List = None,  # 动作列表（用于判断能否一手出完）
    hand_cards: List = None,  # 手牌（用于判断能否一手出完）
    sorted_cards: Dict = None,  # 已组合的手牌（用于判断能否一手出完）
    bomb_info: Dict = None,  # 炸弹信息（用于判断能否一手出完）
    rank_card: str = "H2"  # 级牌（用于判断能否一手出完）
) -> Dict[str, str]:
    """
    残局技巧决策函数
    根据对手剩牌数返回建议。
    集成单张技巧中的残局规则（44-49行）：
    1. 残局忌给下家顺牌
    2. 报双.须打单诱其拆
    3. 报单.只能打非单牌型
    4. 出单倒着打
    """
    action = "未知"
    reason = ""
    
    # 初始化参数
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if action_list is None:
        action_list = []
    if hand_cards is None:
        hand_cards = []
    if sorted_cards is None:
        sorted_cards = {}
    if bomb_info is None:
        bomb_info = {}
    
    # 获取下家剩余牌数（优先使用传入的参数，否则从列表中获取）
    if len(opponent_rest_cards_list) > 1 and lower_hand_rest_cards == 27:
        lower_hand_rest_cards = opponent_rest_cards_list[1]
    
    # 优先判断：能否一手出完（one_hand函数逻辑）
    # 当剩余牌 <= 10 时，优先考虑能否一手出完
    if my_rest_cards <= 10 and len(action_list) > 0:
        one_hand_result = check_one_hand_finish(
            my_rest_cards, action_list, hand_cards, sorted_cards, bomb_info, rank_card
        )
        if one_hand_result['can_finish']:
            action = f"一手出完（{one_hand_result['action_type']}）"
            reason = one_hand_result['reason']
            return {'action': action, 'reason': reason, 'one_hand_index': one_hand_result['best_action_index']}
    
    # （四）残局出单规则（44-49行）
    # 1. 残局忌给下家顺牌，下家剩一张中单10或者单J，就差走完小单形成空炸，出小单就等于送对手一炸
    if lower_hand_rest_cards == 1:
        action = "不出小单（忌给下家顺牌）"
        reason = "下家剩一张，出小单等于送对手一炸。"
        return {'action': action, 'reason': reason}
    
    # 2. 报双.须打单诱其拆
    if is_reported_double:
        action = "打单（报双诱拆）"
        reason = "报双，须打单诱其拆。"
        return {'action': action, 'reason': reason}
    
    # 3. 报单.只能打非单牌型，自己打不完时可递送给队友接牌
    if is_reported_single:
        action = "不打单（报单打非单）"
        reason = "报单，只能打非单牌型，自己打不完时可递送给队友接牌。"
        return {'action': action, 'reason': reason}
    
    # 4. 出单倒着打。在"头游"已经跑了的情况下，剩下两家对手的时候，在对手也是单牌的情况下，可以"从大往小"打
    if is_first_place_finished and my_rest_cards > 1:
        # 判断对手是否也是单牌（简化：根据剩余牌数判断）
        if opponent_rest_cards <= my_rest_cards:
            action = "出单倒着打（从大往小）"
            reason = "头游已跑，对手也是单牌，从大往小打，切不可先打最小的那张。"
            return {'action': action, 'reason': reason}
    
    # 原有残局逻辑
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
