# -*- coding: utf-8 -*-
"""
Hybrid Decision Engine V4
混合决策引擎 V4版本

4层决策架构：
1. Layer 1: YF Strategy (Primary) - 基于原版策略的增强版本
2. Layer 2: DecisionEngine (Fallback 1) - Evaluation-based
3. Layer 3: Knowledge Enhanced (Fallback 2) - Knowledge base
4. Layer 4: Random Selection (Guaranteed) - Always succeeds
"""

import logging
import random
import time
from typing import Dict, List, Optional


class HybridDecisionEngineV4:
    """
    Core decision engine with 4-layer fallback protection.
    
    This engine ensures that a valid action is always returned,
    even in the face of errors or edge cases.
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
        
        # Initialize decision layers (lazy initialization)
        self.yf_adapter = None
        self.decision_engine = None
        self.knowledge_enhanced = None
        
        # Performance monitoring
        self.stats = DecisionStatistics()
        
        # Logging setup
        self.logger = logging.getLogger(f"HybridV4-P{player_id}")
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
        
        self.logger.info("HybridDecisionEngineV4 initialized")
    
    def decide(self, message: dict) -> int:
        """
        Make a decision using enhanced architecture (增强模式).
        
        Enhanced Architecture (Task 1.2):
        0. Critical Rules (Hard Constraints) - Immediate return if triggered
        1. Generate Candidates (Layer 1 + Layer 2) - Multiple candidates from each layer
        2. Knowledge Enhancement (Layer 3) - Score all candidates with knowledge rules
        3. Select Best Action - Choose highest scored candidate
        4. Random Fallback (Guaranteed) - Always succeeds as last resort
        
        Args:
            message: Game state message from server
            
        Returns:
            Action index (0 for PASS, 1+ for play actions)
        """
        start_time = time.time()
        performance_threshold = self.config.get("performance_threshold", 1.0)
        
        # ========== Step 0: Critical Rules Check (Task 1.2.1 & 1.2.2) ==========
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
        
        # ========== Step 1: Generate Candidates (Task 1.2.3) ==========
        # 修改 Layer 1/2 为候选生成模式
        # 从 Layer 1 (YF) 和 Layer 2 (DecisionEngine) 生成多个候选动作
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
                f"(from Layer 1+2)"
            )
            
        except Exception as e:
            # Candidate generation failed, fall back to random
            self.logger.error(f"Candidate generation failed: {e}", exc_info=True)
            action = self._random_valid_action(message)
            duration = time.time() - start_time
            self.stats.record_success("Random", duration)
            return action
        
        # ========== Step 2: Knowledge Enhancement (Task 1.2.4) ==========
        # 添加 Layer 3 增强评分
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
                    f"(Layer 3 applied)"
                )
                self.stats.record_success("KnowledgeEnhanced", enhance_duration)
            
        except Exception as e:
            # Enhancement failed, use original candidates
            self.logger.error(f"Knowledge enhancement failed: {e}", exc_info=True)
            enhanced_candidates = candidates
        
        # ========== Step 3: Select Best Action (Task 1.2.5) ==========
        # 选择最优动作返回
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
                # Using original candidates
                decision_layer = "Hybrid"
            
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
        Generate candidate actions from Layer 1 (YF) and Layer 2 (DecisionEngine).
        
        Enhanced mode: Generate multiple candidates from each layer for better selection.
        
        Returns list of (action_index, base_score, source_layer) tuples.
        
        Args:
            message: Game state message
            
        Returns:
            List of candidates: [(action_idx, score, layer), ...]
        """
        candidates = []
        candidate_indices = set()  # Track unique candidates to avoid duplicates
        
        # ========== Layer 1: YF Strategy (Task 1.3.1) ==========
        # 修改为调用返回候选列表的方法
        try:
            yf_candidates = self._try_yf(message)  # 现在返回 List[tuple] (action_idx, score)
            
            for action_idx, score in yf_candidates:
                if action_idx not in candidate_indices:
                    # YF的候选，保持原有评分，标记来源为YF
                    candidates.append((action_idx, score, "YF"))
                    candidate_indices.add(action_idx)
                    self.logger.debug(f"YF candidate: action={action_idx}, score={score:.1f}")
            
            if yf_candidates:
                self.logger.debug(f"YF generated {len(yf_candidates)} candidate(s)")
            
        except Exception as e:
            self.logger.warning(f"YF candidate generation failed: {e}")
        
        # ========== Layer 2: DecisionEngine (Task 1.3.2) ==========
        # 修改为调用返回候选列表的方法
        try:
            de_candidates = self._try_decision_engine(message)  # 现在返回 List[tuple] (action_idx, score)
            
            for action_idx, score in de_candidates:
                if action_idx not in candidate_indices:
                    # DecisionEngine的候选，保持原有评分，标记来源为DecisionEngine
                    candidates.append((action_idx, score, "DecisionEngine"))
                    candidate_indices.add(action_idx)
                    self.logger.debug(f"DecisionEngine candidate: action={action_idx}, score={score:.1f}")
            
            if de_candidates:
                self.logger.debug(f"DecisionEngine generated {len(de_candidates)} candidate(s)")
            
        except Exception as e:
            self.logger.warning(f"DecisionEngine candidate generation failed: {e}")
        
        # ========== Fallback: If no candidates ==========
        # If no candidates, add all valid actions with low scores
        if not candidates:
            action_list = message.get("actionList", [])
            if action_list:
                for idx in range(len(action_list)):
                    candidates.append((idx, 50.0, "Fallback"))
                self.logger.warning(f"Using fallback: all {len(action_list)} actions as candidates")
        
        self.logger.debug(f"Generated {len(candidates)} total candidates from Layer 1+2")
        return candidates
    
    def _enhance_candidates(self, candidates: List[tuple], message: dict) -> List[tuple]:
        """
        Enhance candidates using Layer 3 (Knowledge).
        
        Args:
            candidates: List of (action_idx, base_score, layer) tuples
            message: Game state message
            
        Returns:
            Enhanced list of (action_idx, enhanced_score, layer) tuples
        """
        try:
            # Initialize knowledge layer if needed
            if self.knowledge_enhanced is None:
                from knowledge.knowledge_enhanced_decision import KnowledgeEnhancedDecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                state_manager = EnhancedGameStateManager()
                self.knowledge_enhanced = KnowledgeEnhancedDecisionEngine(state_manager)
                self.logger.info("KnowledgeEnhancedDecisionEngine initialized (lazy)")
            
            # Extract action list
            action_list = message.get("actionList", [])
            if not action_list:
                return candidates
            
            # Task 3.1: 使用新的 enhance_candidates() 方法
            # 直接调用公共接口，简化代码
            enhanced_candidates = self.knowledge_enhanced.enhance_candidates(
                candidates, message
            )
            
            return enhanced_candidates
            
        except Exception as e:
            self.logger.error(f"Knowledge enhancement error: {e}", exc_info=True)
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
    
    # ========== Legacy Layer Methods (for candidate generation) ==========
    
    def _try_yf(self, message: dict) -> List[tuple]:
        """
        Try YF decision layer and return candidate actions.
        
        Task 1.3: 修改为返回候选动作列表而非单一动作
        
        Args:
            message: Game state message
            
        Returns:
            List of (action_idx, score) tuples, sorted by score descending
            Returns empty list if YF fails or returns None
        """
        candidates = []
        
        try:
            # 延迟初始化YFAdapter（首次使用时）
            if self.yf_adapter is None:
                from communication.lalala_adapter_v4 import YFAdapter
                self.yf_adapter = YFAdapter(self.player_id)
                self.logger.info("YFAdapter initialized (lazy)")
            
            # Task 2.1: YFAdapter.decide() 现在直接返回候选列表
            yf_candidates = self.yf_adapter.decide(message)
            
            # YFAdapter.decide() 现在返回 List[tuple] 格式
            # 如果返回空列表，表示应该触发Layer 2/3
            if not yf_candidates:
                self.logger.debug("YF returned empty candidates list, triggering Layer 2/3")
                return []
            
            # 验证候选的有效性
            action_list = message.get("actionList", [])
            valid_candidates = []
            
            for action_idx, score in yf_candidates:
                # 验证动作索引有效性
                if action_list:
                    if 0 <= action_idx < len(action_list):
                        valid_candidates.append((action_idx, score))
                    else:
                        self.logger.warning(f"YF candidate {action_idx} out of range [0, {len(action_list)})")
                else:
                    # 空动作列表，只有0（PASS）有效
                    if action_idx == 0:
                        valid_candidates.append((0, score))
                    else:
                        self.logger.warning(f"Invalid action {action_idx} for empty actionList")
            
            if valid_candidates:
                self.logger.debug(f"YF generated {len(valid_candidates)} valid candidate(s)")
                return valid_candidates
            else:
                self.logger.warning("YF candidates all invalid, returning empty list")
                return []
                
        except Exception as e:
            # 错误处理：捕获异常，返回空列表
            self.logger.error(f"YF decision error: {e}", exc_info=True)
            return []
    
    def _try_decision_engine(self, message: dict) -> List[tuple]:
        """
        Try DecisionEngine layer and return candidate actions.
        
        Task 1.3: 修改为返回候选动作列表而非单一动作
        
        Args:
            message: Game state message
            
        Returns:
            List of (action_idx, score) tuples, sorted by score descending
            Returns empty list if DecisionEngine fails
        """
        candidates = []
        
        try:
            # 延迟初始化DecisionEngine（首次使用时）
            if self.decision_engine is None:
                from decision.decision_engine import DecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                # 创建状态管理器
                state_manager = EnhancedGameStateManager()
                self.decision_engine = DecisionEngine(state_manager)
                self.logger.info("DecisionEngine initialized (lazy)")
            
            # 获取所有评估结果（top-k）
            evaluations = self._get_top_evaluations(message, top_k=5)
            
            if evaluations:
                # 将评估结果转换为候选列表
                # 评估结果已经是 (action_idx, score) 格式
                candidates = evaluations
                self.logger.debug(
                    f"DecisionEngine generated {len(candidates)} candidates: "
                    f"{[idx for idx, _ in candidates[:3]]}..."
                )
            else:
                # 如果获取评估失败，尝试使用decide()方法获取单一动作
                action = self.decision_engine.decide(message)
                
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
                    self.logger.debug(f"DecisionEngine fallback: single candidate {action}")
                else:
                    self.logger.warning(f"Action {action} out of range [0, {len(action_list)})")
                    return []
            
            return candidates
                
        except Exception as e:
            # 错误处理：捕获异常，返回空列表
            self.logger.error(f"DecisionEngine decision error: {e}", exc_info=True)
            return []
    
    def _get_top_evaluations(self, message: dict, top_k: int = 3) -> List[tuple]:
        """
        Get top-k evaluated actions from DecisionEngine.
        
        This method directly accesses DecisionEngine's evaluator to get
        multiple high-scoring candidates instead of just the best one.
        
        Args:
            message: Game state message
            top_k: Number of top candidates to return
            
        Returns:
            List of (action_idx, score) tuples, sorted by score descending
        """
        try:
            # Ensure DecisionEngine is initialized
            if self.decision_engine is None:
                from decision.decision_engine import DecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                state_manager = EnhancedGameStateManager()
                self.decision_engine = DecisionEngine(state_manager)
            
            # Get action list
            action_list = message.get("actionList", [])
            if not action_list:
                return []
            
            # Get current action for passive decision
            cur_action = message.get("curAction")
            
            # Use DecisionEngine's evaluator to get all evaluations
            evaluations = self.decision_engine.evaluator.evaluate_all_actions(
                action_list, cur_action
            )
            
            # Sort by score descending and take top-k
            sorted_evaluations = sorted(evaluations, key=lambda x: x[1], reverse=True)
            top_evaluations = sorted_evaluations[:top_k]
            
            return top_evaluations
            
        except Exception as e:
            self.logger.debug(f"Failed to get top evaluations: {e}")
            return []
    
    def _try_knowledge_enhanced(self, message: dict) -> Optional[int]:
        """
        Try knowledge-enhanced layer.
        
        Args:
            message: Game state message
            
        Returns:
            Action index if successful, None if failed
        """
        try:
            # 延迟初始化KnowledgeEnhancedDecisionEngine（首次使用时）
            if self.knowledge_enhanced is None:
                from knowledge.knowledge_enhanced_decision import KnowledgeEnhancedDecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                # 创建状态管理器
                state_manager = EnhancedGameStateManager()
                self.knowledge_enhanced = KnowledgeEnhancedDecisionEngine(state_manager)
                self.logger.info("KnowledgeEnhancedDecisionEngine initialized (lazy)")
            
            # 调用knowledge_enhanced.decide(message)
            action = self.knowledge_enhanced.decide(message)
            
            # 验证返回的action有效性
            action_list = message.get("actionList", [])
            if not action_list:
                # 空动作列表，只有0（PASS）有效
                if action == 0:
                    return action
                else:
                    self.logger.warning(f"Invalid action {action} for empty actionList")
                    return None
            
            # 检查action是否为整数
            if not isinstance(action, int):
                self.logger.warning(f"Action {action} is not an integer")
                return None
            
            # 检查action是否在有效范围内
            if 0 <= action < len(action_list):
                return action
            else:
                self.logger.warning(f"Action {action} out of range [0, {len(action_list)})")
                return None
                
        except Exception as e:
            # 错误处理：捕获异常，返回None
            self.logger.error(f"KnowledgeEnhanced decision error: {e}", exc_info=True)
            return None
    
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
        
        Based on knowledge base: 传牌技巧 - 残局传牌
        
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
            cur_action = message.get("curAction", [])
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
            cur_action = message.get("curAction", [])
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
        
        Based on knowledge base:
        - "火不打四" (Don't bomb when opponent has 4 cards)
        - "逢五出对" (Play pair when opponent has 5 cards)
        - 残局传牌策略
        
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
        # (likely a bomb itself, waste to bomb it)
        if min_opponent_cards == 4:
            # Don't force bombing, let normal layers handle it
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
        # This is a placeholder - specific logic depends on tribute rules
        # For now, we don't force any specific action
        
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
            "YF": {"success": 0, "failure": 0, "total_time": 0.0},
            "DecisionEngine": {"success": 0, "failure": 0, "total_time": 0.0},
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
            "YF": {"success": 0, "failure": 0, "total_time": 0.0},
            "DecisionEngine": {"success": 0, "failure": 0, "total_time": 0.0},
            "KnowledgeEnhanced": {"success": 0, "failure": 0, "total_time": 0.0},
            "Random": {"success": 0, "failure": 0, "total_time": 0.0}
        }
        self.error_log = []
        self.decision_count = 0



# Add methods to HybridDecisionEngineV4 class
def _add_methods_to_engine():
    """Add reset_statistics and get_statistics methods to HybridDecisionEngineV4"""
    
    def reset_statistics(self):
        """Reset statistics for new game."""
        self.stats.reset()
        self.logger.info("Statistics reset")
    
    def get_statistics(self):
        """Get decision statistics."""
        return self.stats.get_summary()
    
    HybridDecisionEngineV4.reset_statistics = reset_statistics
    HybridDecisionEngineV4.get_statistics = get_statistics

_add_methods_to_engine()
