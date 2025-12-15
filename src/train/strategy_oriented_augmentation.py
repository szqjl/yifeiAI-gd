# -*- coding: utf-8 -*-
"""
阶段6：策略导向数据增强
基于策略有效性进行数据增强，提高高质量策略样本的比例
"""

import random
from typing import List, Dict, Tuple
import numpy as np


class StrategyOrientedAugmentation:
    """
    策略导向数据增强器
    目标：增加高质量策略决策样本，提高数据集中成功策略的比例
    """
    
    def __init__(self, target_success_rate: float = 0.8):
        """
        Args:
            target_success_rate: 目标成功策略比例（默认80%）
        """
        self.target_success_rate = target_success_rate
        
    def augment_dataset(self, dataset: List[Tuple[Dict, List]], 
                      strategy_effectiveness_threshold: float = 15.0) -> List[Tuple[Dict, List]]:
        """
        对数据集进行策略导向增强
        
        Args:
            dataset: 原始数据集，每个样本为(state_dict, action_cards)
            strategy_effectiveness_threshold: 策略有效性阈值（高于此值的为高质量策略）
            
        Returns:
            增强后的数据集
        """
        # 1. 分析数据集
        high_quality_samples = []
        low_quality_samples = []
        
        for state_dict, action_cards in dataset:
            effectiveness = state_dict.get('strategy_effectiveness', 0.0)
            if effectiveness >= strategy_effectiveness_threshold:
                high_quality_samples.append((state_dict, action_cards))
            else:
                low_quality_samples.append((state_dict, action_cards))
        
        print(f"[数据增强] 原始数据集: {len(dataset)} 个样本")
        print(f"  高质量策略样本: {len(high_quality_samples)} ({len(high_quality_samples)/len(dataset)*100:.1f}%)")
        print(f"  低质量策略样本: {len(low_quality_samples)} ({len(low_quality_samples)/len(dataset)*100:.1f}%)")
        
        # 2. 计算需要增强的数量
        current_success_rate = len(high_quality_samples) / len(dataset) if dataset else 0.0
        if current_success_rate >= self.target_success_rate:
            print(f"[数据增强] 当前成功策略比例({current_success_rate:.1%})已达到目标({self.target_success_rate:.1%})，无需增强")
            return dataset
        
        # 计算需要增加的高质量样本数量
        target_high_quality_count = int(len(dataset) * self.target_success_rate)
        needed_count = max(0, target_high_quality_count - len(high_quality_samples))
        
        print(f"[数据增强] 目标成功策略比例: {self.target_success_rate:.1%}")
        print(f"[数据增强] 需要增加高质量样本: {needed_count} 个")
        
        # 3. 数据增强策略
        augmented_samples = []
        
        # 策略1：高质量样本的轻微变体（保持策略有效性）
        if high_quality_samples and needed_count > 0:
            # 对高质量样本进行轻微扰动，生成变体
            variant_count = min(needed_count, len(high_quality_samples))
            for _ in range(variant_count):
                original_state, original_action = random.choice(high_quality_samples)
                variant_state, variant_action = self._create_variant(original_state, original_action)
                augmented_samples.append((variant_state, variant_action))
        
        # 策略2：从低质量样本中筛选并提升（如果策略类型正确但效果不佳）
        remaining_needed = needed_count - len(augmented_samples)
        if remaining_needed > 0 and low_quality_samples:
            # 筛选策略类型正确但效果不佳的样本
            promotable_samples = []
            for state_dict, action_cards in low_quality_samples:
                strategy_type = state_dict.get('strategy_type', 'unknown')
                # 如果策略类型不是unknown，说明策略选择是正确的，只是效果不佳
                if strategy_type != 'unknown':
                    promotable_samples.append((state_dict, action_cards))
            
            # 提升这些样本的策略有效性（模拟在更好局面下的效果）
            promote_count = min(remaining_needed, len(promotable_samples))
            for i in range(promote_count):
                state_dict, action_cards = promotable_samples[i]
                # 提升策略有效性分数
                enhanced_state = state_dict.copy()
                original_effectiveness = enhanced_state.get('strategy_effectiveness', 0.0)
                # 提升到中等水平（15-25之间）
                enhanced_state['strategy_effectiveness'] = min(25.0, original_effectiveness + 10.0)
                augmented_samples.append((enhanced_state, action_cards))
        
        # 4. 组合数据集
        # 保留所有原始样本
        final_dataset = list(dataset)
        # 添加增强样本
        final_dataset.extend(augmented_samples)
        
        # 5. 重新分析增强后的数据集
        high_quality_final = sum(1 for s, _ in final_dataset 
                                if s.get('strategy_effectiveness', 0.0) >= strategy_effectiveness_threshold)
        final_success_rate = high_quality_final / len(final_dataset) if final_dataset else 0.0
        
        print(f"[数据增强] 增强后数据集: {len(final_dataset)} 个样本")
        print(f"  高质量策略样本: {high_quality_final} ({final_success_rate:.1%})")
        print(f"  新增样本: {len(augmented_samples)} 个")
        
        return final_dataset
    
    def _create_variant(self, state_dict: Dict, action_cards: List) -> Tuple[Dict, List]:
        """
        创建样本的轻微变体（保持策略有效性）
        
        Args:
            state_dict: 原始状态字典
            action_cards: 原始动作卡牌
            
        Returns:
            变体样本 (variant_state, variant_action)
        """
        # 创建状态的副本
        variant_state = state_dict.copy()
        
        # 轻微扰动策略有效性（±2范围内）
        original_effectiveness = variant_state.get('strategy_effectiveness', 0.0)
        variant_state['strategy_effectiveness'] = max(0.0, min(30.0, 
            original_effectiveness + random.uniform(-2.0, 2.0)))
        
        # 动作保持不变（因为策略有效性已经反映了动作的质量）
        variant_action = list(action_cards)
        
        return variant_state, variant_action
    
    def filter_high_quality_samples(self, dataset: List[Tuple[Dict, List]], 
                                   min_effectiveness: float = 15.0) -> List[Tuple[Dict, List]]:
        """
        筛选高质量策略样本
        
        Args:
            dataset: 数据集
            min_effectiveness: 最小策略有效性阈值
            
        Returns:
            筛选后的高质量样本列表
        """
        high_quality = []
        for state_dict, action_cards in dataset:
            effectiveness = state_dict.get('strategy_effectiveness', 0.0)
            if effectiveness >= min_effectiveness:
                high_quality.append((state_dict, action_cards))
        
        return high_quality
    
    def balance_strategy_types(self, dataset: List[Tuple[Dict, List]]) -> List[Tuple[Dict, List]]:
        """
        平衡不同策略类型的样本分布
        
        Args:
            dataset: 数据集
            
        Returns:
            平衡后的数据集
        """
        # 统计各策略类型的样本数
        strategy_counts = {}
        strategy_samples = {}
        
        for state_dict, action_cards in dataset:
            strategy_type = state_dict.get('strategy_type', 'unknown')
            strategy_counts[strategy_type] = strategy_counts.get(strategy_type, 0) + 1
            if strategy_type not in strategy_samples:
                strategy_samples[strategy_type] = []
            strategy_samples[strategy_type].append((state_dict, action_cards))
        
        # 计算目标样本数（使用最多的策略类型作为基准）
        max_count = max(strategy_counts.values()) if strategy_counts else 0
        target_count = int(max_count * 0.8)  # 目标为最大值的80%
        
        # 对每个策略类型进行采样或重复
        balanced_dataset = []
        for strategy_type, samples in strategy_samples.items():
            current_count = len(samples)
            if current_count < target_count:
                # 需要增加样本：重复采样
                needed = target_count - current_count
                additional = random.choices(samples, k=needed)
                balanced_dataset.extend(samples)
                balanced_dataset.extend(additional)
            else:
                # 样本过多：随机采样
                balanced_dataset.extend(random.sample(samples, target_count))
        
        print(f"[策略类型平衡] 原始样本数: {len(dataset)}")
        print(f"[策略类型平衡] 平衡后样本数: {len(balanced_dataset)}")
        for strategy_type, count in strategy_counts.items():
            balanced_count = sum(1 for s, _ in balanced_dataset 
                               if s.get('strategy_type') == strategy_type)
            print(f"  {strategy_type}: {count} → {balanced_count}")
        
        return balanced_dataset


def apply_strategy_augmentation(data_dir: str = "game_records", 
                                target_success_rate: float = 0.8):
    """
    应用策略导向数据增强
    
    Args:
        data_dir: 游戏记录目录
        target_success_rate: 目标成功策略比例
    """
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from src.knowledge_processor.replay_parser import ReplayParser
    
    print("="*60)
    print("阶段6：策略导向数据增强")
    print("="*60)
    
    # 加载数据
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    dataset = parser.extract_training_data(replays)
    
    print(f"原始数据集: {len(dataset)} 个样本\n")
    
    # 应用数据增强
    augmenter = StrategyOrientedAugmentation(target_success_rate=target_success_rate)
    augmented_dataset = augmenter.augment_dataset(dataset)
    
    # 可选：平衡策略类型
    balanced_dataset = augmenter.balance_strategy_types(augmented_dataset)
    
    print(f"\n最终数据集: {len(balanced_dataset)} 个样本")
    
    return balanced_dataset


if __name__ == "__main__":
    apply_strategy_augmentation()

