# -*- coding: utf-8 -*-
"""
Hybrid Decision Engine V5
混合决策引擎 V5版本

专为V5客户端设计的独立决策引擎，摆脱V4痕迹

3层决策架构：
1. Layer 1: Rule-Based Decision Engine - 基于规则的决策引擎
2. Layer 2: Knowledge Enhanced Decision - 基于知识库的决策增强
3. Layer 3: Random Selection - 保证成功的随机选择
"""

import logging
import random
import time
from typing import Dict, List, Optional


class HybridDecisionEngineV5:
    """
    Core decision engine for V5 clients.
    
    This engine is designed to be independent of V4 codebase,
    providing a clean and modern decision architecture.
    """
    
    def __init__(self, player_id: int, config: dict):
        """
        Initialize the hybrid decision engine.
        
        Args:
            player_id: Player position (0-3)
            config: Configuration dictionary
        """
        self.player_id = player_id
        self.config = config
        
        # Initialize game state manager
        from game_logic.enhanced_state import EnhancedGameStateManager
        self.state = EnhancedGameStateManager()
        
        # Initialize decision layers (lazy initialization)
        self.rule_based_engine = None
        self.knowledge_enhanced = None
        
        # Performance monitoring
        self.stats = DecisionStatistics()
        
        # Logging setup
        self.logger = logging.getLogger(f"HybridV5-P{player_id}")
        self.logger.setLevel(logging.INFO)
        
        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'[%(asctime)s] [P{player_id}] [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.info("HybridDecisionEngineV5 initialized")
    
    def decide(self, message: dict) -> int:
        """
        Make a decision using enhanced architecture (增强模式).
        
        Enhanced Architecture:
        0. Critical Rules (Hard Constraints) - Immediate return if triggered
        1. Generate Candidates (Layer 1) - Multiple candidates from rule-based engine
        2. Knowledge Enhancement (Layer 2) - Score all candidates with knowledge rules
        3. Select Best Action - Choose highest scored candidate
        4. Random Fallback (Guaranteed) - Always succeeds as last resort
        
        Args:
            message: Game state message from server
            
        Returns:
            Action index (0 for PASS, 1+ for play actions)
        """
        start_time = time.time()
        performance_threshold = self.config.get("performance_threshold", 1.0)
        
        # ========== Step 0: Critical Rules Check ==========
        # 在 decide() 开头添加关键规则检查
        # 如果关键规则触发，直接返回动作
        try:
            critical_start = time.time()
            critical_action = self._apply_critical_rules(message)
            critical_duration = time.time() - critical_start
            
            if critical_action is not None:
                duration = time.time() - start_time
                self.stats.record_success("CriticalRules", duration)
                self.logger.info(
                    f"✓ Critical Rule triggered: action={critical_action}, "
                    f"time={duration:.3f}s"
                )
                return critical_action
            
            self.logger.debug(f"No critical rules triggered ({critical_duration:.3f}s)")
            
        except Exception as e:
            # Critical rules should not fail, but log if they do
            self.logger.error(f"Critical rules check failed: {e}", exc_info=True)
            # Continue to normal layers
        
        # ========== Step 1: Generate Candidates ==========
        # 从 Layer 1 (Rule-Based) 生成多个候选动作
        try:
            candidates_start = time.time()
            candidates = self._generate_candidates(message)
            candidates_duration = time.time() - candidates_start
            
            if not candidates:
                # No candidates generated, fall back to random
                self.logger.warning("No candidates generated, using random fallback")
                action = self._random_valid_action(message)
                duration = time.time() - start_time
                self.stats.record_success("Random", duration)
                return action
            
            self.logger.debug(
                f"Generated {len(candidates)} candidates in {candidates_duration:.3f}s "
                f"(from Layer 1)"
            )
            
        except Exception as e:
            # Candidate generation failed, fall back to random
            self.logger.error(f"Candidate generation failed: {e}", exc_info=True)
            action = self._random_valid_action(message)
            duration = time.time() - start_time
            self.stats.record_success("Random", duration)
            return action
        
        # ========== Step 2: Knowledge Enhancement ==========
        # 对所有候选动作应用知识库规则进行评分增强
        try:
            enhance_start = time.time()
            enhanced_candidates = self._enhance_candidates(candidates, message)
            enhance_duration = time.time() - enhance_start
            
            if not enhanced_candidates:
                # Enhancement failed, use original candidates
                self.logger.warning("Enhancement failed, using original candidates")
                enhanced_candidates = candidates
            else:
                self.logger.debug(
                    f"Enhanced {len(enhanced_candidates)} candidates in {enhance_duration:.3f}s "
                    f"(Layer 2 applied)"
                )
                self.stats.record_success("KnowledgeEnhanced", enhance_duration)
            
        except Exception as e:
            # Enhancement failed, use original candidates
            self.logger.error(f"Knowledge enhancement failed: {e}", exc_info=True)
            enhanced_candidates = candidates
        
        # ========== Step 3: Select Best Action ==========
        # 从增强后的候选列表中选择评分最高的动作
        try:
            select_start = time.time()
            best_action = self._select_best(enhanced_candidates)
            select_duration = time.time() - select_start
            
            duration = time.time() - start_time
            
            # Determine which layer provided the final decision
            # (for statistics tracking)
            if len(enhanced_candidates) != len(candidates):
                # Knowledge layer modified candidates
                decision_layer = "KnowledgeEnhanced"
            else:
                # Using original candidates (Rule-based decision)
                decision_layer = "RuleBased"
            
            self.stats.record_success(decision_layer, duration)
            
            # Log decision details
            best_score = next((score for idx, score, _ in enhanced_candidates if idx == best_action), 0)
            best_layer = next((layer for idx, _, layer in enhanced_candidates if idx == best_action), "Unknown")
            
            self.logger.info(
                f"✓ Decision complete: action={best_action} (score={best_score:.1f}, "
                f"layer={best_layer}), candidates={len(candidates)}, time={duration:.3f}s"
            )
            
            return best_action
            
        except Exception as e:
            # Selection failed, fall back to random
            self.logger.error(f"Action selection failed: {e}", exc_info=True)
            action = self._random_valid_action(message)
            duration = time.time() - start_time
            self.stats.record_success("Random", duration)
            return action
    
    # ========== Enhanced Architecture Methods ==========
    
    def _generate_candidates(self, message: dict) -> List[tuple]:
        """
        Generate candidate actions from Layer 1 (Rule-Based Engine).
        
        Returns list of (action_index, base_score, source_layer) tuples.
        
        Args:
            message: Game state message
            
        Returns:
            List of candidates: [(action_idx, score, layer), ...]
        """
        candidates = []
        candidate_indices = set()  # Track unique candidates to avoid duplicates
        
        # ========== Layer 1: Rule-Based Decision ==========
        try:
            rb_candidates = self._try_rule_based(message)  # 返回 List[tuple] (action_idx, score)
            
            for action_idx, score in rb_candidates:
                if action_idx not in candidate_indices:
                    # Rule-Based的候选，保持原有评分，标记来源为RuleBased
                    candidates.append((action_idx, score, "RuleBased"))
                    candidate_indices.add(action_idx)
                    self.logger.debug(f"RuleBased candidate: action={action_idx}, score={score:.1f}")
            
            if rb_candidates:
                self.logger.debug(f"RuleBased generated {len(rb_candidates)} candidate(s)")
            
        except Exception as e:
            self.logger.warning(f"Rule-Based candidate generation failed: {e}")
        
        # ========== Fallback: If no candidates ==========
        # If no candidates, add all valid actions with low scores
        if not candidates:
            action_list = message.get("actionList", [])
            if action_list:
                for idx in range(len(action_list)):
                    candidates.append((idx, 50.0, "Fallback"))
                self.logger.warning(f"Using fallback: all {len(action_list)} actions as candidates")
        
        self.logger.debug(f"Generated {len(candidates)} total candidates from Layer 1")
        return candidates
    
    def _enhance_candidates(self, candidates: List[tuple], message: dict) -> List[tuple]:
        """Enhance candidates using Layer 2 (Knowledge).
        
        Args:
            candidates: List of (action_idx, base_score, layer) tuples
            message: Game state message
            
        Returns:
            Enhanced list of (action_idx, enhanced_score, layer) tuples
        """
        try:
            # Lazy initialization of knowledge enhanced decision engine
            if self.knowledge_enhanced is None:
                from knowledge.knowledge_enhanced_decision import KnowledgeEnhancedDecisionEngine
                self.knowledge_enhanced = KnowledgeEnhancedDecisionEngine(self.state)
            
            # Enhance candidates using knowledge rules
            enhanced_candidates = self.knowledge_enhanced.enhance_candidates(candidates, message)
            
            self.logger.debug(f"Enhanced {len(candidates)} candidates to {len(enhanced_candidates)} candidates")
            return enhanced_candidates
        except Exception as e:
            # If knowledge enhancement fails, return original candidates
            self.logger.warning(f"Knowledge enhancement failed: {e}")
            return candidates
    
    def _select_best(self, candidates: List[tuple]) -> int:
        """
        Select the best action from enhanced candidates.
        
        Args:
            candidates: List of (action_idx, score, layer) tuples
            
        Returns:
            Best action index
        """
        if not candidates:
            return 0  # PASS as fallback
        
        # Sort by score (descending)
        sorted_candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
        
        # Return best action
        best_action, best_score, best_layer = sorted_candidates[0]
        
        self.logger.debug(
            f"Best action: {best_action} (score={best_score:.1f}, layer={best_layer})"
        )
        
        return best_action
    
    def _try_rule_based(self, message: dict) -> List[tuple]:
        """
        Try Rule-Based decision layer and return candidate actions.
        
        Args:
            message: Game state message
            
        Returns:
            List of (action_idx, score) tuples, sorted by score descending
            Returns empty list if Rule-Based fails or returns None
        """
        candidates = []
        
        try:
            # 延迟初始化RuleBasedEngine（首次使用时）
            if self.rule_based_engine is None:
                from decision.decision_engine import DecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                # 创建状态管理器
                state_manager = EnhancedGameStateManager()
                self.rule_based_engine = DecisionEngine(state_manager)
                self.logger.info("DecisionEngine initialized (lazy)")
            
            # 获取所有评估结果（top-k）- 修复：从3个增加到5个
            evaluations = self._get_top_evaluations(message, top_k=5)
            
            if evaluations:
                # 将评估结果转换为候选列表
                candidates = evaluations
                self.logger.debug(
                    f"RuleBased generated {len(candidates)} candidates: "
                    f"{[idx for idx, _ in candidates[:3]]}..."
                )
            else:
                # 如果获取评估失败，尝试使用decide()方法获取单一动作
                action = self.rule_based_engine.decide(message)
                
                # 验证返回的action有效性
                action_list = message.get("actionList", [])
                if not action_list:
                    if action == 0:
                        candidates.append((0, 80.0))
                        return candidates
                    else:
                        self.logger.warning(f"Invalid action {action} for empty actionList")
                        return []
                
                # 检查action是否为整数
                if not isinstance(action, int):
                    self.logger.warning(f"Action {action} is not an integer")
                    return []
                
                # 检查action是否在有效范围内
                if 0 <= action < len(action_list):
                    candidates.append((action, 80.0))
                    self.logger.debug(f"RuleBased fallback: single candidate {action}")
                else:
                    self.logger.warning(f"Action {action} out of range [0, {len(action_list)})")
                    return []
            
            return candidates
                
        except Exception as e:
            # 错误处理：捕获异常，返回空列表
            self.logger.error(f"Rule-Based decision error: {e}", exc_info=True)
            return []
    
    def _get_top_evaluations(self, message: dict, top_k: int = 8) -> List[tuple]:
        """
        Get top-k evaluated actions from Rule-Based Engine.
        
        This method directly accesses DecisionEngine's evaluator to get
        multiple high-scoring candidates instead of just the best one.
        
        Args:
            message: Game state message
            top_k: Number of top candidates to return
            
        Returns:
            List of (action_idx, score) tuples, sorted by score descending
        """
        try:
            # Ensure RuleBasedEngine is initialized
            if self.rule_based_engine is None:
                from decision.decision_engine import DecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                state_manager = EnhancedGameStateManager()
                self.rule_based_engine = DecisionEngine(state_manager)
            
            # Get action list
            action_list = message.get("actionList", [])
            if not action_list:
                return []
            
            # Get current action for passive decision
            cur_action = message.get("curAction")

            # 构建游戏上下文，用于动态评估
            game_context = {
                'player_cards': message.get('handCards', []),
                'current_round': message.get('curRound', 1),
                'stage': message.get('stage', 'play'),
                'game_phase': self._analyze_game_phase(message)
            }

            # Use DecisionEngine's evaluator to get all evaluations with dynamic context
            evaluations = self.rule_based_engine.evaluator.evaluate_all_actions(
                action_list, cur_action, game_context
            )
            
            # Sort by score descending and take top-k
            sorted_evaluations = sorted(evaluations, key=lambda x: x[1], reverse=True)
            top_evaluations = sorted_evaluations[:top_k]

            # 修复：确保动作多样性，避免所有候选都是低分动作
            top_evaluations = self._ensure_action_diversity(top_evaluations, sorted_evaluations)

            return top_evaluations
            
        except Exception as e:
            self.logger.debug(f"Failed to get top evaluations: {e}")
            return []

    def _ensure_action_diversity(self, top_evaluations: List[tuple], all_evaluations: List[tuple]) -> List[tuple]:
        """
        确保动作多样性，避免所有候选都是低分动作

        Args:
            top_evaluations: 当前的top-k评估结果
            all_evaluations: 所有的评估结果

        Returns:
            多样化后的评估结果
        """
        if not top_evaluations or len(all_evaluations) <= len(top_evaluations):
            return top_evaluations

        # 降低高分阈值，确保有更多高分动作被考虑
        high_score_threshold = 0.3  # 从0.4降到0.3，更容易触发
        high_score_actions = [eval for eval in all_evaluations if eval[1] >= high_score_threshold]

        # 如果有高分动作，强制包含至少两个
        if len(high_score_actions) >= 3:
            # 检查top_evaluations中高分动作的数量
            high_score_in_top = [eval for eval in top_evaluations if eval[1] >= high_score_threshold]
            if len(high_score_in_top) < 2:
                # 需要添加更多高分动作
                missing_count = 2 - len(high_score_in_top)
                additional_high_score = high_score_actions[:missing_count]

                # 移除一些低分动作，添加高分动作
                low_score_in_top = [eval for eval in top_evaluations if eval[1] < high_score_threshold]
                keep_count = len(top_evaluations) - missing_count

                if keep_count > 0:
                    top_evaluations = (high_score_in_top + low_score_in_top[:keep_count] + additional_high_score)
                else:
                    top_evaluations = high_score_in_top + additional_high_score

                top_evaluations.sort(key=lambda x: x[1], reverse=True)

        # 确保不全是PASS - 更严格的要求
        non_pass_actions = [eval for eval in all_evaluations if eval[0] != 0]  # 0是PASS
        pass_only_threshold = len(top_evaluations) // 2  # 最多只允许一半是PASS

        if len(non_pass_actions) >= 2:
            non_pass_in_top = [eval for eval in top_evaluations if eval[0] != 0]
            if len(non_pass_in_top) < max(1, pass_only_threshold):
                # 非PASS动作太少，强制添加
                additional_non_pass = non_pass_actions[:2]  # 至少添加2个非PASS动作
                # 移除一些PASS动作
                pass_actions = [eval for eval in top_evaluations if eval[0] == 0]
                keep_pass_count = max(0, len(top_evaluations) - len(additional_non_pass) - len(non_pass_in_top))

                top_evaluations = (non_pass_in_top + pass_actions[:keep_pass_count] + additional_non_pass)
                top_evaluations.sort(key=lambda x: x[1], reverse=True)

        return top_evaluations

    def _analyze_game_phase(self, message: dict) -> str:
        """分析游戏阶段

        Args:
            message: 游戏状态消息

        Returns:
            游戏阶段: 'early', 'mid', 'late'
        """
        hand_cards = message.get('handCards', [])
        remaining_count = len(hand_cards)

        if remaining_count >= 15:
            return 'early'  # 早期：15张以上
        elif remaining_count >= 8:
            return 'mid'    # 中期：8-14张
        else:
            return 'late'   # 后期：7张以下

    def _random_valid_action(self, message: dict) -> int:
        """
        Guaranteed fallback: select random valid action.
        
        This method MUST ALWAYS succeed and return a valid action.
        Multiple safety checks ensure it never fails.
        
        Args:
            message: Game state message
            
        Returns:
            Random action index from actionList (guaranteed valid)
        """
        try:
            # Safety check 1: Validate message is a dict
            if not isinstance(message, dict):
                self.logger.error(f"Invalid message type: {type(message)}, returning 0")
                return 0
            
            # Safety check 2: Get actionList with default
            action_list = message.get("actionList", [])
            
            # Safety check 3: Handle empty or invalid actionList
            if not action_list or not isinstance(action_list, list):
                self.logger.warning("Empty or invalid actionList, returning 0 (PASS)")
                return 0
            
            # Safety check 4: Ensure actionList has valid length
            list_length = len(action_list)
            if list_length <= 0:
                self.logger.warning("actionList length <= 0, returning 0 (PASS)")
                return 0
            
            # Select random action from available actions
            # Use modulo as extra safety to ensure valid index
            action_index = random.randint(0, list_length - 1)
            action_index = action_index % list_length  # Extra safety
            
            self.logger.debug(f"Random selection from {list_length} actions: {action_index}")
            return action_index
            
        except Exception as e:
            # CRITICAL: Even random selection failed
            # This should be impossible, but handle it anyway
            self.logger.critical(
                f"CRITICAL: Random selection failed: {e}. Returning 0 (PASS) as emergency fallback",
                exc_info=True
            )
            return 0
    
    def get_statistics(self) -> dict:
        """
        Get current statistics summary.
        
        Returns:
            Statistics dictionary
        """
        return self.stats.get_summary()
    
    def reset_statistics(self):
        """Reset statistics for new game."""
        self.stats.reset()
        self.logger.info("Statistics reset")
    
    # ========== Critical Rules Layer ==========
    
    def _apply_critical_rules(self, message: dict) -> Optional[int]:
        """
        Apply critical rules (hard constraints).
        
        These rules handle situations that require immediate action:
        1. Teammate protection (let teammate win)
        2. Opponent suppression (prevent opponent from winning)
        3. Tribute phase protection (avoid giving away key cards)
        
        Args:
            message: Game state message
            
        Returns:
            Action index if a critical rule is triggered, None otherwise
        """
        # Extract game state information
        action_list = message.get("actionList", [])
        if not action_list:
            return None
        
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        greater_pos = message.get("greaterPos", -1)
        cur_pos = message.get("curPos", -1)
        stage = message.get("stage", "")
        
        # Calculate positions
        teammate_pos = (my_pos + 2) % 4
        next_pos = (my_pos + 1) % 4
        prev_pos = (my_pos - 1) % 4
        
        # Get remaining cards for all players
        cards_left = {}
        for i, info in enumerate(public_info):
            if isinstance(info, dict):
                cards_left[i] = info.get('rest', 27)
            else:
                cards_left[i] = 27
        
        # Rule 0: Teammate Passing (传牌) - 最高优先级
        # 当获得出牌权且队友剩一张牌时，优先传单
        action = self._check_teammate_passing(
            message, action_list, teammate_pos, greater_pos, cards_left
        )
        if action is not None:
            return action
        
        # Rule 1: Teammate Protection
        action = self._check_teammate_protection(
            message, action_list, teammate_pos, greater_pos, cards_left
        )
        if action is not None:
            return action
        
        # Rule 2: Opponent Suppression
        action = self._check_opponent_suppression(
            message, action_list, next_pos, prev_pos, cards_left
        )
        if action is not None:
            return action
        
        # Rule 3: Tribute Phase Protection
        action = self._check_tribute_protection(
            message, action_list, stage
        )
        if action is not None:
            return action
        
        # No critical rules triggered
        return None
    
    def _check_teammate_passing(
        self,
        message: dict,
        action_list: List,
        teammate_pos: int,
        greater_pos: int,
        cards_left: dict
    ) -> Optional[int]:
        """
        检查是否需要传牌给队友（传牌技巧）。
        
        根据传牌技巧文档：
        - 明知队友有单王，传单
        - 队友只剩一张牌，放心出小单
        - 对家和下家都只剩一张牌，发级牌完美放走对家
        
        Args:
            message: Game state message
            action_list: Available actions
            teammate_pos: Teammate position
            greater_pos: Position of player with greatest card
            cards_left: Dictionary of remaining cards per player
            
        Returns:
            Action index to pass single card to teammate, None otherwise
        """
        # 检查是否获得出牌权（主动出牌）
        my_pos = message.get("myPos", 0)
        cur_pos = message.get("curPos", -1)
        is_active = (greater_pos == my_pos) or (cur_pos == -1)
        
        if not is_active:
            return None  # 不是主动出牌，不需要传牌
        
        # 检查队友剩余牌数
        teammate_cards = cards_left.get(teammate_pos, 27)
        
        # 关键规则：队友剩一张牌，优先传单
        if teammate_cards == 1:
            # 查找单牌动作（Single类型）
            single_actions = []
            for idx, action in enumerate(action_list):
                if isinstance(action, list) and len(action) >= 1:
                    if action[0] == "Single":
                        single_actions.append((idx, action))
            
            if single_actions:
                # 优先选择最小的单牌传队友（根据传牌技巧：队友只剩一张牌，放心出小单）
                # 但也要考虑不能给下家顺牌
                best_single = None
                best_idx = None
                
                for idx, action in single_actions:
                    if len(action) >= 2:
                        card_rank = action[1]
                        # 优先选择小单（3-9），避免给下家顺牌
                        if card_rank in ['3', '4', '5', '6', '7', '8', '9']:
                            if best_single is None or self._compare_card_rank(card_rank, best_single) < 0:
                                best_single = card_rank
                                best_idx = idx
                
                # 如果没有小单，选择最小的单牌
                if best_idx is None and single_actions:
                    best_idx = single_actions[0][0]
                
                if best_idx is not None:
                    self.logger.info(
                        f"[Critical Rule] Teammate passing: teammate has 1 card, "
                        f"pass single card (action={best_idx})"
                    )
                    return best_idx
        
        # 检查：对家和下家都只剩一张牌，发级牌
        next_pos = (my_pos + 1) % 4
        next_cards = cards_left.get(next_pos, 27)
        if teammate_cards == 1 and next_cards == 1:
            # 查找级牌单张
            level_card_actions = []
            for idx, action in enumerate(action_list):
                if isinstance(action, list) and len(action) >= 1:
                    if action[0] == "Single" and len(action) >= 3:
                        cards = action[2] if isinstance(action[2], list) else []
                        # 检查是否是级牌（这里简化处理，实际需要根据curRank判断）
                        # 假设级牌是2
                        if any('2' in str(card) for card in cards):
                            level_card_actions.append(idx)
            
            if level_card_actions:
                self.logger.info(
                    f"[Critical Rule] Teammate passing: teammate and lower hand both have 1 card, "
                    f"pass level card (action={level_card_actions[0]})"
                )
                return level_card_actions[0]
        
        return None
    
    def _compare_card_rank(self, rank1: str, rank2: str) -> int:
        """比较两张牌的大小，返回-1表示rank1<rank2，0表示相等，1表示rank1>rank2"""
        rank_order = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A', '2', 'B', 'R']
        try:
            idx1 = rank_order.index(rank1) if rank1 in rank_order else -1
            idx2 = rank_order.index(rank2) if rank2 in rank_order else -1
            if idx1 < idx2:
                return -1
            elif idx1 > idx2:
                return 1
            else:
                return 0
        except:
            return 0
    
    def _check_teammate_protection(
        self, 
        message: dict, 
        action_list: List, 
        teammate_pos: int, 
        greater_pos: int, 
        cards_left: dict
    ) -> Optional[int]:
        """
        Check if we should protect teammate (队友保护).
        
        Conditions:
        - Teammate is leading (has the greatest card)
        - Teammate has few cards left
        - We should PASS to let teammate win
        
        Args:
            message: Game state message
            action_list: Available actions
            teammate_pos: Teammate position
            greater_pos: Position of player with greatest card
            cards_left: Dictionary of remaining cards per player
            
        Returns:
            0 (PASS) if protection is needed, None otherwise
        """
        # Check if teammate is leading
        if greater_pos != teammate_pos:
            return None
        
        # **关键规则：永远不要用炸弹压制队友的炸弹**
        cur_action = message.get("curAction", [])
        if cur_action and len(cur_action) > 0:
            action_type = cur_action[0] if isinstance(cur_action, list) else str(cur_action)
            # 如果队友打了炸弹，绝对不能压制
            if action_type == "Bomb":
                self.logger.info(
                    f"[Critical Rule] Teammate protection: teammate played BOMB, MUST PASS"
                )
                return 0  # PASS
        
        # Check teammate's remaining cards
        teammate_cards = cards_left.get(teammate_pos, 27)
        
        # Critical: Teammate has 1-2 cards (about to win)
        if teammate_cards <= 2:
            self.logger.info(
                f"[Critical Rule] Teammate protection: teammate has {teammate_cards} cards, PASS"
            )
            return 0  # PASS
        
        # Important: Teammate has 3-5 cards (endgame phase)
        if teammate_cards <= 5:
            # Check if current card is high value
            if cur_action and len(cur_action) >= 2:
                try:
                    card_value = self._get_card_value(cur_action[1])
                    # A or higher, let teammate take it
                    if card_value >= 14:
                        self.logger.info(
                            f"[Critical Rule] Teammate protection: teammate has {teammate_cards} cards "
                            f"and high card ({cur_action[1]}), PASS"
                        )
                        return 0  # PASS
                except:
                    pass
        
        # Moderate: Teammate has 6-8 cards (approaching endgame)
        if teammate_cards <= 8:
            # Only PASS if teammate played very high card (2 or Joker)
            if cur_action and len(cur_action) >= 2:
                try:
                    card_value = self._get_card_value(cur_action[1])
                    if card_value >= 15:  # 2 or Joker
                        self.logger.info(
                            f"[Critical Rule] Teammate protection: teammate has {teammate_cards} cards "
                            f"and very high card ({cur_action[1]}), PASS"
                        )
                        return 0  # PASS
                except:
                    pass
        
        return None
    
    def _check_opponent_suppression(
        self, 
        message: dict, 
        action_list: List, 
        next_pos: int, 
        prev_pos: int, 
        cards_left: dict
    ) -> Optional[int]:
        """
        Check if we must suppress opponent (对手压制).
        
        Args:
            message: Game state message
            action_list: Available actions
            next_pos: Next player position
            prev_pos: Previous player position
            cards_left: Dictionary of remaining cards per player
            
        Returns:
            Action index to suppress opponent, None otherwise
        """
        # Check opponents' remaining cards
        next_cards = cards_left.get(next_pos, 27)
        prev_cards = cards_left.get(prev_pos, 27)
        min_opponent_cards = min(next_cards, prev_cards)
        
        # Rule: "火不打四" - Don't bomb when opponent has 4 cards
        if min_opponent_cards == 4:
            return None
        
        # Critical: Opponent has 1-3 cards (about to win)
        if min_opponent_cards <= 3:
            # Must suppress! Find best action to beat current card
            action = self._find_best_beat_action(message, action_list)
            if action is not None and action != 0:
                self.logger.info(
                    f"[Critical Rule] Opponent suppression: opponent has {min_opponent_cards} cards, "
                    f"play action {action}"
                )
                return action
        
        # Important: Opponent has 5 cards
        # Rule: "逢五出对" - Play pair when opponent has 5 cards
        if min_opponent_cards == 5:
            # Check if we're in passive mode
            if message.get("type") == "passive":
                # Try to find a pair to play
                cur_action = message.get("curAction", [])
                if cur_action and cur_action[0] == "Pair":
                    # Current action is pair, try to beat it
                    action = self._find_best_beat_action(message, action_list)
                    if action is not None and action != 0:
                        self.logger.info(
                            f"[Critical Rule] 逢五出对: opponent has 5 cards, "
                            f"beat pair with action {action}"
                        )
                        return action
        
        # Moderate: Opponent has 6-8 cards (approaching endgame)
        if min_opponent_cards <= 8:
            # Only suppress if we're in passive mode and can easily beat
            if message.get("type") == "passive":
                action = self._find_best_beat_action(message, action_list)
                if action is not None and action != 0:
                    # Check if it's a small card (not wasting big cards)
                    action_obj = action_list[action]
                    if len(action_obj) >= 2:
                        try:
                            card_value = self._get_card_value(action_obj[1])
                            if card_value <= 10:  # Small card, safe to play
                                self.logger.info(
                                    f"[Critical Rule] Opponent suppression: opponent has {min_opponent_cards} cards, "
                                    f"beat with small card action {action}"
                                )
                                return action
                        except:
                            pass
        
        return None
    
    def _check_tribute_protection(
        self, 
        message: dict, 
        action_list: List, 
        stage: str
    ) -> Optional[int]:
        """
        Check if we should protect cards during tribute phase.
        
        Conditions:
        - Currently in tribute phase
        - Avoid giving away bombs or key cards
        
        Args:
            message: Game state message
            action_list: Available actions
            stage: Current game stage
            
        Returns:
            Action index if protection is needed, None otherwise
        """
        # Only apply during tribute phase
        if stage != "tribute":
            return None
        
        # During tribute, be conservative
        return None
    
    def _find_best_beat_action(self, message: dict, action_list: List) -> Optional[int]:
        """
        Find the best action to beat the current card.
        
        Strategy:
        - Find the smallest card that can beat current action
        - Avoid using bombs unless necessary
        
        Args:
            message: Game state message
            action_list: Available actions
            
        Returns:
            Action index of best beating card, None if can't beat
        """
        cur_action = message.get("curAction", [])
        if not cur_action or len(cur_action) < 2:
            # No current action to beat, return first non-PASS action
            for idx, action in enumerate(action_list):
                if action[0] != "PASS":
                    return idx
            return None
        
        cur_type = cur_action[0]
        cur_rank = cur_action[1]
        
        # Find all actions that can beat current action
        beating_actions = []
        for idx, action in enumerate(action_list):
            if action[0] == "PASS":
                continue
            
            action_type = action[0]
            action_rank = action[1] if len(action) > 1 else ""
            
            # Same type, higher rank
            if action_type == cur_type:
                try:
                    if self._get_card_value(action_rank) > self._get_card_value(cur_rank):
                        beating_actions.append((idx, action_type, action_rank))
                except:
                    pass
            
            # Bomb beats everything (except bigger bomb)
            if action_type == "Bomb":
                beating_actions.append((idx, action_type, action_rank))
        
        if not beating_actions:
            return None
        
        # Sort by card value (prefer smaller cards)
        # Bombs go last (save them)
        beating_actions.sort(key=lambda x: (
            1 if x[1] == "Bomb" else 0,  # Bombs last
            self._get_card_value(x[2]) if x[2] else 0  # Then by value
        ))
        
        return beating_actions[0][0]
    
    def _get_card_value(self, rank: str) -> int:
        """
        Get numeric value of a card rank.
        
        Args:
            rank: Card rank (e.g., "3", "J", "A", "2")
            
        Returns:
            Numeric value (3-17)
        """
        if not rank:
            return 0
        
        rank_map = {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'T': 10, '10': 10,
            'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            '2': 15,
            'B': 16,  # Small Joker
            'R': 17   # Big Joker
        }
        
        return rank_map.get(str(rank).upper(), 0)


