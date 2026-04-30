"""分析损失函数计算问题"""
import torch
import numpy as np

print("="*60)
print("损失函数计算分析")
print("="*60)

# 模拟当前参数
over_prediction_penalty = 576650.390625
sparsity_reward = 2883251.953125
alpha = 0.09313225746154785
gamma = 6.0

# 模拟预测情况（基于训练历史）
pred_count = 512.0  # 模型预测了所有卡牌
true_count = 1.44  # 真实卡牌数

print(f"\n当前参数:")
print(f"  over_prediction_penalty: {over_prediction_penalty:,.2f}")
print(f"  sparsity_reward: {sparsity_reward:,.2f}")
print(f"  alpha: {alpha}")
print(f"  gamma: {gamma}")

print(f"\n模拟预测情况:")
print(f"  预测卡牌数: {pred_count}")
print(f"  真实卡牌数: {true_count}")

# 计算过度预测惩罚
over_prediction = max(0, pred_count - true_count)
over_prediction_penalty_value = over_prediction_penalty * (over_prediction ** 2)

print(f"\n过度预测惩罚计算:")
print(f"  过度预测数: {over_prediction:.2f}")
print(f"  惩罚值: {over_prediction_penalty_value:,.2f}")

# 计算稀疏性奖励
sparsity_bonus = sparsity_reward * np.exp(-pred_count / 10.0)
print(f"\n稀疏性奖励计算:")
print(f"  奖励值: {sparsity_bonus:,.2f}")

# 分析问题
print(f"\n问题分析:")
print(f"  1. 过度预测惩罚过大: {over_prediction_penalty_value:,.2f}")
print(f"     这导致损失值异常高（800亿级别）")
print(f"  2. 稀疏性奖励相对较小: {sparsity_bonus:,.2f}")
print(f"     无法抵消过度预测惩罚")
print(f"  3. 阈值可能设置不当，导致所有卡牌都被预测")

print(f"\n建议:")
print(f"  1. 降低过度预测惩罚系数（当前过大）")
print(f"  2. 检查阈值设置（adaptive_threshold * sparsity_weight）")
print(f"  3. 考虑使用更温和的惩罚函数（如线性而非平方）")
print(f"  4. 增加稀疏性奖励的权重")

print("\n" + "="*60)
