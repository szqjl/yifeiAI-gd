# -*- coding: utf-8 -*-
"""
阶段6：预测参数优化
实现动态阈值调整和概率校准
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging


class PredictionOptimizer:
    """
    预测参数优化器
    实现：
    1. 基于上下文的预测阈值选择
    2. 学习不同局面下的最优阈值
    3. 概率校准（温度缩放）
    4. 置信度评估
    """
    
    def __init__(self):
        self.logger = logging.getLogger("PredictionOptimizer")
        
        # 阈值选择策略
        self.threshold_strategies = {
            'early_game': 0.25,      # 开局：较低阈值，鼓励探索
            'mid_game': 0.3,         # 中局：标准阈值
            'late_game': 0.35,       # 残局：较高阈值，更保守
            'urgent': 0.2,           # 紧急情况：低阈值，快速出牌
            'safe': 0.4,             # 安全情况：高阈值，谨慎出牌
        }
        
        # 温度缩放参数（用于概率校准）
        self.temperature = 1.0  # 默认温度
        
        # 上下文特征权重
        self.context_weights = {
            'game_phase': 0.3,       # 游戏阶段权重
            'card_count': 0.2,       # 剩余牌数权重
            'opponent_threat': 0.3,  # 对手威胁权重
            'teammate_support': 0.2  # 队友支持权重
        }
    
    def get_adaptive_threshold(self, context: Dict) -> float:
        """
        基于上下文获取自适应阈值
        
        Args:
            context: 上下文信息，包含：
                - game_phase: 游戏阶段 (0=开局, 1=中局, 2=残局)
                - player_rest_cards: 玩家剩余牌数列表
                - current_player: 当前玩家
                - opponent_rest_cards: 对手剩余牌数
                - teammate_rest_cards: 队友剩余牌数
                
        Returns:
            自适应阈值 (0.0-1.0)
        """
        game_phase = context.get('game_phase', 1)
        player_rest_cards = context.get('player_rest_cards', [27, 27, 27, 27])
        current_player = context.get('current_player', 0)
        
        # 计算对手威胁
        opponent_threat = self._calculate_opponent_threat(context)
        
        # 计算队友支持
        teammate_support = self._calculate_teammate_support(context)
        
        # 计算当前玩家剩余牌数
        my_cards = player_rest_cards[current_player] if current_player < len(player_rest_cards) else 27
        
        # 基础阈值（根据游戏阶段）
        if game_phase == 0:
            base_threshold = self.threshold_strategies['early_game']
        elif game_phase == 2:
            base_threshold = self.threshold_strategies['late_game']
        else:
            base_threshold = self.threshold_strategies['mid_game']
        
        # 根据对手威胁调整
        if opponent_threat > 0.7:  # 高威胁
            base_threshold -= 0.05  # 降低阈值，快速应对
        elif opponent_threat < 0.3:  # 低威胁
            base_threshold += 0.05  # 提高阈值，更谨慎
        
        # 根据队友支持调整
        if teammate_support > 0.7:  # 队友支持强
            base_threshold += 0.03  # 可以更谨慎
        elif teammate_support < 0.3:  # 队友支持弱
            base_threshold -= 0.03  # 需要更主动
        
        # 根据剩余牌数调整
        if my_cards <= 5:  # 残局
            base_threshold += 0.05  # 更保守
        elif my_cards >= 20:  # 开局
            base_threshold -= 0.03  # 可以探索
        
        # 限制在合理范围内
        threshold = max(0.1, min(0.5, base_threshold))
        
        return threshold
    
    def calibrate_probabilities(self, logits: torch.Tensor, temperature: Optional[float] = None) -> torch.Tensor:
        """
        概率校准（温度缩放）
        
        Args:
            logits: 模型输出的logits
            temperature: 温度参数（None则使用默认值）
            
        Returns:
            校准后的概率
        """
        if temperature is None:
            temperature = self.temperature
        
        # 温度缩放：probs = softmax(logits / temperature)
        calibrated_logits = logits / temperature
        probs = torch.sigmoid(calibrated_logits)  # 对于二分类，使用sigmoid
        
        return probs
    
    def get_confidence_score(self, probs: torch.Tensor, threshold: float) -> float:
        """
        计算预测的置信度分数
        
        Args:
            probs: 预测概率
            threshold: 使用的阈值
            
        Returns:
            置信度分数 (0.0-1.0)
        """
        # 计算高于阈值的概率的平均值和最大值
        above_threshold = probs > threshold
        if above_threshold.sum() == 0:
            return 0.0
        
        above_probs = probs[above_threshold]
        mean_confidence = above_probs.mean().item()
        max_confidence = above_probs.max().item()
        
        # 综合置信度：平均值 * 0.6 + 最大值 * 0.4
        confidence = mean_confidence * 0.6 + max_confidence * 0.4
        
        return min(1.0, max(0.0, confidence))
    
    def optimize_prediction(self, logits: torch.Tensor, context: Dict) -> Dict:
        """
        优化预测参数
        
        Args:
            logits: 模型输出的logits
            context: 上下文信息
            
        Returns:
            优化后的预测结果，包含：
                - probs: 校准后的概率
                - threshold: 使用的阈值
                - predictions: 二进制预测
                - confidence: 置信度分数
        """
        # 1. 获取自适应阈值
        threshold = self.get_adaptive_threshold(context)
        
        # 2. 概率校准
        calibrated_probs = self.calibrate_probabilities(logits)
        
        # 3. 应用缩放因子（如果需要）
        scaling_factor = context.get('scaling_factor', 5.0)
        scaled_probs = calibrated_probs * scaling_factor
        scaled_probs = torch.clamp(scaled_probs, 0, 1)
        
        # 4. 生成预测
        predictions = (scaled_probs > threshold).float()
        
        # 5. 计算置信度
        confidence = self.get_confidence_score(scaled_probs, threshold)
        
        return {
            'probs': scaled_probs,
            'threshold': threshold,
            'predictions': predictions,
            'confidence': confidence,
            'temperature': self.temperature
        }
    
    def _calculate_opponent_threat(self, context: Dict) -> float:
        """
        计算对手威胁程度 (0.0-1.0)
        """
        player_rest_cards = context.get('player_rest_cards', [27, 27, 27, 27])
        current_player = context.get('current_player', 0)
        
        # 计算对手（非当前玩家和队友）
        teammate = (current_player + 2) % 4
        opponents = [i for i in range(4) if i != current_player and i != teammate]
        
        opponent_cards = [player_rest_cards[i] for i in opponents if i < len(player_rest_cards)]
        if not opponent_cards:
            return 0.5  # 默认中等威胁
        
        min_opponent_cards = min(opponent_cards)
        
        # 对手剩余牌数越少，威胁越大
        if min_opponent_cards <= 5:
            return 0.9  # 高威胁
        elif min_opponent_cards <= 10:
            return 0.7  # 中高威胁
        elif min_opponent_cards <= 15:
            return 0.5  # 中等威胁
        else:
            return 0.3  # 低威胁
    
    def _calculate_teammate_support(self, context: Dict) -> float:
        """
        计算队友支持程度 (0.0-1.0)
        """
        player_rest_cards = context.get('player_rest_cards', [27, 27, 27, 27])
        current_player = context.get('current_player', 0)
        
        teammate = (current_player + 2) % 4
        teammate_cards = player_rest_cards[teammate] if teammate < len(player_rest_cards) else 27
        
        # 队友剩余牌数越少，支持越强（队友快走完）
        if teammate_cards <= 5:
            return 0.9  # 强支持
        elif teammate_cards <= 10:
            return 0.7  # 中强支持
        elif teammate_cards <= 15:
            return 0.5  # 中等支持
        else:
            return 0.3  # 弱支持
    
    def update_temperature(self, validation_results: Dict):
        """
        根据验证结果更新温度参数
        
        Args:
            validation_results: 验证结果，包含：
                - prediction_accuracy: 预测准确率
                - over_prediction_rate: 过度预测率
        """
        accuracy = validation_results.get('prediction_accuracy', 0.5)
        over_prediction = validation_results.get('over_prediction_rate', 0.5)
        
        # 如果准确率低，降低温度（使概率分布更尖锐）
        if accuracy < 0.5:
            self.temperature = max(0.5, self.temperature - 0.1)
        # 如果过度预测严重，提高温度（使概率分布更平滑）
        elif over_prediction > 0.6:
            self.temperature = min(2.0, self.temperature + 0.1)
        # 否则保持稳定
        else:
            self.temperature = max(0.8, min(1.2, self.temperature))
        
        self.logger.info(f"Updated temperature to {self.temperature:.2f}")


# 全局实例
_global_optimizer = None

def get_prediction_optimizer() -> PredictionOptimizer:
    """获取全局预测优化器实例"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PredictionOptimizer()
    return _global_optimizer

