#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段5模型评估脚本
评估阶段5模型的性能指标
"""

import sys
import os
import torch
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.knowledge_processor.replay_parser import ReplayParser
from src.rl_agent.model import ImprovedGuandanPolicyNet
from src.rl_agent.strategy_pattern_recognizer import StrategyPatternRecognizer
from src.rl_agent.opponent_model import OpponentModel
from src.rl_agent.dynamic_strategy_adjuster import DynamicStrategyAdjuster

def evaluate_stage5_model(model_path="models/bc_model_stage5_final.pth", data_dir="game_records", max_samples=1000):
    """
    评估阶段5模型
    
    Args:
        model_path: 模型文件路径
        data_dir: 数据目录
        max_samples: 最大评估样本数
    """
    print("="*80)
    print("阶段5模型评估")
    print("="*80)
    print(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模型路径: {model_path}")
    print(f"数据目录: {data_dir}")
    print("="*80)
    print()
    
    # 检查模型文件是否存在
    if not os.path.exists(model_path):
        print(f"❌ 错误: 模型文件不存在: {model_path}")
        print("   请先完成训练，或检查模型路径是否正确")
        return
    
    # 加载数据
    print("📊 加载评估数据...")
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    if len(raw_data) == 0:
        print("❌ 错误: 未找到训练数据")
        return
    
    # 限制评估样本数
    if max_samples and len(raw_data) > max_samples:
        raw_data = raw_data[:max_samples]
        print(f"   限制评估样本数: {max_samples}")
    
    print(f"✅ 加载了 {len(raw_data)} 个评估样本")
    print()
    
    # 加载模型
    print("🤖 加载模型...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"   使用设备: {device}")
    
    # 创建模型
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
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'], strict=False)
            print(f"✅ 模型加载成功（检查点格式）")
            if 'final_action_exact_accuracy' in checkpoint:
                print(f"   训练时完全匹配准确率: {checkpoint['final_action_exact_accuracy']:.2%}")
            if 'final_strategy_accuracy' in checkpoint:
                print(f"   训练时策略分类准确率: {checkpoint['final_strategy_accuracy']:.2%}")
        else:
            model.load_state_dict(checkpoint, strict=False)
            print(f"✅ 模型加载成功（直接权重格式）")
    except Exception as e:
        print(f"❌ 错误: 模型加载失败: {e}")
        return
    
    model.eval()
    print()
    
    # 创建阶段5组件（用于评估）
    strategy_pattern_recognizer = StrategyPatternRecognizer(
        input_dim=512,
        pattern_types=8,
        hidden_dim=256
    ).to(device)
    
    opponent_model = OpponentModel(
        state_dim=512,
        action_dim=512,
        opponent_types=5
    ).to(device)
    
    dynamic_strategy_adjuster = DynamicStrategyAdjuster(
        state_dim=512,
        strategy_count=7
    ).to(device)
    
    # 评估指标
    print("📈 开始评估...")
    total_samples = 0
    correct_action_predictions = 0
    total_action_cards = 0
    matched_action_cards = 0
    
    total_strategy_samples = 0
    correct_strategy_predictions = 0
    strategy_understanding_count = 0
    
    # 预测分布统计
    prediction_too_many = 0
    prediction_too_few = 0
    exact_match = 0
    
    # 评估参数（基线参数）
    prob_scale = 5.0  # 概率缩放因子（根据历次训练效果汇总，796样本使用5.0）
    threshold = 0.3   # 预测阈值（根据历次训练效果汇总，796样本使用0.3）
    
    print(f"   评估参数: 概率缩放={prob_scale}, 阈值={threshold}")
    print()
    
    with torch.no_grad():
        for i, (state_dict, action_cards) in enumerate(raw_data):
            # 转换为模型输入格式（简化版，实际需要完整的数据处理）
            # 这里使用简化的评估，实际应该使用完整的Dataset类
            
            if (i + 1) % 100 == 0:
                print(f"   评估进度: {i+1}/{len(raw_data)} ({100*(i+1)/len(raw_data):.1f}%)")
    
    print()
    print("="*80)
    print("评估结果")
    print("="*80)
    
    if total_samples > 0:
        action_exact_accuracy = correct_action_predictions / total_samples
        action_card_accuracy = matched_action_cards / total_action_cards if total_action_cards > 0 else 0.0
        strategy_accuracy = correct_strategy_predictions / total_strategy_samples if total_strategy_samples > 0 else 0.0
        strategy_understanding_rate = strategy_understanding_count / total_strategy_samples if total_strategy_samples > 0 else 0.0
        
        print(f"📊 动作预测性能:")
        print(f"   完全匹配准确率: {action_exact_accuracy:.2%}")
        print(f"   卡牌级别准确率: {action_card_accuracy:.2%}")
        print()
        
        if total_strategy_samples > 0:
            print(f"📊 策略分类性能:")
            print(f"   策略分类准确率: {strategy_accuracy:.2%}")
            print(f"   策略理解率: {strategy_understanding_rate:.2%}")
            print()
        
        print(f"📊 预测分布:")
        print(f"   完全匹配: {exact_match} ({100*exact_match/total_samples:.1f}%)")
        print(f"   预测过多: {prediction_too_many} ({100*prediction_too_many/total_samples:.1f}%)")
        print(f"   预测过少: {prediction_too_few} ({100*prediction_too_few/total_samples:.1f}%)")
        print()
        
        # 保存评估结果
        result_file = f"training_logs/stage5_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("阶段5模型评估结果\n")
            f.write("="*80 + "\n")
            f.write(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"模型路径: {model_path}\n")
            f.write(f"评估样本数: {total_samples}\n")
            f.write(f"评估参数: 概率缩放={prob_scale}, 阈值={threshold}\n")
            f.write("\n")
            f.write(f"完全匹配准确率: {action_exact_accuracy:.2%}\n")
            f.write(f"卡牌级别准确率: {action_card_accuracy:.2%}\n")
            if total_strategy_samples > 0:
                f.write(f"策略分类准确率: {strategy_accuracy:.2%}\n")
                f.write(f"策略理解率: {strategy_understanding_rate:.2%}\n")
            f.write(f"\n预测分布:\n")
            f.write(f"  完全匹配: {exact_match} ({100*exact_match/total_samples:.1f}%)\n")
            f.write(f"  预测过多: {prediction_too_many} ({100*prediction_too_many/total_samples:.1f}%)\n")
            f.write(f"  预测过少: {prediction_too_few} ({100*prediction_too_few/total_samples:.1f}%)\n")
        
        print(f"✅ 评估结果已保存到: {result_file}")
    else:
        print("⚠️ 未完成评估（需要实现完整的数据处理逻辑）")
        print("   建议使用现有的评估脚本: src/train/evaluate_baseline.py")
    
    print("="*80)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="阶段5模型评估")
    parser.add_argument("--model_path", type=str, default="models/bc_model_stage5_final.pth",
                        help="模型文件路径")
    parser.add_argument("--data_dir", type=str, default="game_records",
                        help="数据目录")
    parser.add_argument("--max_samples", type=int, default=1000,
                        help="最大评估样本数")
    
    args = parser.parse_args()
    evaluate_stage5_model(args.model_path, args.data_dir, args.max_samples)

