# -*- coding: utf-8 -*-
"""
YF_V5 阶段5决策引擎
集成阶段5全部高级策略学习功能
"""

import asyncio
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
import time
import torch
import numpy as np

from .rl_decision_engine import RLDecisionEngine
from src.rl_agent.strategy_pattern_recognizer import StrategyPatternRecognizer
from src.rl_agent.opponent_model import OpponentModel, OpponentAnalyzer
from src.rl_agent.dynamic_strategy_adjuster import DynamicStrategyAdjuster, STRATEGIES, SITUATION_TYPES


class AdvancedAIAnalyzer:
    """
    高级AI分析器
    整合所有阶段5分析功能
    """

    def __init__(self):
        self.logger = logging.getLogger("AdvancedAIAnalyzer")

        # 初始化阶段5组件
        self.pattern_recognizer = None
        self.opponent_model = None
        self.strategy_adjuster = None
        self.game_history = []

        self._init_components()

    def _init_components(self):
        """初始化所有组件"""
        try:
            # 策略模式识别器
            self.pattern_recognizer = StrategyPatternRecognizer(
                input_dim=512, pattern_types=8, hidden_dim=256
            )
            self.logger.info("✓ Strategy Pattern Recognizer initialized")

            # 对手建模器
            self.opponent_model = OpponentModel()
            self.logger.info("✓ Opponent Model initialized")

            # 动态策略调整器
            self.strategy_adjuster = DynamicStrategyAdjuster()
            self.logger.info("✓ Dynamic Strategy Adjuster initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize Advanced AI components: {e}")
            # 禁用失败的组件
            if self.pattern_recognizer is None:
                self.logger.warning("Strategy Pattern Recognizer disabled")
            if self.opponent_model is None:
                self.logger.warning("Opponent Model disabled")
            if self.strategy_adjuster is None:
                self.logger.warning("Dynamic Strategy Adjuster disabled")

    def analyze_game_state(self, game_state: Dict) -> Dict[str, Any]:
        """
        分析游戏状态，生成高级AI洞察

        Args:
            game_state: 游戏状态信息

        Returns:
            高级AI分析结果
        """
        analysis_result = {
            'pattern_analysis': {},
            'opponent_analysis': {},
            'strategy_recommendation': {},
            'confidence_scores': {}
        }

        try:
            # 1. 策略模式识别
            if self.pattern_recognizer is not None:
                pattern_result = self._analyze_strategy_pattern(game_state)
                analysis_result['pattern_analysis'] = pattern_result

            # 2. 对手建模分析
            if self.opponent_model is not None:
                opponent_result = self._analyze_opponent(game_state)
                analysis_result['opponent_analysis'] = opponent_result

            # 3. 动态策略调整
            if self.strategy_adjuster is not None:
                strategy_result = self._recommend_strategy(game_state)
                analysis_result['strategy_recommendation'] = strategy_result

            # 4. 计算综合置信度
            confidence_scores = self._calculate_confidence_scores(analysis_result)
            analysis_result['confidence_scores'] = confidence_scores

        except Exception as e:
            self.logger.error(f"Advanced AI analysis failed: {e}")
            analysis_result['error'] = str(e)

        return analysis_result

    def _analyze_strategy_pattern(self, game_state: Dict) -> Dict[str, Any]:
        """分析策略模式"""
        try:
            # 将游戏状态转换为模型输入格式
            state_vec = self._preprocess_state_for_pattern(game_state)

            with torch.no_grad():
                state_tensor = torch.FloatTensor(state_vec).unsqueeze(0)
                pattern_logits, pattern_confidence = self.pattern_recognizer(state_tensor)

                # 获取最可能的策略模式
                pattern_probs = torch.softmax(pattern_logits, dim=-1).squeeze(0)
                best_pattern_idx = torch.argmax(pattern_probs).item()
                best_pattern_confidence = pattern_probs[best_pattern_idx].item()

                return {
                    'pattern_id': best_pattern_idx,
                    'pattern_name': STRATEGIES.get(best_pattern_idx, 'unknown'),
                    'confidence': best_pattern_confidence,
                    'all_patterns': pattern_probs.tolist()
                }

        except Exception as e:
            self.logger.error(f"Strategy pattern analysis failed: {e}")
            return {'error': str(e)}

    def _analyze_opponent(self, game_state: Dict) -> Dict[str, Any]:
        """分析对手行为"""
        try:
            # 从游戏历史中提取对手动作
            opponent_actions = self._extract_opponent_actions(game_state)

            if not opponent_actions:
                return {'analysis': 'insufficient_data'}

            # 分析对手行为模式
            analysis = OpponentAnalyzer.analyze_opponent_behavior(opponent_actions)

            # 使用模型进行更深入的分析
            if len(opponent_actions) >= 3:  # 至少需要3个历史动作
                opponent_action_tensor = torch.randn(1, min(len(opponent_actions), 10), 512)  # 简化的张量
                opp_type, confidence = self.opponent_model.predict_opponent_type(opponent_action_tensor[0])

                analysis.update({
                    'predicted_type': opp_type,
                    'prediction_confidence': confidence,
                    'type_description': OpponentAnalyzer.get_opponent_type_description(
                        ['aggressive', 'conservative', 'random', 'follower', 'strategic'][opp_type]
                    )
                })

            return analysis

        except Exception as e:
            self.logger.error(f"Opponent analysis failed: {e}")
            return {'error': str(e)}

    def _recommend_strategy(self, game_state: Dict) -> Dict[str, Any]:
        """推荐策略调整"""
        try:
            # 将游戏状态转换为策略调整器的输入格式
            state_vec = self._preprocess_state_for_strategy(game_state)

            recommendation = self.strategy_adjuster.recommend_strategy(
                torch.FloatTensor(state_vec),
                current_strategy=getattr(self, 'current_strategy', 2)  # 默认跟牌策略
            )

            # 更新当前策略
            if recommendation['should_switch']:
                self.current_strategy = recommendation['recommended_strategy']

            return recommendation

        except Exception as e:
            self.logger.error(f"Strategy recommendation failed: {e}")
            return {'error': str(e)}

    def _calculate_confidence_scores(self, analysis_result: Dict) -> Dict[str, float]:
        """计算综合置信度分数"""
        confidence_scores = {}

        try:
            # 策略模式置信度
            pattern_conf = analysis_result.get('pattern_analysis', {}).get('confidence', 0.5)
            confidence_scores['pattern_confidence'] = pattern_conf

            # 对手分析置信度
            opponent_analysis = analysis_result.get('opponent_analysis', {})
            if 'predicted_type' in opponent_analysis:
                opp_conf = opponent_analysis.get('prediction_confidence', 0.5)
                confidence_scores['opponent_confidence'] = opp_conf
            else:
                confidence_scores['opponent_confidence'] = 0.3  # 基于规则的分析

            # 策略推荐置信度
            strategy_conf = analysis_result.get('strategy_recommendation', {}).get('overall_confidence', 0.5)
            confidence_scores['strategy_confidence'] = strategy_conf

            # 综合置信度（加权平均）
            overall_confidence = (
                0.4 * pattern_conf +
                0.3 * confidence_scores['opponent_confidence'] +
                0.3 * strategy_conf
            )
            confidence_scores['overall_confidence'] = overall_confidence

        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            confidence_scores = {
                'pattern_confidence': 0.5,
                'opponent_confidence': 0.5,
                'strategy_confidence': 0.5,
                'overall_confidence': 0.5
            }

        return confidence_scores

    def _preprocess_state_for_pattern(self, game_state: Dict) -> np.ndarray:
        """预处理状态用于策略模式识别"""
        # 简化的状态预处理
        # 实际实现应该与训练时保持一致
        hand_cards = game_state.get('handCards', [])
        state_vec = np.zeros(512)

        # 简单的牌到索引映射
        for card in hand_cards:
            if isinstance(card, str):
                # 简化的卡牌编码
                card_idx = hash(card) % 512
                state_vec[card_idx] = 1.0

        return state_vec

    def _preprocess_state_for_strategy(self, game_state: Dict) -> np.ndarray:
        """预处理状态用于策略调整"""
        # 与模式识别使用相同的状态预处理
        return self._preprocess_state_for_pattern(game_state)

    def _extract_opponent_actions(self, game_state: Dict) -> List[Dict]:
        """从游戏状态中提取对手动作历史"""
        # 从游戏历史中提取对手动作
        # 这是一个简化的实现
        history = game_state.get('history', [])
        opponent_actions = []

        for action in history:
            if isinstance(action, dict) and 'player' in action:
                # 如果不是当前玩家，则认为是对手动作
                if action.get('player') != game_state.get('current_player'):
                    opponent_actions.append(action)

        return opponent_actions[-10:]  # 只保留最近10个动作

    def update_game_history(self, action_result: Dict):
        """更新游戏历史记录"""
        self.game_history.append(action_result)
        # 限制历史长度
        if len(self.game_history) > 100:
            self.game_history = self.game_history[-100:]


