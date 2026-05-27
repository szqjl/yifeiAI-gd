# -*- coding: utf-8 -*-
"""
M2 阶段处理器 — 重构版（硬编码精确规则，无分数累积+阈值保护）

与 M1 的核心区别：
1. handle() 不调用 _apply_team_strategies() —— 去掉共享 TeammateProtectionStrategy 分数累积
2. 保护逻辑完全内联在按牌型分发的处理器中（参考 lalala 的 Single/Pair/Trips 式精确分支）
3. PASS 次数降级链：pass_num>=4 → special()，pass_num>=6 → bomb
4. 队友剩牌≤6 → 只出刚好大1（精确边界控制）
5. 开局主动恢复一手出完检查
6. 所有改动限制在 M2 专用文件，不碰共用层
"""

from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from game_logic.guandan_constants import CARDS_PER_PLAYER, DEFAULT_REST_CARDS, DEFAULT_ALL_REST_LIST
except ImportError:
    CARDS_PER_PLAYER = 27
    DEFAULT_REST_CARDS = 27
    DEFAULT_ALL_REST_LIST = [27, 27, 27, 27]

from .stage_router import BasePhaseHandler
from .card_power_evaluator import calculate_card_power
from .optimal_combination_scanner import OptimalCombinationScanner, find_excess_singles_for_passive_play


