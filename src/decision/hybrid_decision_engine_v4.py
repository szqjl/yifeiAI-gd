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
        
        # Layer 1: lalala (Primary)
        try:
            action = self._try_lalala(message)
            if action is not None:
                duration = time.time() - start_time
                self.stats.record_success("lalala", duration)
                self.logger.info(f"Layer 1 (lalala) succeeded: action={action}, time={duration:.3f}s")
                return action
        except Exception as e:
            self.logger.warning(f"Layer 1 (lalala) failed: {e}")
            self.stats.record_failure("lalala", str(e))
        
        # Layer 2: DecisionEngine (Fallback 1)
        try:
            action = self._try_decision_engine(message)
            if action is not None:
                duration = time.time() - start_time
                self.stats.record_success("DecisionEngine", duration)
                self.logger.info(f"Layer 2 (DecisionEngine) succeeded: action={action}, time={duration:.3f}s")
                return action
        except Exception as e:
            self.logger.warning(f"Layer 2 (DecisionEngine) failed: {e}")
            self.stats.record_failure("DecisionEngine", str(e))
        
        # Layer 3: Knowledge Enhanced (Fallback 2)
        try:
            action = self._try_knowledge_enhanced(message)
            if action is not None:
                duration = time.time() - start_time
                self.stats.record_success("KnowledgeEnhanced", duration)
                self.logger.info(f"Layer 3 (KnowledgeEnhanced) succeeded: action={action}, time={duration:.3f}s")
                return action
        except Exception as e:
            self.logger.warning(f"Layer 3 (KnowledgeEnhanced) failed: {e}")
            self.stats.record_failure("KnowledgeEnhanced", str(e))
        
        # Layer 4: Random (Guaranteed)
        action = self._random_valid_action(message)
        duration = time.time() - start_time
        self.stats.record_success("Random", duration)
        self.logger.info(f"Layer 4 (Random) used: action={action}, time={duration:.3f}s")
        return action
    
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
                from src.communication.lalala_adapter_v4 import LalalaAdapter
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
        # TODO: Implement in Task 5
        # This will use DecisionEngine for evaluation-based decisions
        return None
    
    def _try_knowledge_enhanced(self, message: dict) -> Optional[int]:
        """
        Try knowledge-enhanced layer.
        
        Args:
            message: Game state message
            
        Returns:
            Action index if successful, None if failed
        """
        # TODO: Implement in Task 6
        # This will use KnowledgeEnhancedDecision for pattern matching
        return None
    
    def _random_valid_action(self, message: dict) -> int:
        """
        Guaranteed fallback: select random valid action.
        
        This method always succeeds and returns a valid action.
        
        Args:
            message: Game state message
            
        Returns:
            Random action index from actionList
        """
        action_list = message.get("actionList", [])
        
        if not action_list:
            self.logger.warning("Empty actionList, returning 0 (PASS)")
            return 0
        
        # Select random action from available actions
        action_index = random.randint(0, len(action_list) - 1)
        
        self.logger.debug(f"Random selection from {len(action_list)} actions: {action_index}")
        return action_index
    
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
        self.__init__()
