"""
组牌策略模块
根据组牌技巧文档，评估动作的组牌效果
"""
from typing import Dict, List, Tuple, Union
from collections import Counter


def _int_to_card_code(card_id: int) -> str:
    """将game_engine中的整数索引转换为卡牌代码字符串"""
    if card_id == 52:
        return 'B'  # 小王
    elif card_id == 53:
        return 'R'  # 大王
    else:
        # 0-51: 4个花色，每个花色13张牌
        # 0-12: Spades (S), 13-25: Hearts (H), 26-38: Clubs (C), 39-51: Diamonds (D)
        suit_idx = card_id // 13
        rank_idx = card_id % 13
        suit_map = {0: 'S', 1: 'H', 2: 'C', 3: 'D'}
        rank_map = {
            0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8', 7: '9',
            8: 'T', 9: 'J', 10: 'Q', 11: 'K', 12: 'A'
        }
        suit = suit_map.get(suit_idx, 'S')
        rank = rank_map.get(rank_idx, '2')
        return f"{suit}{rank}"


def _normalize_cards(cards: List[Union[str, int]]) -> List[str]:
    """将卡牌列表标准化为字符串格式"""
    normalized = []
    for card in cards:
        if isinstance(card, int):
            normalized.append(_int_to_card_code(card))
        else:
            normalized.append(str(card))
    return normalized