class M2OpeningActiveHandler(BasePhaseHandler):
    """M2 开局主动出牌处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        """M2：不加载共享 TeammateProtectionStrategy / TeamOffensiveStrategy，仅加载分析工具"""
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            from .card_power_evaluator import calculate_card_power
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
            self.calculate_power = calculate_card_power
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None
            self.calculate_power = None

    def handle(self, message: Dict) -> int:
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])

        if not action_list:
            return 0

        # M2：主动出牌先检查一手出完（M1 此处在 OpeningActive 被注掉，M2 恢复）
        one_hand = self._check_one_hand_complete(action_list, handcards)
        if one_hand is not None:
            return one_hand

        # 扫描手牌并基于优先级出牌
        context = self._build_context(message)
        context['is_passive'] = False
        scan_result = self._scan_hand_combination(message, context)
        excess_singles = scan_result.get('excess_singles', [])

        if excess_singles:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                    if cards and cards[0] in excess_singles:
                        if self._validate_action_cards(action, handcards):
                            return i

        # M2修复：主动出牌选最低牌，非首项（server按从高到低排序）
        return self._get_lowest_non_bomb_index(action_list, handcards)


class M2OpeningPassiveHandler(BasePhaseHandler):
    """M2 开局被动出牌处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None

    def handle(self, message: Dict) -> int:
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        if not action_list:
            return 0

        # M2：不调用 _apply_team_strategies()，完全内联处理
        cur_action = message.get("curAction", [])
        if not cur_action:
            return 0

        cur_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        if cur_type == 'Single':
            return self._single_passive(message, action_list, handcards)
        elif cur_type == 'Pair':
            return self._pair_passive(message, action_list)
        else:
            return self._other_passive(message, action_list)

    def _should_bomb_this_action(self, message, cur_rank_val, max_val, cur_type=""):
        """
        基于 docs/skill/出炸弹要领.txt 的完整炸弹判定。
        
        不宜出炸（前置门控）：
        1. 牌型不明（开局>20张且对手非冲刺）→ 不炸
        2. 对手牌不到顶牌点（<A且非级牌/王）→ 不炸
        3. 对手不是主攻无法判断 → 不炸（暂朴素：自己牌>15张时慎炸）
        4. 残局敌剩4张（炸不打四）
        
        应该炸（满足任一即可）：
        1. 对手再出一手就赢（≤3张）
        2. 当前牌是高价值（≥A/级牌/王）
        3. \枪打头一顺\：对手出第一个小顺子（cur_type=Straight且rank≤9）
        4. 连续PASS≥4次必须干预
        5. 保护残血队友（≤6张且对手也≤6）
        6. 残局敌剩5张（逢5要炸）
        """
        pass_num = message.get("pass_num", 0)
        my_pass_num = message.get("my_pass_num", 0)
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        greater_pos = message.get("greaterPos", -1)
        handcards = message.get("handCards", [])
        my_rest = len(handcards) if handcards else 27

        numofplayers = list(DEFAULT_ALL_REST_LIST)
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                numofplayers[i] = info.get("rest", DEFAULT_REST_CARDS)

        numofnext = numofplayers[(my_pos + 1) % 4] if numofplayers else DEFAULT_REST_CARDS
        numofgreaterPos = numofplayers[greater_pos] if greater_pos >= 0 and numofplayers else DEFAULT_REST_CARDS
        teammate_pos = (my_pos + 2) % 4
        numoffri = numofplayers[teammate_pos] if numofplayers else DEFAULT_REST_CARDS

        # ═══════════════════════════════════════
        # 不宜出炸 (前置门控)
        # ═══════════════════════════════════════

        # 1. 牌型不明：开局>20张且对手非冲刺 → 不炸
        if my_rest > 20 and numofnext > 3:
            return False

        # 2. 对手牌不到顶牌点（<A且非级牌/王）→ 不炸
        if cur_rank_val < 14 and pass_num < 4:
            return False

        # 3. 敌剩4张：炸不打四（除非队友能冲头游）
        if numofnext == 4 and numoffri > 6:
            return False

        # ═══════════════════════════════════════
        # 应该炸 (满足任一即可)
        # ═══════════════════════════════════════

        # 1. 对手再出一手就赢（≤3张）
        if numofnext <= 3:
            return True

        # 2. 残局敌剩5张：逢5要炸
        if numofnext == 5:
            return True

        # 3. 当前牌是高价值（≥A/级牌/王）
        if cur_rank_val >= 14:
            return True

        # 4. 枪打头一顺：对手出第一个小顺子且我方缺顺子
        if cur_type == 'Straight' and cur_rank_val <= 9:
            return True

        # 5. 连续PASS≥4次必须干预
        if pass_num >= 4 or my_pass_num >= 3:
            return True

        # 6. 保护残血队友（≤6张且对手也≤6）
        if numoffri <= 6 and numofgreaterPos <= 6:
            return True

        return False

    def _single_passive(self, message, action_list, handcards):
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        cur_rank = message.get("curRank", "2")
        cur_rank_val = self._get_rank_value(action_rank, cur_rank)

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                if self._validate_action_cards(action, handcards):
                    return i

        # 没有更高单张→判断是否值得用炸弹
        if self._should_bomb_this_action(message, cur_rank_val, 14, 'Single'):
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    if self._validate_action_cards(action, handcards):
                        return i

        return 0

    def _pair_passive(self, message, action_list):
        cur_rank = message.get("curRank", "2")
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        cur_rank_val = self._get_rank_value(action_rank, cur_rank)
        handcards = message.get("handCards", [])

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                if len(action) > 1:
                    act_val = self._get_rank_value(action[1], cur_rank)
                    if act_val > cur_rank_val:
                        if self._validate_action_cards(action, handcards):
                            return i

        # 没有更高对子→判断是否值得用炸弹
        if self._should_bomb_this_action(message, cur_rank_val, 14, 'Pair'):
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    if self._validate_action_cards(action, handcards):
                        return i

        return 0

    def _other_passive(self, message, action_list):
        """其他牌型（Trips/ThreeWithTwo等）：按牌型匹配，不到万不得已不用炸弹。"""
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        cur_rank_param = message.get("curRank", "2")
        handcards = message.get("handCards", [])
        action_rank_val = self._get_rank_value(cur_rank, cur_rank_param)

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_type:
                if len(action) > 1:
                    act_val = self._get_rank_value(action[1], cur_rank_param)
                    if act_val > action_rank_val:
                        if self._validate_action_cards(action, handcards):
                            return i

        # 没有更高同类型→判断是否值得用炸弹
        if self._should_bomb_this_action(message, action_rank_val, 14, cur_type):
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    if self._validate_action_cards(action, handcards):
                        return i

        return 0


