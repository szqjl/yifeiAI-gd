"""
对子技巧策略函数
基于《对子技巧.md》的完整知识体系
"""
from typing import Dict, List


def pair_strategy(
    game_phase: str = 'mid',  # opening, mid, endgame
    power: float = 5.0,
    opponent_rest_cards: int = 27,
    opponent_rest_cards_list: List[int] = None,
    teammate_rest_cards: int = 27,
    my_rest_cards: int = 27,
    is_active: bool = False,  # 是否主动出牌
    is_teammate_action: bool = False,  # 是否是队友出牌
    greater_pos: int = -1,  # 出牌者位置
    my_pos: int = -1,  # 我的位置
    teammate_pos: int = -1,  # 队友位置
    action_type: str = 'none',  # 当前动作类型
    action_rank: str = '',  # 当前动作牌点
    has_three_with_two: bool = False,  # 是否有三带二
    has_straight: bool = False,  # 是否有顺子
    pair_count: int = 0,  # 对子数量
    pair_ranks: List[str] = None,  # 对子牌点列表
    can_form_three_pair: bool = False,  # 能否组成三连对
    can_form_straight: bool = False,  # 能否组成顺子
    is_first_place_finished: bool = False,  # 头游是否已跑
) -> Dict[str, str]:
    """
    对子技巧决策函数
    返回对子出牌建议
    """
    action = "未知"
    reason = ""
    
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if pair_ranks is None:
        pair_ranks = []
    
    # 一、情况不明，对子先行
    if game_phase == 'opening' and is_active:
        # 牌力中下，不明确对手牌力分布，先出对子试探
        if power < 6:
            action = "情况不明对子先行"
            reason = "牌力中下，不明确对手牌力分布，先出对子试探，为抓四游、防止被双上做好铺垫。"
            return {'action': action, 'reason': reason}
    
    # 二、对子使用顺序
    if action_type == 'Pair' or action_type == 'PAIR':
        # 开局出对子顺序
        if game_phase == 'opening':
            if power < 5:
                # 牌力弱，先出次中小对子，留小对子方便后期送队友
                if action_rank in ['3', '4', '5', '6', '7', '8']:
                    action = "出次中小对子"
                    reason = "牌力弱，先出次中小对子，留小对子方便后期送队友。"
                    return {'action': action, 'reason': reason}
            elif power >= 6:
                # 对子强，牌力中上，从最小对子出，方便队友送对子
                if action_rank in ['3', '4', '5']:
                    action = "出最小对子"
                    reason = "对子强，牌力中上，从最小对子出，方便队友送对子。"
                    return {'action': action, 'reason': reason}
    
    # 三、灵活运用
    if action_type == 'Pair' or action_type == 'PAIR':
        # 1. 若是多对子，出牌可顺对
        if is_teammate_action and pair_count >= 3:
            # 队友先出对，顺下中对
            action = "顺下中对"
            reason = "队友先出对，顺下中对，配合队友。"
            return {'action': action, 'reason': reason}
        
        # 2. 顶大对子
        if not is_teammate_action and greater_pos != -1:
            # 下家出对，队友顺小对子，上家让过，直接顶J、Q、K大对子
            if action_rank in ['J', 'Q', 'K']:
                action = "顶大对子"
                reason = "下家出对，队友顺小对子，上家让过，直接顶J、Q、K大对子，防止下家顺牌。"
                return {'action': action, 'reason': reason}
        
        # 3. 让对子，轻易不接队友对子
        if is_teammate_action:
            action = "让对子"
            reason = "队友主打对，上家套小对，视情可让过，下家不一定接牌，可以让队友顺一中对子。"
            return {'action': action, 'reason': reason}
        
        # 4. 封对手对子，改牌路
        if not is_teammate_action and greater_pos != -1:
            action = "封对手对子"
            reason = "对手方打对，尽量要封，牌路不对，立即封杀。"
            return {'action': action, 'reason': reason}
        
        # 5. 送对子
        if is_teammate_action and teammate_rest_cards <= 10:
            action = "送对子"
            reason = "队友出对子被封死，上手继续出对子送队友。"
            return {'action': action, 'reason': reason}
    
    # 四、残局运用
    if game_phase == 'endgame' or opponent_rest_cards <= 10:
        # 1. 逢五出对
        if opponent_rest_cards == 5:
            if action_type == 'Pair' or action_type == 'PAIR':
                action = "逢五出对"
                reason = "对手冲刺后剩5张牌时，出对就是控牌首选，不给其炸弹胜的机会。"
                return {'action': action, 'reason': reason}
        
        # 2. 逢10出对子
        if opponent_rest_cards == 10:
            if action_type == 'Pair' or action_type == 'PAIR':
                action = "逢10出对子"
                reason = "在特定情况下，逢10出对子也是有效的控牌手段。"
                return {'action': action, 'reason': reason}
        
        # 3. 一炸一夯（顺）一对子，先出小对子
        if my_rest_cards <= 10 and pair_count >= 2:
            # 判断是否有炸弹和三带二/顺子
            if action_rank in ['3', '4']:
                action = "先出小对子"
                reason = "一炸一夯（顺）一对子，先出小对子。"
                return {'action': action, 'reason': reason}
        
        # 4. 顶对子，方便队友
        if opponent_rest_cards in [6, 7]:
            if action_type == 'Pair' or action_type == 'PAIR':
                if action_rank in ['J', 'Q', 'K', 'A', '2']:
                    action = "顶大对子方便队友"
                    reason = "对方剩六七张，恐无顺或夯，判是一对加一炸，急需顶大对（不惜顶级牌对或王对），跳过此对手方，另一方抢接或加炸上游。"
                    return {'action': action, 'reason': reason}
        
        # 5. 送对
        if teammate_rest_cards == 4:
            if action_type == 'Pair' or action_type == 'PAIR':
                action = "送对"
                reason = "队友剩四张，判断是两对，要送对。"
                return {'action': action, 'reason': reason}
        
        # 6. 留对
        if my_rest_cards <= 5 and has_three_with_two:
            if action_type != 'Pair' and action_type != 'PAIR':
                action = "留对"
                reason = "上家剩一王，本家剩一小单加一中对，出单留对，靠队友炸后送最小对获上游。"
                return {'action': action, 'reason': reason}
    
    # 默认建议
    if action == "未知":
        action = "根据牌局情况灵活出对"
        reason = "对子可以组、顺、顶、让、封、逼、送、抢、拆，根据牌局情况灵活运用。"
    
    return {'action': action, 'reason': reason}

