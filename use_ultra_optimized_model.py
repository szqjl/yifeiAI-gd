#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用超优化版模型进行推理和评估
模型: models/bc_model_stage5_ultra_optimized.pth
"""

import sys
import os
import torch
import numpy as np

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.rl_agent.model import ImprovedGuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader

def load_ultra_optimized_model(model_path="models/bc_model_stage5_ultra_optimized.pth"):
    """
    加载超优化版模型
    
    Args:
        model_path: 模型文件路径
        
    Returns:
        model: 加载的模型
        device: 使用的设备
        model_info: 模型信息字典
    """
    print("="*80)
    print("加载超优化版模型")
    print("="*80)
    
    # 检查模型文件
    if not os.path.exists(model_path):
        print(f"❌ 错误: 模型文件不存在: {model_path}")
        return None, None, None
    
    model_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
    print(f"✓ 模型文件: {model_path}")
    print(f"✓ 模型大小: {model_size:.2f} MB")
    
    # 选择设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"✓ 使用设备: {device}")
    
    # 创建模型（超优化版使用ImprovedGuandanPolicyNet）
    model = ImprovedGuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=0.1,
        strategy_num_classes=7,
        enable_strategy_head=True,
        attention_heads=8
    ).to(device)
    
    # 加载模型权重
    try:
        checkpoint = torch.load(model_path, map_location=device)
        model_info = {}
        
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'], strict=False)
            print(f"✓ 模型加载成功（检查点格式）")
            
            # 提取模型信息
            if 'final_action_exact_accuracy' in checkpoint:
                model_info['action_exact_accuracy'] = checkpoint['final_action_exact_accuracy']
                print(f"  训练时完全匹配准确率: {checkpoint['final_action_exact_accuracy']:.2%}")
            if 'final_action_card_accuracy' in checkpoint:
                model_info['action_card_accuracy'] = checkpoint['final_action_card_accuracy']
                print(f"  训练时卡牌级别准确率: {checkpoint['final_action_card_accuracy']:.2%}")
            if 'final_strategy_accuracy' in checkpoint:
                model_info['strategy_accuracy'] = checkpoint['final_strategy_accuracy']
                print(f"  训练时策略分类准确率: {checkpoint['final_strategy_accuracy']:.2%}")
            if 'final_strategy_understanding_rate' in checkpoint:
                model_info['strategy_understanding_rate'] = checkpoint['final_strategy_understanding_rate']
                print(f"  训练时策略理解率: {checkpoint['final_strategy_understanding_rate']:.2%}")
        else:
            model.load_state_dict(checkpoint, strict=False)
            print(f"✓ 模型加载成功（直接权重格式）")
            
    except Exception as e:
        print(f"❌ 错误: 模型加载失败: {e}")
        import traceback
        print(traceback.format_exc())
        return None, None, None
    
    model.eval()
    print()
    
    return model, device, model_info


def evaluate_model(model, device, data_dir="game_records", max_samples=500):
    """
    评估模型性能
    
    Args:
        model: 模型
        device: 设备
        data_dir: 数据目录
        max_samples: 最大样本数
    """
    print("="*80)
    print("评估模型性能")
    print("="*80)
    
    # 加载数据
    print(f"📦 加载数据: {data_dir}")
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    if len(raw_data) == 0:
        print(f"❌ 错误: 没有找到数据: {data_dir}")
        return
    
    if max_samples:
        raw_data = raw_data[:max_samples]
    
    print(f"✓ 数据加载完成，共 {len(raw_data)} 个样本")
    
    # 创建数据集
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    # 评估参数（基线参数）
    prediction_threshold = 0.3
    scaling_factor = 5.0
    
    print(f"✓ 评估参数: 阈值={prediction_threshold}, 缩放因子={scaling_factor}")
    print()
    
    # 评估指标
    total_samples = 0
    correct_action_predictions = 0
    total_action_cards = 0
    matched_action_cards = 0
    
    total_strategy_samples = 0
    correct_strategy_predictions = 0
    strategy_understanding_count = 0
    
    with torch.no_grad():
        for batch in dataloader:
            if len(batch) >= 2:
                states = batch[0].to(device)
                actions = batch[1].to(device)
                
                # 获取策略标签（如果有）
                strategy_labels = None
                if len(batch) >= 3:
                    strategy_labels = batch[2]
                
                # 动作预测
                predictions_list = []
                for i in range(len(states)):
                    state = states[i:i+1]
                    action = model.get_action(state, deterministic=True, 
                                             threshold=prediction_threshold, 
                                             scaling_factor=scaling_factor)
                    predictions_list.append(torch.from_numpy(action).float())
                predictions = torch.stack(predictions_list).to(device)
                
                # 确保维度一致
                if predictions.shape != actions.shape:
                    min_dim = min(predictions.shape[1], actions.shape[1])
                    predictions = predictions[:, :min_dim]
                    actions = actions[:, :min_dim]
                
                # 完全匹配准确率和卡牌级别准确率（逐样本计算）
                for i in range(len(states)):
                    exact_match = (predictions[i] == actions[i]).all().item()
                    if exact_match:
                        correct_action_predictions += 1
                    total_samples += 1
                    
                    # 卡牌级别准确率
                    sample_matched_cards = (predictions[i] == actions[i]).sum().item()
                    sample_total_cards = actions[i].numel()
                    matched_action_cards += sample_matched_cards
                    total_action_cards += sample_total_cards
                
                # 策略分类准确率（如果有策略标签）
                if strategy_labels is not None:
                    strategy_logits = model(states, return_strategy=True)[1]
                    strategy_preds = torch.argmax(strategy_logits, dim=1).cpu()
                    
                    # 逐样本计算策略准确率和策略理解率
                    for i in range(len(states)):
                        if strategy_labels[i] < 7:  # 排除unknown
                            total_strategy_samples += 1
                            if strategy_preds[i] == strategy_labels[i]:
                                correct_strategy_predictions += 1
                            
                            # 策略理解率（动作和策略都正确）
                            exact_match = (predictions[i] == actions[i]).all().item()
                            strategy_correct = (strategy_preds[i] == strategy_labels[i]).item() if strategy_labels[i] < 7 else False
                            if exact_match and strategy_correct:
                                strategy_understanding_count += 1
    
    # 输出结果
    print("="*80)
    print("评估结果")
    print("="*80)
    
    action_exact_accuracy = correct_action_predictions / total_samples if total_samples > 0 else 0.0
    action_card_accuracy = matched_action_cards / total_action_cards if total_action_cards > 0 else 0.0
    
    print(f"动作预测准确率:")
    print(f"  - 完全匹配: {action_exact_accuracy:.2%} ({correct_action_predictions}/{total_samples})")
    print(f"  - 卡牌级别: {action_card_accuracy:.2%}")
    
    if total_strategy_samples > 0:
        strategy_accuracy = correct_strategy_predictions / total_strategy_samples
        strategy_understanding_rate = strategy_understanding_count / total_strategy_samples
        
        print(f"策略分类准确率: {strategy_accuracy:.2%} ({correct_strategy_predictions}/{total_strategy_samples})")
        print(f"策略理解率: {strategy_understanding_rate:.2%} ({strategy_understanding_count}/{total_strategy_samples})")
    
    print("="*80)
    
    return {
        'action_exact_accuracy': action_exact_accuracy,
        'action_card_accuracy': action_card_accuracy,
        'strategy_accuracy': strategy_accuracy if total_strategy_samples > 0 else None,
        'strategy_understanding_rate': strategy_understanding_rate if total_strategy_samples > 0 else None
    }


if __name__ == "__main__":
    # 加载模型
    model, device, model_info = load_ultra_optimized_model()
    
    if model is None:
        print("模型加载失败，退出")
        sys.exit(1)
    
    print()
    print("="*80)
    print("模型信息")
    print("="*80)
    print("超优化版模型配置:")
    print("  - 策略权重: 0.3")
    print("  - 阶段5任务: 禁用")
    print("  - 预测数量惩罚权重: 3.0")
    print("  - L1损失权重: 0.5")
    print("  - 数据量: 15000样本")
    print("  - 训练轮数: 60 epochs")
    print()
    print("训练时性能:")
    if model_info:
        if 'action_exact_accuracy' in model_info:
            print(f"  - 完全匹配准确率: {model_info['action_exact_accuracy']:.2%}")
        if 'action_card_accuracy' in model_info:
            print(f"  - 卡牌级别准确率: {model_info['action_card_accuracy']:.2%}")
        if 'strategy_accuracy' in model_info:
            print(f"  - 策略分类准确率: {model_info['strategy_accuracy']:.2%}")
        if 'strategy_understanding_rate' in model_info:
            print(f"  - 策略理解率: {model_info['strategy_understanding_rate']:.2%}")
    print()
    
    # 评估模型
    print("是否进行评估? (y/n): ", end="")
    # 默认进行评估
    evaluate = True
    
    if evaluate:
        results = evaluate_model(model, device, max_samples=500)
        print()
        print("="*80)
        print("评估完成")
        print("="*80)
    else:
        print("跳过评估")
        print()
        print("="*80)
        print("模型已加载，可以使用 model.get_action() 进行推理")
        print("="*80)