class M2MidEarlyActiveHandler(BasePhaseHandler):
    """M2 中局前期主动出牌处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None

    def handle(self, message: Dict) -> int:
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        if not action_list:
            return 0

        one_hand = self._check_one_hand_complete(action_list, handcards)
        if one_hand is not None:
            return one_hand

        # M2修复：主动出牌选最低牌，非首项（server按从高到低排序）
        return self._get_lowest_non_bomb_index(action_list, handcards)


class M2MidEarlyPassiveHandler(BasePhaseHandler):
    """
    M2 中局前期被动出牌处理器
    核心变化：不调用 _apply_team_strategies()，保护逻辑完全内联
    参考 lalala 的 Single/Pair/Trips 式精确分支
    """

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        """M2：仅加载分析工具，不加载分数累积式保护策略"""
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            from .card_power_evaluator import calculate_card_power
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
            self.calculate_power = calculate_card_power
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None
            self.calculate_power = None

    def _extract_game_state(self, message: Dict) -> Dict:
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)

        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        opponent_rest_cards_list = list(DEFAULT_ALL_REST_LIST)
        teammate_rest_cards = DEFAULT_REST_CARDS

        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                if i != my_pos:
                    rest = info.get("rest", DEFAULT_REST_CARDS)
                    if i < len(opponent_rest_cards_list):
                        opponent_rest_cards_list[i] = rest
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest

        power = 5.0
        if self.calculate_power and handcards:
            power_result = self.calculate_power(handcards, game_phase='mid', opponent_rest_cards=min(opponent_rest_cards_list))
            power = power_result.get('total_power', 5.0)

        return {
            'my_rest': my_rest,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'power': power,
            'my_pos': my_pos
        }

    def _is_teammate(self, pos: int, my_pos: int) -> bool:
        if pos == -1 or my_pos == -1:
            return False
        return (my_pos in [0, 2] and pos in [0, 2]) or (my_pos in [1, 3] and pos in [1, 3])

    def handle(self, message: Dict) -> int:
        """
        M2 handle() — 不调用 _apply_team_strategies()
        保护逻辑完全由按牌型分发的 _handle_single_passive 等内联处理
        """
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")

        if not action_list or not cur_action:
            return 0

        state = self._extract_game_state(message)
        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        greater_pos = message.get("greaterPos", -1)
        my_pos = state['my_pos']
        is_teammate = self._is_teammate(greater_pos, my_pos)

        # M2：队友出牌时，仅当无任何非 PASS 可选才 PASS（精确条件，非分数累积）
        if is_teammate:
            if not self._action_list_has_non_pass(action_list):
                return 0

        # 对手出牌，按牌型分发（每个分支内已内联保护逻辑）
        if cur_action_type == 'Single':
            return self._handle_single_passive(message, action_list, state, greater_pos, my_pos)
        elif cur_action_type == 'Pair':
            return self._handle_pair_passive(message, action_list, state, greater_pos, my_pos)
        else:
            return self._handle_other_passive(message, action_list, state)

    def _handle_single_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """
        单张被动出牌 — 集成 lalala 精确分支逻辑
        保护逻辑内联，无分数累积
        """
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""

        cur_rank = message.get("curRank", "2")
        handcards = message.get("handCards", [])
        rank_card = 'H' + cur_rank

        pass_num = message.get("pass_num", 0)
        my_pass_num = message.get("my_pass_num", 0)

        public_info = message.get("publicInfo", [])
        numofplayers = list(DEFAULT_ALL_REST_LIST)
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                numofplayers[i] = info.get("rest", DEFAULT_REST_CARDS)

        numofnext = numofplayers[(my_pos + 1) % 4]
        numofpre = numofplayers[(my_pos - 1) % 4]
        numoffri = numofplayers[(my_pos + 2) % 4]
        numofgreaterPos = numofplayers[greater_pos] if greater_pos >= 0 else DEFAULT_REST_CARDS

        cur_rank_val = self._get_rank_value(action_rank, cur_rank)
        max_val = 14
        rest_cards = message.get("remainCards", [])
        if rest_cards and len(rest_cards) > 0:
            last_card = rest_cards[-1] if isinstance(rest_cards[-1], list) else rest_cards[-1]
            if isinstance(last_card, list) and len(last_card) > 0:
                last_card_str = last_card[0] if isinstance(last_card[0], str) else str(last_card[0])
                if len(last_card_str) >= 2:
                    max_val = self._get_rank_value(last_card_str[1], cur_rank)

        card_val = self._build_card_value_map(cur_rank)

        hand_structure = self._analyze_hand_structure_detailed(handcards, cur_rank)
        single_member = hand_structure['single_member']
        pair_member = hand_structure['pair_member']
        trip_member = hand_structure['trip_member']
        bomb_member = hand_structure['bomb_member']
        straight_member = hand_structure['straight_member']
        sorted_cards = hand_structure['sorted_cards']
        bomb_info = hand_structure['bomb_info']

        single_action_list = []
        bomb_action_list = []
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] == 'Single':
                    single_action_list.append((i, action))
                elif action[0] == 'Bomb':
                    bomb_action_list.append((i, action))

        # ⭐ 残局/关键阶段（下家≤6或上家≤5）
        if numofnext <= 6 or (numofpre <= 5 and numofpre >= 1):
            if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= max_val:
                return 0
            if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= 15 and numofnext != 1:
                return 0

            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val and first_card in single_member and rank_card not in action_cards:
                            if self._validate_action_cards(action, handcards):
                                return i

            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val and first_card not in bomb_member and rank_card not in action_cards:
                            if not self._is_in_straight(action, straight_member):
                                if self._validate_action_cards(action, handcards):
                                    return i

            bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
            if bomb_index != -1:
                return bomb_index

            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val - 1 and first_card not in bomb_member and rank_card not in action_cards:
                            if not self._is_in_straight(action, straight_member):
                                if self._validate_action_cards(action, handcards):
                                    return i

        # ⭐ 队友是最大动作者（精确边界控制，无分数累积）
        if (my_pos + 2) % 4 == greater_pos:
            if cur_rank_val >= 14 or cur_rank_val >= max_val - 1:
                return 0

            if numoffri <= 6:
                index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                if index == -1:
                    return 0
                if cur_rank_val <= 10:
                    return index
                else:
                    selected_action = action_list[index] if index < len(action_list) else None
                    if selected_action and len(selected_action) > 1:
                        selected_rank_val = card_val.get(selected_action[1], 0)
                        if selected_rank_val == cur_rank_val + 1:
                            return index
            else:
                index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                if index != -1:
                    return index
                else:
                    return 0

        # ⭐ 对手是最大动作者
        else:
            index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
            if index != -1:
                return index

            # PASS 次数降级链（M2：更早触发）
            if pass_num >= 4 or my_pass_num >= 2:
                index = self._special_strategy(single_action_list, bomb_member, straight_member, rank_card, card_val, action_list)
                if index != -1:
                    return index

            # ═══════════════════════════════════════
            # 不宜出炸门控：炸中局单张，不到顶牌点不炸、敌剩4张不炸、牌型不明不炸
            # ═══════════════════════════════════════
            if cur_rank_val >= 14 or pass_num >= 4:
                cur_bomb_num = self._cal_bomb_num(sorted_cards, handcards, rank_card)
                if cur_rank_val >= max_val and numofgreaterPos >= 15 and cur_bomb_num > 1:
                    bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                    if bomb_index != -1:
                        return bomb_index
                elif ((cur_rank_val >= 15 or cur_rank_val >= max_val - 1) and numofgreaterPos <= 15) or pass_num >= 6 or my_pass_num >= 4:
                    bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                    if bomb_index != -1:
                        return bomb_index
                    else:
                        return 0

        # 降级路径：多余单张 → 拆对子 → 级牌/王 → 其他单张
        suitable_singles = self._find_excess_singles_for_action(message, action_rank)
        if suitable_singles:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1 and action[1] in suitable_singles:
                        if self._validate_action_cards(action, handcards):
                            return i

        from collections import Counter
        handcard_counts = Counter(handcards)
        high_ranks = ['T', 'J', 'Q', 'K', 'A']
        high_pairs = []
        for rank_char in high_ranks:
            rank_count = sum(1 for card in handcards if len(card) >= 2 and card[1] == rank_char)
            if rank_count >= 2:
                high_pairs.append(rank_char)

        if high_pairs:
            preferred_ranks = ['J', 'K', 'Q', 'T', 'A']
            for preferred_rank in preferred_ranks:
                if preferred_rank in high_pairs:
                    for i, action in enumerate(action_list):
                        if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                            if len(action) > 1:
                                action_rank_str = action[1]
                                if action_rank_str == preferred_rank:
                                    action_rank_val = self._get_rank_value(action_rank_str, cur_rank)
                                    if action_rank_val > cur_rank_val:
                                        if self._validate_action_cards(action, handcards):
                                            return i

        my_rest = len(handcards) if handcards else CARDS_PER_PLAYER
        is_endgame = my_rest <= 10
        if is_endgame:
            level_card_rank = cur_rank
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1:
                        action_rank_str = action[1]
                        if action_rank_str == level_card_rank or action_rank_str == 'B' or action_rank_str == 'R':
                            action_rank_val = self._get_rank_value(action_rank_str, cur_rank)
                            if action_rank_val > cur_rank_val:
                                if self._validate_action_cards(action, handcards):
                                    return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                if len(action) > 1:
                    if not self._validate_action_cards(action, handcards):
                        continue
                    action_rank_val = self._get_rank_value(action[1], cur_rank)
                    if action_rank_val > cur_rank_val:
                        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
                        is_split = False
                        for card in action_cards:
                            if len(card) >= 2:
                                card_rank = card[1] if len(card) == 2 else card[1:]
                                rank_count = sum(1 for hc in handcards if len(hc) >= 2 and hc[1] == card_rank)
                                if rank_count >= 3:
                                    is_split = True
                                    break
                        if not is_split:
                            return i

        return self._default_passive_action(action_list, message)

    def _handle_pair_passive(self, message: Dict, action_list: List, state: Dict, greater_pos: int, my_pos: int) -> int:
        """对子被动出牌"""
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        is_teammate = self._is_teammate(greater_pos, my_pos)

        if is_teammate and not self._action_list_has_non_pass(action_list):
            return 0

        cur_rank = message.get("curRank", "2")
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Pair':
                if len(action) > 1:
                    action_rank_val = self._get_rank_value(action[1], cur_rank)
                    cur_rank_val = self._get_rank_value(action_rank, cur_rank)
                    if action_rank_val > cur_rank_val:
                        return i

        return self._default_passive_action(action_list, message)

    def _handle_other_passive(self, message: Dict, action_list: List, state: Dict) -> int:
        """其他牌型被动出牌"""
        cur_action = message.get("curAction", [])
        cur_type = cur_action[0] if len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        cur_rank_param = message.get("curRank", "2")
        handcards = message.get("handCards", [])

        if cur_type == 'ThreeWithTwo':
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'ThreeWithTwo':
                    if len(action) > 1:
                        action_rank_val = self._get_rank_value(action[1], cur_rank_param)
                        cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param)
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                return i
            fallback_types = ['Trips', 'ThreePair', 'TwoTrips', 'Straight', 'Pair', 'Single']
            for fallback_type in fallback_types:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        if self._validate_action_cards(action, handcards):
                            return i

        elif cur_type == 'Bomb':
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Bomb':
                    if len(action) > 1:
                        action_rank_val = self._get_rank_value(action[1], cur_rank_param)
                        cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param)
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                return i
            fallback_types = ['ThreeWithTwo', 'Trips', 'ThreePair', 'TwoTrips', 'Straight', 'Pair', 'Single']
            for fallback_type in fallback_types:
                for i, action in enumerate(action_list):
                    if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                        if self._validate_action_cards(action, handcards):
                            return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_type:
                if len(action) > 1:
                    action_rank_val = self._get_rank_value(action[1], cur_rank_param)
                    cur_rank_val = self._get_rank_value(cur_rank, cur_rank_param)
                    if action_rank_val > cur_rank_val:
                        if self._validate_action_cards(action, handcards):
                            return i

        return self._default_passive_action(action_list, message)

    def _default_passive_action(self, action_list: List, message: Dict = None) -> int:
        """默认被动动作选择（第一个非 PASS 非炸弹）"""
        handcards = message.get("handCards", []) if message else []
        # M2修复：被动出牌默认不炸弹，除非有理由
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] in ("PASS", "Bomb"):
                    continue
                if handcards and hasattr(self, '_validate_action_cards'):
                    if self._validate_action_cards(action, handcards):
                        return i
                else:
                    return i
            elif action != "PASS":
                return i
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] not in ("PASS", "Bomb"):
                return i
            elif action != "PASS":
                return i
        return 0


class M2MidLateActiveHandler(BasePhaseHandler):
    """M2 中局后期主动出牌处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None

    def handle(self, message: Dict) -> int:
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        if not action_list:
            return 0
        one_hand = self._check_one_hand_complete(action_list, handcards)
        if one_hand is not None:
            return one_hand
        # M2修复：主动出牌选最低牌
        return self._get_lowest_non_bomb_index(action_list, handcards)


