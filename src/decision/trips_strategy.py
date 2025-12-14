"""
三张技巧策略函数
基于《三张技巧.md》的完整知识体系
"""
from typing import Dict, List


def trips_strategy(
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
    has_pair: bool = False,  # 是否有对子
    has_straight: bool = False,  # 是否有顺子
    has_three_with_two: bool = False,  # 是否有三带二
    trips_count: int = 0,  # 三张数量
    trips_ranks: List[str] = None,  # 三张牌点列表
    has_wild_card: bool = False,  # 是否有红心配
) -> Dict[str, str]:
    """
    三张技巧决策函数
    返回三张出牌建议
    """
    action = "未知"
    reason = ""
    
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if trips_ranks is None:
        trips_ranks = []
    
    # 一、出牌技巧
    if action_type == 'Trips' or action_type == 'TRIPS':
        # 1. 手中就是"三张"牌型
        if not has_straight and not has_pair and trips_count >= 1:
            action = "手中就是三张牌型"
            reason = "基本牌型只能打三张，打出来多数有回手、甚至对手大牌控制开炸出牌。"
            return {'action': action, 'reason': reason}
        
        # 2. "三张"小，对子大
        if has_pair and action_rank in ['3', '4', '5', '6', '7', '8']:
            action = "三张小，对子大"
            reason = "让对手误以为没有对子，引起对手用大的三个头压牌，打对后遭遇出牌人大对上手。从控牌的角度说，三张上手控一牌，若出对控一手，不吃亏。"
            return {'action': action, 'reason': reason}
        
        # 3. 搅局
        if power < 5 and has_three_with_two:
            action = "搅局"
            reason = "牌不好，应该打三带二的牌，为不给对手带牌，打三张，让对手多出对子。牌力弱的三张，打出来后就不要，打对也不要。"
            return {'action': action, 'reason': reason}
        
        # 4. 拆三张
        if has_wild_card and action_rank in ['A', 'K']:
            action = "拆三张配炸"
            reason = "对子是弱项，可用三A（或三K）+红配，封对方两次大对。"
            return {'action': action, 'reason': reason}
        
        # 5. 溜牌
        if game_phase == 'endgame' and my_rest_cards <= 5:
            if has_wild_card and has_pair:
                action = "溜牌"
                reason = "下家剩两张，判断是大对，己剩1单+1对+红配，可组三个头跑溜。"
                return {'action': action, 'reason': reason}
    
    # 二、应对技巧
    if action_type == 'Trips' or action_type == 'TRIPS':
        # 1. 队友前打过三张，最后剩三张
        if is_teammate_action and teammate_rest_cards == 3:
            action = "送队友三张"
            reason = "即判一手牌。己有小三，直接送；没有三个头，又无力做上游，可用红配配小对成小三。"
            return {'action': action, 'reason': reason}
        
        # 2. 出牌顺序中大小
        if is_teammate_action and teammate_rest_cards == 3:
            if action_rank in ['3', '4', '5', '6']:
                action = "不能从最小三个头出"
                reason = "队友剩三张，不能从最小三个头出，防下家封或炸，等对手拦截再出大的三张，最后出小的三张。"
                return {'action': action, 'reason': reason}
        
        # 3. 先出三张，后有三带二
        if is_teammate_action and teammate_rest_cards == 9:
            action = "送三带二"
            reason = "队友前打三张，不是一对没有（对大或对少），如队友最后剩九张，己应直接去送三带二，送三张，队友反而多一对。"
            return {'action': action, 'reason': reason}
        
        # 4. 顶大牌拦截
        if opponent_rest_cards == 7:
            if action_rank in ['J', 'Q', 'K', 'A']:
                action = "顶大牌拦截"
                reason = "对手剩七张，恐有一炸，外加三个头，需顶大三个头，直接顶死。"
                return {'action': action, 'reason': reason}
        
        # 5. 开炸
        if opponent_rest_cards == 4 and my_rest_cards >= 5:
            action = "判三炸四"
            reason = "上家曾多次打过三张，最后剩4张，按理枪不打四，本家多两小单，此时需判三炸四，否则对方出三留单。"
            return {'action': action, 'reason': reason}
    
    # 默认建议
    if action == "未知":
        action = "根据牌局情况灵活出三张"
        reason = "三张主要用于助攻打法，破坏对手牌型。但主攻也可以使用三张，掼蛋就是这么神奇，在不同的情况下，助攻可转换成主攻。"
    
    return {'action': action, 'reason': reason}

