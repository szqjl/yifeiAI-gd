from typing import Dict, List
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27

def bomb_strategy(
    game_phase: str = 'mid',
    power: float = 5.0,
    opponent_rest_cards: int = None,
    opponent_action_type: str = 'none',  # e.g., 'trips', 'pair', 'straight', 'three_head', 'single'
    opponent_action_rank: int = 0,  # 牌点，如10 for 10以上
    opponent_action_cards: List = None,  # 对手出的牌
    has_better_combo: bool = False,  # 有更好牌型压
    teammate_needs_help: bool = False,
    is_critical_moment: bool = False,
    bomb_quality: str = 'normal',  # small, mid, high
    is_teammate_action: bool = False,
    cur_pos: int = -1,  # 当前位置
    greater_pos: int = -1,  # 出牌者位置
    my_pos: int = -1,  # 我的位置
    teammate_pos: int = -1,  # 队友位置
    can_change_card_type: bool = False,  # 能否改变牌型
    opponent_is_main_attacker: bool = False,  # 对手是否主攻
    is_last_player: bool = False,  # 是否是最后一家
    has_clear_next_action: bool = True,  # 炸完后是否有明确出牌
    card_type_clear: bool = True  # 牌型是否明朗
) -> Dict[str, List[Dict[str, str]]]:
    """
    出炸弹要领决策函数。目标：为己方赢（头游+二游）服务，该炸则炸、该省则省。
    基于《出炸弹要领.txt》的完整知识体系。
    """
    opponent_rest_cards = opponent_rest_cards if opponent_rest_cards is not None else DEFAULT_REST_CARDS
    suggestions = []
    opponent_action_cards = opponent_action_cards or []
    
    # ========== 第一节：配炸技巧（已在组牌策略中处理） ==========
    
    # ========== 第二节：炸什么牌 ==========
    
    # 1. 改变牌路、牌型（90%的炸弹作用）
    # 当对手出己方没有的牌型，或余牌已无顺套，及时利用炸弹制止，扭转到己家优势牌型
    if can_change_card_type:
        suggestions.append({'action': '炸（改牌路）', 'reason': '改变牌路，转到己方优势牌型。'})
    
    # 1.1 对手出己方没有的牌型时，果断开炸
    # 如对手出顺，队友都没有这个牌型，果断开炸，改走单、对子，或与顺子相佐的三带二牌型
    if opponent_action_type in ['straight', 'three_with_two'] and not has_better_combo:
        # 对手出了我方没有的牌型（has_better_combo=False），果断开炸
        suggestions.append({'action': '炸（改牌路）', 'reason': '对手出我方没有的牌型，果断开炸，改变牌路到己方优势牌型。'})
    
    # 1.2 枪打第一顺
    if opponent_action_type == 'straight' and len(opponent_action_cards) >= 5:
        suggestions.append({'action': '炸（枪打第一顺）', 'reason': '枪打第一顺，改走单、对子。'})
    
    # 2. 炸常规牌型的控牌
    if opponent_action_type == 'single' and opponent_action_rank >= 15:  # 大王
        suggestions.append({'action': '炸（控牌）', 'reason': '炸单牌控牌大王，比较划算。'})
    elif opponent_action_type == 'pair' and opponent_action_rank >= 15:  # 小王对
        suggestions.append({'action': '炸（控牌）', 'reason': '炸一对小王，比较划算。'})
    elif opponent_action_type == 'straight' and opponent_action_rank >= 10:  # 10JQKA
        suggestions.append({'action': '炸（控牌）', 'reason': '炸顺子控牌10JQKA，比较划算。'})
    
    # 3. 追炸
    if opponent_action_type == 'bomb':
        suggestions.append({'action': '炸（追炸）', 'reason': '用大炸弹追炸对手的小炸弹，防止对手获得控牌权。'})
    
    # 4. 残局冲刺抢头游
    if game_phase == 'endgame' and opponent_rest_cards <= 5:
        suggestions.append({'action': '炸（冲刺）', 'reason': '残局冲刺抢头游，提前用大炸开路。'})
    
    # 5. 阻止对手冲刺
    if opponent_rest_cards <= 7 and bomb_quality in ['high', 'mid']:
        suggestions.append({'action': '炸（阻冲刺）', 'reason': '阻止对手冲刺，给队友创造机会。'})
    
    # ========== 第三节：炸谁的牌 ==========
    
    # 1. 首选打上家（牌力差时）
    if power < 5 and greater_pos != -1:
        # 计算上家位置
        if my_pos == 0:
            up_pos = 3
        elif my_pos == 1:
            up_pos = 0
        elif my_pos == 2:
            up_pos = 1
        else:  # my_pos == 3
            up_pos = 2
        
        if greater_pos == up_pos:
            suggestions.append({'action': '炸（打上家）', 'reason': '牌力差，首选炸上家，让对家跟套牌。'})
    
    # 2. 次打下家（牌力强时）
    if power >= 8 and greater_pos != -1:
        # 计算下家位置
        if my_pos == 0:
            down_pos = 1
        elif my_pos == 1:
            down_pos = 2
        elif my_pos == 2:
            down_pos = 3
        else:  # my_pos == 3
            down_pos = 0
        
        if greater_pos == down_pos:
            suggestions.append({'action': '炸（打下家）', 'reason': '牌力强，炸下家争上游。'})
    
    # 3. 炸敌方主攻
    if opponent_is_main_attacker:
        suggestions.append({'action': '炸（主攻）', 'reason': '炸敌方主攻，放助攻多出一手不影响全局。'})
    
    # ========== 第四节：出炸的时机（炸点） ==========
    
    # 1. 牌路若不对，炸弹来应对
    if can_change_card_type and is_last_player:
        suggestions.append({'action': '炸（改牌路）', 'reason': '最后一家，牌路不对及时出炸。'})
    
    # 2. 对手已经把这种牌型打完
    # （需要牌型追踪，这里简化处理）
    
    # 3. 对手要急于处理困难牌
    if opponent_rest_cards <= 3:
        suggestions.append({'action': '炸（阻冲刺）', 'reason': '对手剩牌少，及时动炸阻止。'})
    
    # 4. 对手即将听牌时要炸
    if opponent_rest_cards == 2:
        suggestions.append({'action': '炸（阻听牌）', 'reason': '对手即将听牌，果断出炸让其听不了牌。'})
    
    # 5. 枪打第一顺
    if opponent_action_type == 'straight' and len(opponent_action_cards) >= 5:
        if is_last_player:
            suggestions.append({'action': '炸（枪打第一顺）', 'reason': '最后一家，枪打第一顺，改走单、对子。'})
    
    # 6. 早炸大王继续走单
    if opponent_action_type == 'single' and opponent_action_rank >= 15:
        suggestions.append({'action': '炸（早炸大王）', 'reason': '早炸大王，继续走单。'})
    
    # 7. 炸对手首对级牌
    if opponent_action_type == 'pair' and opponent_action_rank >= 15:  # 级牌对
        suggestions.append({'action': '炸（级牌对）', 'reason': '炸对手首对级牌，打断牌路。'})
    
    # ========== 第五节：残局用炸（关键规则） ==========
    
    # 1. 炸不打四（关键规则）
    if opponent_rest_cards == 4:
        # 例外情况
        exceptions = [
            teammate_needs_help and opponent_rest_cards == 4,  # 对家剩一手牌
            power >= 8 and opponent_rest_cards == 4,  # 己方剩一两手牌，炸弹大
        ]
        if not any(exceptions):
            suggestions.append({'action': '不炸（炸不打四）', 'reason': '敌方剩4张，一般不炸（炸不打四）。'})
    
    # 2. 逢5出对
    if opponent_rest_cards == 5:
        suggestions.append({'action': '炸（逢5出对）', 'reason': '敌方剩5张，一般要炸，炸后出对子。'})
    
    # 3. 敌家剩6张
    if opponent_rest_cards == 6:
        suggestions.append({'action': '炸（剩6）', 'reason': '敌家剩6张，偷机开溜要炸。'})
    
    # 4. 敌家剩7张
    if opponent_rest_cards == 7:
        suggestions.append({'action': '炸（剩7）', 'reason': '敌家剩7张，判敌4+3要提前炸。'})
    
    # 5. 敌家剩8张
    if opponent_rest_cards == 8:
        suggestions.append({'action': '炸（剩8）', 'reason': '敌家剩8张，判是5+3要提前炸。'})
    
    # 6. 下家剩9张
    if opponent_rest_cards == 9:
        if greater_pos != -1:
            # 计算下家位置
            if my_pos == 0:
                down_pos = 1
            elif my_pos == 1:
                down_pos = 2
            elif my_pos == 2:
                down_pos = 3
            else:  # my_pos == 3
                down_pos = 0
            
            if greater_pos == down_pos:
                suggestions.append({'action': '炸（下家剩9）', 'reason': '下家剩9张，下家有炸要先炸。'})
    
    # **增强**：残局阶段更积极使用炸弹
    if opponent_rest_cards <= 8:
        if opponent_action_type in ['pair', 'trips'] and opponent_action_rank < 12:
            suggestions.append({'action': '炸（残局压制）', 'reason': '残局阶段，积极压制对手小牌型。'})
    
    # ========== 第六节：不宜出炸 ==========
    
    # 1. 牌型不明时不出炸
    if not card_type_clear:
        suggestions.append({'action': '不炸（牌型不明）', 'reason': '牌型不明，出炸后不好出牌。'})
    
    # 2. 明知炸了走不了不出炸
    if not has_clear_next_action:
        suggestions.append({'action': '不炸（走不了）', 'reason': '炸完不知道出什么牌，一般不要开炸。'})
    
    # 3. 当对手的牌型不是到顶牌点
    if opponent_action_type == 'single' and opponent_action_rank < 15:  # 不是大王
        if not is_last_player:  # 不是守底者
            suggestions.append({'action': '不炸（非顶牌）', 'reason': '对手牌型不是到顶牌点，不是守底者一般不要先炸。'})
    
    # 4. 单张、对子、三张不值得炸（非残局）
    if opponent_rest_cards > 10:
        if opponent_action_type in ['single', 'pair', 'trips']:
            suggestions.append({'action': '不炸（小牌型）', 'reason': f'非残局，{opponent_action_type}不值得炸。'})

    # **增强**：中期阶段谨慎控制炸弹使用
    if opponent_rest_cards > 12:  # 中期阶段
        if opponent_action_type in ['pair', 'trips'] and opponent_action_rank < 8:
            suggestions.append({'action': '不炸（中期保守）', 'reason': '中期阶段，很小的对子和三张不炸，节省炸弹。'})
        elif opponent_action_type in ['pair', 'trips'] and opponent_action_rank >= 8 and opponent_action_rank < 12:
            suggestions.append({'action': '谨慎炸（中期评估）', 'reason': '中期阶段，中等大小的对子三张，评估牌路后再决定是否炸。'})
    
    # ========== 原有8点要领 ==========
    
    # 1. 贵在及时
    if is_critical_moment:
        suggestions.append({'action': '炸（及时）', 'reason': '关键时刻炸，扭转局面。'})
    
    # 2. 贵在准确
    if opponent_action_type in ['straight', 'three_with_two'] and opponent_action_rank >= 10:
        suggestions.append({'action': '炸（准确）', 'reason': '针对高牌型准确炸。'})
    
    # 3. 贵在经济
    if has_better_combo:
        suggestions.append({'action': '不炸（经济）', 'reason': '有更好牌型压，节省炸弹。'})
    
    # 4. 贵在价值
    if teammate_needs_help:
        suggestions.append({'action': '炸（价值）', 'reason': '帮助队友，掩护头游。'})
    
    # 5. 贵在隐蔽
    if game_phase == 'opening':
        suggestions.append({'action': '不炸（隐蔽）', 'reason': '开局隐蔽实力，后发制人。'})
    
    # 6. 贵在顺序
    if bomb_quality == 'small':
        suggestions.append({'action': '先小后大', 'reason': '小炸先出，诱大炸。'})
    
    # 7. 贵在配合
    if is_teammate_action:
        suggestions.append({'action': '不炸（配合）', 'reason': '队友行动，不干扰。'})
    
    # 8. 盲目轻动 匹夫之勇
    if opponent_action_type == 'three_head' and opponent_action_rank < 10:
        suggestions.append({'action': '不炸（慎动）', 'reason': '对手三头间隔近，可能烂牌或管不了，等10+再炸。'})
    
    # 通用：牌力弱不炸
    if power < 5:
        suggestions.append({'action': '不炸（牌力弱）', 'reason': '牌力差，保留炸弹关键用。'})
    
    return {'suggestions': suggestions}

if __name__ == "__main__":
    result = bomb_strategy(
        opponent_action_type='three_head', 
        opponent_action_rank=8,
        opponent_rest_cards=5,
        my_pos=2,
        greater_pos=1
    )
    print(result)
