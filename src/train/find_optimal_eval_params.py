# -*- coding: utf-8 -*-
"""
快速测试关键评估参数组合，找到达到70%完全匹配准确率的最优参数
"""

import sys
import os
import torch
import numpy as np

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
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader

def evaluate_with_params(model, dataset, threshold, scaling_factor, max_samples=500):
    """使用指定参数评估模型"""
    model.eval()
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    device = next(model.parameters()).device
    
    total_samples = 0
    correct_predictions = 0
    total_cards = 0
    card_match = 0
    predicted_cards = 0
    
    prediction_distribution = {
        'exact_match': 0,
        'predict_more': 0,
        'predict_less': 0
    }
    
    with torch.no_grad():
        for batch in dataloader:
            if len(batch) >= 2:
                states, actions = batch[0], batch[1]
                states = states.to(device)
                actions = actions.to(device)
                
                predictions_list = []
                for i in range(len(states)):
                    state = states[i:i+1]
                    action = model.get_action(state, deterministic=True, threshold=threshold, scaling_factor=scaling_factor)
                    predictions_list.append(torch.from_numpy(action).float())
                predictions = torch.stack(predictions_list).to(device)
                
                if predictions.shape != actions.shape:
                    min_dim = min(predictions.shape[1], actions.shape[1])
                    predictions = predictions[:, :min_dim]
                    actions = actions[:, :min_dim]
                
                for i in range(len(states)):
                    exact_match = (predictions[i] == actions[i]).all().item()
                    if exact_match:
                        correct_predictions += 1
                        prediction_distribution['exact_match'] += 1
                    else:
                        pred_count = predictions[i].sum().item()
                        true_count = actions[i].sum().item()
                        if pred_count > true_count:
                            prediction_distribution['predict_more'] += 1
                        elif pred_count < true_count:
                            prediction_distribution['predict_less'] += 1
                    
                    batch_card_match = (predictions[i] == actions[i]).sum().item()
                    card_match += batch_card_match
                    total_cards += actions[i].numel()
                    predicted_cards += predictions[i].sum().item()
                    
                    total_samples += 1
                    if total_samples >= max_samples:
                        break
                
                if total_samples >= max_samples:
                    break
    
    exact_accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0
    card_accuracy = card_match / total_cards if total_cards > 0 else 0.0
    avg_predicted_cards = predicted_cards / total_samples if total_samples > 0 else 0.0
    
    return {
        'exact_accuracy': exact_accuracy,
        'card_accuracy': card_accuracy,
        'avg_predicted_cards': avg_predicted_cards,
        'prediction_distribution': prediction_distribution
    }

if __name__ == "__main__":
    print("测试评估参数以解决完全匹配准确率为0.00%的问题")
    print("目标：达到70%完全匹配准确率")
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
    
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.eval()
    
    print(f"[OK] 模型加载成功")
    
    # 2. 加载数据
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    dataset = GuandanDataset(raw_data)
    
    print(f"[OK] 数据加载成功: {len(raw_data)} 个样本")
    print()
    
    # 3. 测试关键参数组合（按文档建议）
    print("测试关键参数组合:")
    print(f"{'阈值':<8} {'缩放因子':<10} {'完全匹配':<12} {'卡牌级别':<12} {'平均预测卡牌数':<15} {'预测分布':<30}")
    print("-" * 100)
    
    # 方案A：提高阈值，降低缩放因子
    test_params = [
        (0.5, 3.0),  # 方案A建议1
        (0.5, 2.0),  # 方案A建议2
        (0.6, 3.0),  # 方案A建议3
        (0.6, 2.0),  # 方案A建议4
        (0.7, 2.0),  # 更激进
        (0.8, 2.0),  # 最激进
    ]
    
    results = []
    for threshold, scaling_factor in test_params:
        result = evaluate_with_params(model, dataset, threshold, scaling_factor, max_samples=500)
        dist = result['prediction_distribution']
        dist_str = f"匹配:{dist['exact_match']}, 过多:{dist['predict_more']}, 过少:{dist['predict_less']}"
        
        print(f"{threshold:<8.1f} {scaling_factor:<10.1f} {result['exact_accuracy']:<12.2%} "
              f"{result['card_accuracy']:<12.2%} {result['avg_predicted_cards']:<15.2f} {dist_str:<30}")
        
        results.append({
            'threshold': threshold,
            'scaling_factor': scaling_factor,
            **result
        })
    
    print("-" * 100)
    print()
    
    # 找到达到目标的参数
    target_accuracy = 0.70
    achieving_target = [r for r in results if r['exact_accuracy'] >= target_accuracy]
    
    if achieving_target:
        print("="*60)
        print(f"✅ 找到达到目标准确率（≥{target_accuracy:.0%}）的参数组合:")
        print("="*60)
        achieving_target.sort(key=lambda x: x['exact_accuracy'], reverse=True)
        best = achieving_target[0]
        print(f"最优参数: 阈值={best['threshold']:.1f}, 缩放因子={best['scaling_factor']:.1f}")
        print(f"完全匹配准确率: {best['exact_accuracy']:.2%}")
        print(f"卡牌级别准确率: {best['card_accuracy']:.2%}")
        print(f"平均预测卡牌数: {best['avg_predicted_cards']:.2f}")
        dist = best['prediction_distribution']
        print(f"预测分布: 完全匹配 {dist['exact_match']}, 预测过多 {dist['predict_more']}, 预测过少 {dist['predict_less']}")
    else:
        print("="*60)
        print(f"⚠️ 当前参数组合未达到目标准确率（≥{target_accuracy:.0%}）")
        print("="*60)
        best = max(results, key=lambda x: x['exact_accuracy'])
        print(f"当前最佳参数: 阈值={best['threshold']:.1f}, 缩放因子={best['scaling_factor']:.1f}")
        print(f"完全匹配准确率: {best['exact_accuracy']:.2%} (目标: {target_accuracy:.0%})")
        print()
        print("建议：")
        print("1. 尝试更高的阈值（0.8-0.9）")
        print("2. 尝试更低的缩放因子（1.0-1.5）")
        print("3. 考虑改进训练（方案B）：降低Dropout到0.01，增加pos_weight到8.0")

