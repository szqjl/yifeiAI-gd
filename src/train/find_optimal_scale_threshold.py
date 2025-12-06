# -*- coding: utf-8 -*-
"""
自动测试不同缩放因子和阈值组合，找到最优参数
"""

import sys
import os
import torch
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader


def test_scale_threshold_combination(model, dataloader, device, scale, threshold):
    """测试特定的缩放因子和阈值组合"""
    
    total_samples = 0
    correct_predictions = 0
    total_cards = 0
    card_match = 0
    predicted_cards = 0
    true_cards = 0
    
    with torch.no_grad():
        for states, actions in dataloader:
            states = states.to(device)
            actions = actions.to(device)
            
            # 使用指定的缩放因子和阈值
            logits = model(states)
            probs = torch.sigmoid(logits)
            probs_scaled = probs * scale
            probs_clamped = torch.clamp(probs_scaled, 0, 1)
            predictions = (probs_clamped > threshold).float()
            
            # 计算准确率
            exact_match = (predictions == actions).all(dim=1)
            correct_predictions += exact_match.sum().item()
            total_samples += len(states)
            
            # 卡牌级别准确率
            batch_card_match = (predictions == actions).sum().item()
            card_match += batch_card_match
            total_cards += actions.numel()
            predicted_cards += predictions.sum().item()
            true_cards += actions.sum().item()
    
    exact_accuracy = correct_predictions / total_samples if total_samples > 0 else 0
    card_accuracy = card_match / total_cards if total_cards > 0 else 0
    avg_pred_count = predicted_cards / total_samples if total_samples > 0 else 0
    avg_true_count = true_cards / total_samples if total_samples > 0 else 0
    pred_diff = abs(avg_pred_count - avg_true_count)
    
    return {
        'exact_accuracy': exact_accuracy,
        'card_accuracy': card_accuracy,
        'avg_pred_count': avg_pred_count,
        'avg_true_count': avg_true_count,
        'pred_diff': pred_diff
    }


def find_optimal_parameters(model_path="models/bc_model_v1.pth", data_dir="game_records"):
    """找到最优的缩放因子和阈值组合"""
    
    print("="*60)
    print("自动测试最优参数组合")
    print("="*60)
    
    # 加载模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GuandanPolicyNet(input_dim=512, hidden_dim=256, output_dim=512).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # 加载数据
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    if len(raw_data) == 0:
        print("[ERROR] 没有找到测试数据")
        return
    
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    print(f"[OK] 测试数据: {len(raw_data)} 个样本")
    print(f"[OK] 开始测试不同参数组合...\n")
    
    # 测试不同的缩放因子和阈值组合
    scales = [5.0, 7.0, 8.0, 10.0, 12.0, 15.0]
    thresholds = [0.3, 0.4, 0.5]
    
    results = []
    
    for scale in scales:
        for threshold in thresholds:
            print(f"测试: 缩放因子={scale:.1f}, 阈值={threshold:.1f}...", end=" ")
            result = test_scale_threshold_combination(model, dataloader, device, scale, threshold)
            result['scale'] = scale
            result['threshold'] = threshold
            results.append(result)
            
            print(f"准确率={result['exact_accuracy']:.2%}, "
                  f"预测卡牌数={result['avg_pred_count']:.2f}, "
                  f"差异={result['pred_diff']:.2f}")
    
    # 找到最优组合
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    # 按准确率排序
    results_sorted = sorted(results, key=lambda x: x['exact_accuracy'], reverse=True)
    
    print("\n前5名组合（按准确率）:")
    for i, r in enumerate(results_sorted[:5], 1):
        print(f"{i}. 缩放因子={r['scale']:.1f}, 阈值={r['threshold']:.1f}")
        print(f"   完全匹配准确率: {r['exact_accuracy']:.2%}")
        print(f"   卡牌级别准确率: {r['card_accuracy']:.2%}")
        print(f"   平均预测卡牌数: {r['avg_pred_count']:.2f}")
        print(f"   真实平均卡牌数: {r['avg_true_count']:.2f}")
        print(f"   预测差异: {r['pred_diff']:.2f}")
        print()
    
    # 按预测差异排序（预测卡牌数最接近真实值）
    results_diff_sorted = sorted(results, key=lambda x: x['pred_diff'])
    
    print("前5名组合（按预测差异，最接近真实值）:")
    for i, r in enumerate(results_diff_sorted[:5], 1):
        print(f"{i}. 缩放因子={r['scale']:.1f}, 阈值={r['threshold']:.1f}")
        print(f"   完全匹配准确率: {r['exact_accuracy']:.2%}")
        print(f"   平均预测卡牌数: {r['avg_pred_count']:.2f}")
        print(f"   真实平均卡牌数: {r['avg_true_count']:.2f}")
        print(f"   预测差异: {r['pred_diff']:.2f}")
        print()
    
    # 综合评分（准确率权重0.7，差异权重0.3）
    for r in results:
        # 归一化准确率（0-1）
        max_acc = max(res['exact_accuracy'] for res in results)
        norm_acc = r['exact_accuracy'] / max_acc if max_acc > 0 else 0
        
        # 归一化差异（越小越好，所以用1-归一化值）
        max_diff = max(res['pred_diff'] for res in results)
        norm_diff = 1 - (r['pred_diff'] / max_diff if max_diff > 0 else 0)
        
        r['score'] = 0.7 * norm_acc + 0.3 * norm_diff
    
    results_score_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
    
    print("="*60)
    print("最优组合（综合评分）")
    print("="*60)
    
    best = results_score_sorted[0]
    print(f"\n最优参数:")
    print(f"  缩放因子: {best['scale']:.1f}")
    print(f"  阈值: {best['threshold']:.1f}")
    print(f"\n效果:")
    print(f"  完全匹配准确率: {best['exact_accuracy']:.2%}")
    print(f"  卡牌级别准确率: {best['card_accuracy']:.2%}")
    print(f"  平均预测卡牌数: {best['avg_pred_count']:.2f}")
    print(f"  真实平均卡牌数: {best['avg_true_count']:.2f}")
    print(f"  预测差异: {best['pred_diff']:.2f}")
    print(f"  综合评分: {best['score']:.4f}")
    
    print("\n" + "="*60)
    print("应用建议")
    print("="*60)
    print(f"\n修改 src/rl_agent/model.py:")
    print(f"  probs = probs * {best['scale']:.1f}  # 最优缩放因子")
    print(f"  threshold = {best['threshold']:.1f}   # 最优阈值")
    
    return best


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="找到最优的缩放因子和阈值")
    parser.add_argument("--model", default="models/bc_model_v1.pth", help="模型文件路径")
    parser.add_argument("--data", default="game_records", help="测试数据目录")
    args = parser.parse_args()
    
    find_optimal_parameters(args.model, args.data)