class M2MidLatePassiveHandler(M2MidEarlyPassiveHandler):
    """M2 中局后期被动 — 继承 M2MidEarlyPassiveHandler"""
    pass


class M2EndgameEarlyActiveHandler(BasePhaseHandler):
    """M2 残局前期主动出牌处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            from .card_power_evaluator import calculate_card_power
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
            self.calculate_power = calculate_card_power
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None
            self.calculate_power = None

    def handle(self, message: Dict) -> int:
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        if not action_list:
            return 0
        one_hand = self._check_one_hand_complete(action_list, handcards)
        if one_hand is not None:
            return one_hand
        # M2修复：主动出牌选最低牌；残局≤6手牌时优先一手出完
        my_rest = len(handcards) if handcards else 0
        if my_rest <= 6:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    if self._validate_action_cards(action, handcards):
                        return i
            return self._first_non_pass_index(action_list, handcards)
        return self._get_lowest_non_bomb_index(action_list, handcards)


class M2EndgameEarlyPassiveHandler(BasePhaseHandler):
    """M2 残局前期被动出牌处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            from .card_power_evaluator import calculate_card_power
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
            self.calculate_power = calculate_card_power
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None
            self.calculate_power = None

    def _is_teammate(self, pos: int, my_pos: int) -> bool:
        if pos == -1 or my_pos == -1:
            return False
        return (my_pos in [0, 2] and pos in [0, 2]) or (my_pos in [1, 3] and pos in [1, 3])

    def handle(self, message: Dict) -> int:
        action_list = message.get("actionList", [])
        cur_action = message.get("curAction")
        handcards = message.get("handCards", [])

        if not action_list or not cur_action:
            return 0

        cur_action_type = cur_action[0] if isinstance(cur_action, list) and len(cur_action) > 0 else ""
        cur_rank = cur_action[1] if len(cur_action) > 1 else ""
        cur_rank_str = message.get("curRank", "2")
        my_pos = message.get("myPos", 0)
        greater_pos = message.get("greaterPos", -1)
        is_teammate = self._is_teammate(greater_pos, my_pos)

        # M2：队友出牌仅当无任何非 PASS 才 PASS
        if is_teammate:
            if not self._action_list_has_non_pass(action_list):
                return 0

        if cur_action_type == 'Single':
            return self._single_passive(message, action_list, handcards, cur_rank, cur_rank_str, my_pos, greater_pos)

        # 非单张：按牌型匹配
        one_hand_idx = self._check_one_hand_complete(action_list, handcards)
        if one_hand_idx is not None:
            return one_hand_idx

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == cur_action_type:
                if len(action) > 1 and action[1] > cur_rank:
                    if self._validate_action_cards(action, handcards):
                        return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                if self._validate_action_cards(action, handcards):
                    return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                return i

        return 0

    def _single_passive(self, message, action_list, handcards, cur_rank_str, cur_rank, my_pos, greater_pos):
        cur_action = message.get("curAction", [])
        action_rank = cur_action[1] if len(cur_action) > 1 else ""
        rank_card = 'H' + cur_rank

        pass_num = message.get("pass_num", 0)
        my_pass_num = message.get("my_pass_num", 0)

        public_info = message.get("publicInfo", [])
        numofplayers = list(DEFAULT_ALL_REST_LIST)
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                numofplayers[i] = info.get("rest", DEFAULT_REST_CARDS)

        numofnext = numofplayers[(my_pos + 1) % 4]
        numofpre = numofplayers[(my_pos - 1) % 4]
        numoffri = numofplayers[(my_pos + 2) % 4]
        numofgreaterPos = numofplayers[greater_pos] if greater_pos >= 0 else DEFAULT_REST_CARDS

        cur_rank_val = self._get_rank_value(action_rank, cur_rank)
        max_val = 14
        rest_cards = message.get("remainCards", [])
        if rest_cards and len(rest_cards) > 0:
            last_card = rest_cards[-1] if isinstance(rest_cards[-1], list) else rest_cards[-1]
            if isinstance(last_card, list) and len(last_card) > 0:
                last_card_str = last_card[0] if isinstance(last_card[0], str) else str(last_card[0])
                if len(last_card_str) >= 2:
                    max_val = self._get_rank_value(last_card_str[1], cur_rank)

        card_val = self._build_card_value_map(cur_rank)
        hand_structure = self._analyze_hand_structure_detailed(handcards, cur_rank)
        single_member = hand_structure['single_member']
        bomb_member = hand_structure['bomb_member']
        straight_member = hand_structure['straight_member']
        sorted_cards = hand_structure['sorted_cards']
        bomb_info = hand_structure['bomb_info']

        single_action_list = []
        bomb_action_list = []
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] == 'Single':
                    single_action_list.append((i, action))
                elif action[0] == 'Bomb':
                    bomb_action_list.append((i, action))

        if numofnext <= 6 or (numofpre <= 5 and numofpre >= 1):
            if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= max_val:
                return 0
            if (my_pos + 2) % 4 == greater_pos and cur_rank_val >= 15 and numofnext != 1:
                return 0

            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val and first_card in single_member and rank_card not in action_cards:
                            if self._validate_action_cards(action, handcards):
                                return i

            for i, action in single_action_list:
                if len(action) > 1:
                    action_rank_str = action[1]
                    action_cards = action[2] if len(action) > 2 else []
                    if action_cards and len(action_cards) > 0:
                        first_card = action_cards[0] if isinstance(action_cards[0], str) else str(action_cards[0])
                        action_rank_val = card_val.get(action_rank_str, 0)
                        if action_rank_val >= max_val and first_card not in bomb_member and rank_card not in action_cards:
                            if not self._is_in_straight(action, straight_member):
                                if self._validate_action_cards(action, handcards):
                                    return i

            bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
            if bomb_index != -1:
                return bomb_index

        if (my_pos + 2) % 4 == greater_pos:
            if cur_rank_val >= 14 or cur_rank_val >= max_val - 1:
                return 0
            if numoffri <= 6:
                index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                if index == -1:
                    return 0
                if cur_rank_val <= 10:
                    return index
                else:
                    selected_action = action_list[index] if index < len(action_list) else None
                    if selected_action and len(selected_action) > 1:
                        selected_rank_val = card_val.get(selected_action[1], 0)
                        if selected_rank_val == cur_rank_val + 1:
                            return index
            else:
                index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
                if index != -1:
                    return index
                else:
                    return 0
        else:
            index = self._normal_strategy(single_action_list, single_member, rank_card, card_val, action_list)
            if index != -1:
                return index

            if pass_num >= 4 or my_pass_num >= 2:
                index = self._special_strategy(single_action_list, bomb_member, straight_member, rank_card, card_val, action_list)
                if index != -1:
                    return index

            # ═══════════════════════════════════════
            # 不宜出炸门控：不到顶牌点不炸、敌剩4张不炸、牌型不明不炸
            # ═══════════════════════════════════════
            if cur_rank_val >= 14 or pass_num >= 4:
                cur_bomb_num = self._cal_bomb_num(sorted_cards, handcards, rank_card)
                if cur_rank_val >= max_val and numofgreaterPos >= 15 and cur_bomb_num > 1:
                    bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                    if bomb_index != -1:
                        return bomb_index
                elif ((cur_rank_val >= 15 or cur_rank_val >= max_val - 1) and numofgreaterPos <= 15) or pass_num >= 6 or my_pass_num >= 4:
                    bomb_index = self._choose_bomb(bomb_action_list, handcards, sorted_cards, bomb_info, rank_card, card_val, action_list)
                    if bomb_index != -1:
                        return bomb_index
                    else:
                        return 0

        # 降级路径
        suitable_singles = self._find_excess_singles_for_action(message, action_rank)
        if suitable_singles:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                    if len(action) > 1 and action[1] in suitable_singles:
                        if self._validate_action_cards(action, handcards):
                            return i

        from collections import Counter
        handcard_counts = Counter(handcards)
        high_ranks = ['T', 'J', 'Q', 'K', 'A']
        high_pairs = []
        for rank_char in high_ranks:
            rank_count = sum(1 for card in handcards if len(card) >= 2 and card[1] == rank_char)
            if rank_count >= 2:
                high_pairs.append(rank_char)
        if high_pairs:
            preferred_ranks = ['J', 'K', 'Q', 'T', 'A']
            for preferred_rank in preferred_ranks:
                if preferred_rank in high_pairs:
                    for i, action in enumerate(action_list):
                        if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                            if len(action) > 1:
                                action_rank_str = action[1]
                                if action_rank_str == preferred_rank:
                                    action_rank_val = self._get_rank_value(action_rank_str, cur_rank)
                                    if action_rank_val > cur_rank_val:
                                        if self._validate_action_cards(action, handcards):
                                            return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                if len(action) > 1:
                    action_rank_str = action[1]
                    if action_rank_str == cur_rank or action_rank_str == 'B' or action_rank_str == 'R':
                        action_rank_val = self._get_rank_value(action_rank_str, cur_rank)
                        if action_rank_val > cur_rank_val:
                            if self._validate_action_cards(action, handcards):
                                return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                if len(action) > 1:
                    action_rank_val = self._get_rank_value(action[1], cur_rank)
                    if action_rank_val > cur_rank_val:
                        if self._validate_action_cards(action, handcards):
                            return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] == 'Single':
                if len(action) > 1:
                    if self._validate_action_cards(action, handcards):
                        return i

        fallback_types = ['Pair', 'Trips', 'ThreeWithTwo', 'ThreePair', 'TwoTrips', 'Straight']
        for fallback_type in fallback_types:
            for i, action in enumerate(action_list):
                if isinstance(action, list) and len(action) > 0 and action[0] == fallback_type:
                    if self._validate_action_cards(action, handcards):
                        return i

        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                return i

        return 0


class M2EndgameLateActiveHandler(BasePhaseHandler):
    """M2 残局后期主动出牌处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        try:
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
        except ImportError:
            self.hand_analyzer = None
            self.combination_scanner = None

    def handle(self, message: Dict) -> int:
        action_list = message.get("actionList", [])
        handcards = message.get("handCards", [])
        if not action_list:
            return 0
        one_hand = self._check_one_hand_complete(action_list, handcards)
        if one_hand is not None:
            return one_hand
        # M2修复：主动出牌选最低牌
        return self._get_lowest_non_bomb_index(action_list, handcards)


class M2EndgameLatePassiveHandler(M2EndgameEarlyPassiveHandler):
    """M2 残局后期被动 — 继承 M2EndgameEarlyPassiveHandler"""
    pass


class M2TributeHandler(BasePhaseHandler):
    """M2 进贡处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        pass

    def handle(self, message: Dict) -> int:
        return 0


class M2BackHandler(BasePhaseHandler):
    """M2 还贡处理器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def _init_strategy_engine(self):
        pass

    def handle(self, message: Dict) -> int:
        return 0
