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
    
    def _apply_knowledge_rules(self, evaluations: List[tuple], 
                              action_list: List[List], 
                              message: Dict,
                              is_active: bool) -> List[tuple]:
        """
        ???????????
        
        Args:
            evaluations: ?????? [(??, ??), ...]
            action_list: ????
            message: ????
            is_active: ??????
        
        Returns:
            ????????
        """
        if not self.knowledge_loader:
            return evaluations
            
        enhanced_evaluations = []
        
        for idx, base_score in evaluations:
            action = action_list[idx]
            card_type = action[0] if action[0] != "PASS" else None
            
            # ????????
            if card_type:
                try:
                    skills = self.knowledge_loader.get_skills_by_card_type(card_type)
                    
                    # ?????????
                    knowledge_bonus = self._calculate_knowledge_bonus(
                        action, skills, message, is_active
                    )
                    
                    enhanced_score = base_score + knowledge_bonus
                except Exception:
                    enhanced_score = base_score
            else:
                enhanced_score = base_score
            
            enhanced_evaluations.append((idx, enhanced_score))
        
        # ???????
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
