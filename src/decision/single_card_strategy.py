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
    just_bombed: bool = False,
    single_card_count: int = 0,  # 单张数量
    bomb_count: int = 0,  # 炸弹数量
    has_straight_or_three_with_two: bool = False,  # 有顺子或三带二
    is_upper_hand: bool = False,  # 是否上家出单（顺上家）
    opponent_not_accept_small_single: bool = False,  # 对手不接小单牌
    teammate_rest_cards: int = 27,  # 队友剩余牌数
    is_active: bool = False,  # 是否主动出牌
    single_card_ranks: list = None,  # 单张牌点列表，用于判断高单/中单/低单
    opponent_rest_cards_list: list = None,  # 对手剩余牌数列表 [上家, 下家, 对家]
    teammate_rest_cards_detail: int = 27,  # 队友剩余牌数详情
    opponent_has_single: bool = False,  # 对手是否有单张（从历史记录判断）
    opponent_straight_history: list = None,  # 对手出顺子历史，用于猜测单牌大小
    teammate_straight_history: list = None,  # 队友出顺子历史，用于送单
    is_first_place_finished: bool = False,  # 头游是否已跑
    my_rest_cards: int = 27,  # 自己剩余牌数
    is_reported_double: bool = False,  # 是否报双
    is_reported_single: bool = False  # 是否报单
) -> Dict[str, str]:
    """
    单张技巧决策函数
    根据牌局情况返回出单建议
    """
    action = "未知"
    reason = ""

    # 初始化参数
    if single_card_ranks is None:
        single_card_ranks = []
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if opponent_straight_history is None:
        opponent_straight_history = []
    if teammate_straight_history is None:
        teammate_straight_history = []
    
    # （四）残局出单（44-49行）
    # 残局优先 (opponent_rest_cards <=10)
    if game_phase == 'endgame' or opponent_rest_cards <= 10:
        # 1. 残局忌给下家顺牌，下家剩一张中单10或者单J，就差走完小单形成空炸
        # 获取下家剩余牌数（简化：假设opponent_rest_cards_list[1]是下家）
        if len(opponent_rest_cards_list) > 1:
            lower_hand_rest = opponent_rest_cards_list[1]
            if lower_hand_rest == 1:
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
        # 1. 有王有级牌，单张有保护、能回手
        if has_king or has_level_card:
            action = "起始出单（有保护）"
            reason = "有王/级牌保护，能回手。"
        # 2. 有两个以上的炸弹，其他轮次可套，单张是最难处理的轮次
        elif bomb_count >= 2:
            action = "出单（多炸保护）"
            reason = "有两个+炸弹，单张难处理，先出。"
        # 3. 单张特别多，几乎除了炸弹就是单
        elif single_card_count >= 8:
            action = "出单（单张多）"
            reason = "单张特别多，几乎除了炸弹就是单，先出单。"
        # 4. 吃双贡获得牌权后出单
        elif is_double_tribute and is_active:
            if has_king:
                action = "出单（进贡大王）"
                reason = "进贡大王，对家可接。"
            else:
                action = "出单（双贡后）"
                reason = "吃双贡获得牌权后出单。"
        # 5. 手中有一炸，外加一顺（夯），还有两单张，要先出一单
        elif bomb_count >= 1 and has_straight_or_three_with_two and single_card_count >= 2:
            action = "出单（一炸一顺两单）"
            reason = "手中有一炸，外加一顺（夯），还有两单张，要先出一单。"
        # 6. 顺上家出单（上家是朋友）
        elif is_upper_hand:
            action = "顺上家出单"
            reason = "上家的单牌，对自己有利，上家是朋友。"
        else:
            action = "不出单"
            reason = "双贡不出单，暂缓走。"

    elif game_phase == 'mid':
        # 1. 前期炸掉后不要立刻出小单张
        if just_bombed:
            action = "不出小单"
            reason = "前期炸后不立刻出小单，等于送对手一炸。"
        # 2. 对手不接小单牌，打完一轮接着来
        elif opponent_not_accept_small_single:
            action = "继续出小单"
            reason = "对手不接小单牌，继续出小单压迫对手。"
        # 3. 控下家单牌（卡小）
        elif opponent_needs_single:
            action = "控下家单（卡小）"
            reason = "卡下家小单，防顺/过牌。首用Q，次用JK。"
        # 4. 让对家出单（送小单）
        elif teammate_needs_single:
            if teammate_rest_cards == 1:
                action = "送小单（队友剩一张）"
                reason = "队友只剩一张牌，放心出小单。"
            else:
                action = "让对家出单（送小单）"
                reason = "对家需要，送小单让他出尽。"
        # 5. 顺子出中间
        elif has_straight:
            action = "顺子出中间"
            reason = "出顺中间单，减少轮次。"
        # 6. 没有单牌拆大对，下家套牌没机会
        elif not has_pair_above_q:
            action = "不出（无单拆大对）"
            reason = "无单拆大对，下家无套牌机会。"
        else:
            action = "拆大对出单"
            reason = "无单时拆大对（如Q+）出，卡下家小单。"

    # （二）出那张单牌（32-37行）
    # 如果已经确定了要出单，进一步判断出高单/中单/低单
    if "出单" in action or "打一张" in action:
        # 判断单牌优势（简化：根据牌力、炸弹数量、单张数量判断）
        has_single_advantage = (power >= 7 and bomb_count >= 2) or (is_double_tribute and power >= 6)
        
        # 1. 高单出牌：双吃贡，单牌优势，挡住下家的中低单
        if has_single_advantage and is_double_tribute:
            action = "出高单（挡住下家中低单）"
            reason = "双吃贡，单牌优势，通过高单挡住下家的中低单而使对家能轻松取得优先出牌权。若出中低单让下家过中低单，相当于送给下家一个炸弹。"
        # 2. 低单出牌：传牌给对家，下家不吃单牌时
        elif not has_single_advantage or (opponent_not_accept_small_single and teammate_needs_single):
            if teammate_rest_cards == 1:
                action = "出低单（队友剩一张）"
                reason = "队友只剩一张牌，放心出小单。敌方明知守不住时，也可能放弃防守。"
            elif opponent_not_accept_small_single and teammate_needs_single:
                action = "出低单（传牌给对家）"
                reason = "下家不吃单牌，对家需要过单牌。单3单4都可以随意出，可以拆对4和对5来给下家造成困扰。"
            else:
                action = "出低单（传牌）"
                reason = "我方不具备明显单牌优势，低单传牌给对家。"
        # 3. 中单出牌：水闸，试探性，打上家、卡下家
        elif power >= 5 and power < 7:
            action = "出中单（水闸试探）"
            reason = "牌力中等，中单相当于一道'水闸'，打上家、卡下家，既防住了下家的中低单，又给对家过单牌的机会，切忌从小顺着出。"
        # 默认：根据具体情况选择
        else:
            if has_single_advantage:
                action = "出高单（单牌优势）"
                reason = "单牌优势，出高单挡住下家的中低单。"
            else:
                action = "出中单（试探）"
                reason = "牌力一般，出中单试探。"
    
    # （三）卡点出单牌（38-43行）
    # 1. 对家和下家都只剩一张牌，发级牌
    if opponent_rest_cards_list and len(opponent_rest_cards_list) >= 3:
        teammate_rest = opponent_rest_cards_list[2] if len(opponent_rest_cards_list) > 2 else 27
        lower_hand_rest = opponent_rest_cards_list[1] if len(opponent_rest_cards_list) > 1 else 27
        if teammate_rest == 1 and lower_hand_rest == 1 and has_level_card and is_active:
            action = "卡点出单（发级牌）"
            reason = "对家和下家都只剩一张牌，发级牌完美放走对家。"
            return {'action': action, 'reason': reason}
    
    # 2. 从出顺子来猜测单牌的大小
    if opponent_straight_history:
        # 如果对手出过小顺子，他手里大概率还有一张小单牌要过
        for straight in opponent_straight_history:
            if isinstance(straight, list) and len(straight) >= 2:
                straight_rank = straight[1] if len(straight) > 1 else ""
                if straight_rank in ['3', '4', '5', '6', '7']:
                    action = "出单防守（大于顺子最大点）"
                    reason = f"对手出过{straight_rank}以下的小顺子，手里大概率还有一张{straight_rank}以下的单牌要过，出单张防守至少要大于{straight_rank}。"
                    break
    
    # 3. 从队友出顺子来送单
    if teammate_straight_history and teammate_needs_single:
        for straight in teammate_straight_history:
            if isinstance(straight, list) and len(straight) >= 2:
                straight_rank = straight[1] if len(straight) > 1 else ""
                if straight_rank in ['5', '6', '7', '8', '9']:
                    action = "送小单（队友顺子）"
                    reason = f"队友出过{straight_rank}以下的顺子，送单张就要从小单张送起，队友可能要过{straight_rank}以下的小单张。"
                    break
    
    # 通用：去单化、算单
    if power < 5:
        action = "不出小单（牌力差）"
        reason = "牌力差，留小单耗下家牌力，保对家。不要出8以下的小单张。"
    
    return {'action': action, 'reason': reason}

if __name__ == "__main__":
    # 测试示例
    result = single_card_strategy(game_phase='endgame', opponent_rest_cards=5, has_pair_above_q=False)
    print(result)
