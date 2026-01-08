# -*- coding: utf-8 -*-
"""
阶段路由器 (Stage Router)
功能：
- 根据游戏状态和剩余牌数，路由到对应的阶段处理器
- 实现5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
- 支持主动/被动出牌路由
- 支持特殊阶段处理（进贡/还贡）
"""

from typing import Dict, Optional, List, Tuple
from abc import ABC, abstractmethod


class BasePhaseHandler(ABC):
    """阶段处理器基类（优化：统一接口，减少代码重复）"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 初始化策略引擎（延迟导入，避免循环依赖）
        self._init_strategy_engine()
    
    def _init_strategy_engine(self):
        """初始化策略引擎"""
        try:
            from .strategy_engine import (
                TeammateProtectionStrategy,
                PrioritySystem,
                CardValueSystem
            )
            
            # 根据配置选择使用基础协作策略还是增强协作策略
            use_enhanced_collaboration = self.config.get('use_enhanced_collaboration', False)
            base_protection_strategy = TeammateProtectionStrategy(self.config)
            
            if use_enhanced_collaboration:
                try:
                    from .enhanced_collaboration import EnhancedCollaborationStrategy
                    self.teammate_protection = EnhancedCollaborationStrategy(
                        self.config,
                        base_protection_strategy=base_protection_strategy
                    )
                except ImportError:
                    # 如果导入失败，使用基础协作策略
                    self.teammate_protection = base_protection_strategy
            else:
                self.teammate_protection = base_protection_strategy
            from .hand_structure_analyzer import HandStructureAnalyzer
            from .optimal_combination_scanner import OptimalCombinationScanner
            
            # 根据配置选择使用基础协作策略还是增强协作策略（已在上面处理）
            
            # 根据配置选择使用基础优先级系统还是增强优先级系统
            use_enhanced_priority = self.config.get('use_enhanced_priority', False)
            base_priority_system = PrioritySystem(self.config)
            
            if use_enhanced_priority:
                try:
                    from .enhanced_priority_system import EnhancedPrioritySystem
                    self.priority_system = EnhancedPrioritySystem(
                        self.config, 
                        base_priority_system=base_priority_system
                    )
                except ImportError:
                    # 如果导入失败，使用基础优先级系统
                    self.priority_system = base_priority_system
            else:
                self.priority_system = base_priority_system
            
            self.card_value_system = CardValueSystem(
                self.config.get("curRank", "2")
            )
            self.hand_analyzer = HandStructureAnalyzer()
            self.combination_scanner = OptimalCombinationScanner()
        except ImportError as e:
            # 如果导入失败，设置为None，后续可以优雅降级
            self.teammate_protection = None
            self.priority_system = None
            self.card_value_system = None
            self.hand_analyzer = None
            self.combination_scanner = None
    
    @abstractmethod
    def handle(self, message: Dict) -> int:
        """处理出牌（子类实现）"""
        pass
    
    def _check_one_hand_complete(self, action_list: list, handcards: list) -> Optional[int]:
        """检查一手出完（所有阶段都可能需要，但实现可能不同）"""
        for i, action in enumerate(action_list):
            if len(action) > 2 and len(action[2]) == len(handcards):
                return i
        return None
    
    def _scan_hand_combination(self, message: Dict, context: Dict = None) -> Dict:
        """
        扫描手牌最优组合（通用方法，供各阶段使用）
        
        ⚠️ 优化：优先使用context中的手牌信息（如果已构建），确保手牌信息的一致性
        
        Args:
            message: 游戏状态消息
            context: 上下文信息（可选，如果提供则优先使用其中的手牌信息）
            
        Returns:
            扫描结果字典，包含：
            - optimal_combination: 最优组合方案
            - excess_singles: 多余单张列表
            - combination_score: 组合评分
        """
        import logging
        logger = logging.getLogger("BasePhaseHandler")
        
        # ⚠️ 优先使用context中的手牌信息（如果已构建）
        if context and 'handcards' in context:
            handcards = context['handcards']
            rank = context.get('cur_rank', message.get("curRank", "2"))
            logger.debug("使用context中的手牌信息进行扫描")
        else:
            # 降级：从message中获取
            handcards = message.get("handCards", [])
            rank = message.get("curRank", "2")
            logger.debug("从message中获取手牌信息进行扫描")
        
        if not handcards or not hasattr(self, 'combination_scanner') or not self.combination_scanner:
            return {
                'optimal_combination': {},
                'excess_singles': [],
                'combination_score': 0.0,
                'complex_types': {},  # 新增
                'protected_combinations': []  # 新增
            }
        
        try:
            # 构建游戏状态（用于动态调整）
            game_state = {}
            if context:
                game_state = {
                    'opponent_rest_cards': context.get('opponent_rest_cards', 27),
                    'greater_action': context.get('greater_action', []),
                    'game_phase': context.get('game_phase', 'opening')
                }
            
            # 获取动作列表（用于实际动作评估）
            action_list = message.get("actionList", [])
            
            scan_result = self.combination_scanner.scan_optimal_combination(
                handcards, rank, game_state=game_state, action_list=action_list
            )
            logger.debug(f"手牌最优组合扫描: 评分={scan_result.get('combination_score', 0):.1f}, "
                        f"多余单张={len(scan_result.get('excess_singles', []))}张, "
                        f"复杂牌型={len(scan_result.get('complex_types', {}))}种, "
                        f"受保护组合={len(scan_result.get('protected_combinations', []))}个, "
                        f"动作评估={len(scan_result.get('action_evaluations', {}))}个")
            return scan_result
        except Exception as e:
            logger.warning(f"扫描手牌最优组合时出错: {e}")
            return {
                'optimal_combination': {},
                'excess_singles': [],
                'combination_score': 0.0,
                'complex_types': {},  # 新增
                'protected_combinations': []  # 新增
            }
    
    def _find_excess_singles_for_action(self, message: Dict, cur_action_rank: str) -> List[str]:
        """
        找出可以顺走的多余单张（被动出牌时使用）
        
        Args:
            message: 游戏状态消息
            cur_action_rank: 当前动作的牌值
            
        Returns:
            可以顺走的多余单张列表（牌值大于cur_action_rank的单张）
        """
        if not cur_action_rank:
            return []
        
        scan_result = self._scan_hand_combination(message)
        excess_singles = scan_result.get('excess_singles', [])
        
        if not excess_singles:
            return []
        
        # 过滤出牌值大于cur_action_rank的单张
        cur_rank_val = self._get_rank_value(cur_action_rank) if hasattr(self, '_get_rank_value') else 0
        suitable_singles = []
        
        for card in excess_singles:
            card_rank_val = self._get_rank_value(card) if hasattr(self, '_get_rank_value') else 0
            if card_rank_val > cur_rank_val:
                suitable_singles.append(card)
        
        return suitable_singles
    
    def _validate_action_cards(self, action: List, handcards: List) -> bool:
        """
        验证动作中的卡牌是否在手牌中（卡牌一致性检查）
        
        Args:
            action: 动作列表，格式为 [action_type, rank, cards]
            handcards: 当前手牌列表
            
        Returns:
            True: 动作中的所有卡牌都在手牌中
            False: 动作中有卡牌不在手牌中
        """
        import logging
        logger = logging.getLogger("BasePhaseHandler")
        
        if not action or not isinstance(action, list):
            return True  # 无法验证，默认通过
        
        # 提取动作中的卡牌
        action_cards = []
        if len(action) >= 3 and isinstance(action[2], list):
            action_cards = action[2]
        elif len(action) == 2 and isinstance(action[1], list):
            action_cards = action[1]
        elif all(isinstance(card, str) for card in action):
            # 如果action本身就是卡牌列表
            action_cards = action
        
        if not action_cards:
            # 如果没有卡牌（如PASS），直接通过
            return True
        
        # 统计手牌中每张卡牌的数量
        from collections import Counter
        handcard_counts = Counter(handcards)
        action_card_counts = Counter(action_cards)
        
        # 检查动作中的每张卡牌是否都在手牌中
        for card, count in action_card_counts.items():
            if card not in handcard_counts:
                logger.warning(f"卡牌一致性检查失败：动作中的卡牌 {card} 不在手牌中")
                logger.debug(f"动作: {action}, 手牌: {handcards}")
                return False
            if handcard_counts[card] < count:
                logger.warning(f"卡牌一致性检查失败：动作中需要 {count} 张 {card}，但手牌中只有 {handcard_counts[card]} 张")
                logger.debug(f"动作: {action}, 手牌: {handcards}")
                return False
        
        return True
    
    def _filter_valid_actions(self, action_list: List, handcards: List, logger=None) -> Tuple[List, List]:
        """
        过滤有效的动作（验证卡牌一致性）
        
        Args:
            action_list: 原始动作列表
            handcards: 当前手牌
            logger: 日志记录器
            
        Returns:
            (valid_actions, valid_indices) - 有效动作列表和对应的原始索引
        """
        if logger is None:
            import logging
            logger = logging.getLogger("BasePhaseHandler")
        
        valid_actions = []
        valid_indices = []
        
        for i, action in enumerate(action_list):
            if isinstance(action, list) and len(action) > 0:
                if action[0] != "PASS":
                    # ⚠️ 卡牌一致性检查：验证动作中的卡牌是否在手牌中
                    if self._validate_action_cards(action, handcards):
                        valid_actions.append(action)
                        valid_indices.append(i)
                    else:
                        logger.warning(f"Action {i} contains cards not in handcards, skipping: {action}")
                else:
                    # PASS动作也保留
                    valid_actions.append(action)
                    valid_indices.append(i)
            elif action != "PASS":
                valid_actions.append(action)
                valid_indices.append(i)
            else:
                # PASS动作也保留
                valid_actions.append(action)
                valid_indices.append(i)
        
        return valid_actions, valid_indices
    
    def _evaluate_split_impact(self, action: List, handcards: List, rank: str) -> Dict:
        """
        评估拆牌影响
        
        Args:
            action: 动作列表
            handcards: 当前手牌
            rank: 级牌
            
        Returns:
            评估结果字典，包含：
            - is_split: 是否拆牌
            - split_type: 拆牌类型（'pair', 'trips', 'bomb', 'straight'等）
            - impact_score: 影响评分（负数表示负面影响）
        """
        import logging
        logger = logging.getLogger("BasePhaseHandler")
        
        result = {
            'is_split': False,
            'split_type': None,
            'impact_score': 0.0
        }
        
        if not action or not isinstance(action, list) or len(action) < 3:
            return result
        
        action_type = action[0]
        action_cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        
        if not action_cards:
            return result
        
        # 统计手牌中每张牌的数量
        from collections import Counter
        handcard_counts = Counter(handcards)
        
        # 检查是否是拆牌
        for card in action_cards:
            if len(card) >= 2:
                card_rank = card[1] if len(card) == 2 else card[1:]
                card_count = handcard_counts.get(card, 0)
                
                # 如果手牌中有2张或更多相同点数的牌，出单张就是拆对
                if action_type == 'Single' and card_count >= 2:
                    result['is_split'] = True
                    result['split_type'] = 'pair'
                    result['impact_score'] = -30.0  # 拆对子负面影响
                    logger.debug(f"检测到拆对子: {card}")
                    break
                
                # 如果手牌中有3张或更多相同点数的牌，出单张就是拆三张
                if action_type == 'Single' and card_count >= 3:
                    result['is_split'] = True
                    result['split_type'] = 'trips'
                    result['impact_score'] = -50.0  # 拆三张负面影响更大
                    logger.debug(f"检测到拆三张: {card}")
                    break
                
                # 如果手牌中有4张或更多相同点数的牌，出单张就是拆炸弹
                if action_type == 'Single' and card_count >= 4:
                    result['is_split'] = True
                    result['split_type'] = 'bomb'
                    result['impact_score'] = -80.0  # 拆炸弹负面影响最大
                    logger.debug(f"检测到拆炸弹: {card}")
                    break
        
        return result
    
    def _build_context(self, message: Dict) -> Dict:
        """构建上下文信息（供策略引擎使用）"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        cur_rank = message.get("curRank", "2")
        
        # 计算剩余牌数
        my_remain = len(handcards) if handcards else 27
        cards_left = {}
        opponent_rest_cards_list = []
        teammate_rest_cards = 27
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                rest = info.get("rest", 27)
                cards_left[i] = rest
                if i != my_pos:
                    opponent_rest_cards_list.append(rest)
                    # 队友位置：第1个和第3个为一队，第2个和第4个为一队
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        # 判断游戏阶段
        game_phase = "opening"
        if my_remain > 20:
            game_phase = "opening"
        elif my_remain > 15:
            game_phase = "mid_early"
        elif my_remain > 10:
            game_phase = "mid_late"
        elif my_remain > 5:
            game_phase = "endgame_early"
        else:
            game_phase = "endgame_late"
        
        # 判断是否被动出牌
        is_passive = message.get("curAction") is not None and len(message.get("curAction", [])) > 0
        
        return {
            'my_remain': my_remain,
            'cards_left': cards_left,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'cur_rank': cur_rank,
            'my_pos': my_pos,
            'game_phase': game_phase,
            'is_endgame': game_phase in ["endgame_early", "endgame_late"],
            'is_active': not is_passive,
            'is_passive': is_passive,  # ⚠️ 被动出牌标志（供优先级系统使用，允许合理拆牌压制）
            'handcards': handcards,  # ⚠️ 手牌信息（供优先级系统使用）
            'max_remain_value': max(opponent_rest_cards_list) if opponent_rest_cards_list else 15,
            'next_player_remain': cards_left.get((my_pos + 1) % 4, 27),
            'pass_count': message.get("pass_count", 0),
        }