class DecisionStatistics:
    """
    Track decision performance and layer usage statistics.
    """
    
    def __init__(self):
        self.layer_usage = {
            "CriticalRules": {"success": 0, "failure": 0, "total_time": 0.0},
            "RuleBased": {"success": 0, "failure": 0, "total_time": 0.0},
            "KnowledgeEnhanced": {"success": 0, "failure": 0, "total_time": 0.0},
            "Random": {"success": 0, "failure": 0, "total_time": 0.0}
        }
        self.error_log = []
        self.decision_count = 0
    
    def record_success(self, layer: str, duration: float):
        """
        Record successful decision.

        Args:
            layer: Layer name
            duration: Decision duration in seconds
        """
        # 映射策略相关的layer名称到RuleBased层级
        if layer.startswith("Strategy"):
            layer = "RuleBased"

        if layer in self.layer_usage:
            self.layer_usage[layer]["success"] += 1
            self.layer_usage[layer]["total_time"] += duration
            self.decision_count += 1
    
    def record_failure(self, layer: str, error: str):
        """
        Record failed decision attempt.

        Args:
            layer: Layer name
            error: Error message
        """
        # 映射策略相关的layer名称到RuleBased层级
        if layer.startswith("Strategy"):
            layer = "RuleBased"

        if layer in self.layer_usage:
            self.layer_usage[layer]["failure"] += 1
            self.error_log.append({
                "layer": layer,
                "error": error,
                "timestamp": time.time()
            })
    
    def get_layer_success_rate(self, layer: str) -> float:
        """
        Calculate success rate for a layer.
        
        Args:
            layer: Layer name
            
        Returns:
            Success rate (0.0 to 1.0)
        """
        if layer not in self.layer_usage:
            return 0.0
        
        stats = self.layer_usage[layer]
        total = stats["success"] + stats["failure"]
        
        if total == 0:
            return 0.0
        
        return stats["success"] / total
    
    def get_summary(self) -> dict:
        """
        Get statistics summary.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_decisions": self.decision_count,
            "layer_usage": self.layer_usage,
            "success_rates": {
                layer: self.get_layer_success_rate(layer)
                for layer in self.layer_usage.keys()
            },
            "recent_errors": self.error_log[-10:]  # Last 10 errors
        }
    
    def reset(self):
        """Reset statistics for new game."""
        self.layer_usage = {
            "CriticalRules": {"success": 0, "failure": 0, "total_time": 0.0},
            "RuleBased": {"success": 0, "failure": 0, "total_time": 0.0},
            "KnowledgeEnhanced": {"success": 0, "failure": 0, "total_time": 0.0},
            "Random": {"success": 0, "failure": 0, "total_time": 0.0}
        }
        self.error_log = []
        self.decision_count = 0
