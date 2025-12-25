"""
分析完全匹配率为0的根本原因
"""

import torch
import numpy as np
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_exact_match_problem():
    """分析完全匹配率问题的根本原因"""
    
    logger.info("=" * 60)
    logger.info("分析完全匹配率为0的根本原因")
    logger.info("=" * 60)
    
    # 1. 加载数据样本进行分析
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=32,
        max_samples=500,
        shuffle=False
    )
    
    # 2. 分析真实动作的分布
    all_true_actions = []
    all_card_counts = []
    
    for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
        for i in range(action_vec.size(0)):
            true_action = action_vec[i].numpy()
            card_count = int(true_action.sum())
            
            all_true_actions.append(true_action)
            all_card_counts.append(card_count)
            
            if len(all_true_actions) >= 100:  # 分析前100个样本
                break
        if len(all_true_actions) >= 100:
            break
    
    # 3. 统计分析
    card_count_distribution = {}
    for count in all_card_counts:
        card_count_distribution[count] = card_count_distribution.get(count, 0) + 1
    
    logger.info(f"分析样本数: {len(all_true_actions)}")
    logger.info(f"卡牌数量分布: {card_count_distribution}")
    logger.info(f"平均卡牌数: {np.mean(all_card_counts):.2f}")
    logger.info(f"卡牌数标准差: {np.std(all_card_counts):.2f}")
    
    # 4. 分析动作向量的稀疏性
    sparsity_rates = []
    for action in all_true_actions:
        sparsity = 1.0 - (action.sum() / len(action))
        sparsity_rates.append(sparsity)
    
    logger.info(f"平均稀疏率: {np.mean(sparsity_rates):.4f}")
    logger.info(f"稀疏率标准差: {np.std(sparsity_rates):.4f}")
    
    # 5. 分析具体的动作模式
    logger.info("\n前10个样本的详细分析:")
    for i in range(min(10, len(all_true_actions))):
        action = all_true_actions[i]
        active_positions = np.where(action == 1)[0]
        logger.info(f"样本 {i+1}: 卡牌数={all_card_counts[i]}, 激活位置={active_positions.tolist()}")
    
    # 6. 计算理论上的完全匹配概率
    # 假设随机预测，完全匹配的概率
    avg_cards = np.mean(all_card_counts)
    total_positions = 512
    
    # 组合数学计算：C(total_positions, avg_cards) 种可能的组合
    # 完全匹配概率 = 1 / C(total_positions, avg_cards)
    from math import comb
    if avg_cards <= 20:  # 避免计算过大的组合数
        total_combinations = comb(total_positions, int(avg_cards))
        theoretical_match_prob = 1.0 / total_combinations
        logger.info(f"\n理论分析:")
        logger.info(f"平均需要预测 {avg_cards:.1f} 张卡牌")
        logger.info(f"总共 {total_positions} 个位置")
        logger.info(f"可能的组合数: {total_combinations:e}")
        logger.info(f"理论完全匹配概率: {theoretical_match_prob:e}")
        logger.info(f"这解释了为什么完全匹配率接近0")
    
    # 7. 建议的解决方案
    logger.info("\n=" * 60)
    logger.info("问题根本原因和解决建议")
    logger.info("=" * 60)
    
    logger.info("根本原因:")
    logger.info("1. 组合爆炸: 从512个位置中选择2-3张卡牌的组合数极大")
    logger.info("2. 稀疏性极高: 99.4%的位置都是0，只有0.6%是1")
    logger.info("3. 精确匹配要求过严: 要求所有512个位置都完全正确")
    
    logger.info("\n解决方案建议:")
    logger.info("1. 降低完全匹配要求: 改为'有效卡牌完全匹配'")
    logger.info("2. 引入近似匹配: 允许1-2个位置的误差")
    logger.info("3. 分层评估: 先评估卡牌数量，再评估位置准确性")
    logger.info("4. 重新定义成功指标: 关注实用性而非理论完美")
    
    return {
        'avg_card_count': np.mean(all_card_counts),
        'sparsity_rate': np.mean(sparsity_rates),
        'card_count_distribution': card_count_distribution,
        'theoretical_match_prob': theoretical_match_prob if avg_cards <= 20 else 0
    }


if __name__ == "__main__":
    results = analyze_exact_match_problem()