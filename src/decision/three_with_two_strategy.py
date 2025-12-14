"""
三带二技巧策略函数
基于《三带二技巧.md》的完整知识体系
"""
from typing import Dict, List


def three_with_two_strategy(
    game_phase: str = 'mid',  # opening, mid, endgame
    power: float = 5.0,
    opponent_rest_cards: int = 27,
    opponent_rest_cards_list: List[int] = None,
    teammate_rest_cards: int = 27,
    my_rest_cards: int = 27,
    is_active: bool = False,  # 是否主动出牌
    is_teammate_action: bool = False,  # 是否是队友出牌
    action_type: str = 'none',  # 当前动作类型
    action_rank: str = '',  # 当前动作牌点（三张的牌点）
    has_straight: bool = False,  # 是否有顺子
    has_bomb: bool = False,  # 是否有炸弹
    three_with_two_count: int = 0,  # 三带二数量
    three_with_two_ranks: List[str] = None,  # 三带二牌点列表
    can_change_card_type: bool = False,  # 能否改变牌型
    is_first_place_finished: bool = False,  # 头游是否已跑
    has_king: bool = False,  # 是否有王
) -> Dict[str, str]:
    """
    三带二技巧决策函数
    返回三带二出牌建议
    """
    action = "未知"
    reason = ""
    
    if opponent_rest_cards_list is None:
        opponent_rest_cards_list = [27, 27, 27]
    if three_with_two_ranks is None:
        three_with_two_ranks = []
    
    # 一、出牌策略
    if action_type == 'ThreeWithTwo' or action_type == 'THREE_WITH_TWO':
        # 1. 有打有收
        if is_active and action_rank in ['3', '4', '5', '6', '7', '8']:
            # 检查是否有更大的三带二可以回收
            if any(rank in ['9', 'T', 'J', 'Q', 'K', 'A'] for rank in three_with_two_ranks):
                action = "有打有收"
                reason = "初次打出小三带二，能够确保用大于K的三带二收回牌权。一次打出10张牌，即使最终被对手用炸抢走出牌权，消耗对手一个炸，属于不亏本的选择。"
                return {'action': action, 'reason': reason}
        
        # 2. 强牌非常多，先处理不够大的三带二
        if power >= 8 and action_rank in ['3', '4', '5', '6', '7', '8']:
            action = "先处理不够大的三带二"
            reason = "没有适合首发小牌，可以先处理掉手上不够大的三带二。迅速处理偏小牌，避免后期冲刺带来障碍。"
            return {'action': action, 'reason': reason}
        
        # 3. 相生相克反打
        if has_straight and not is_active:
            action = "相生相克反打"
            reason = "打三带二骗顺子，或打顺子骗三带二，这是当今掼蛋牌局中运用非常普遍的技巧。"
            return {'action': action, 'reason': reason}
        
        # 4. 先出大三带二夯，防对手同等大
        if game_phase == 'endgame' and my_rest_cards == 10:
            if three_with_two_count >= 2:
                if action_rank in ['J', 'Q', 'K', 'A']:
                    action = "先出大三带二夯"
                    reason = "最后剩十张，手中有两夯，对手已无炸，对手同夯大，先出大夯。"
                    return {'action': action, 'reason': reason}
        
        # 5. 反手出三带二
        if not is_active and has_bomb:
            action = "反手出三带二"
            reason = "手中有三带二，都比对手方小，等对方三带二打完，炸后反打三带二。"
            return {'action': action, 'reason': reason}
    
    # 二、应对技巧
    if action_type == 'ThreeWithTwo' or action_type == 'THREE_WITH_TWO':
        # 1. 进贡首打夯，重点要严防
        if game_phase == 'opening' and not is_teammate_action:
            action = "进贡首打夯，重点要严防"
            reason = "起手先出三带二，一般后还有三带二，先封AAA，后堵中KKK（要倒打）。"
            return {'action': action, 'reason': reason}
        
        # 2. 出相克牌型
        if not is_teammate_action and has_straight:
            action = "出相克牌型"
            reason = "三带二和顺子、对子相克，对方出夯我发顺。对方两夯到头，表明没有三带二，有可能是顺子，不轻易发小顺。"
            return {'action': action, 'reason': reason}
        
        # 3. 对手方九十张，不能出三带二
        if opponent_rest_cards in [9, 10]:
            if action_type == 'ThreeWithTwo' or action_type == 'THREE_WITH_TWO':
                action = "对手方九十张，不能出三带二"
                reason = "牌剩9张10张，有可能是三带二或者顺加一炸，出三带二有可能给对手送牌。牌剩5张，尤其不能出三带二。"
                return {'action': action, 'reason': reason}
    
    # 三、队友接应
    if action_type == 'ThreeWithTwo' or action_type == 'THREE_WITH_TWO':
        # 1. 首夯被对方封，小夯尽快送
        if is_teammate_action and teammate_rest_cards <= 10:
            action = "小夯尽快送"
            reason = "队友首次三带二被封，上手后，继续送三带二。"
            return {'action': action, 'reason': reason}
        
        # 2. 不接队友夯，留小夯送对手
        if is_teammate_action and power < 6:
            action = "不接队友夯"
            reason = "本家仅一三带二，不能上游，尽量不套，可回送队友。"
            return {'action': action, 'reason': reason}
        
        # 3. 先送大三带二
        if is_teammate_action and teammate_rest_cards == 5:
            if action_rank in ['J', 'Q', 'K', 'A']:
                action = "先送大三带二"
                reason = "队友剩五张（77722），看己去救牌。如能回三手，先送大三带二走，后送中三带二，再送小三带二，队友获上游。"
                return {'action': action, 'reason': reason}
        
        # 4. 队友九十张，尽快要送夯
        if teammate_rest_cards in [9, 10]:
            if action_type == 'ThreeWithTwo' or action_type == 'THREE_WITH_TWO':
                action = "尽快要送夯"
                reason = "队友剩五张，明显是三带二。本家有顺夯，根据下家牌型，下家牌低于5张，直接送夯。"
                return {'action': action, 'reason': reason}
        
        # 5. 队友先出三带二，强接中望差不接
        if is_teammate_action:
            if power >= 7:
                action = "可先接，稍后送"
                reason = "牌力强，可先接，稍后送。"
                return {'action': action, 'reason': reason}
            elif power < 5:
                action = "绝不套"
                reason = "牌力差，绝不套，炸对方后尽快送。"
                return {'action': action, 'reason': reason}
    
    # 残局应对
    if game_phase == 'endgame' or opponent_rest_cards <= 10:
        # 对手七张八张，出夯
        if opponent_rest_cards in [7, 8]:
            if action_type == 'ThreeWithTwo' or action_type == 'THREE_WITH_TWO':
                action = "对手七张八张，出夯"
                reason = "对手七张八张，出夯。"
                return {'action': action, 'reason': reason}
        
        # 对手剩余5、9、10张，一般不出夯
        if opponent_rest_cards in [5, 9, 10]:
            if action_type == 'ThreeWithTwo' or action_type == 'THREE_WITH_TWO':
                action = "对手剩余5、9、10张，一般不出夯"
                reason = "对手剩余5、9、10张，一般不出夯。"
                return {'action': action, 'reason': reason}
    
    # 默认建议
    if action == "未知":
        action = "根据牌局情况灵活出三带二"
        reason = "三带二速度快，且可带走对子赘牌，是最常见的组牌。情况不明，不宜先出，以免加快下家跑牌速度。"
    
    return {'action': action, 'reason': reason}