class YF_V5_Stage5_DecisionEngine:
    """
    YF_V5 阶段5决策引擎
    集成阶段5全部高级策略学习功能
    """

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.logger = logging.getLogger(f"YF_V5_Stage5_Player{player_id}")

        # 初始化RL决策引擎（使用超优化版模型）
        self.rl_engine = RLDecisionEngine(
            model_path="models/bc_model_stage5_ultra_optimized.pth",
            use_stage5_model=True
        )

        # 初始化阶段5高级AI分析器
        self.advanced_ai = AdvancedAIAnalyzer()

        # 阶段5决策权重配置
        self.stage5_weights = {
            'rl_weight': 0.25,           # RL决策权重 (增强)
            'knowledge_weight': 0.25,    # 知识库权重
            'rule_weight': 0.20,         # 规则引擎权重
            'advanced_ai_weight': 0.30   # 高级AI权重 (新增)
        }

        # 初始化决策统计
        self.decision_stats = {
            'total_decisions': 0,
            'rl_decisions': 0,
            'knowledge_decisions': 0,
            'rule_decisions': 0,
            'advanced_ai_decisions': 0,
            'avg_decision_time': 0.0
        }

        self.logger.info("✓ YF_V5 Stage5 Decision Engine initialized")
        self.logger.info(f"Stage5 weights: {self.stage5_weights}")

    def record_success(self, decision_type: str, duration: float):
        """记录决策统计"""
        self.decision_stats['total_decisions'] += 1
        if decision_type in self.decision_stats:
            self.decision_stats[decision_type] += 1

        # 更新平均决策时间
        total_time = self.decision_stats['avg_decision_time'] * (self.decision_stats['total_decisions'] - 1)
        self.decision_stats['avg_decision_time'] = (total_time + duration) / self.decision_stats['total_decisions']

    def decide(self, message: Dict) -> int:
        """
        阶段5增强决策流程

        Args:
            message: 服务器消息

        Returns:
            动作索引（int）
        """
        start_time = time.time()

        try:
            # 1. 使用RL引擎进行基础决策
            action_index = self.rl_engine.decide(message)

            # 2. 验证动作索引有效性
            action_list = message.get("actionList", [])
            if action_index >= len(action_list) or action_index < 0:
                self.logger.warning(f"Invalid action_index {action_index}, falling back to PASS")
                action_index = 0

            # 3. 高级AI分析（异步进行，不影响决策速度）
            try:
            game_state = self._extract_game_state(message)
            ai_analysis = self.advanced_ai.analyze_game_state(game_state)
                confidence = ai_analysis.get('confidence_scores', {}).get('overall_confidence', 0)
            except Exception as e:
                self.logger.debug(f"AI analysis failed (non-critical): {e}")
                confidence = 0.5

            # 4. 记录决策统计
            duration = time.time() - start_time
            self.record_success("rl_decisions", duration)

            self.logger.debug(f"Stage5 decision: action_index={action_index}, time={duration:.3f}s, confidence={confidence:.3f}")
            return action_index

        except Exception as e:
            self.logger.error(f"Stage5 decision failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 回退到PASS
            return 0

    def _extract_game_state(self, message: Dict) -> Dict:
        """从消息中提取游戏状态"""
        return {
            'handCards': message.get('handCards', []),
            'actionList': message.get('actionList', []),
            'current_player': self.player_id,
            'history': getattr(self, 'game_history', []),
            'message': message
        }

    def get_stats(self) -> Dict:
        """获取决策统计信息"""
        return self.decision_stats.copy()
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息（兼容客户端接口）
        
        Returns:
            统计信息字典，包含layer_usage等
        """
        # 构建兼容的统计格式
        stats = {
            'layer_usage': {
                'RL': {
                    'success': self.decision_stats.get('rl_decisions', 0),
                    'failure': max(0, self.decision_stats.get('total_decisions', 0) - self.decision_stats.get('rl_decisions', 0))
                },
                'Knowledge': {
                    'success': self.decision_stats.get('knowledge_decisions', 0),
                    'failure': 0
                },
                'Rule': {
                    'success': self.decision_stats.get('rule_decisions', 0),
                    'failure': 0
                },
                'AdvancedAI': {
                    'success': self.decision_stats.get('advanced_ai_decisions', 0),
                    'failure': 0
                }
            },
            'total_decisions': self.decision_stats.get('total_decisions', 0),
            'avg_decision_time': self.decision_stats.get('avg_decision_time', 0.0)
        }
        return stats
    
    def reset_statistics(self):
        """重置统计信息（新游戏开始时调用）"""
        self.decision_stats = {
            'total_decisions': 0,
            'rl_decisions': 0,
            'knowledge_decisions': 0,
            'rule_decisions': 0,
            'advanced_ai_decisions': 0,
            'avg_decision_time': 0.0
        }
        self.logger.info("Statistics reset for new game")
    
    def _generate_candidates(self, message: Dict) -> List[Tuple[int, float, str]]:
        """
        生成候选动作（兼容客户端接口）
        
        Args:
            message: 游戏状态消息
            
        Returns:
            候选动作列表: [(action_idx, score, layer), ...]
        """
        candidates = []
        action_list = message.get("actionList", [])
        
        if not action_list:
            return candidates
        
        try:
            # 使用RL引擎生成基础候选
            action_index = self.rl_engine.decide(message)
            
            # 验证动作索引
            if 0 <= action_index < len(action_list):
                # RL决策作为主要候选
                candidates.append((action_index, 100.0, "RL"))
                
                # 添加其他动作作为备选（分数较低）
                for idx in range(len(action_list)):
                    if idx != action_index:
                        # 根据索引距离给予不同分数
                        distance = abs(idx - action_index)
                        score = max(10.0, 50.0 - distance * 5.0)
                        candidates.append((idx, score, "Fallback"))
            else:
                # 如果RL决策无效，添加所有动作作为候选
                for idx in range(len(action_list)):
                    candidates.append((idx, 50.0, "Fallback"))
                    
        except Exception as e:
            self.logger.warning(f"Failed to generate candidates: {e}")
            # 回退：添加所有动作
            for idx in range(len(action_list)):
                candidates.append((idx, 30.0, "Fallback"))
        
        return candidates
    
    def _enhance_candidates(self, candidates: List[Tuple[int, float, str]], message: Dict) -> List[Tuple[int, float, str]]:
        """
        增强候选动作（兼容客户端接口）
        
        Args:
            candidates: 基础候选列表
            message: 游戏状态消息
            
        Returns:
            增强后的候选列表
        """
        if not candidates:
            return candidates
        
        try:
            # 使用高级AI分析增强候选分数
            game_state = self._extract_game_state(message)
            ai_analysis = self.advanced_ai.analyze_game_state(game_state)
            
            # 获取AI置信度
            confidence = ai_analysis.get('confidence_scores', {}).get('overall_confidence', 0.5)
            
            # 根据AI分析调整候选分数
            enhanced_candidates = []
            for idx, score, layer in candidates:
                # 如果AI置信度高，提升RL候选的分数
                if layer == "RL" and confidence > 0.7:
                    enhanced_score = score * (1.0 + confidence * 0.2)
                else:
                    enhanced_score = score
                
                enhanced_candidates.append((idx, enhanced_score, layer))
            
            return enhanced_candidates
            
        except Exception as e:
            self.logger.warning(f"Failed to enhance candidates: {e}")
            # 返回原始候选
            return candidates
