# -*- coding: utf-8 -*-
"""
Hybrid Decision Engine V4
混合决策引擎 V4版本

4层决策架构：
1. Layer 1: lalala Strategy (Primary) - 40-50% win rate
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
        self.lalala_adapter = None
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
        Make a decision using 4-layer fallback mechanism.
        
        Args:
            message: Game state message from server
            
        Returns:
            Action index (0 for PASS, 1+ for play actions)
        """
        start_time = time.time()
        performance_threshold = self.config.get("performance_threshold", 1.0)
        
        # Layer 1: lalala (Primary)
        try:
            layer_start = time.time()
            action = self._try_lalala(message)
            layer_duration = time.time() - layer_start
            
            if action is not None:
                duration = time.time() - start_time
                self.stats.record_success("lalala", duration)
                
                # Performance warning
                if layer_duration > performance_threshold:
                    self.logger.warning(
                        f"Layer 1 (lalala) slow: {layer_duration:.3f}s > {performance_threshold}s threshold"
                    )
                
                self.logger.info(f"✓ Layer 1 (lalala) succeeded: action={action}, time={duration:.3f}s")
                return action
            else:
                self.logger.warning("Layer 1 (lalala) returned None, falling back to Layer 2")
                self.stats.record_failure("lalala", "Returned None")
                
        except Exception as e:
            duration = time.time() - layer_start
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.logger.error(
                f"✗ Layer 1 (lalala) failed after {duration:.3f}s: {error_msg}",
                exc_info=True
            )
            self.stats.record_failure("lalala", error_msg)
        
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
    
    def _try_lalala(self, message: dict) -> Optional[int]:
        """
        Try lalala decision layer.
        
        Args:
            message: Game state message
            
        Returns:
            Action index if successful, None if failed
        """
        try:
            # 延迟初始化LalalaAdapter（首次使用时）
            if self.lalala_adapter is None:
                from communication.lalala_adapter_v4 import LalalaAdapter
                self.lalala_adapter = LalalaAdapter(self.player_id)
                self.logger.info("LalalaAdapter initialized (lazy)")
            
            # 调用lalala_adapter.decide(message)
            action = self.lalala_adapter.decide(message)
            
            # 验证返回的action有效性
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
            self.logger.error(f"lalala decision error: {e}", exc_info=True)
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
                from src.decision.decision_engine import DecisionEngine
                from game_logic.enhanced_state import EnhancedGameStateManager
                
                # 创建状态管理器
                state_manager = EnhancedGameStateManager(self.player_id)
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
                state_manager = EnhancedGameStateManager(self.player_id)
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


class DecisionStatistics:
    """
    Track decision performance and layer usage statistics.
    """
    
    def __init__(self):
        self.layer_usage = {
            "lalala": {"success": 0, "failure": 0, "total_time": 0.0},
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
            "lalala": {"success": 0, "failure": 0, "total_time": 0.0},
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
