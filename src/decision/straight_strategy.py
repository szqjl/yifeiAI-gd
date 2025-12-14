"""
顺子技巧策略函数
基于《顺子技巧.md》的完整知识体系
"""
from typing import Dict, List


def straight_strategy(
    game_phase: str = 'mid',  # opening, mid, endgame
    power: float = 5.0,
    opponent_rest_cards: int = 27,
    opponent_rest_cards_list: List[int] = None,
    teammate_rest_cards: int = 27,
    my_rest_cards: int = 27,
    is_active: bool = False,  # 是否主动出牌
    is_teammate_action: bool = False,  # 是否是队友出牌
    action_type: str = 'none',  # 当前动作类型
    action_rank: str = '',  # 当前动作牌点
    straight_count: int = 0,  # 顺子数量
    straight_ranks: List[str] = None,  # 顺子牌点列表（最小牌点）
    has_three_with_two: bool = False,  # 是否有三带二
    has_bomb: bool = False,  # 是否有炸弹
    single_card_count: int = 0,  # 单张数量
    can_form_straight: bool = False,  # 能否组成顺子
    is_first_place_finished: bool = False,  # 头游是否已跑
    has_king: bool = False,  # 是否有王
) -> Dict[str, str]:
    """
    顺子技巧决策函数
    返回顺子出牌建议
    """
    action = "未知"
    reason = ""
    
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if straight_ranks is None:
        straight_ranks = []
    
    # 一、顺子组牌
    if action_type == 'Straight' or action_type == 'STRAIGHT':
        # 1. 顺子的组牌内单牌不应超过两张
        if single_card_count > 2:
            action = "组顺生两单，肯定没眼光"
            reason = "顺子的组牌内单牌不应超过两张，组顺生两单，肯定没眼光。"
            return {'action': action, 'reason': reason}
    
    # 二、顺子出牌技巧
    if action_type == 'Straight' or action_type == 'STRAIGHT':
        # 1. 牌弱先出顺，牌强后出顺
        if is_active:
            if power < 5:
                action = "牌弱先出顺"
                reason = "牌较弱，考虑先出顺子，以减手牌数量。"
                return {'action': action, 'reason': reason}
            elif power >= 7 and straight_count == 1:
                action = "牌强后出顺"
                reason = "牌强只有一手小顺子是不宜先出，出去容易被对手接手，等到接近残局阶段，看牌局情况再决定什么时候打出。"
                return {'action': action, 'reason': reason}
        
        # 2. 小顺往前凑，大顺必殿后
        if straight_count >= 2:
            # 判断当前顺子大小（通过action_rank判断）
            if action_rank in ['3', '4', '5', '6', '7', '8']:
                action = "小顺往前凑"
                reason = "牌中有多个顺子，先出较小的顺子，小顺子用于牵制对手，保留大顺子以应对后续的牌局变化。"
                return {'action': action, 'reason': reason}
            elif action_rank in ['9', 'T', 'J', 'Q', 'K', 'A']:
                action = "大顺必殿后"
                reason = "牌中有多个顺子，保留大顺子以应对后续的牌局变化。"
                return {'action': action, 'reason': reason}
        
        # 3. 顺子多了有点累，单张多了活受罪
        if straight_count >= 3 and single_card_count >= 5:
            action = "顺子多了有点累"
            reason = "顺子虽好，却不能贪多。组顺后手中单张过多，需要高牌来收回牌权，极大地消耗了牌力。"
            return {'action': action, 'reason': reason}
        
        # 4. 谁打谁收
        if is_teammate_action:
            action = "谁打谁收"
            reason = "先顺后夯还有顺，先夯后顺还有夯。队友先出顺子，一般不要接。"
            return {'action': action, 'reason': reason}
        
        # 5. 后发制对手
        if not is_teammate_action and has_bomb:
            action = "后发制对手"
            reason = "对手方出顺，也有两把顺，都比对手方小，等对方顺打完，炸后反出顺。"
            return {'action': action, 'reason': reason}
        
        # 6. 送顺先送中顺
        if is_teammate_action and teammate_rest_cards <= 10:
            if action_rank in ['6', '7', '8', '9', 'T']:
                action = "送顺先送中顺"
                reason = "队友要顺，己有小顺可即送。如能回手，先送中顺，后救小顺，防下家顶。"
                return {'action': action, 'reason': reason}
    
    # 三、顺子的应对技巧
    if action_type == 'Straight' or action_type == 'STRAIGHT':
        # 1. 顺子管到头，对手没想头
        if action_rank in ['T', 'J', 'Q', 'K', 'A']:
            action = "顺子管到头"
            reason = "出最大的顺子（如10JQKA）可以有效压制对手，逼炸或放弃出牌。"
            return {'action': action, 'reason': reason}
        
        # 2. 枪打头一顺
        if is_active and not is_teammate_action:
            action = "枪打头一顺"
            reason = "当对手首次出顺子时，应立即用更强的牌型进行压制，以阻断对手的出牌节奏。"
            return {'action': action, 'reason': reason}
        
        # 3. 一般不接队友小顺
        if is_teammate_action:
            if action_rank in ['3', '4', '5', '6', '7', '8']:
                if power < 5:
                    action = "绝不接队友小顺"
                    reason = "牌力差，绝不接，炸对方尽快送。"
                    return {'action': action, 'reason': reason}
                elif power >= 6:
                    action = "可不接队友小顺"
                    reason = "牌力强，可不接，稍后送。"
                    return {'action': action, 'reason': reason}
    
    # 四、顺子残局运用
    if game_phase == 'endgame' or opponent_rest_cards <= 10:
        # 1. 尽量不留最后一手顺
        if my_rest_cards <= 5 and action_type == 'Straight':
            action = "尽量不留最后一手顺"
            reason = "尽量不留最后一手顺，这也是最难有变换的牌型。"
            return {'action': action, 'reason': reason}
        
        # 2. 七张八张，打顺打夯
        if opponent_rest_cards in [7, 8]:
            if action_type == 'Straight' or action_type == 'STRAIGHT':
                action = "七张八张，打顺打夯"
                reason = "对手剩七张或者八张牌，主动打顺子。"
                return {'action': action, 'reason': reason}
        
        # 3. 九张十张，不出顺夯
        if opponent_rest_cards in [9, 10]:
            if action_type == 'Straight' or action_type == 'STRAIGHT':
                action = "九张十张，不出顺夯"
                reason = "对手剩九张或者10张牌，不要主动打顺子。"
                return {'action': action, 'reason': reason}
        
        # 4. 明牌留大王不留顺，队友好送牌
        if my_rest_cards <= 5 and has_king:
            if action_type == 'Straight' or action_type == 'STRAIGHT':
                action = "明牌留大王不留顺"
                reason = "己剩两手牌，一王加中顺。顺、王都为大，先出顺，留明王，队友好送牌。"
                return {'action': action, 'reason': reason}
        
        # 5. 接队友报听后小顺
        if is_teammate_action and teammate_rest_cards <= 5:
            if action_type == 'Straight' or action_type == 'STRAIGHT':
                if action_rank in ['3', '4', '5', '6', '7']:
                    action = "接队友报听后小顺"
                    reason = "队友炸后倒数第二手，放一小顺，明显剩炸，本家有顺要抢接。"
                    return {'action': action, 'reason': reason}
    
    # 默认建议
    if action == "未知":
        action = "根据牌局情况灵活出顺"
        reason = "顺子技巧：牌弱先出顺，牌强后出顺；小顺往前凑，大顺必殿后；谁打谁收。"
    
    return {'action': action, 'reason': reason}

