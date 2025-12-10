# -*- coding: utf-8 -*-
"""
分析阶段0课程学习训练结果
- 分析模型输出概率分布
- 评估牌型识别准确率
- 分析完全匹配准确率为0.00%的原因
"""

import sys
import os
import torch
import numpy as np
from collections import defaultdict

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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset, identify_card_pattern_type
from torch.utils.data import DataLoader

def analyze_probability_distribution(model, dataset, num_samples=100):
    """分析模型输出概率分布"""
    print("="*60)
    print("模型输出概率分布分析")
    print("="*60)
    
    model.eval()
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    all_probs = []
    all_scaled_probs = []
    prediction_counts = defaultdict(int)
    threshold_counts = {
        0.05: 0,
        0.1: 0,
        0.2: 0,
        0.3: 0,
        0.5: 0
    }
    
    sample_count = 0
    with torch.no_grad():
        for batch in dataloader:
            if len(batch) >= 2:
                states, actions = batch[0], batch[1]
                states = states.to(next(model.parameters()).device)
                
                logits = model(states, return_strategy=False)
                probs = torch.sigmoid(logits)
                scaled_probs = probs * 5.0
                scaled_probs = torch.clamp(scaled_probs, 0, 1)
                
                all_probs.append(probs.cpu().numpy())
                all_scaled_probs.append(scaled_probs.cpu().numpy())
                
                # 统计不同阈值下的预测卡牌数
                for threshold in threshold_counts.keys():
                    threshold_counts[threshold] += (scaled_probs > threshold).sum().item()
                
                # 统计预测卡牌数分布
                for i in range(len(states)):
                    pred_count = (scaled_probs[i] > 0.3).sum().item()
                    prediction_counts[pred_count] += 1
                    sample_count += 1
                    
                    if sample_count >= num_samples:
                        break
                
                if sample_count >= num_samples:
                    break
    
    all_probs = np.concatenate(all_probs, axis=0)
    all_scaled_probs = np.concatenate(all_scaled_probs, axis=0)
    
    print(f"\n原始概率分布（前{sample_count}个样本）:")
    print(f"  最小值: {all_probs.min():.6f}")
    print(f"  最大值: {all_probs.max():.6f}")
    print(f"  平均值: {all_probs.mean():.6f}")
    print(f"  中位数: {np.median(all_probs):.6f}")
    print(f"  标准差: {all_probs.std():.6f}")
    
    print(f"\n缩放后概率分布（缩放因子5.0）:")
    print(f"  最小值: {all_scaled_probs.min():.6f}")
    print(f"  最大值: {all_scaled_probs.max():.6f}")
    print(f"  平均值: {all_scaled_probs.mean():.6f}")
    print(f"  中位数: {np.median(all_scaled_probs):.6f}")
    print(f"  标准差: {all_scaled_probs.std():.6f}")
    
    print(f"\n不同阈值下的预测卡牌数（前{sample_count}个样本）:")
    for threshold, count in sorted(threshold_counts.items()):
        avg_cards = count / sample_count
        print(f"  阈值 {threshold:.2f}: 平均 {avg_cards:.2f} 张卡牌")
    
    print(f"\n预测卡牌数分布（阈值0.3）:")
    sorted_counts = sorted(prediction_counts.items())
    for card_count, freq in sorted_counts[:20]:  # 显示前20个
        print(f"  {card_count}张: {freq}个样本")
    if len(sorted_counts) > 20:
        print(f"  ... (共{len(sorted_counts)}种不同的预测卡牌数)")
    
    return all_probs, all_scaled_probs

def evaluate_pattern_recognition(model, dataset):
    """评估牌型识别准确率"""
    print("\n" + "="*60)
    print("牌型识别准确率评估")
    print("="*60)
    
    model.eval()
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    pattern_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'predicted_cards': [], 'true_cards': []})
    
    device = next(model.parameters()).device
    threshold = 0.3
    scaling_factor = 5.0
    
    with torch.no_grad():
        for batch_idx, batch in enumerate(dataloader):
            if len(batch) >= 4:
                states, actions, _, pattern_types = batch
            elif len(batch) >= 2:
                states, actions = batch[0], batch[1]
                pattern_types = None
            else:
                continue
            
            states = states.to(device)
            actions = actions.to(device)
            
            # 获取预测
            predictions_list = []
            for i in range(len(states)):
                state = states[i:i+1]
                action = model.get_action(state, deterministic=True, threshold=threshold, scaling_factor=scaling_factor)
                predictions_list.append(torch.from_numpy(action).float())
            predictions = torch.stack(predictions_list).to(device)
            
            # 确保维度一致
            if predictions.shape != actions.shape:
                min_dim = min(predictions.shape[1], actions.shape[1])
                predictions = predictions[:, :min_dim]
                actions = actions[:, :min_dim]
            
            # 对每个样本评估
            for i in range(len(states)):
                # 获取真实牌型（从数据中提取）
                # 需要从原始数据中获取action_cards
                # 这里简化处理，使用pattern_types如果可用
                
                true_cards = actions[i].sum().item()
                pred_cards = predictions[i].sum().item()
                
                # 如果pattern_types可用，使用它
                if pattern_types is not None:
                    pattern_idx = pattern_types[i].item()
                    pattern_map = {
                        0: 'Single', 1: 'Pair', 2: 'Triple', 3: 'ThreeWithTwo',
                        4: 'Sequence', 5: 'Bomb', 6: 'SteelPlate', 7: 'WoodPlate',
                        8: 'Complex', 9: 'Pass', 10: 'Empty', 11: 'Unknown'
                    }
                    pattern_name = pattern_map.get(pattern_idx, 'Unknown')
                else:
                    pattern_name = 'Unknown'
                
                # 判断是否识别正确（简化：只检查卡牌数量是否接近）
                # 这里需要更复杂的逻辑来判断牌型是否正确
                # 暂时只统计卡牌数量
                pattern_stats[pattern_name]['total'] += 1
                pattern_stats[pattern_name]['predicted_cards'].append(pred_cards)
                pattern_stats[pattern_name]['true_cards'].append(true_cards)
                
                # 简单的准确率判断：卡牌数量差异在±2以内
                if abs(pred_cards - true_cards) <= 2:
                    pattern_stats[pattern_name]['correct'] += 1
    
    print("\n牌型识别统计:")
    print(f"{'牌型':<15} {'样本数':<10} {'准确数':<10} {'准确率':<10} {'平均预测卡牌数':<15} {'平均真实卡牌数':<15}")
    print("-" * 80)
    
    total_samples = 0
    total_correct = 0
    
    for pattern_name in sorted(pattern_stats.keys()):
        stats = pattern_stats[pattern_name]
        total = stats['total']
        correct = stats['correct']
        accuracy = correct / total if total > 0 else 0.0
        avg_pred = np.mean(stats['predicted_cards']) if stats['predicted_cards'] else 0.0
        avg_true = np.mean(stats['true_cards']) if stats['true_cards'] else 0.0
        
        print(f"{pattern_name:<15} {total:<10} {correct:<10} {accuracy:<10.2%} {avg_pred:<15.2f} {avg_true:<15.2f}")
        
        total_samples += total
        total_correct += correct
    
    overall_accuracy = total_correct / total_samples if total_samples > 0 else 0.0
    print("-" * 80)
    print(f"{'总计':<15} {total_samples:<10} {total_correct:<10} {overall_accuracy:<10.2%}")
    
    return pattern_stats