def evaluate_grouping_effect(hand_cards: List[Union[str, int]], action_cards: List[Union[str, int]], 
                             action_type: str, game_phase: str, power: float, 
                             cur_rank: str = "2", my_rest_cards: int = 27, 
                             opponent_rest_cards: int = 27, is_teammate_action: bool = False) -> Dict:
    """
    评估动作的组牌效果
    
    组牌最高准则：
    0. 胜负规则优先：掼蛋的胜负规则就是谁最先出完手牌，因此开局组牌时，应尽可能降低手数，减少出完牌的轮次，轮次越少、出牌越快，也就越容易获得头游。
    
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
    
    # 标准化卡牌格式（将整数转换为字符串）
    hand_cards = _normalize_cards(hand_cards)
    action_cards = _normalize_cards(action_cards)
    
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
    
    # 判断是否有王或级牌
    has_king = any('B' in card or 'R' in card for card in hand_cards)
    has_level_card = any(cur_rank in card for card in hand_cards)
    
    # 有王或级牌保护时，单张策略更优
    if action_type == "Single" or action_type == "SINGLE":
        if has_king or has_level_card:
            # 有王/级牌保护，单张能回收，增加评分
            score += 30.0
            reasons.append("有王/级牌保护，单张能回收，优先出单")
    # 1. 评估轮次减少（组牌第一原则，体现胜负规则优先准则）
    # 如果动作能减少轮次（如三带对、顺子等），大幅加分
    elif action_type in ["THREE_WITH_TWO", "Straight", "STRAIGHT"]:
        # 三带对或普通顺子可以减少轮次
        if len(action_cards) >= 5:
            rounds_reduced = 1
            score += 45.0  # 增加轮次减少的权重，体现胜负规则优先
            reasons.append("减少轮次（胜负规则优先）")
    # 同花顺特殊处理：不鼓励第一轮主动打出
    elif action_type == "StraightFlush":
        if len(action_cards) >= 5:
            rounds_reduced = 1
            # 减少轮次加分，但主动出牌时降低同花顺优先级
            score += 15.0  # 增加同花顺的轮次减少权重
            reasons.append("减少轮次（同花顺，胜负规则优先）")
    
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
    
    # 检查是否拆了炸弹
    original_bomb_ranks = [rank for rank, count in original_rank_count.items() if count >= 4]
    remaining_bomb_ranks = [rank for rank, count in rank_count.items() if count >= 4]
    bomb_broken = len(original_bomb_ranks) > len(remaining_bomb_ranks)
    
    if action_type == "THREE_WITH_TWO":
        # 三带对可以消除1个单牌（三头）和1个对子
        if bomb_broken:
            # 拆了炸弹组三带二，给予大幅减分
            score -= 80.0  # 拆炸弹的代价远大于三带二的收益
            reasons.append("拆炸弹组三带二，代价过大，不建议")
        else:
            score += 15.0
            reasons.append("三带对减少手数")
    
    # 检查是否使用了红桃配（百搭牌，红心级牌 = H + cur_rank）
    has_wild_card = False
    red_heart_wildcard = f"H{cur_rank}"  # 红心级牌（逢人配、百搭）
    for card in action_cards:
        if isinstance(card, str) and card.startswith(red_heart_wildcard):
            has_wild_card = True
            break
    
    # 3. 评估炸弹保留（炸弹越多越好）
    # 如果动作不是炸弹，且保留炸弹，加分
    if action_type != "Bomb" and action_type != "BOMB" and action_type != "StraightFlush":
        # 检查是否保留了炸弹
        bomb_ranks = [rank for rank, count in rank_count.items() if count >= 4]
        if bomb_ranks:
            score += 10.0 * len(bomb_ranks)
            reasons.append(f"保留{len(bomb_ranks)}个炸弹")
    
    # 4. 红桃配（百搭牌）策略：红心配炸弹留到最后再使用，初期保留
    # 核心原则：首配4头和同花，可配6头，忌配5头。实战中逢人配成炸比例为85%。
    # 禁止用红心配组小顺子（浪费百搭牌价值）
    if has_wild_card:
        if action_type in ["Bomb", "BOMB"]:
            if game_phase in ["early", "mid"]:
                # 初期/中期使用红桃配炸弹，给予减分
                score -= 30.0
                reasons.append("红桃配炸弹留到最后再使用，初期保留")
        elif action_type in ["Straight", "STRAIGHT"]:
            # **关键修复**：用红心配组顺子，特别是小顺子，大幅减分
            # 检查顺子大小（通过action_cards数量判断，5张顺子通常较小）
            if len(action_cards) == 5:
                # 小顺子（5张），用红心配组小顺子浪费百搭牌价值
                score -= 80.0  # 大幅减分（从-20提升到-80）
                reasons.append(f"核心规则：禁止用红心配组小顺子，浪费百搭牌价值（应保留用于炸弹或关键组合）")
            else:
                # 长顺子，也减分但力度稍小
                score -= 50.0
                reasons.append("红心配组顺子，应优先用于炸弹或同花顺")
        elif action_type == "StraightFlush":
            # 同花顺可以接受，但初期仍减分
            if game_phase == "early":
                score -= 30.0
                reasons.append("初期用红心配组同花顺，建议保留到关键时机")
        elif action_type in ["ThreePair", "THREE_PAIR"]:
            # **配木板（三连对）策略**：根据牌力和阶段判断
            # 知识库：1. 主攻减少手数（33、4、55补成木板，减少2手赘牌）
            #         2. 助攻尽量组成木板不要出，保留多种牌型
            if power >= 7:  # 主攻（牌力强）
                if game_phase == "endgame" or my_rest_cards <= 10:
                    # 残局阶段，主攻配木板减少手数，可以接受
                    score -= 20.0  # 轻微减分，允许但非最优
                    reasons.append("残局主攻用红心配组木板减少手数，可接受但非最优（应优先配炸）")
                else:
                    # 非残局阶段，主攻配木板，减分但力度较小
                    score -= 50.0
                    reasons.append("主攻用红心配组木板减少手数，但应优先保留用于配炸")
            else:  # 助攻（牌力弱）
                # 助攻尽量组成木板不要出，保留多种牌型，所以配木板可以接受
                if game_phase == "endgame":
                    # 残局助攻配木板，可以接受
                    score -= 15.0
                    reasons.append("残局助攻用红心配组木板保留牌型，可接受")
                else:
                    # 非残局助攻配木板，保留牌型，减分较小
                    score -= 30.0
                    reasons.append("助攻用红心配组木板保留牌型，可接受但应优先配炸")
        elif action_type in ["TwoTrips", "TWO_TRIPS"]:
            # **配钢板策略**：主要是主攻减少手数，或者避免对手压制，或者逼对手炸弹
            if power >= 7:  # 主攻（牌力强）
                if game_phase == "endgame" or my_rest_cards <= 10:
                    # 残局阶段，主攻配钢板减少手数或逼炸，可以接受
                    score -= 25.0
                    reasons.append("残局主攻用红心配组钢板减少手数/逼炸，可接受但非最优")
                else:
                    # 非残局阶段，主攻配钢板，减分
                    score -= 60.0
                    reasons.append("主攻用红心配组钢板，应优先保留用于配炸")
            else:  # 助攻（牌力弱）
                # 助攻配钢板，减分较大
                if game_phase == "endgame":
                    score -= 40.0
                    reasons.append("残局助攻用红心配组钢板，不推荐（应优先配炸）")
                else:
                    score -= 70.0
                    reasons.append("助攻用红心配组钢板，不推荐（应优先配炸或保留）")
        elif action_type in ["ThreeWithTwo", "THREE_WITH_TWO"]:
            # **配三带二策略**：根据牌力和阶段判断
            # 知识库：1. 减少手数，便于争上游（小对子多，一下出两手）
            #         2. 手中就剩5张牌，恰好三带二直接走牌
            #         3. 管压对手三带二
            #         4. 送队友
            if my_rest_cards == 5:
                # 手中就剩5张牌，恰好三带二直接走牌，可以接受
                score -= 15.0  # 轻微减分，允许
                reasons.append("残局剩5张用红心配组三带二直接走牌，可接受")
            elif game_phase == "endgame" or my_rest_cards <= 10:
                # 残局阶段，配三带二减少手数
                if power >= 7:  # 主攻
                    score -= 20.0
                    reasons.append("残局主攻用红心配组三带二减少手数，可接受但非最优")
                else:  # 助攻
                    score -= 30.0
                    reasons.append("残局助攻用红心配组三带二，不推荐（应优先配炸）")
            else:
                # 非残局阶段，配三带二不推荐
                if power >= 7:  # 主攻
                    score -= 60.0
                    reasons.append("主攻用红心配组三带二，应优先保留用于配炸")
                else:  # 助攻
                    score -= 70.0
                    reasons.append("助攻用红心配组三带二，不推荐（应优先配炸或保留）")
        elif action_type in ["Pair", "PAIR"]:
            # **核心规则**：禁止用红心配组对子（特别是小对子），这是最浪费的用法
            # 根据知识库：残局时配小对子有两种情况：1. 防对手（对手剩1张或5张） 2. 送队友
            # 非残局阶段，用红心配配对子是严重浪费
            if len(action_cards) == 2:
                # 检查是否是小对子（3-9）
                action_rank = ""
                for card in action_cards:
                    if len(card) >= 2:
                        rank = card[1] if len(card) == 2 else card[1:2]
                        if rank != cur_rank:  # 不是级牌本身
                            action_rank = rank
                            break
                
                rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15}
                rank_val = rank_map.get(action_rank, 0)
                
                # 非残局阶段，禁止用红心配配对子
                if game_phase != "endgame":
                    if rank_val <= 7:  # 3-7是小对子
                        score -= 120.0  # 大幅减分，强制禁止用红心配组小对子
                        reasons.append(f"核心规则：禁止用红心配组小对子（{action_rank}），这是最浪费的用法，应保留用于炸弹或关键组合")
                    else:  # 8以上
                        score -= 80.0  # 大幅减分，不鼓励用红心配组对子
                        reasons.append(f"核心规则：禁止用红心配组对子（{action_rank}），应保留用于炸弹或关键组合")
                else:
                    # 残局阶段，配小对子可以接受（防对手或送队友），但仍有减分
                    if rank_val <= 7:  # 小对子
                        score -= 30.0  # 残局配小对子，轻微减分
                        reasons.append(f"残局用红心配组小对子（{action_rank}），可接受但非最优")
                    else:
                        score -= 20.0
                        reasons.append(f"残局用红心配组对子（{action_rank}），可接受")
        else:
            if game_phase == "early":
                # 初期使用红桃配组其他牌型，给予减分
                score -= 40.0  # 从-20提升到-40
                reasons.append("初期保留红桃配，为后期提供更多战略变化")
    
    # 4. 惩罚：拆炸弹组其他牌型
    if bomb_broken and action_type not in ["Bomb", "BOMB", "StraightFlush"]:
        # 拆了炸弹组其他牌型，给予额外惩罚
        score -= 50.0
        reasons.append(f"拆炸弹组{action_type}，代价过大，不建议")
    
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
    
    # 8. 核心规则：检测拆对是否会破坏钢板或顺子组合
    if action_type == "Single" or action_type == "SINGLE":
        if len(action_cards) == 1 and action_cards:
            # 获取被拆的牌点数
            broken_card = action_cards[0]
            if len(broken_card) >= 2:
                broken_rank = broken_card[1] if len(broken_card) == 2 else broken_card[1:2]
                
                # 检查原始手牌中这个点数是否有对子（说明是拆对）
                if original_rank_count.get(broken_rank, 0) >= 2:
                    # 这是拆对，检查是否会破坏钢板或顺子组合
                    rank_val_map = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14}
                    broken_val = rank_val_map.get(broken_rank, 0)
                    
                    if broken_val > 0:  # 有效点数
                        # 检测钢板组合：检查broken_rank是否在连续3个对子中
                        # 例如：223344、334455、445566、556677、778899、88991010等
                        for start_val in range(max(2, broken_val - 2), min(12, broken_val + 3)):
                            if start_val + 2 > 14:  # 超出范围
                                continue
                            
                            # 检查连续3个对子
                            three_pair_ranks = []
                            can_form_three_pair = True
                            for offset in range(3):
                                check_val = start_val + offset
                                check_rank = None
                                for r, v in rank_val_map.items():
                                    if v == check_val:
                                        check_rank = r
                                        break
                                if check_rank and original_rank_count.get(check_rank, 0) >= 2:
                                    three_pair_ranks.append(check_rank)
                                else:
                                    can_form_three_pair = False
                                    break
                            
                            if can_form_three_pair and broken_rank in three_pair_ranks:
                                # 拆对会破坏钢板组合，但不是绝对禁止，而是强烈建议保留
                                # 模型可以在特殊情况下（如残局、关键压制等）覆盖此建议
                                score -= 60.0  # 强烈建议减分（从100降到60，允许模型覆盖）
                                reasons.append(f"组牌建议：拆对{broken_rank}会破坏钢板组合（{''.join(three_pair_ranks)}），建议保留对子（特殊情况可拆）")
                                break
                        
                        # 检测顺子组合：检查broken_rank是否在连续5个点数的顺子中
                        # 例如：2-6、3-7、4-8、5-9、6-10、7-J、8-Q、9-K、10-A等
                        for start_val in range(max(2, broken_val - 4), min(11, broken_val + 1)):
                            if start_val + 4 > 14:  # 超出范围
                                continue
                            
                            # 检查连续5个点数是否都有牌
                            straight_ranks = []
                            can_form_straight = True
                            for offset in range(5):
                                check_val = start_val + offset
                                check_rank = None
                                for r, v in rank_val_map.items():
                                    if v == check_val:
                                        check_rank = r
                                        break
                                if check_rank and original_rank_count.get(check_rank, 0) >= 1:
                                    straight_ranks.append(check_rank)
                                else:
                                    can_form_straight = False
                                    break
                            
                            if can_form_straight and broken_rank in straight_ranks:
                                # 检查拆对后是否还能组成顺子
                                # 如果broken_rank只有2张，拆了1张后只剩1张，可能还能组成顺子
                                # 但如果其他点数也只有1-2张，拆对可能破坏顺子组合的稳定性
                                # 更严格的判断：如果broken_rank在顺子中，且是唯一对子，拆对会破坏
                                broken_count_after = original_rank_count.get(broken_rank, 0) - 1
                                other_ranks_weak = sum(1 for r in straight_ranks if r != broken_rank and original_rank_count.get(r, 0) <= 2)
                                
                                # 如果拆对后broken_rank只剩1张，且其他点数也较弱，拆对会破坏顺子
                                # 但不是绝对禁止，模型可以在特殊情况下覆盖
                                if broken_count_after == 1 and other_ranks_weak >= 2:
                                    score -= 50.0  # 强烈建议减分（从90降到50，允许模型覆盖）
                                    reasons.append(f"组牌建议：拆对{broken_rank}会破坏顺子组合（{'-'.join(straight_ranks)}），建议保留对子（特殊情况可拆）")
                                    break
    
    return {
        'score': score,
        'reasons': reasons,
        'rounds_reduced': rounds_reduced,
        'singles_reduced': singles_reduced
    }


def grouping_strategy(hand_cards: List[str], action_list: List, 
                     game_phase: str, power: float, cur_rank: str = "2",
                     my_rest_cards: int = 27, opponent_rest_cards: int = 27,
                     is_teammate_action: bool = False) -> Dict:
    """
    组牌策略主函数
    
    为每个动作评估组牌效果，返回建议
    
    Args:
        cur_rank: 当前级牌（如"2"），用于判断是否可以组同花顺
        my_rest_cards: 自己剩余牌数
        opponent_rest_cards: 对手剩余牌数
    
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
            hand_cards, action_cards, action_type, game_phase, power, cur_rank,
            my_rest_cards, opponent_rest_cards, is_teammate_action
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

