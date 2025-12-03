from typing import Dict, List, Tuple
from collections import Counter, defaultdict
import re

def parse_hand_cards(hand_cards: List[str]) -> Dict:
    """
    解析手牌，统计牌型。
    输入: ["H3","H4","S5",...] 
    输出: 牌型计数字典 {rank: {suit: count}, total_cards: int, cards_by_suit: dict}
    """
    rank_map = {'3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, 'T':10, 'J':11, 'Q':12, 'K':13, 'A':14, '2':15, 'B':16}
    
    rank_suit_count = defaultdict(lambda: Counter())
    total_cards = len(hand_cards)
    
    for card in hand_cards:
        if len(card) < 2:
            continue
        suit = card[0]
        rank_str = card[1] if len(card) == 2 else card[1:2]
        rank = rank_map.get(rank_str, 0)
        if rank > 0:
            rank_suit_count[rank][suit] += 1
    
    # Convert to regular dict for JSON serialization
    rank_count_dict = {rank: dict(counts) for rank, counts in rank_suit_count.items()}
    
    return {
        'rank_suit_count': rank_count_dict,
        'total_cards': total_cards
    }

def find_best_combinations(rank_suit_count: Dict[int, Dict[str, int]]) -> Dict:
    """
    查找最佳牌型组合，避免重复使用牌
    """
    # Get all available ranks
    all_ranks = sorted([r for r in rank_suit_count if any(rank_suit_count[r].values()) > 0])
    
    # 1. 首先检测炸弹（最高优先级）
    bomb_combinations = []
    for rank in all_ranks:
        total_count = sum(rank_suit_count[rank].values())
        if total_count >= 4:
            bomb_combinations.append((rank, total_count))
    
    # 2. Find possible steel板 (连三带二)
    steel_board_combinations = []
    used_ranks = set()
    i = 0
    while i < len(all_ranks) - 2:
        r1, r2, r3 = all_ranks[i], all_ranks[i+1], all_ranks[i+2]
        if r2 == r1 + 1 and r3 == r2 + 1:
            # Check if we can form steel板 with these three consecutive ranks
            if (sum(rank_suit_count[r1].values()) >= 3 and 
                sum(rank_suit_count[r2].values()) >= 3 and 
                sum(rank_suit_count[r3].values()) >= 3):
                steel_board_combinations.append((r1, r2, r3))
                used_ranks.update([r1, r2, r3])
        i += 1
    
    # 3. Find possible straight flushes by suit
    straight_flush_combinations = {'S': [], 'H': [], 'D': [], 'C': []}
    for suit in ['S', 'H', 'D', 'C']:
        suit_ranks = [r for r in all_ranks if suit in rank_suit_count[r] and rank_suit_count[r][suit] > 0]
        suit_ranks.sort()
        
        # Find consecutive sequences of 5+ cards in this suit
        j = 0
        while j < len(suit_ranks) - 4:
            if (suit_ranks[j+4] == suit_ranks[j] + 4 and
                all(suit_ranks[j+k] == suit_ranks[j] + k for k in range(1, 5))):
                # Check if all these ranks have cards in this suit
                if all(rank_suit_count[suit_ranks[j+k]][suit] > 0 for k in range(5)):
                    # Check if these ranks are not used in steel板
                    if all(r not in used_ranks for r in suit_ranks[j:j+5]):
                        straight_flush_combinations[suit].append((suit_ranks[j], 5))
                        used_ranks.update(suit_ranks[j:j+5])
            j += 1
    
    # 4. Find mixed straights (杂顺): longest first, non-overlapping
    straight_combinations = []
    j = 0
    while j < len(all_ranks) - 4:
        max_length = 5
        while j + max_length < len(all_ranks) and all(all_ranks[j + k] == all_ranks[j] + k for k in range(1, max_length + 1)):
            if all(sum(rank_suit_count[all_ranks[j + k]].values()) > 0 for k in range(max_length + 1)):
                if all(r not in used_ranks for r in all_ranks[j:j + max_length + 1]):
                    straight_combinations.append((all_ranks[j], max_length + 1))
                    used_ranks.update(all_ranks[j:j + max_length + 1])
                    j += max_length
                    break
            max_length += 1
        else:
            j += 1
    
    return {
        'steel_board': len(steel_board_combinations),
        'straight_flush': sum(len(combs) for combs in straight_flush_combinations.values()),
        'straight_combinations': straight_combinations,
        'bomb_super_high': sum(1 for rank, count in bomb_combinations if rank >= 13 and count >= 4),
        'bomb_mid': sum(1 for rank, count in bomb_combinations if 10 <= rank < 13 and count >= 4),
        'bomb_normal': sum(1 for rank, count in bomb_combinations if rank < 10 and count >= 4)
    }

def calculate_card_power(hand_cards: List[str], game_phase: str = 'opening', my_role: str = None, opponent_power: float = 4.0, cur_level_rank: int = 10, opponent_rest_cards: int = 27) -> Dict:
    """
    掼蛋牌力计算（基于用户提供的公式，避免重复计算）
    
    改进：避免钢板和同花顺重复计算，选择最佳组合
    """
    parsed = parse_hand_cards(hand_cards)
    rank_suit_count = parsed['rank_suit_count']
    total_cards = parsed['total_cards']
    
    # Find best combinations (mutually exclusive)
    combinations = find_best_combinations(rank_suit_count)
    
    power = 0.0
    
    # 1. 同花顺 (优先于钢板)
    straight_flush_count = combinations['straight_flush']
    power += straight_flush_count * 3
    
    # 2. 钢板 (如果没有同花顺占用这些牌)
    steel_board_count = combinations['steel_board']
    power += steel_board_count * 1
    
    # 3. 炸弹 (最高优先级)
    straight_count = len(combinations['straight_combinations'])
    power += combinations['bomb_super_high'] * 4 + combinations['bomb_mid'] * 3 + combinations['bomb_normal'] * 2
    
    # 4. 高牌 (A, 2, 王)
    # 14=A, 15=2, 16=小王, 17=大王
    high_cards = sum(1 for rank in rank_suit_count if rank >= 14 and sum(rank_suit_count[rank].values()) > 0)
    power += high_cards
    
    # 5. 逢人配 (级牌对子)
    meet_pair_count = 0
    high_ranks = {14, cur_level_rank, 16}  # A, level, small king
    for rank in high_ranks:
        if rank in rank_suit_count and sum(rank_suit_count[rank].values()) >= 2:
            meet_pair_count += 1
    power += meet_pair_count
    
    # 6. 赘牌扣分 (简化计算)
    # 小单牌 (<10)
    used_in_straight = set()
    for start, length in combinations['straight_combinations']:
        for k in range(length):
            used_in_straight.add(start + k)

    small_singles = 0
    for rank in range(3, 10):  # 3-9
        total = sum(rank_suit_count.get(rank, {}).values())
        if total == 1 and rank not in used_in_straight:
            small_singles += 1
    # 小对子 (<6)
    small_pairs = 0
    for rank in range(3, 6):  # 3-5
        total = sum(rank_suit_count.get(rank, {}).values())
        if total == 2:
            small_pairs += 1
    redundant_penalty = -(small_singles + small_pairs)
    power += redundant_penalty
    
    endgame_bonus = 0
    if game_phase == 'endgame' and opponent_rest_cards <= 10:
        has_pair = any(sum(counts.values()) >= 2 for counts in rank_suit_count.values())
        has_trips = any(sum(counts.values()) >= 3 for counts in rank_suit_count.values())
        has_straight = straight_count > 0 or straight_flush_count > 0
        has_three_with_two = any(sum(counts.values()) >= 3 for counts in rank_suit_count.values()) and has_pair
        has_single = any(sum(counts.values()) == 1 for counts in rank_suit_count.values())
        has_bomb = (combinations['bomb_super_high'] + combinations['bomb_mid'] + combinations['bomb_normal']) > 0

        if opponent_rest_cards == 5 and has_pair:
            endgame_bonus += 1
        if opponent_rest_cards == 6 and has_trips:
            endgame_bonus += 1
        if opponent_rest_cards in [7,8] and (has_straight or has_three_with_two):
            endgame_bonus += 1
        if opponent_rest_cards == 9 and has_single:
            endgame_bonus += 1
        if opponent_rest_cards == 10 and has_pair:
            endgame_bonus += 1
        if opponent_rest_cards == 7 and has_bomb:
            endgame_bonus += 1

    power += endgame_bonus

    # 7. 出牌权加分 (非开局)
    if game_phase != 'opening':
        power += 1
    
    # 分级判断
    if power > 10:
        grade = "强牌"
        suggested_role = "主攻"
    elif 5 <= power <= 10:
        grade = "中等牌"
        suggested_role = "攻守兼备"
    elif 2 <= power < 5:
        grade = "中弱牌力"
        suggested_role = "助攻"
    else:
        grade = "弱牌"
        suggested_role = "未游"
    
    # 临界调整 (5-6分根据对手)
    if 5 <= power < 6:
        if opponent_power >= 5:  # 对手强，定位助攻
            suggested_role = "助攻"
        else:  # 对手弱，尝试主攻
            suggested_role = "尝试主攻"
    
    details = {
        'straight_flush': straight_flush_count,
        'steel_board': steel_board_count,
        'straight': straight_count,
        'bomb_super_high': combinations['bomb_super_high'],
        'bomb_mid': combinations['bomb_mid'],
        'bomb_normal': combinations['bomb_normal'],
        'high_cards': high_cards,
        'meet_pair': meet_pair_count,
        'redundant_penalty': redundant_penalty,
        'out_right_bonus': 1 if game_phase != 'opening' else 0,
        'ascending_straight': sum(1 for start, length in combinations['straight_combinations'] if start == 10 and length == 5),
        'endgame_bonus': endgame_bonus
    }
    
    return {
        'total_power': round(power, 1),
        'grade': grade,
        'suggested_role': suggested_role,
        'details': details
    }

# 测试用户手牌 (预期中等牌力 ~4.5分)
if __name__ == "__main__":
    user_hand = ["H3", "H4", "S5", "S6", "C7", "C7", "C8", "D8", "D8", "S8", "H9", "S9", "CT", "DT", "DT", "HT", "ST", "CJ", "DJ", "CK", "CK", "DK", "CA", "SA", "SB", "SB"]
    result = calculate_card_power(user_hand, game_phase='opening')
    print(f"牌力计算结果: {result}")
