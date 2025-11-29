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
        Make a decision using enhanced architecture with critical rules.
        
        New Architecture:
        0. Critical Rules (Hard Constraints) - Immediate return
        1. Layer 1: YF (Primary)
        2. Layer 2: DecisionEngine (Fallback 1)
        3. Layer 3: Knowledge Enhanced (Fallback 2)
        4. Layer 4: Random Selection (Guaranteed)
        
        Args:
            message: Game state message from server
            
        Returns:
            Action index (0 for PASS, 1+ for play actions)
        """
        start_time = time.time()
        performance_threshold = self.config.get("performance_threshold", 1.0)
        
        # Layer 0: Critical Rules (Hard Constraints)
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
        
        # Layer 1: YF (Primary)
        try:
            layer_start = time.time()
            action = self._try_yf(message)
            layer_duration = time.time() - layer_start
            
            if action is not None:
                duration = time.time() - start_time
                self.stats.record_success("YF", duration)
                
                # Performance warning
                if layer_duration > performance_threshold:
                    self.logger.warning(
                        f"Layer 1 (YF) slow: {layer_duration:.3f}s > {performance_threshold}s threshold"
                    )
                
                self.logger.info(f"✓ Layer 1 (YF) succeeded: action={action}, time={duration:.3f}s")
                return action
            else:
                self.logger.warning("Layer 1 (YF) returned None, falling back to Layer 2")
                self.stats.record_failure("YF", "Returned None")
                
        except Exception as e:
            duration = time.time() - layer_start
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.logger.error(
                f"✗ Layer 1 (YF) failed after {duration:.3f}s: {error_msg}",
                exc_info=True
            )
            self.stats.record_failure("YF", error_msg)
        
        # Layer 2: DecisionEngine (Fallback 1)
        try:
            layer_start = time.time()
            action = self._try_decision_engine(message)
            layer_duration = time.time() - layer_start
            
            if action is not None:
                duration = time.time() - start_time
                self.stats.record_success("DecisionEngine", duration)
                
                # Performance warning
                if layer_duration > performance_threshold * 1.5:
                    self.logger.warning(
                        f"Layer 2 (DecisionEngine) slow: {layer_duration:.3f}s > {performance_threshold * 1.5}s threshold"
                    )
                
                self.logger.info(f"✓ Layer 2 (DecisionEngine) succeeded: action={action}, time={duration:.3f}s")
                return action
            else:
                self.logger.warning("Layer 2 (DecisionEngine) returned None, falling back to Layer 3")
                self.stats.record_failure("DecisionEngine", "Returned None")
                
        except Exception as e:
            duration = time.time() - layer_start
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.logger.error(
                f"✗ Layer 2 (DecisionEngine) failed after {duration:.3f}s: {error_msg}",
                exc_info=True
            )
            self.stats.record_failure("DecisionEngine", error_msg)
        
        # Layer 3: Knowledge Enhanced (Fallback 2)
        try:
            layer_start = time.time()
            action = self._try_knowledge_enhanced(message)
            layer_duration = time.time() - layer_start
            
            if action is not None:
                duration = time.time() - start_time
                self.stats.record_success("KnowledgeEnhanced", duration)
                
                # Performance warning
                if layer_duration > performance_threshold * 2.0:
                    self.logger.warning(
                        f"Layer 3 (KnowledgeEnhanced) slow: {layer_duration:.3f}s > {performance_threshold * 2.0}s threshold"
                    )
                
                self.logger.info(f"✓ Layer 3 (KnowledgeEnhanced) succeeded: action={action}, time={duration:.3f}s")
                return action
            else:
                self.logger.warning("Layer 3 (KnowledgeEnhanced) returned None, falling back to Layer 4")
                self.stats.record_failure("KnowledgeEnhanced", "Returned None")
                
        except Exception as e:
            duration = time.time() - layer_start
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.logger.error(
                f"✗ Layer 3 (KnowledgeEnhanced) failed after {duration:.3f}s: {error_msg}",
                exc_info=True
            )
            self.stats.record_failure("KnowledgeEnhanced", error_msg)
        
        # Layer 4: Random (Guaranteed - MUST NEVER FAIL)
        try:
            layer_start = time.time()
            action = self._random_valid_action(message)
            layer_duration = time.time() - layer_start
            duration = time.time() - start_time
            
            self.stats.record_success("Random", duration)
            self.logger.warning(
                f"⚠ Layer 4 (Random) used as last resort: action={action}, time={duration:.3f}s"
            )
            return action
            
        except Exception as e:
            # CRITICAL: Layer 4 should NEVER fail
            # If it does, we have a serious problem
            self.logger.critical(
                f"CRITICAL: Layer 4 (Random) failed! This should never happen: {e}",
                exc_info=True
            )
            # Emergency fallback: return 0 (PASS)
            self.logger.critical("Emergency fallback: returning 0 (PASS)")
            return 0
    
    def _try_yf(self, message: dict) -> Optional[int]:
        """
        Try YF decision layer.
        
        Args:
            message: Game state message
            
        Returns:
            Action index if successful, None if failed
        """
        try:
            # 延迟初始化YFAdapter（首次使用时）
            if self.yf_adapter is None:
                from communication.lalala_adapter_v4 import YFAdapter
                self.yf_adapter = YFAdapter(self.player_id)
                self.logger.info("YFAdapter initialized (lazy)")
            
            # 调用yf_adapter.decide(message)
            action = self.yf_adapter.decide(message)
            
            # 验证返回的action有效性
            # 首先检查action是否为None
            if action is None:
                return None  # 触发下一层
            
            action_list = message.get("actionList", [])
            if not action_list:
                # 空动作列表，只有0（PASS）有效
                if action == 0:
                    return action
                else:
                    self.logger.warning(f"Invalid action {action} for empty actionList")
                    return None
            
            # 检查action是否在有效范围内
            if 0 <= action < len(action_list):
                return action
            else:
                self.logger.warning(f"Action {action} out of range [0, {len(action_list)})")
                return None
                
        except Exception as e:
            # 错误处理：捕获异常，返回None
            self.logger.error(f"YF decision error: {e}", exc_info=True)
            return None
    
    def _try_decision_engine(self, message: dict) -> Optional[int]:
        """
        Try DecisionEngine layer.
        
        Args:
            message: Game state message
            
        Returns:
            Action index if successful, None if failed
        """
        try:
            # 延迟初始化DecisionEngine（首次使用时）
            if self.decision_engine is None:
                from decision.decision_engine import DecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                # 创建状态管理器
                state_manager = EnhancedGameStateManager()
                self.decision_engine = DecisionEngine(state_manager)
                self.logger.info("DecisionEngine initialized (lazy)")
            
            # 调用decision_engine.decide(message)
            action = self.decision_engine.decide(message)
            
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
            self.logger.error(f"DecisionEngine decision error: {e}", exc_info=True)
            return None
    
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
        Check if we should protect teammate.
        
        Conditions:
        - Teammate is leading (has the greatest card)
        - Teammate has few cards left (<=5)
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
        
        # Critical: Teammate has very few cards
        if teammate_cards <= 3:
            self.logger.info(
                f"[Critical Rule] Teammate protection: teammate has {teammate_cards} cards, PASS"
            )
            return 0  # PASS
        
        # Important: Teammate has few cards
        if teammate_cards <= 5:
            # Check if current card is high value
            cur_action = message.get("curAction", [])
            if cur_action and len(cur_action) >= 2:
                try:
                    card_value = self._get_card_value(cur_action[1])
                    if card_value >= 14:  # A or higher
                        self.logger.info(
                            f"[Critical Rule] Teammate protection: teammate has {teammate_cards} cards "
                            f"and high card ({cur_action[1]}), PASS"
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
        Check if we must suppress opponent.
        
        Conditions:
        - Opponent has very few cards left (<=5)
        - We must play a card to prevent opponent from winning
        - Find the best card to beat current action
        
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
        
        # Critical: Opponent is about to win
        if min_opponent_cards <= 3:
            # Find best action to beat current card
            action = self._find_best_beat_action(message, action_list)
            if action is not None and action != 0:
                self.logger.info(
                    f"[Critical Rule] Opponent suppression: opponent has {min_opponent_cards} cards, "
                    f"play action {action}"
                )
                return action
        
        # Important: Opponent has few cards
        if min_opponent_cards <= 5:
            # Check if we're in passive mode and can beat
            if message.get("type") == "passive":
                action = self._find_best_beat_action(message, action_list)
                if action is not None and action != 0:
                    self.logger.info(
                        f"[Critical Rule] Opponent suppression: opponent has {min_opponent_cards} cards, "
                        f"beat with action {action}"
                    )
                    return action
        
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
