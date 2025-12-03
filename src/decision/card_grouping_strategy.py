"""
组牌策略模块
根据组牌技巧文档，评估动作的组牌效果
"""
from typing import Dict, List, Tuple
from collections import Counter


def evaluate_grouping_effect(hand_cards: List[str], action_cards: List[str], 
                             action_type: str, game_phase: str, power: float, 
                             cur_rank: str = "2") -> Dict:
    """
    评估动作的组牌效果
    
    组牌原则：
    1. 轮次优先：轮次越少越好
    2. 单牌越少越好
    3. 炸弹越多越好
    4. 保持牌型可控性和可变性
    5. 组同花顺原则：如果组了同花顺多余两个小单张，非必要不组。如果2是级牌，那可以组。只多余1个小单张3。
    
    Args:
        cur_rank: 当前级牌（如"2"），用于判断是否可以组同花顺
    
    Returns:
        {
            'score': 组牌评分,
            'reasons': [原因列表],
            'rounds_reduced': 减少的轮次数,
            'singles_reduced': 减少的单牌数
        }
    """
    if not hand_cards or not action_cards:
        return {'score': 0, 'reasons': [], 'rounds_reduced': 0, 'singles_reduced': 0}
    
    score = 0.0
    reasons = []
    rounds_reduced = 0
    singles_reduced = 0
    
    # 计算剩余手牌
    remaining_cards = hand_cards.copy()
    for card in action_cards:
        if card in remaining_cards:
            remaining_cards.remove(card)
    
    # 统计剩余手牌
    rank_count = Counter()
    for card in remaining_cards:
        if len(card) >= 2:
            rank = card[1] if len(card) == 2 else card[1:2]
            rank_count[rank] += 1
    
    # 统计动作执行前的单牌数（估算）
    original_rank_count = Counter()
    for card in hand_cards:
        if len(card) >= 2:
            rank = card[1] if len(card) == 2 else card[1:2]
            original_rank_count[rank] += 1
    original_singles = sum(1 for count in original_rank_count.values() if count == 1)
    
    # 1. 评估轮次减少（组牌第一原则）
    # 如果动作能减少轮次（如三带对、顺子等），加分
    if action_type in ["THREE_WITH_TWO", "Straight", "STRAIGHT"]:
        # 三带对或普通顺子可以减少轮次
        if len(action_cards) >= 5:
            rounds_reduced = 1
            score += 30.0
            reasons.append("减少轮次")
    # 同花顺特殊处理：不鼓励第一轮主动打出
    elif action_type == "StraightFlush":
        if len(action_cards) >= 5:
            rounds_reduced = 1
            # 减少轮次加分，但主动出牌时大幅降低同花顺优先级
            score += 10.0  # 普通顺子加30分，同花顺只加10分
            reasons.append("减少轮次（同花顺）")
    
    # 2. 评估单牌减少（组牌第一原则）
    # 统计剩余单牌数（在动作执行后）
    remaining_singles_after = sum(1 for count in rank_count.values() if count == 1)
    
    # 统计剩余小单张数（2-9，不包括级牌）
    # 如果2是级牌，则不算小单张；如果2不是级牌，则算小单张
    remaining_small_singles = []
    for rank, count in rank_count.items():
        if count == 1:
            if rank == "2":
                # 如果2不是级牌，算小单张
                if cur_rank != "2":
                    remaining_small_singles.append(rank)
            elif rank in ['3', '4', '5', '6', '7', '8', '9']:
                remaining_small_singles.append(rank)
    
    remaining_small_singles_count = len(remaining_small_singles)
    
    # 如果动作能消除单牌（如组成顺子、三带对），加分
    if action_type in ["Straight", "STRAIGHT", "StraightFlush"]:
        # 顺子可以消除多个单牌
        if len(action_cards) >= 5:
            # 估算消除的单牌数
            singles_reduced = max(0, original_singles - remaining_singles_after)
            if singles_reduced > 0:
                score += 20.0 * min(singles_reduced, 3)  # 最多加60分
                reasons.append(f"消除{singles_reduced}个单牌")
    
    # 2.1. 组同花顺特殊规则：如果组了同花顺多余两个小单张，非必要不组
    # 规则：如果组了同花顺多余两个小单张，非必要不组。如果2是级牌，那可以组。只多余1个小单张3。
    if action_type == "StraightFlush":
        # 检查是否拆了炸弹（通过检查原始手牌中是否有4个或5个相同点数的牌）
        original_bomb_ranks = [rank for rank, count in original_rank_count.items() if count >= 4]
        remaining_bomb_ranks = [rank for rank, count in rank_count.items() if count >= 4]
        bomb_broken = len(original_bomb_ranks) > len(remaining_bomb_ranks)
        
        # 无论是否拆炸弹，只要组了同花顺后多余两个小单张，且2不是级牌，则减分
        if remaining_small_singles_count >= 2:
            if cur_rank != "2":  # 2不是级牌
                score -= 50.0  # 大幅减分，不建议组
                if bomb_broken:
                    reasons.append(f"组同花顺拆炸多余{remaining_small_singles_count}个小单张（{','.join(remaining_small_singles)}），且2不是级牌，不建议组")
                else:
                    reasons.append(f"组同花顺多余{remaining_small_singles_count}个小单张（{','.join(remaining_small_singles)}），且2不是级牌，不建议组")
            else:
                # 2是级牌，可以组，但只多余1个小单张3时更优
                if remaining_small_singles_count > 1:
                    score -= 20.0  # 轻微减分
                    reasons.append(f"组同花顺多余{remaining_small_singles_count}个小单张（{','.join(remaining_small_singles)}），2是级牌可组但非最优")
                else:
                    reasons.append(f"组同花顺多余1个小单张（{','.join(remaining_small_singles)}），2是级牌，可以组")
    
    if action_type == "THREE_WITH_TWO":
        # 三带对可以消除1个单牌（三头）和1个对子
        score += 15.0
        reasons.append("三带对减少手数")
    
    # 3. 评估炸弹保留（炸弹越多越好）
    # 如果动作不是炸弹，且保留炸弹，加分
    if action_type != "Bomb" and action_type != "BOMB" and action_type != "StraightFlush":
        # 检查是否保留了炸弹
        bomb_ranks = [rank for rank, count in rank_count.items() if count >= 4]
        if bomb_ranks:
            score += 10.0 * len(bomb_ranks)
            reasons.append(f"保留{len(bomb_ranks)}个炸弹")
    
    # 4. 开局阶段：优先组牌
    if game_phase == "opening":
        # 开局优先减少轮次和单牌
        if rounds_reduced > 0 or singles_reduced > 0:
            score += 15.0
            reasons.append("开局优化组牌")
    
    # 5. 主攻角色：轮次优先
    if power >= 8:  # 强牌，可能是主攻
        if rounds_reduced > 0:
            score += 20.0
            reasons.append("主攻减少轮次")
    
    # 6. 助攻角色：保留炸弹
    if power < 5:  # 弱牌，可能是助攻
        bomb_ranks = [rank for rank, count in rank_count.items() if count >= 4]
        if bomb_ranks:
            score += 15.0
            reasons.append("助攻保留炸弹")
    
    # 7. 惩罚：产生过多单牌的动作
    if action_type == "Single" and remaining_singles_after > 5:
        score -= 10.0
        reasons.append("产生过多单牌")
    
    return {
        'score': score,
        'reasons': reasons,
        'rounds_reduced': rounds_reduced,
        'singles_reduced': singles_reduced
    }


def grouping_strategy(hand_cards: List[str], action_list: List, 
                     game_phase: str, power: float, cur_rank: str = "2") -> Dict:
    """
    组牌策略主函数
    
    为每个动作评估组牌效果，返回建议
    
    Args:
        cur_rank: 当前级牌（如"2"），用于判断是否可以组同花顺
    
    Returns:
        {
            'suggestions': [(action_index, score, reason), ...]
        }
    """
    suggestions = []
    
    for idx, action in enumerate(action_list):
        if not action or len(action) == 0:
            continue
        
        action_type = action[0] if isinstance(action, list) else str(action)
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        
        # 评估组牌效果
        grouping_result = evaluate_grouping_effect(
            hand_cards, action_cards, action_type, game_phase, power, cur_rank
        )
        
        # 即使评分为负，也记录建议（用于警告）
        suggestions.append({
            'action_index': idx,
            'score': grouping_result['score'],
            'reasons': grouping_result['reasons'],
            'rounds_reduced': grouping_result['rounds_reduced'],
            'singles_reduced': grouping_result['singles_reduced']
        })
    
    return {'suggestions': suggestions}

