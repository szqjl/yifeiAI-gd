"""
三连对技巧策略函数
基于《三连对技巧.md》的完整知识体系
"""
from typing import Dict, List


def three_pair_strategy(
    game_phase: str = 'mid',  # opening, mid, endgame
    power: float = 5.0,
    opponent_rest_cards: int = 27,
    opponent_rest_cards_list: List[int] = None,
    teammate_rest_cards: int = 27,
    my_rest_cards: int = 27,
    is_active: bool = False,  # 是否主动出牌
    is_teammate_action: bool = False,  # 是否是队友出牌
    action_type: str = 'none',  # 当前动作类型
    action_rank: str = '',  # 当前动作牌点（最小对子的牌点）
    has_straight: bool = False,  # 是否有顺子
    has_bomb: bool = False,  # 是否有炸弹
    three_pair_count: int = 0,  # 三连对数量
    three_pair_ranks: List[str] = None,  # 三连对牌点列表
    has_three_with_two: bool = False,  # 是否有三带二
    has_wild_card: bool = False,  # 是否有红心配
    is_first_place_finished: bool = False,  # 头游是否已跑
) -> Dict[str, str]:
    """
    三连对技巧决策函数
    返回三连对出牌建议
    """
    action = "未知"
    reason = ""
    
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if three_pair_ranks is None:
        three_pair_ranks = []
    
    # 一、木板技巧
    if action_type == 'ThreePair' or action_type == 'THREE_PAIR':
        # 1. 首引一般不轻易出木板
        if game_phase == 'opening' and is_active:
            if 5 <= power < 7:
                action = "首引一般不轻易出木板"
                reason = "进贡方，牌力中，但不一定下游，首引一般不轻易出木板。首引木板，对手会变化牌型来进行阻击。后面打出来，对手用变牌来进行防范可能性变小，产生威胁变大，达到先逼对手开炸目的。"
                return {'action': action, 'reason': reason}
        
        # 2. 不接队友木板
        if is_teammate_action:
            if power < 5:
                action = "不接队友木板，留着送队友"
                reason = "队友首引木板，手中即便有木板，一般也不要顺接。己若牌力差，留着送队友。除非差这手，顺过能头游，可接队友木板。"
                return {'action': action, 'reason': reason}
            elif power >= 7:
                action = "照顾队友"
                reason = "牌力强，照顾队友。除非差这手，顺过能头游，可接队友木板。"
                return {'action': action, 'reason': reason}
        
        # 3. 木板直接封到顶
        if not is_teammate_action and is_active:
            if action_rank in ['J', 'Q', 'K']:
                action = "木板直接封到顶"
                reason = "对方首引小木板，本家有1010JJQQKK，要封就封大JJQQKK，防对方回手JJQQKK压。"
                return {'action': action, 'reason': reason}
        
        # 4. 送队友木板
        if is_teammate_action and teammate_rest_cards <= 10:
            action = "送队友木板"
            reason = "队友首引木板曾被对方封或炸，队友最后剩六张，可能还是木板。本家可用百搭配5，组445566送队友。"
            return {'action': action, 'reason': reason}
        
        # 5. 诱骗炸弹
        if game_phase == 'endgame' and my_rest_cards == 11:
            action = "诱骗炸弹"
            reason = "贡牌方，上游没希望，最后11张，忽出木板，急报剩5张杂牌，骗对手炸弹，方便队友走牌。"
            return {'action': action, 'reason': reason}
        
        # 6. 利用特殊牌型摆尾
        if game_phase == 'endgame' and my_rest_cards == 7:
            action = "利用特殊牌型摆尾"
            reason = "尾牌剩七张木板加一张，如7788999，恐对方有大三带二，判对方已无炸，可出木板，留单9上游。"
            return {'action': action, 'reason': reason}
        
        # 7. 故意牌摆偷跑
        if game_phase == 'endgame' and my_rest_cards == 6:
            action = "故意牌摆偷跑"
            reason = "手工牌我方出牌后剩6张，左5右1张，或者上4下2，对方看牌背面不是一手牌，犹豫没有炸，偷机跑溜。"
            return {'action': action, 'reason': reason}
    
    # 二、改变牌型组木板阻对手
    if action_type != 'ThreePair' and action_type != 'THREE_PAIR':
        # 1. 拆三带二组成木板阻对手
        if has_three_with_two and not is_teammate_action:
            action = "拆三带二组成木板阻对手"
            reason = "对方首引223344，己可组99101010JJ，多单10。"
            return {'action': action, 'reason': reason}
        
        # 2. 变顺为木板
        if has_straight and not is_teammate_action:
            action = "变顺为木板"
            reason = "对方首出顺，被队友炸，己原有两把小顺，可变一至两个木板。"
            return {'action': action, 'reason': reason}
        
        # 3. 变木板为顺
        if three_pair_count >= 2 and not is_teammate_action:
            action = "变木板为顺"
            reason = "对方首出木板，被队友炸，己有两个小木板，可变两把小顺。也可配合队友牌型变换。"
            return {'action': action, 'reason': reason}
    
    # 默认建议
    if action == "未知":
        action = "根据牌局情况灵活出三连对"
        reason = "三连对（木板）出牌速度快，一次可以出6张牌，有效减少牌的手数，达到快跑目的。首引一般不轻易出木板，后面打出来，威胁更大。"
    
    return {'action': action, 'reason': reason}

