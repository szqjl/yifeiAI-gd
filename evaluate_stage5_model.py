#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段5模型评估脚本
评估阶段5模型的性能指标（包含策略模式识别、对手建模、动态策略调整）
"""

import sys
import os
import torch
import numpy as np
from datetime import datetime

# 修复Windows控制台编码
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.knowledge_processor.replay_parser import ReplayParser
from src.rl_agent.model import ImprovedGuandanPolicyNet
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader

def evaluate_stage5_model(model_path="models/bc_model_stage5_final.pth", 
                         data_dir="game_records", 
                         max_samples=1000,
                         threshold=0.3,
                         scaling_factor=5.0):
    """
    评估阶段5模型
    
    Args:
        model_path: 模型文件路径
        data_dir: 数据目录
        max_samples: 最大评估样本数
        threshold: 预测阈值（基线：0.3）
        scaling_factor: 概率缩放因子（基线：5.0）
    """
    print("="*80)
    print("阶段5模型评估")
    print("="*80)
    print(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模型路径: {model_path}")
    print(f"数据目录: {data_dir}")
    print(f"评估参数: 阈值={threshold}, 缩放因子={scaling_factor}")
    print("="*80)
    print()
    
    # 检查模型文件是否存在
    if not os.path.exists(model_path):
        print(f"❌ 错误: 模型文件不存在: {model_path}")
        print("   请先完成训练，或检查模型路径是否正确")
        return None
    
    model_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
    print(f"✅ 模型文件: {model_path}")
    print(f"✅ 模型大小: {model_size:.2f} MB")
    print()
    
    # 加载数据
    print("📊 加载评估数据...")
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    if len(raw_data) == 0:
        print("❌ 错误: 未找到训练数据")
        return None
    
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
    
    # 创建模型（阶段5使用ImprovedGuandanPolicyNet）
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
            if 'final_strategy_understanding_rate' in checkpoint:
                print(f"   训练时策略理解率: {checkpoint['final_strategy_understanding_rate']:.2%}")
        else:
            model.load_state_dict(checkpoint, strict=False)
            print(f"✅ 模型加载成功（直接权重格式）")
    except Exception as e:
        print(f"❌ 错误: 模型加载失败: {e}")
        import traceback
        print(traceback.format_exc())
        return None
    
    model.eval()
    print()
    
    # 创建数据集和数据加载器
    print("📦 准备评估数据集...")
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    print(f"✅ 数据集准备完成，批次大小: 32")
    print()
    
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
    exact_match_count = 0
    over_predict_count = 0
    under_predict_count = 0
    
    # 策略模式识别统计（如果启用）
    strategy_pattern_correct = 0
    strategy_pattern_total = 0
    
    with torch.no_grad():
        for batch_idx, batch in enumerate(dataloader):
            # 处理不同格式的批次数据
            if len(batch) == 5:
                # 阶段5：返回5个值（state, action, strategy, pattern, strategy_pattern）
                states, actions, strategy_labels, pattern_types, strategy_pattern_labels = batch
                strategy_labels = strategy_labels.to(device)
                strategy_pattern_labels = strategy_pattern_labels.to(device) if strategy_pattern_labels is not None else None
            elif len(batch) == 4:
                # 返回4个值（state, action, strategy, pattern）
                states, actions, strategy_labels, pattern_types = batch
                strategy_labels = strategy_labels.to(device)
                strategy_pattern_labels = None
            elif len(batch) == 3:
                # 返回3个值（state, action, strategy）
                states, actions, strategy_labels = batch
                strategy_labels = strategy_labels.to(device)
                strategy_pattern_labels = None
            else:
                # 向后兼容：只有state和action
                states, actions = batch[0], batch[1]
                strategy_labels = None
                strategy_pattern_labels = None
            
            states = states.to(device)
            actions = actions.to(device)
            
            # 模型预测（使用基线参数）
            predictions_list = []
            for i in range(len(states)):
                state = states[i:i+1]
                action = model.get_action(state, deterministic=True, 
                                        threshold=threshold, 
                                        scaling_factor=scaling_factor)
                if action.ndim > 1:
                    action = action.flatten()
                predictions_list.append(torch.from_numpy(action).float())
            predictions = torch.stack(predictions_list).to(device)
            
            # 确保维度一致
            if predictions.shape != actions.shape:
                min_dim = min(predictions.shape[1], actions.shape[1])
                predictions = predictions[:, :min_dim]
                actions = actions[:, :min_dim]
            
            # 计算动作预测准确率（完全匹配）
            exact_match = (predictions == actions).all(dim=1)
            correct_action_predictions += exact_match.sum().item()
            total_samples += len(states)
            
            # 计算卡牌级别的准确率
            batch_card_match = (predictions == actions).sum().item()
            card_match += batch_card_match
            total_action_cards += actions.numel()
            
            # 统计预测分布
            for i in range(len(states)):
                true_count = actions[i].sum().item()
                pred_count = predictions[i].sum().item()
                if true_count == pred_count:
                    exact_match_count += 1
                elif pred_count > true_count:
                    over_predict_count += 1
                else:
                    under_predict_count += 1
            
            # 策略分类准确率（如果启用）
            if strategy_labels is not None:
                action_logits, strategy_logits = model(states, return_strategy=True)
                strategy_preds = torch.argmax(strategy_logits, dim=1)
                valid_mask = (strategy_labels < 7)  # 排除unknown（索引7）
                
                if valid_mask.sum() > 0:
                    valid_strategy_labels = strategy_labels[valid_mask]
                    valid_strategy_preds = strategy_preds[valid_mask]
                    
                    # 整体策略分类准确率
                    strategy_correct = (valid_strategy_preds == valid_strategy_labels)
                    correct_strategy_predictions += strategy_correct.sum().item()
                    total_strategy_samples += valid_mask.sum().item()
                    
                    # 策略理解率（动作预测和策略分类都正确）
                    valid_exact_match = exact_match[valid_mask]
                    if valid_exact_match.shape == strategy_correct.shape:
                        both_correct = (valid_exact_match & strategy_correct)
                        strategy_understanding_count += both_correct.sum().item()
            
            # 进度显示
            if (batch_idx + 1) % 10 == 0:
                progress = 100 * (batch_idx + 1) / len(dataloader)
                print(f"   评估进度: {batch_idx+1}/{len(dataloader)} ({progress:.1f}%)")
    
    print()
    print("="*80)
    print("评估结果")
    print("="*80)
    
    # 计算指标
    action_exact_accuracy = correct_action_predictions / total_samples if total_samples > 0 else 0.0
    action_card_accuracy = card_match / total_action_cards if total_action_cards > 0 else 0.0
    strategy_accuracy = correct_strategy_predictions / total_strategy_samples if total_strategy_samples > 0 else 0.0
    strategy_understanding_rate = strategy_understanding_count / total_strategy_samples if total_strategy_samples > 0 else 0.0
    
    print(f"📊 动作预测性能:")
    print(f"   完全匹配准确率: {action_exact_accuracy:.2%} ({correct_action_predictions}/{total_samples})")
    print(f"   卡牌级别准确率: {action_card_accuracy:.2%}")
    print()
    
    if total_strategy_samples > 0:
        print(f"📊 策略分类性能:")
        print(f"   策略分类准确率: {strategy_accuracy:.2%} ({correct_strategy_predictions}/{total_strategy_samples})")
        print(f"   策略理解率: {strategy_understanding_rate:.2%} ({strategy_understanding_count}/{total_strategy_samples})")
        print()
    
    print(f"📊 预测分布:")
    print(f"   完全匹配: {exact_match_count} ({100*exact_match_count/total_samples:.1f}%)")
    print(f"   预测过多: {over_predict_count} ({100*over_predict_count/total_samples:.1f}%)")
    print(f"   预测过少: {under_predict_count} ({100*under_predict_count/total_samples:.1f}%)")
    print()
    
    # 与阶段5目标对比
    print("="*80)
    print("与阶段5目标对比")
    print("="*80)
    
    target_strategy_understanding = 0.70  # 70-80%
    target_pattern_accuracy = 0.75  # >75%
    target_opponent_accuracy = 0.60  # >60%
    
    print(f"策略理解率:")
    print(f"  目标: {target_strategy_understanding:.0%}-80%")
    print(f"  实际: {strategy_understanding_rate:.2%}")
    if strategy_understanding_rate >= target_strategy_understanding:
        print(f"  状态: ✅ 达到目标")
    else:
        diff = target_strategy_understanding - strategy_understanding_rate
        print(f"  状态: ⚠️ 未达到目标（差距: {diff:.2%}）")
    print()
    
    print(f"完全匹配准确率:")
    print(f"  目标: ≥ 阶段4水平（不应下降）")
    print(f"  实际: {action_exact_accuracy:.2%}")
    print()
    
    # 保存评估结果
    result_file = f"training_logs/stage5_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("阶段5模型评估结果\n")
        f.write("="*80 + "\n")
        f.write(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"模型路径: {model_path}\n")
        f.write(f"评估样本数: {total_samples}\n")
        f.write(f"评估参数: 阈值={threshold}, 缩放因子={scaling_factor}\n")
        f.write("\n")
        f.write(f"完全匹配准确率: {action_exact_accuracy:.2%}\n")
        f.write(f"卡牌级别准确率: {action_card_accuracy:.2%}\n")
        if total_strategy_samples > 0:
            f.write(f"策略分类准确率: {strategy_accuracy:.2%}\n")
            f.write(f"策略理解率: {strategy_understanding_rate:.2%}\n")
        f.write(f"\n预测分布:\n")
        f.write(f"  完全匹配: {exact_match_count} ({100*exact_match_count/total_samples:.1f}%)\n")
        f.write(f"  预测过多: {over_predict_count} ({100*over_predict_count/total_samples:.1f}%)\n")
        f.write(f"  预测过少: {under_predict_count} ({100*under_predict_count/total_samples:.1f}%)\n")
    
    print(f"✅ 评估结果已保存到: {result_file}")
    print("="*80)
    
    return {
        'action_exact_accuracy': action_exact_accuracy,
        'action_card_accuracy': action_card_accuracy,
        'strategy_accuracy': strategy_accuracy,
        'strategy_understanding_rate': strategy_understanding_rate,
        'exact_match_count': exact_match_count,
        'over_predict_count': over_predict_count,
        'under_predict_count': under_predict_count,
        'total_samples': total_samples
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="阶段5模型评估")
    parser.add_argument("--model_path", type=str, default="models/bc_model_stage5_final.pth",
                        help="模型文件路径")
    parser.add_argument("--data_dir", type=str, default="game_records",
                        help="数据目录")
    parser.add_argument("--max_samples", type=int, default=1000,
                        help="最大评估样本数")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="预测阈值（基线：0.3）")
    parser.add_argument("--scaling_factor", type=float, default=5.0,
                        help="概率缩放因子（基线：5.0）")
    
    args = parser.parse_args()
    evaluate_stage5_model(args.model_path, args.data_dir, args.max_samples, 
                         args.threshold, args.scaling_factor)

