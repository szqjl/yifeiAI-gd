"""
钢板技巧策略函数
基于《钢板技巧.md》的完整知识体系
"""
from typing import Dict, List


def two_trips_strategy(
    game_phase: str = 'mid',  # opening, mid, endgame
    power: float = 5.0,
    opponent_rest_cards: int = 27,
    opponent_rest_cards_list: List[int] = None,
    teammate_rest_cards: int = 27,
    my_rest_cards: int = 27,
    is_active: bool = False,  # 是否主动出牌
    is_teammate_action: bool = False,  # 是否是队友出牌
    action_type: str = 'none',  # 当前动作类型
    action_rank: str = '',  # 当前动作牌点（最小三张的牌点）
    has_three_with_two: bool = False,  # 是否有三带二
    has_bomb: bool = False,  # 是否有炸弹
    two_trips_count: int = 0,  # 钢板数量
    two_trips_ranks: List[str] = None,  # 钢板牌点列表
    pair_count: int = 0,  # 对子数量
    trips_count: int = 0,  # 三张数量
    has_wild_card: bool = False,  # 是否有红心配
) -> Dict[str, str]:
    """
    钢板技巧决策函数
    返回钢板出牌建议
    """
    action = "未知"
    reason = ""
    
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if two_trips_ranks is None:
        two_trips_ranks = []
    
    # 一、钢板技巧
    if action_type == 'TwoTrips' or action_type == 'TWO_TRIPS':
        # 1. 牌力中等，小钢板先出
        if 5 <= power < 7:
            if action_rank in ['3', '4', '5', '6', '7']:
                action = "牌力中等，小钢板先出"
                reason = "没有上手机会的牌型，小钢板早点出，打出后可能会继续取得出牌权，即便对手接，也可能破坏了牌型。"
                return {'action': action, 'reason': reason}
        
        # 2. 牌力很差，小钢板不出
        if power < 5:
            action = "牌力很差，小钢板不出"
            reason = "留着给队友送桥。钢板出就是6张牌，避免对手走的快。"
            return {'action': action, 'reason': reason}
        
        # 3. 牌力强，小钢板后出
        if power >= 7:
            if action_rank in ['3', '4', '5', '6', '7']:
                action = "牌力强，小钢板后出"
                reason = "但要避免憋在手上，最后没机会上手出。对手不好防范阻击，产生的威胁越大，至少可以逼对手先开炸从而消耗其牌力。"
                return {'action': action, 'reason': reason}
        
        # 4. 拆分小钢板，传牌给队友
        if is_teammate_action and has_three_with_two:
            if action_rank in ['3', '4', '5', '6', '7']:
                action = "拆分小钢板，传牌给队友"
                reason = "当推断出队友手上有比较大的三带二，可以将小钢板拆成一个三带二和一个单张，顺利传牌给队友，增强队友的出牌能力。"
                return {'action': action, 'reason': reason}
        
        # 5. 引炸策略
        if game_phase == 'endgame' and my_rest_cards == 11:
            action = "引炸策略"
            reason = "在牌局的末段，获得牌权时一次打出6张牌，迅速减少手牌数量，可以让对手误以为你即将冲刺头游，从而慌乱出炸。"
            return {'action': action, 'reason': reason}
        
        # 6. 本家有小钢板，另有两个3同张，4个以上对子
        if two_trips_count >= 1 and trips_count >= 2 and pair_count >= 4:
            action = "放弃出钢板，组三带二"
            reason = "应放弃出钢板，直接组出四个三带二，既带走小对，又减少手数。"
            return {'action': action, 'reason': reason}
        
        # 7. 红配变钢板
        if game_phase == 'endgame' and my_rest_cards == 6 and has_wild_card:
            action = "红配变钢板"
            reason = "最后剩六张（AAA22+红配），判对方有一五头炸，可一手跑光。"
            return {'action': action, 'reason': reason}
    
    # 二、应对技巧
    if action_type == 'TwoTrips' or action_type == 'TWO_TRIPS':
        # 1. 直接管压
        if not is_teammate_action and is_active:
            if action_rank in ['J', 'Q', 'K', 'A']:
                action = "直接管压"
                reason = "对方首引小钢板，有现牌大钢板，可直接压，不宜开始即用红配配压（少一炸）。"
                return {'action': action, 'reason': reason}
        
        # 2. 不接队友钢板
        if is_teammate_action:
            if power < 5:
                action = "不接队友钢板，留着送队友"
                reason = "如队友首引小钢板，下家出管压，一般也不要顺接，谁打谁收。己若牌力差，留着送队友。"
                return {'action': action, 'reason': reason}
            elif power >= 7:
                action = "照顾队友"
                reason = "牌力强，照顾队友。除非差这手，顺过能头游，可接队友钢板。"
                return {'action': action, 'reason': reason}
        
        # 3. 对手出小钢板被封，自己小钢板暂时不出
        if not is_teammate_action and not is_active:
            if action_rank in ['3', '4', '5', '6', '7']:
                action = "对手出小钢板被封，自己小钢板暂时不出"
                reason = "防止对手还有钢板。"
                return {'action': action, 'reason': reason}
    
    # 默认建议
    if action == "未知":
        action = "根据牌局情况灵活出钢板"
        reason = "钢板是特殊牌型，队友不宜管压，但是队友也不易传牌。避免憋在手上，最后没机会上手出就可惜。"
    
    return {'action': action, 'reason': reason}

