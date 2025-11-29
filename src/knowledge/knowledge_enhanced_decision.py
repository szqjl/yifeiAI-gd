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
        
        # 计算位置关系（掼蛋4人游戏，位置编号0-3）
        # 
        # 【重要】位置关系说明（根据平台使用说明和lalala代码）：
        # 
        # 1. 组队规则（平台规则）：
        #    - 第1个连接的玩家（位置0）和第3个连接的玩家（位置2）自动为一队
        #    - 第2个连接的玩家（位置1）和第4个连接的玩家（位置3）自动为一队
        #    - 队友（teammate/对家）：位置 = (my_pos + 2) % 4
        #      例如：玩家0的队友是玩家2，玩家1的队友是玩家3
        # 
        # 2. 出牌顺序（已通过实际日志验证）：
        #    - 出牌顺序：顺时针循环 0 → 1 → 2 → 3 → 0
        #    - 下家（next）：下一个出牌的玩家，位置 = (my_pos + 1) % 4
        #      例如：玩家0的下家是玩家1，玩家1的下家是玩家2，玩家2的下家是玩家3，玩家3的下家是玩家0
        #    - 上家（prev）：上一个出牌的玩家，位置 = (my_pos - 1) % 4 = (my_pos + 3) % 4
        #      例如：玩家0的上家是玩家3，玩家1的上家是玩家0，玩家2的上家是玩家1，玩家3的上家是玩家2
        #    - 注意：游戏开始时第一个出牌者可能不是0号，但一旦开始，顺序固定为顺时针
        # 
        # 3. 对手（opponent）：
        #    - 对方队伍的玩家，包括下家和上家
        #    - 例如：玩家0的对手是玩家1（下家）和玩家3（上家）
        # 
        # 4. 关键字段说明：
        #    - myPos: 我的位置（0-3）
        #    - curPos: 当前出牌者的位置（-1表示无人出牌，如开局、接风等）
        #    - greaterPos: 当前最大动作持有者的位置（-1表示无最大动作）
        # 
        # 5. 位置编号示例：
        #    假设玩家0是我：
        #    - 队友（对家）：玩家2
        #    - 下家：玩家1
        #    - 上家：玩家3
        #    - 对手：玩家1和玩家3
        teammate_pos = (my_pos + 2) % 4  # 队友（对家）
        next_pos = (my_pos + 1) % 4      # 下家（对手）
        prev_pos = (my_pos - 1) % 4      # 上家（对手），等价于 (my_pos + 3) % 4
        
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
            
            # 策略1：队友保护（验证并完善）
            # 参考：lalala策略和关键规则层实现
            teammate_cards = cards_left.get(teammate_pos, 27)
            
            # 条件1：队友是最大牌持有者（控场）
            if greater_pos == teammate_pos:
                # 关键情况：队友剩余1-2张牌（即将获胜）
                if teammate_cards <= 2:
                    if action_type == "PASS":
                        score += 150  # 极强烈鼓励PASS，让队友走
                    else:
                        score -= 80   # 严重惩罚出牌
                
                # 重要情况：队友剩余3-5张牌（残局阶段）
                elif teammate_cards <= 5:
                    # 检查当前牌值（如果是被动模式）
                    if not is_active:
                        cur_action = message.get("curAction", [])
                        if cur_action and len(cur_action) >= 2:
                            try:
                                card_value = self._get_card_value(cur_action[1])
                                # 如果队友出的是大牌（A或以上），让队友走
                                if card_value >= 14:  # A=14, 2=15, Joker=16/17
                                    if action_type == "PASS":
                                        score += 120  # 强烈鼓励PASS
                                    else:
                                        score -= 60   # 惩罚出牌
                                # 如果队友出的是中等牌（10-K），适度保护
                                elif card_value >= 10:
                                    if action_type == "PASS":
                                        score += 80   # 鼓励PASS
                                    else:
                                        score -= 30   # 轻微惩罚出牌
                            except:
                                # 无法解析牌值，使用默认规则
                                if action_type == "PASS":
                                    score += 100
                                else:
                                    score -= 50
                        else:
                            # 没有当前动作（主动模式），队友控场时鼓励PASS
                            if action_type == "PASS":
                                score += 100
                            else:
                                score -= 50
                    else:
                        # 主动模式，队友控场时适度保护
                        if action_type == "PASS":
                            score += 60
                        else:
                            score -= 30
                
                # 中等情况：队友剩余6-8张牌（接近残局）
                elif teammate_cards <= 8:
                    # 只在队友出非常大的牌时保护（2或Joker）
                    if not is_active:
                        cur_action = message.get("curAction", [])
                        if cur_action and len(cur_action) >= 2:
                            try:
                                card_value = self._get_card_value(cur_action[1])
                                if card_value >= 15:  # 2或Joker
                                    if action_type == "PASS":
                                        score += 50   # 适度鼓励PASS
                                    else:
                                        score -= 20   # 轻微惩罚
                            except:
                                pass
            
            # 条件2：队友刚出牌（被动模式，队友是上一个出牌者）
            elif not is_active and cur_pos == teammate_pos:
                # 队友刚出牌，我们被动响应
                teammate_cards = cards_left.get(teammate_pos, 27)
                
                # 如果队友快走完了，让队友继续控场
                if teammate_cards <= 3:
                    if action_type == "PASS":
                        score += 100  # 强烈鼓励PASS
                    else:
                        score -= 50   # 惩罚出牌
                elif teammate_cards <= 6:
                    # 检查队友出的牌值
                    cur_action = message.get("curAction", [])
                    if cur_action and len(cur_action) >= 2:
                        try:
                            card_value = self._get_card_value(cur_action[1])
                            # 队友出大牌，让队友走
                            if card_value >= 14:
                                if action_type == "PASS":
                                    score += 70
                                else:
                                    score -= 35
                        except:
                            pass
            
            # 策略2：对手压制（验证并完善）
            # 参考：lalala策略和关键规则层实现
            opponent_cards = [
                cards_left.get(next_pos, 27),
                cards_left.get(prev_pos, 27)
            ]
            min_opponent_cards = min(opponent_cards)
            max_opponent_cards = max(opponent_cards)
            
            # 关键情况：对手剩余1-3张牌（即将获胜）
            if min_opponent_cards <= 3:
                # 必须压制！强烈鼓励出牌
                if action_type != "PASS":
                    # 检查是否能够压制当前动作
                    if not is_active:
                        cur_action = message.get("curAction", [])
                        if cur_action and len(cur_action) > 0:
                            # 被动模式，检查是否能压制对手
                            if action_type == cur_action[0] or action_type == "Bomb":
                                # 同类型或炸弹，可以压制
                                score += 150  # 极强烈鼓励压制
                            else:
                                # 不同类型，无法压制，但还是要出牌
                                score += 100  # 强烈鼓励出牌
                        else:
                            # 没有当前动作，鼓励出牌
                            score += 120
                    else:
                        # 主动模式，对手快走完，必须出牌压制
                        score += 120
                else:
                    # PASS是严重错误
                    score -= 100  # 严重惩罚PASS
            
            # 重要情况：对手剩余4张牌
            # 规则："火不打四" - 对手4张时可能是炸弹，不要轻易用炸弹
            elif min_opponent_cards == 4:
                if not is_active:
                    # 被动模式，可以出牌，但避免用炸弹
                    cur_action = message.get("curAction", [])
                    if cur_action and len(cur_action) > 0:
                        if action_type == "Bomb":
                            # 对手4张，可能是炸弹，不要轻易用炸弹
                            score -= 30  # 轻微惩罚用炸弹
                        elif action_type == cur_action[0] or action_type == "Bomb":
                            # 可以压制，但不是炸弹
                            score += 60  # 鼓励出牌压制
                        else:
                            score += 30  # 适度鼓励出牌
                    else:
                        score += 40
                else:
                    # 主动模式，适度出牌
                    if action_type != "PASS":
                        if action_type == "Bomb":
                            score -= 20  # 避免用炸弹
                        else:
                            score += 50
                    else:
                        score -= 20
            
            # 重要情况：对手剩余5张牌
            # 规则："逢五出对" - 对手5张时优先出对子
            elif min_opponent_cards == 5:
                if not is_active:
                    # 被动模式
                    cur_action = message.get("curAction", [])
                    if cur_action and len(cur_action) > 0:
                        # 如果当前是对子，优先出对子压制
                        if cur_action[0] == "Pair" and action_type == "Pair":
                            score += 100  # 强烈鼓励出对子压制
                        elif action_type == "Pair":
                            # 主动出对子（虽然是被动模式，但可以主动出对子）
                            score += 80
                        elif action_type != "PASS":
                            score += 60  # 鼓励出牌
                        else:
                            score -= 40  # 惩罚PASS
                    else:
                        # 被动模式但没有当前动作（接风等情况），鼓励出对子
                        if action_type == "Pair":
                            score += 80
                        elif action_type != "PASS":
                            score += 50
                        else:
                            score -= 30
                else:
                    # 主动模式，鼓励出对子
                    if action_type == "Pair":
                        score += 70
                    elif action_type != "PASS":
                        score += 50
                    else:
                        score -= 30
            
            # 中等情况：对手剩余6-8张牌（接近残局）
            elif min_opponent_cards <= 8:
                if not is_active:
                    # 被动模式，可以适度压制
                    cur_action = message.get("curAction", [])
                    if cur_action and len(cur_action) > 0:
                        # 检查是否能用小牌压制
                        if action_type == cur_action[0]:
                            # 同类型，检查牌值
                            try:
                                if len(action) >= 2:
                                    card_value = self._get_card_value(action[1])
                                    if card_value <= 10:  # 小牌，安全
                                        score += 70  # 鼓励用小牌压制
                                    elif card_value <= 13:  # 中等牌
                                        score += 50
                                    else:  # 大牌，谨慎
                                        score += 30
                            except:
                                score += 50
                        elif action_type != "PASS":
                            score += 40
                        else:
                            score -= 20
                    else:
                        if action_type != "PASS":
                            score += 40
                else:
                    # 主动模式，适度出牌
                    if action_type != "PASS":
                        score += 30
                    else:
                        score -= 15
            
            # 一般情况：对手剩余9-15张牌（中局）
            elif min_opponent_cards <= 15:
                # 适度关注，但不强制
                if not is_active:
                    cur_action = message.get("curAction", [])
                    if cur_action and len(cur_action) > 0:
                        if action_type != "PASS":
                            score += 20  # 适度鼓励出牌
                else:
                    if action_type != "PASS":
                        score += 15
            
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
    
    def _get_card_value(self, rank: str) -> int:
        """
        获取牌值的数字表示
        
        Task 3.2: 添加辅助方法，用于队友保护规则中的牌值判断
        
        Args:
            rank: 牌面值（如 "3", "J", "A", "2", "B", "R"）
            
        Returns:
            数字值（3-17）
            - 3-9: 3-9
            - T/10: 10
            - J: 11
            - Q: 12
            - K: 13
            - A: 14
            - 2: 15
            - B (小王): 16
            - R (大王): 17
        """
        if not rank:
            return 0
        
        rank_map = {
            '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'T': 10, '10': 10,
            'J': 11, 'Q': 12, 'K': 13, 'A': 14,
            '2': 15,
            'B': 16,  # Small Joker (小王)
            'R': 17   # Big Joker (大王)
        }
        
        return rank_map.get(str(rank).upper(), 0)
    
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