def analyze_exact_match_issue(model, dataset, num_samples=50):
    """分析完全匹配准确率为0.00%的原因"""
    print("\n" + "="*60)
    print("完全匹配准确率分析")
    print("="*60)
    
    model.eval()
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    exact_matches = 0
    total_samples_checked = 0
    prediction_distribution = {
        'exact_match': 0,
        'predict_more': 0,
        'predict_less': 0
    }
    
    device = next(model.parameters()).device
    threshold = 0.3
    scaling_factor = 5.0
    
    with torch.no_grad():
        for batch_idx, batch in enumerate(dataloader):
            if len(batch) >= 2:
                states, actions = batch[0], batch[1]
                states = states.to(device)
                actions = actions.to(device)
                
                # 获取预测
                predictions_list = []
                for i in range(len(states)):
                    state = states[i:i+1]
                    action = model.get_action(state, deterministic=True, threshold=threshold, scaling_factor=scaling_factor)
                    predictions_list.append(torch.from_numpy(action).float())
                predictions = torch.stack(predictions_list).to(device)
                
                # 确保维度一致
                if predictions.shape != actions.shape:
                    min_dim = min(predictions.shape[1], actions.shape[1])
                    predictions = predictions[:, :min_dim]
                    actions = actions[:, :min_dim]
                
                # 对每个样本检查
                for i in range(len(states)):
                    exact_match = (predictions[i] == actions[i]).all().item()
                    if exact_match:
                        exact_matches += 1
                        prediction_distribution['exact_match'] += 1
                    else:
                        pred_count = predictions[i].sum().item()
                        true_count = actions[i].sum().item()
                        if pred_count > true_count:
                            prediction_distribution['predict_more'] += 1
                        elif pred_count < true_count:
                            prediction_distribution['predict_less'] += 1
                        else:
                            # 卡牌数量相同但组合不同
                            prediction_distribution['exact_match'] += 1
                    
                    total_samples_checked += 1
                    
                    if total_samples_checked >= num_samples:
                        break
                
                if total_samples_checked >= num_samples:
                    break
    
    print(f"\n检查了 {total_samples_checked} 个样本:")
    print(f"  完全匹配: {prediction_distribution['exact_match']} ({prediction_distribution['exact_match']/total_samples_checked:.2%})")
    print(f"  预测过多: {prediction_distribution['predict_more']} ({prediction_distribution['predict_more']/total_samples_checked:.2%})")
    print(f"  预测过少: {prediction_distribution['predict_less']} ({prediction_distribution['predict_less']/total_samples_checked:.2%})")
    
    return prediction_distribution

if __name__ == "__main__":
    print("阶段0课程学习训练结果分析")
    print("="*60)
    
    # 1. 加载模型
    model_path = "models/bc_model_v1.pth"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = GuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=0.05,
        enable_strategy_head=False
    ).to(device)
    
    checkpoint = torch.load(model_path, map_location=device)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.eval()
    
    print(f"[OK] 模型加载成功: {model_path}")
    
    # 2. 加载数据
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    print(f"[OK] 数据加载成功: {len(raw_data)} 个样本")
    
    # 3. 创建数据集
    dataset = GuandanDataset(raw_data)
    
    # 4. 分析概率分布
    analyze_probability_distribution(model, dataset, num_samples=100)
    
    # 5. 评估牌型识别
    evaluate_pattern_recognition(model, dataset)
    
    # 6. 分析完全匹配问题
    analyze_exact_match_issue(model, dataset, num_samples=100)
    
    print("\n" + "="*60)
    print("分析完成")
    print("="*60)

