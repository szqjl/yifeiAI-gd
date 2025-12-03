"""
炸弹选择策略模块
优先使用不灵活的炸弹，避免拆顺子和三带二
"""
from typing import Dict, List, Tuple

def select_bomb_priority(
    bomb_action_list: List,
    hand_cards: List,
    sorted_cards: Dict,
    bomb_info: Dict,
    rank_card: str,
    card_val: Dict,
    avoid_straight: bool = True,  # 避免拆顺子
    avoid_three_with_two: bool = True  # 避免拆三带二
) -> Tuple[int, str]:
    """
    选择炸弹的优先级策略
    
    优先级（从高到低）：
    1. 不灵活的炸弹（固定炸弹，不能拆的）
    2. 不拆顺子的炸弹
    3. 不拆三带二的炸弹
    4. 级牌炸弹（去掉优先使用级牌炸弹，改为最后考虑）
    
    返回：
    (index, reason) - 最佳炸弹索引和原因，如果没有合适的返回 (-1, "")
    """
    if not bomb_action_list:
        return (-1, "")
    
    # 获取顺子和三带二中的牌
    straight_member = []
    three_with_two_member = []
    
    # 方法1：从 sorted_cards 中获取（如果提供）
    if avoid_straight and sorted_cards:
        if "Straight" in sorted_cards and sorted_cards["Straight"]:
            for straight in sorted_cards["Straight"]:
                if isinstance(straight, list):
                    straight_member.extend(straight)
        
        if "StraightFlush" in sorted_cards and sorted_cards["StraightFlush"]:
            for sf in sorted_cards["StraightFlush"]:
                if isinstance(sf, list):
                    straight_member.extend(sf)
    
    if avoid_three_with_two and sorted_cards:
        if "ThreeWithTwo" in sorted_cards and sorted_cards["ThreeWithTwo"]:
            for thw in sorted_cards["ThreeWithTwo"]:
                if isinstance(thw, list):
                    three_with_two_member.extend(thw)
    
    # 方法2：从 action_list 中推断（如果 sorted_cards 为空或未提供）
    # 检查 action_list 中是否有顺子和三带二动作（从所有动作中查找，不仅仅是炸弹动作）
    # 注意：这里我们需要从外部传入完整的 action_list，但为了简化，我们从 hand_cards 推断
    # 实际上，我们可以通过检查手牌中是否有顺子和三带二的组合来推断
    # 简化处理：如果 sorted_cards 为空，我们假设没有顺子和三带二需要保护
    
    # 分类炸弹
    fixed_bombs = []  # 固定炸弹（不能拆的）
    non_straight_bombs = []  # 不拆顺子的炸弹
    non_three_with_two_bombs = []  # 不拆三带二的炸弹
    rank_card_bombs = []  # 级牌炸弹（最后考虑）
    other_bombs = []  # 其他炸弹
    
    for idx, action_tuple in enumerate(bomb_action_list):
        if isinstance(action_tuple, tuple) and len(action_tuple) >= 2:
            action_idx = action_tuple[0]
            action = action_tuple[1]
        else:
            action_idx = idx
            action = action_tuple
        
        if not isinstance(action, list) or len(action) < 3:
            continue
        
        action_type = action[0]
        action_cards = action[2] if len(action) > 2 else []
        
        if action_type not in ["Bomb", "BOMB", "StraightFlush"]:
            continue
        
        # 检查是否在顺子中
        in_straight = False
        if avoid_straight:
            for card in action_cards:
                if card in straight_member:
                    in_straight = True
                    break
        
        # 检查是否在三带二中
        in_three_with_two = False
        if avoid_three_with_two:
            for card in action_cards:
                if card in three_with_two_member:
                    in_three_with_two = True
                    break
        
        # 检查是否是级牌炸弹
        is_rank_card_bomb = False
        if rank_card and len(action_cards) > 0:
            # 检查是否包含级牌
            rank_card_value = rank_card[-1] if len(rank_card) > 1 else rank_card
            for card in action_cards:
                if len(card) > 1 and card[-1] == rank_card_value:
                    is_rank_card_bomb = True
                    break
        
        # 计算炸弹大小（用于排序）
        bomb_size = 0
        if action_type == "StraightFlush":
            bomb_size = 1000  # 同花顺优先级最高
        elif action_type in ["Bomb", "BOMB"]:
            if len(action_cards) >= 4:
                bomb_size = len(action_cards) * 100  # 多头炸优先级更高
        
        # 分类
        if not in_straight and not in_three_with_two and not is_rank_card_bomb:
            # 固定炸弹（不拆顺子、不拆三带二、不是级牌炸弹）
            fixed_bombs.append((action_idx, bomb_size, action))
        elif not in_straight and not in_three_with_two:
            # 不拆顺子和三带二，但是级牌炸弹
            rank_card_bombs.append((action_idx, bomb_size, action))
        elif not in_straight:
            # 不拆顺子，但可能拆三带二
            non_straight_bombs.append((action_idx, bomb_size, action))
        elif not in_three_with_two:
            # 不拆三带二，但可能拆顺子
            non_three_with_two_bombs.append((action_idx, bomb_size, action))
        else:
            # 其他炸弹（可能拆顺子或三带二）
            other_bombs.append((action_idx, bomb_size, action))
    
    # 按优先级选择：固定炸弹 > 不拆顺子 > 不拆三带二 > 其他 > 级牌炸弹
    # 每个类别内按炸弹大小排序（从小到大，优先使用小炸弹）
    
    def sort_bombs(bomb_list):
        return sorted(bomb_list, key=lambda x: x[1])  # 按炸弹大小排序
    
    # 优先级1：固定炸弹
    if fixed_bombs:
        sorted_fixed = sort_bombs(fixed_bombs)
        return (sorted_fixed[0][0], "优先使用固定炸弹（不拆顺子和三带二）")
    
    # 优先级2：不拆顺子的炸弹
    if non_straight_bombs:
        sorted_non_straight = sort_bombs(non_straight_bombs)
        return (sorted_non_straight[0][0], "使用不拆顺子的炸弹")
    
    # 优先级3：不拆三带二的炸弹
    if non_three_with_two_bombs:
        sorted_non_three = sort_bombs(non_three_with_two_bombs)
        return (sorted_non_three[0][0], "使用不拆三带二的炸弹")
    
    # 优先级4：其他炸弹（可能拆顺子或三带二，但总比没有好）
    if other_bombs:
        sorted_other = sort_bombs(other_bombs)
        return (sorted_other[0][0], "使用其他炸弹（可能拆顺子或三带二）")
    
    # 优先级5：级牌炸弹（最后考虑，因为级牌可以拆成对子或三带二，灵活性高）
    if rank_card_bombs:
        sorted_rank = sort_bombs(rank_card_bombs)
        return (sorted_rank[0][0], "使用级牌炸弹（最后考虑，级牌灵活性高）")
    
    return (-1, "没有合适的炸弹")

