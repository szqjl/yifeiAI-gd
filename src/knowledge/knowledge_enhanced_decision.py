# -*- coding: utf-8 -*-
"""
????????? (Knowledge-Enhanced Decision)
???
- ????????????
- ???????????
"""

from typing import Dict, List, Optional
import sys
from pathlib import Path

# ??src????????????
if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from decision.decision_engine import DecisionEngine
from game_logic.enhanced_state import EnhancedGameStateManager
from knowledge.knowledge_loader import KnowledgeLoader


class KnowledgeEnhancedDecisionEngine(DecisionEngine):
    """??????????"""
    
    def __init__(self, state_manager: EnhancedGameStateManager, 
                 knowledge_loader: Optional[KnowledgeLoader] = None,
                 max_decision_time: float = 0.8):
        """
        ????????????
        
        Args:
            state_manager: ?????
            knowledge_loader: ??????????None?????
            max_decision_time: ??????
        """
        super().__init__(state_manager, max_decision_time)
        
        # ?????????
        if knowledge_loader is None:
            try:
                self.knowledge_loader = KnowledgeLoader()
            except Exception as e:
                print(f"Warning: Failed to load knowledge base: {e}")
                self.knowledge_loader = None
        else:
            self.knowledge_loader = knowledge_loader
    
    def active_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        ??????????????
        """
        # ??????
        evaluations = self.evaluator.evaluate_all_actions(action_list, None)
        
        # ???????????
        if self.knowledge_loader:
            enhanced_evaluations = self._apply_knowledge_rules(
                evaluations, action_list, message, is_active=True
            )
        else:
            enhanced_evaluations = evaluations
        
        # ????
        if self.timer.check_timeout():
            if enhanced_evaluations:
                return enhanced_evaluations[0][0]
            return 0
        
        # ?????????
        for idx, score in enhanced_evaluations:
            action = action_list[idx]
            if action[0] != "PASS":
                if self.timer.check_timeout():
                    return idx
                return idx
        
        return 0
    
    def passive_decision(self, message: Dict, action_list: List[List]) -> int:
        """
        ??????????????
        """
        cur_action = message.get("curAction")
        
        # ??????
        evaluations = self.evaluator.evaluate_all_actions(action_list, cur_action)
        
        # ???????????
        if self.knowledge_loader:
            enhanced_evaluations = self._apply_knowledge_rules(
                evaluations, action_list, message, is_active=False
            )
        else:
            enhanced_evaluations = evaluations
        
        # ????
        if self.timer.check_timeout():
            if enhanced_evaluations:
                return enhanced_evaluations[0][0]
            return 0
        
        # ?????????
        for idx, score in enhanced_evaluations:
            if self.timer.check_timeout():
                return idx
            return idx
        
        return 0
    
    def enhance_candidates(self, candidates: List[tuple], message: Dict) -> List[tuple]:
        """
        Enhance candidate actions using knowledge rules.
        
        Task 3.1: 修改为增强评分模式
        
        This is the main public interface for enhancing candidates.
        It receives a list of candidates and returns enhanced scores.
        
        Args:
            candidates: List of (action_idx, base_score, layer) tuples
            message: Game state message
            
        Returns:
            Enhanced list of (action_idx, enhanced_score, layer) tuples
        """
        # Extract action list
        action_list = message.get("actionList", [])
        if not action_list:
            return candidates
        
        # Convert candidates to evaluation format (idx, score)
        evaluations = [(idx, score) for idx, score, _ in candidates]
        
        # Determine if this is an active decision
        is_active = message.get("type") == "active"
        
        # Apply knowledge rules
        enhanced_evaluations = self._apply_knowledge_rules(
            evaluations, action_list, message, is_active
        )
        
        # Convert back to candidate format, preserving layer information
        enhanced_candidates = []
        for idx, enhanced_score in enhanced_evaluations:
            # Find original layer
            original_layer = "Unknown"
            for orig_idx, _, layer in candidates:
                if orig_idx == idx:
                    original_layer = layer
                    break
            
            enhanced_candidates.append((idx, enhanced_score, original_layer))
        
        return enhanced_candidates
    
    def _apply_knowledge_rules(self, evaluations: List[tuple], 
                              action_list: List[List], 
                              message: Dict,
                              is_active: bool) -> List[tuple]:
        """
        应用知识规则（实现真正的策略逻辑，而不是简单加分）
        
        参考：策略对比分析.md - 方案1
        
        Args:
            evaluations: 基础评分 [(索引, 分数), ...]
            action_list: 动作列表
            message: 游戏消息
            is_active: 是否主动
        
        Returns:
            增强后的评分
        """
        # 提取游戏状态信息
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        greater_pos = message.get("greaterPos", -1)
        cur_pos = message.get("curPos", -1)
        
        # 计算位置关系
        teammate_pos = (my_pos + 2) % 4
        next_pos = (my_pos + 1) % 4
        prev_pos = (my_pos - 1) % 4
        
        # 获取剩余牌数
        cards_left = {}
        for i, info in enumerate(public_info):
            if isinstance(info, dict):
                cards_left[i] = info.get('rest', 27)
            else:
                cards_left[i] = 27
        
        # 应用核心策略
        enhanced_evaluations = []
        for idx, base_score in evaluations:
            action = action_list[idx]
            action_type = action[0] if len(action) > 0 else "PASS"
            score = base_score
            
            # 策略1：队友保护
            if greater_pos == teammate_pos:
                # 队友是最大牌持有者
                if cards_left.get(teammate_pos, 27) <= 5:
                    # 队友快走完了
                    if action_type == "PASS":
                        score += 100  # 强烈鼓励PASS，让队友走
                    else:
                        score -= 50   # 惩罚出牌
            
            # 策略2：对手压制
            opponent_cards = [
                cards_left.get(next_pos, 27),
                cards_left.get(prev_pos, 27)
            ]
            min_opponent_cards = min(opponent_cards)
            
            if min_opponent_cards <= 5:
                # 对手快走完了
                if action_type != "PASS":
                    score += 80  # 强烈鼓励出牌压制
                else:
                    score -= 40  # 惩罚PASS
            
            # 策略3：对手控场检测
            if greater_pos != teammate_pos and greater_pos != my_pos and greater_pos != -1:
                # 对手控场
                if action_type != "PASS":
                    score += 30  # 鼓励出牌打断对手节奏
            
            # 策略4：主动出牌时更积极
            if is_active:
                if action_type != "PASS":
                    score += 20  # 主动时鼓励出牌
            
            # 策略5：被动时根据情况
            else:
                if cur_pos == teammate_pos:
                    # 队友刚出牌
                    if action_type == "PASS":
                        score += 15  # 适当鼓励PASS
                elif cur_pos in [next_pos, prev_pos]:
                    # 对手刚出牌
                    if action_type != "PASS":
                        score += 25  # 鼓励压制对手
            
            enhanced_evaluations.append((idx, score))
        
        # 按分数降序排序
        enhanced_evaluations.sort(key=lambda x: x[1], reverse=True)
        
        return enhanced_evaluations
    
    def _calculate_knowledge_bonus(self, action: List, 
                                   skills: List[Dict],
                                   message: Dict,
                                   is_active: bool) -> float:
        """
        ???????????
        
        Args:
            action: ??
            skills: ??????
            message: ????
            is_active: ??????
        
        Returns:
            ?????0-50??
        """
        bonus = 0.0
        
        # ??????????????
        for skill in skills:
            priority = skill.get('priority', 0)
            
            # ?????????
            if priority >= 5:  # ??????
                bonus += 15.0
            elif priority >= 3:  # ??????
                bonus += 8.0
            else:  # ??????
                bonus += 2.0
        
        # ??????
        return min(bonus, 50.0)