class StageRouter:
    """阶段路由器（优化：阶段细分路由，提升决策质量和速度）"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 初始化各阶段处理器（优化：直接路由到专门处理器）
        self.handlers = {
            # 开局阶段（剩余牌数 > 20）
            'opening_active': None,  # 将在后续实现
            'opening_passive': None,
            # 中局前期（剩余牌数 15-20）
            'mid_early_active': None,
            'mid_early_passive': None,
            # 中局后期（剩余牌数 10-15）
            'mid_late_active': None,
            'mid_late_passive': None,
            # 残局前期（剩余牌数 5-10）
            'endgame_early_active': None,
            'endgame_early_passive': None,
            # 残局后期（剩余牌数 ≤ 5）
            'endgame_late_active': None,
            'endgame_late_passive': None,
        }
        # 特殊阶段处理器
        self.tribute_handler = None  # 将在后续实现
        self.back_handler = None
    
    def set_handlers(self, handlers: Dict[str, BasePhaseHandler]):
        """设置各阶段处理器"""
        self.handlers.update(handlers)
    
    def set_special_handlers(self, tribute_handler=None, back_handler=None):
        """设置特殊阶段处理器"""
        if tribute_handler:
            self.tribute_handler = tribute_handler
        if back_handler:
            self.back_handler = back_handler
    
    def route(self, message: Dict) -> int:
        """路由到对应阶段处理器（优化：直接路由，无额外判断）"""
        stage = message.get("stage", "play")
        handcards = message.get("handCards", [])
        my_remain = len(handcards) if handcards else 0
        
        # 特殊阶段处理（进贡/还贡）
        if stage == "tribute":
            if self.tribute_handler:
                return self.tribute_handler.handle(message)
            return 0
        elif stage == "back":
            if self.back_handler:
                return self.back_handler.handle(message)
            return 0
        
        # 打牌阶段：根据剩余牌数和出牌类型直接路由
        if stage == "play":
            # 判断游戏阶段（优化：在路由层直接判断）
            game_phase = self._get_game_phase(my_remain)
            
            # 判断主动/被动出牌
            is_passive = self._is_passive_play(message)
            
            # 直接路由到专门处理器（优化：一步到位，无额外判断）
            handler_key = f"{game_phase}_{'passive' if is_passive else 'active'}"
            handler = self.handlers.get(handler_key)
            
            if handler:
                action_idx = handler.handle(message)
                action_list = message.get("actionList", [])
                
                # ⚠️ 最终防线：无论handler返回什么，只要有非PASS动作就强制返回第一个非PASS动作
                # 这是最后的保障，确保不会在有可选动作时PASS
                if action_list and len(action_list) > 1:
                    # 检查返回的动作是否是PASS
                    selected_action = action_list[action_idx] if action_idx < len(action_list) else None
                    is_pass = False
                    if selected_action == "PASS":
                        is_pass = True
                    elif isinstance(selected_action, list) and len(selected_action) > 0:
                        if selected_action[0] == "PASS":
                            is_pass = True
                    
                    # 如果返回的是PASS，但actionList中有非PASS动作，强制返回第一个非PASS动作
                    if is_pass:
                        import logging
                        logger = logging.getLogger("StageRouter")
                        logger.warning(f"Handler returned PASS (index {action_idx}), but actionList has {len(action_list)} actions, forcing return first non-PASS action")
                        
                        # ⚠️ 关键修复：必须跳过index 0（因为它是PASS），从index 1开始查找
                        for i in range(1, len(action_list)):
                            action = action_list[i]
                            if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                                logger.warning(f"Forcing return non-PASS action at index {i}: {action[0]}")
                                return i
                            elif action != "PASS":
                                logger.warning(f"Forcing return non-PASS action at index {i}: {action}")
                                return i
                        
                        # 如果从index 1开始都没找到，再检查index 0（虽然它应该是PASS）
                        # 但为了安全，还是检查一下
                        first_action = action_list[0] if action_list else None
                        if first_action and isinstance(first_action, list) and len(first_action) > 0 and first_action[0] != "PASS":
                            logger.warning(f"Forcing return non-PASS action at index 0: {first_action[0]}")
                            return 0
                        elif first_action and first_action != "PASS":
                            logger.warning(f"Forcing return non-PASS action at index 0: {first_action}")
                            return 0
                        
                        logger.error(f"CRITICAL: Handler returned PASS, but no non-PASS action found in actionList of size {len(action_list)}")
                
                return action_idx
        
        return 0
    
    def _get_game_phase(self, my_remain: int) -> str:
        """获取游戏阶段（优化：细分为5个阶段）"""
        if my_remain > 20:
            return "opening"        # 开局
        elif my_remain > 15:
            return "mid_early"      # 中局前期
        elif my_remain > 10:
            return "mid_late"       # 中局后期
        elif my_remain > 5:
            return "endgame_early"  # 残局前期
        else:
            return "endgame_late"   # 残局后期
    
    def _is_passive_play(self, message: Dict) -> bool:
        """判断是否为被动出牌"""
        cur_action = message.get("curAction")
        cur_pos = message.get("curPos", -1)
        greater_pos = message.get("greaterPos", -1)
        
        # 如果curAction是None或空，肯定是主动出牌
        if not cur_action:
            return False
        
        # 如果curAction是字符串，尝试解析
        if isinstance(cur_action, str):
            try:
                import ast
                cur_action = ast.literal_eval(cur_action)
            except (ValueError, SyntaxError):
                # 解析失败，可能是主动出牌
                return False
        
        # 如果curAction是列表，检查第一个元素
        if isinstance(cur_action, list) and len(cur_action) > 0:
            first_elem = cur_action[0]
            # 如果第一个元素是None或"PASS"，可能是主动出牌
            if first_elem is None or first_elem == "PASS":
                # 进一步检查：如果curPos=-1或greaterPos=-1，说明是主动出牌
                if cur_pos == -1 or greater_pos == -1:
                    return False
                # 如果actionList的第一个动作不是PASS，说明是主动出牌
                action_list = message.get("actionList", [])
                if action_list and len(action_list) > 0:
                    first_action = action_list[0]
                    if isinstance(first_action, list) and len(first_action) > 0:
                        if first_action[0] != "PASS":
                            return False
            # 如果第一个元素是有效的动作类型，说明是被动出牌
            elif isinstance(first_elem, str) and first_elem in ["Single", "Pair", "Trips", "ThreeWithTwo", "ThreePair", "TwoTrips", "Straight", "StraightFlush", "Bomb"]:
                return True
        
        # 默认：如果curPos != -1 且 greaterPos != -1，说明是被动出牌
        return cur_pos != -1 and greater_pos != -1