def should_use_bomb(
    bomb_count: int,
    opponent_rest_cards: int,
    game_phase: str = 'mid',
    my_rest_cards: int = 27,
    power: float = 5.0,
    has_strong_singles: bool = False,  # 是否有强单牌（王、级牌多）
    has_alternative: bool = False,  # 是否有替代牌型可以管住对手
    is_active: bool = False,  # 是否主动出牌
    opponent_action_type: str = 'none',  # 对手动作类型
    opponent_action_rank: int = 0,  # 对手动作排名
    my_pos: int = 0,  # 当前位置
    cur_pos: int = -1,  # 当前出牌位置
    greater_pos: int = -1,  # 最大出牌位置
    teammate_pos: int = 2,  # 队友位置
    power_level: str = "medium"  # 牌力等级：weak/medium/strong
) -> Tuple[bool, str]:
    """
    根据炸弹数量和对手剩余牌数决定是否使用炸弹
    
    返回：
    (should_use, reason) - 是否应该使用炸弹和原因
    """
    # 1. 主动出牌时，绝不是自己上手出炸弹（除非必要）
    if is_active:
        return (False, f"主动出牌，不轻易使用炸弹")
    
    # 2. 王多、级牌多，单牌也比较大，考虑保留炸弹
    if has_strong_singles and bomb_count < 3:
        return (False, f"王多、级牌多，单牌强，且炸弹不多，保留炸弹")
    
    # 3. 有替代牌型可以管住对手，不使用炸弹
    if has_alternative:
        return (False, f"有替代牌型可以管住对手，不使用炸弹")
    
    # 4. 炸弹多时（>=3）更容易使用
    if bomb_count >= 3:
        return (True, f"炸弹多（{bomb_count}个），可以使用")
    
    # 5. 对手剩余牌少时（<=18）更容易使用
    if opponent_rest_cards <= 18:
        return (True, f"对手剩余牌少（{opponent_rest_cards}张），可以使用")
    
    # 6. 残局阶段更容易使用
    if game_phase == 'endgame' and opponent_rest_cards <= 10:
        return (True, f"残局阶段，对手剩余{opponent_rest_cards}张，可以使用")
    
    # 7. 自己剩余牌少且牌力强时，可以使用
    if my_rest_cards <= 5 and power >= 7:
        return (True, f"自己剩余牌少（{my_rest_cards}张）且牌力强，可以使用")
    
    # 8. 炸牌目标选择策略
    # 计算上家、下家位置
    upper_hand_pos = (my_pos - 1) % 4  # 上家位置
    lower_hand_pos = (my_pos + 1) % 4  # 下家位置
    
    # 8.1 首选打上家
    # 本家牌力差（power < 5），下游牌，尤其单贡或双贡，首选炸上家
    if power < 5 or power_level == "weak":
        if greater_pos == upper_hand_pos or cur_pos == upper_hand_pos:
            return (True, f"牌力差，下游牌，首选炸上家（位置{upper_hand_pos}），让对家跟套牌")
    
    # 8.2 次打下家
    # 牌力强（power >= 7），想争上游，体现强势牌
    # 进入冲刺阶段（my_rest_cards <= 10）
    if (power >= 7 or power_level == "strong") and my_rest_cards <= 10:
        if greater_pos == lower_hand_pos or cur_pos == lower_hand_pos:
            return (True, f"牌力强，冲刺阶段，次打下家（位置{lower_hand_pos}），争取上游")
    
    # 8.3 仅剩一手牌，减轻搭档防守压力
    if my_rest_cards <= 5:
        return (True, f"仅剩{my_rest_cards}张牌，炸牌减轻搭档防守压力，引对方火力")
    
    # 9. 其他情况谨慎使用
    return (False, f"炸弹数量（{bomb_count}个）和对手剩余牌数（{opponent_rest_cards}张）不满足使用条件")

if __name__ == "__main__":
    # 测试
    bomb_list = [
        (1, ["Bomb", "5", ["S5", "H5", "C5", "D5"]]),
        (2, ["Bomb", "6", ["S6", "H6", "C6", "D6", "H2"]]),  # 级牌炸弹
        (3, ["StraightFlush", "7", ["S7", "S8", "S9", "ST", "SJ"]])
    ]
    
    sorted_cards = {
        "Straight": [["S7", "S8", "S9", "ST", "SJ"]],
        "ThreeWithTwo": [],
        "Bomb": []
    }
    
    result = select_bomb_priority(
        bomb_list, [], sorted_cards, {}, "H2", {"5": 5, "6": 6, "7": 7}
    )
    print(f"选择结果：{result}")

