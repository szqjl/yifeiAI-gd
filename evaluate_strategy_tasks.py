#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估6个策略任务的具体效果
通过测试模型在6个任务上的表现来验证训练效果
"""

import sys
import os
import torch
import numpy as np
from pathlib import Path

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.rl_agent.model import ImprovedGuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser

def evaluate_strategy_tasks():
    """评估6个策略任务的效果"""
    print("="*80)
    print("6个策略任务效果评估")
    print("="*80)
    print()
    
    # 1. 加载模型
    model_path = "models/bc_model_strategy_tasks.pth"
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return
    
    print(f"✓ 加载模型: {model_path}")
    device = torch.device('cpu')
    
    # 创建模型
    model = ImprovedGuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=0.1,
        strategy_num_classes=7,
        enable_strategy_head=True,
        attention_heads=8,
        enable_strategy_tasks=True  # 启用6个策略任务
    ).to(device)
    
    # 加载权重
    checkpoint = torch.load(model_path, map_location='cpu')
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'], strict=False)
        print("✓ 模型权重加载成功")
    else:
        print("❌ 检查点中未找到模型权重")
        return
    
    model.eval()
    print()
    
    # 2. 加载测试数据
    print("加载测试数据...")
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    # 使用前100个样本进行测试
    test_samples = raw_data[:100]
    print(f"✓ 使用 {len(test_samples)} 个测试样本")
    print()
    
    # 3. 评估6个策略任务
    print("[6个策略任务评估]")
    print("-"*80)
    
    # 统计指标
    grouping_correct = 0
    role_correct = 0
    power_errors = []
    protect_suppress_correct = 0
    bomb_timing_correct = 0
    red_heart_correct = 0
    total_samples = 0
    
    with torch.no_grad():
        for state_dict, action_cards in test_samples:
            # 构建状态向量（简化版，使用与训练时相同的编码）
            state_vec = np.zeros(512, dtype=np.float32)
            
            # 编码手牌（简化版）
            hand_cards = state_dict.get('hand', [])
            for card in hand_cards[:60]:  # 只编码前60张
                # 简化的编码方式
                if len(card) >= 2:
                    suit = card[0]
                    rank = card[1] if len(card) == 2 else card[1:2]
                    suit_map = {'S': 0, 'H': 1, 'C': 2, 'D': 3}
                    rank_map = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                               'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12, 'B': 13, 'R': 14}
                    suit_val = suit_map.get(suit, 0)
                    rank_val = rank_map.get(rank, 0)
                    idx = suit_val * 15 + rank_val
                    if idx < 60:
                        state_vec[idx] = 1.0
            
            # 转换为tensor
            state_tensor = torch.FloatTensor(state_vec).unsqueeze(0).to(device)
            
            # 前向传播
            outputs = model(state_tensor, return_strategy=True, return_strategy_tasks=True)
            
            if len(outputs) == 3:
                action_logits, strategy_logits, strategy_tasks_outputs = outputs
                
                # 获取真实标签
                strategy_tasks = state_dict.get('strategy_tasks', {})
                if not strategy_tasks:
                    continue
                
                total_samples += 1
                
                # 任务1: 组牌策略
                grouping_pred = torch.argmax(strategy_tasks_outputs['grouping'], dim=1).item()
                grouping_true = strategy_tasks.get('grouping', 0)
                if grouping_pred == grouping_true:
                    grouping_correct += 1
                
                # 任务2: 角色判断
                role_pred = torch.argmax(strategy_tasks_outputs['role'], dim=1).item()
                role_true = strategy_tasks.get('role', 2)
                if role_pred == role_true:
                    role_correct += 1
                
                # 任务3: 牌力评估（回归）
                power_pred = strategy_tasks_outputs['power'].squeeze().item()
                power_true = strategy_tasks.get('power', 5.0)
                power_error = abs(power_pred - power_true)
                power_errors.append(power_error)
                
                # 任务4: 保护/压制判断
                protect_suppress_pred = torch.argmax(strategy_tasks_outputs['protect_suppress'], dim=1).item()
                protect_suppress_true = strategy_tasks.get('protect_suppress', 2)
                if protect_suppress_pred == protect_suppress_true:
                    protect_suppress_correct += 1
                
                # 任务5: 炸弹出炸时机
                bomb_timing_pred = torch.argmax(strategy_tasks_outputs['bomb_timing'], dim=1).item()
                bomb_timing_true = strategy_tasks.get('bomb_timing', 4)
                if bomb_timing_pred == bomb_timing_true:
                    bomb_timing_correct += 1
                
                # 任务6: 红心配策略
                red_heart_pred = torch.argmax(strategy_tasks_outputs['red_heart'], dim=1).item()
                red_heart_true = strategy_tasks.get('red_heart', 3)
                if red_heart_pred == red_heart_true:
                    red_heart_correct += 1
    
    # 4. 输出结果
    if total_samples > 0:
        print(f"测试样本数: {total_samples}")
        print()
        print("任务1 - 组牌策略分类:")
        print(f"  准确率: {grouping_correct/total_samples:.2%} ({grouping_correct}/{total_samples})")
        print()
        print("任务2 - 角色判断:")
        print(f"  准确率: {role_correct/total_samples:.2%} ({role_correct}/{total_samples})")
        print()
        print("任务3 - 牌力评估（回归）:")
        if power_errors:
            avg_error = np.mean(power_errors)
            max_error = np.max(power_errors)
            print(f"  平均误差: {avg_error:.2f} 分")
            print(f"  最大误差: {max_error:.2f} 分")
            print(f"  误差 < 1.0: {sum(1 for e in power_errors if e < 1.0)/len(power_errors):.2%}")
            print(f"  误差 < 2.0: {sum(1 for e in power_errors if e < 2.0)/len(power_errors):.2%}")
        print()
        print("任务4 - 保护/压制判断:")
        print(f"  准确率: {protect_suppress_correct/total_samples:.2%} ({protect_suppress_correct}/{total_samples})")
        print()
        print("任务5 - 炸弹出炸时机:")
        print(f"  准确率: {bomb_timing_correct/total_samples:.2%} ({bomb_timing_correct}/{total_samples})")
        print()
        print("任务6 - 红心配策略:")
        print(f"  准确率: {red_heart_correct/total_samples:.2%} ({red_heart_correct}/{total_samples})")
        print()
        
        # 总体评估
        avg_accuracy = (grouping_correct + role_correct + protect_suppress_correct + 
                       bomb_timing_correct + red_heart_correct) / (total_samples * 5)
        print("="*80)
        print("总体评估")
        print("="*80)
        print(f"5个分类任务平均准确率: {avg_accuracy:.2%}")
        if power_errors:
            print(f"牌力评估平均误差: {np.mean(power_errors):.2f} 分")
        print()
        
        if avg_accuracy > 0.7:
            print("✓ 策略任务学习效果良好")
        elif avg_accuracy > 0.5:
            print("⚠ 策略任务学习效果一般，需要改进")
        else:
            print("✗ 策略任务学习效果较差，需要重新训练或调整")
    else:
        print("❌ 没有有效的测试样本（可能缺少strategy_tasks标注）")
    
    print("="*80)

if __name__ == "__main__":
    evaluate_strategy_tasks()

