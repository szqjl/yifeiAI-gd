# -*- coding: utf-8 -*-
"""
评估方案B训练效果
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

def evaluate_model(model_path, threshold=0.3, scaling_factor=5.0, max_samples=1000):
    """评估模型"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 加载模型
    model = GuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=0.01,
        enable_strategy_head=False
    ).to(device)
    
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.eval()
    
    # 加载数据
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
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
        'prediction_distribution': prediction_distribution,
        'total_samples': total_samples
    }

if __name__ == "__main__":
    print("="*60)
    print("方案B训练效果评估")
    print("="*60)
    print()
    
    # 评估最新模型（epoch 120）
    model_path = "models/bc_model_v1_epoch_120.pth"
    if not os.path.exists(model_path):
        print(f"[ERROR] 模型文件不存在: {model_path}")
        print("尝试使用最终模型...")
        model_path = "models/bc_model_v1.pth"
    
    print(f"评估模型: {model_path}")
    print()
    
    # 使用基线参数评估
    print("使用基线参数评估（阈值0.3，缩放因子5.0）:")
    result_baseline = evaluate_model(model_path, threshold=0.3, scaling_factor=5.0, max_samples=1000)
    print(f"  完全匹配准确率: {result_baseline['exact_accuracy']:.2%}")
    print(f"  卡牌级别准确率: {result_baseline['card_accuracy']:.2%}")
    print(f"  平均预测卡牌数: {result_baseline['avg_predicted_cards']:.2f}")
    dist = result_baseline['prediction_distribution']
    print(f"  预测分布: 完全匹配 {dist['exact_match']}, 预测过多 {dist['predict_more']}, 预测过少 {dist['predict_less']}")
    print()
    
    # 测试不同参数组合
    print("测试不同参数组合以寻找最优参数:")
    print(f"{'阈值':<8} {'缩放因子':<10} {'完全匹配':<12} {'卡牌级别':<12} {'平均预测卡牌数':<15}")
    print("-" * 60)
    
    test_params = [
        (0.5, 3.0),
        (0.6, 2.0),
        (0.7, 2.0),
        (0.8, 2.0),
        (0.9, 2.0),
    ]
    
    best_result = None
    best_accuracy = 0.0
    
    for threshold, scaling_factor in test_params:
        result = evaluate_model(model_path, threshold=threshold, scaling_factor=scaling_factor, max_samples=500)
        print(f"{threshold:<8.1f} {scaling_factor:<10.1f} {result['exact_accuracy']:<12.2%} "
              f"{result['card_accuracy']:<12.2%} {result['avg_predicted_cards']:<15.2f}")
        
        if result['exact_accuracy'] > best_accuracy:
            best_accuracy = result['exact_accuracy']
            best_result = (threshold, scaling_factor, result)
    
    print("-" * 60)
    print()
    
    if best_result:
        threshold, scaling_factor, result = best_result
        print("="*60)
        print("最优参数组合:")
        print("="*60)
        print(f"阈值: {threshold:.1f}")
        print(f"缩放因子: {scaling_factor:.1f}")
        print(f"完全匹配准确率: {result['exact_accuracy']:.2%}")
        print(f"卡牌级别准确率: {result['card_accuracy']:.2%}")
        print(f"平均预测卡牌数: {result['avg_predicted_cards']:.2f}")
        dist = result['prediction_distribution']
        print(f"预测分布: 完全匹配 {dist['exact_match']}, 预测过多 {dist['predict_more']}, 预测过少 {dist['predict_less']}")
        
        if result['exact_accuracy'] >= 0.70:
            print()
            print("✅ 达到目标！完全匹配准确率≥70%")
        else:
            print()
            print(f"⚠️ 未达到目标（70%），当前: {result['exact_accuracy']:.2%}")
            print(f"差距: {0.70 - result['exact_accuracy']:.2%}")

