# -*- coding: utf-8 -*-
"""
基线模型评估脚本
使用基线参数（阈值0.3，缩放因子5.0）和基线数据量（796样本，34个对局）重新评估基线
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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader


def evaluate_baseline(model_path="models/bc_model_v1.pth", data_dir="game_records", 
                     max_samples=796, max_games=34):
    """
    评估基线模型效果
    
    Args:
        model_path: 模型文件路径
        data_dir: 测试数据目录
        max_samples: 最大样本数（基线：796）
        max_games: 最大对局数（基线：34）
    """
    print("="*60)
    print("基线模型重新评估")
    print("="*60)
    print(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"基线参数: 阈值0.3, 缩放因子5.0")
    print(f"基线数据量: {max_samples}样本（{max_games}个对局）")
    print()
    
    # 1. 检查模型文件
    if not os.path.exists(model_path):
        print(f"[ERROR] 模型文件不存在: {model_path}")
        return
    
    model_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
    print(f"[OK] 模型文件: {model_path}")
    print(f"[OK] 模型大小: {model_size:.2f} MB")
    
    # 2. 加载模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[OK] 使用设备: {device}")
    
    try:
        checkpoint = torch.load(model_path, map_location=device)
        
        if isinstance(checkpoint, dict):
            if 'model_state_dict' in checkpoint:
                model_state_dict = checkpoint['model_state_dict']
            elif any(key.startswith('fc') or key.startswith('strategy') for key in checkpoint.keys()):
                model_state_dict = checkpoint
            else:
                model_state_dict = checkpoint
        else:
            model_state_dict = checkpoint
        
        has_strategy_head = 'fc_strategy.weight' in model_state_dict
        
        model = GuandanPolicyNet(
            input_dim=512, 
            hidden_dim=256, 
            output_dim=512,
            enable_strategy_head=has_strategy_head
        ).to(device)
        
        try:
            model.load_state_dict(model_state_dict, strict=True)
        except RuntimeError as e:
            print(f"[WARNING] 严格加载失败，尝试非严格加载: {e}")
            model.load_state_dict(model_state_dict, strict=False)
        
        print("[OK] 模型加载成功")
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        import traceback
        print(traceback.format_exc())
        return
    
    model.eval()
    
    # 3. 加载测试数据并限制数据量
    print("\n[INFO] 加载测试数据...")
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    if len(raw_data) == 0:
        print(f"[ERROR] 没有找到测试数据: {data_dir}")
        return
    
    print(f"[OK] 原始数据: {len(raw_data)} 个样本")
    
    # 限制数据量：按对局分组，最多取max_games个对局
    # 由于无法直接知道每个样本属于哪个对局，我们按顺序取前max_samples个样本
    if len(raw_data) > max_samples:
        print(f"[INFO] 限制数据量: {len(raw_data)} -> {max_samples} 个样本")
        raw_data = raw_data[:max_samples]
    
    print(f"[OK] 使用数据: {len(raw_data)} 个样本")
    
    # 4. 评估指标
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    total_samples = 0
    correct_predictions = 0
    total_cards = 0
    predicted_cards = 0
    card_match = 0
    
    # 预测分布统计
    exact_match_count = 0
    over_predict_count = 0
    under_predict_count = 0
    
    # 基线评估参数
    prediction_threshold = 0.3  # 基线阈值
    scaling_factor = 5.0  # 基线缩放因子
    
    print(f"\n[INFO] 开始评估（阈值={prediction_threshold}, 缩放因子={scaling_factor}）...")
    
    with torch.no_grad():
        for batch in dataloader:
            if len(batch) == 3:
                states, actions, _ = batch
            elif len(batch) == 4:
                states, actions, _, _ = batch
            else:
                states, actions = batch[0], batch[1]
            states = states.to(device)
            actions = actions.to(device)
            
            # 模型预测（使用基线参数）
            predictions_list = []
            for i in range(len(states)):
                state = states[i:i+1]
                action = model.get_action(state, deterministic=True, 
                                        threshold=prediction_threshold, 
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
            
            # 计算准确率（完全匹配）
            exact_match = (predictions == actions).all(dim=1)
            correct_predictions += exact_match.sum().item()
            total_samples += len(states)
            
            # 计算卡牌级别的准确率
            batch_card_match = (predictions == actions).sum().item()
            card_match += batch_card_match
            total_cards += actions.numel()
            predicted_cards += predictions.sum().item()
            
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
    
    # 5. 输出结果
    print("\n" + "="*60)
    print("基线评估结果")
    print("="*60)
    
    exact_accuracy = correct_predictions / total_samples if total_samples > 0 else 0
    card_accuracy = card_match / total_cards if total_cards > 0 else 0
    avg_pred_cards = predicted_cards / total_samples if total_samples > 0 else 0
    
    print(f"评估参数: 阈值={prediction_threshold}, 缩放因子={scaling_factor}")
    print(f"数据量: {total_samples} 个样本")
    print()
    print(f"完全匹配样本数: {correct_predictions}")
    print(f"完全匹配准确率: {exact_accuracy:.4%} ({exact_accuracy*100:.2f}%)")
    print()
    print(f"卡牌级别准确率: {card_accuracy:.4%} ({card_accuracy*100:.2f}%)")
    print()
    print(f"平均预测卡牌数: {avg_pred_cards:.2f} 张")
    print()
    
    # 预测分布
    print("预测分布:")
    print(f"  完全匹配: {exact_match_count} ({exact_match_count/total_samples*100:.1f}%)")
    print(f"  预测过多: {over_predict_count} ({over_predict_count/total_samples*100:.1f}%)")
    print(f"  预测过少: {under_predict_count} ({under_predict_count/total_samples*100:.1f}%)")
    
    # 6. 与基线对比
    print("\n" + "="*60)
    print("与基线对比")
    print("="*60)
    
    baseline_exact = 0.3731  # 37.31%
    baseline_card = 0.9673   # 96.73%
    baseline_avg_cards = 15.99
    
    print(f"完全匹配准确率:")
    print(f"  基线: {baseline_exact:.4%} ({baseline_exact*100:.2f}%)")
    print(f"  当前: {exact_accuracy:.4%} ({exact_accuracy*100:.2f}%)")
    diff_exact = exact_accuracy - baseline_exact
    print(f"  差异: {diff_exact:+.4%} ({diff_exact*100:+.2f}%)")
    
    print(f"\n卡牌级别准确率:")
    print(f"  基线: {baseline_card:.4%} ({baseline_card*100:.2f}%)")
    print(f"  当前: {card_accuracy:.4%} ({card_accuracy*100:.2f}%)")
    diff_card = card_accuracy - baseline_card
    print(f"  差异: {diff_card:+.4%} ({diff_card*100:+.2f}%)")
    
    print(f"\n平均预测卡牌数:")
    print(f"  基线: {baseline_avg_cards:.2f} 张")
    print(f"  当前: {avg_pred_cards:.2f} 张")
    diff_cards = avg_pred_cards - baseline_avg_cards
    print(f"  差异: {diff_cards:+.2f} 张")
    
    # 7. 结论
    print("\n" + "="*60)
    print("评估结论")
    print("="*60)
    
    if abs(diff_exact) < 0.01:  # 差异小于1%
        print("[OK] 完全匹配准确率与基线基本一致")
    elif diff_exact > 0:
        print(f"[INFO] 完全匹配准确率比基线提升了 {diff_exact*100:.2f}%")
    else:
        print(f"[WARNING] 完全匹配准确率比基线下降了 {abs(diff_exact)*100:.2f}%")
    
    if abs(diff_card) < 0.01:  # 差异小于1%
        print("[OK] 卡牌级别准确率与基线基本一致")
    elif diff_card > 0:
        print(f"[INFO] 卡牌级别准确率比基线提升了 {diff_card*100:.2f}%")
    else:
        print(f"[WARNING] 卡牌级别准确率比基线下降了 {abs(diff_card)*100:.2f}%")
    
    print("\n" + "="*60)
    
    return {
        'exact_accuracy': exact_accuracy,
        'card_accuracy': card_accuracy,
        'avg_pred_cards': avg_pred_cards,
        'exact_match_count': exact_match_count,
        'over_predict_count': over_predict_count,
        'under_predict_count': under_predict_count,
        'total_samples': total_samples
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="重新评估基线模型")
    parser.add_argument("--model", default="models/bc_model_v1.pth", help="模型文件路径")
    parser.add_argument("--data", default="game_records", help="测试数据目录")
    parser.add_argument("--max-samples", type=int, default=796, help="最大样本数（基线：796）")
    parser.add_argument("--max-games", type=int, default=34, help="最大对局数（基线：34）")
    args = parser.parse_args()
    
    evaluate_baseline(args.model, args.data, args.max_samples, args.max_games)

