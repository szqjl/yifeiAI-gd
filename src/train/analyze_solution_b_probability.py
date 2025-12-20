# -*- coding: utf-8 -*-
"""
分析方案B训练后的模型输出概率分布
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

if __name__ == "__main__":
    print("="*60)
    print("分析方案B训练后的模型输出概率分布")
    print("="*60)
    print()
    
    # 加载模型
    model_path = "models/bc_model_v1_epoch_120.pth"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
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
    
    all_probs = []
    all_scaled_probs = []
    true_card_counts = []
    
    sample_count = 0
    max_samples = 100
    
    with torch.no_grad():
        for batch in dataloader:
            if len(batch) >= 2:
                states, actions = batch[0], batch[1]
                states = states.to(device)
                actions = actions.to(device)
                
                logits = model(states, return_strategy=False)
                probs = torch.sigmoid(logits)
                scaled_probs = probs * 5.0
                scaled_probs = torch.clamp(scaled_probs, 0, 1)
                
                all_probs.append(probs.cpu().numpy())
                all_scaled_probs.append(scaled_probs.cpu().numpy())
                
                for i in range(len(states)):
                    true_count = actions[i].sum().item()
                    true_card_counts.append(true_count)
                    sample_count += 1
                    
                    if sample_count >= max_samples:
                        break
                
                if sample_count >= max_samples:
                    break
    
    all_probs = np.concatenate(all_probs, axis=0)
    all_scaled_probs = np.concatenate(all_scaled_probs, axis=0)
    
    print(f"分析前 {sample_count} 个样本:")
    print()
    print("原始概率分布:")
    print(f"  最小值: {all_probs.min():.6f}")
    print(f"  最大值: {all_probs.max():.6f}")
    print(f"  平均值: {all_probs.mean():.6f}")
    print(f"  中位数: {np.median(all_probs):.6f}")
    print(f"  标准差: {all_probs.std():.6f}")
    print()
    
    print("缩放后概率分布（缩放因子5.0）:")
    print(f"  最小值: {all_scaled_probs.min():.6f}")
    print(f"  最大值: {all_scaled_probs.max():.6f}")
    print(f"  平均值: {all_scaled_probs.mean():.6f}")
    print(f"  中位数: {np.median(all_scaled_probs):.6f}")
    print(f"  标准差: {all_scaled_probs.std():.6f}")
    print()
    
    # 统计不同阈值下的预测卡牌数
    print("不同阈值下的预测卡牌数统计:")
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    for threshold in thresholds:
        pred_counts = []
        for i in range(sample_count):
            pred_count = (all_scaled_probs[i] > threshold).sum()
            pred_counts.append(pred_count)
        avg_pred = np.mean(pred_counts)
        print(f"  阈值 {threshold:.1f}: 平均 {avg_pred:.2f} 张卡牌")
    print()
    
    # 真实卡牌数统计
    print("真实卡牌数统计:")
    print(f"  最小值: {min(true_card_counts)}")
    print(f"  最大值: {max(true_card_counts)}")
    print(f"  平均值: {np.mean(true_card_counts):.2f}")
    print(f"  中位数: {np.median(true_card_counts):.2f}")
    print()
    
    # 分析问题
    print("="*60)
    print("问题分析")
    print("="*60)
    
    # 计算阈值0.3时的平均预测卡牌数
    threshold_03_pred_counts = [(all_scaled_probs[i] > 0.3).sum() for i in range(sample_count)]
    avg_pred_03 = np.mean(threshold_03_pred_counts)
    avg_true = np.mean(true_card_counts)
    
    print(f"阈值0.3时:")
    print(f"  平均预测卡牌数: {avg_pred_03:.2f} 张")
    print(f"  平均真实卡牌数: {avg_true:.2f} 张")
    print(f"  差异: {avg_pred_03 - avg_true:.2f} 张（预测过多 {((avg_pred_03 - avg_true) / avg_true * 100):.1f}%）")
    print()
    
    if avg_pred_03 > avg_true * 2:
        print("⚠️ 问题：预测卡牌数过多，是真实卡牌数的2倍以上")
        print("可能原因：")
        print("1. 模型输出概率分布过于分散，很多卡牌都有较高的概率")
        print("2. 缩放因子5.0可能过大，导致过多卡牌超过阈值")
        print("3. 模型可能没有学会精确预测，而是倾向于预测更多卡牌")
        print()
        print("建议解决方案：")
        print("1. 进一步降低缩放因子（5.0 → 2.0或1.5）")
        print("2. 提高预测阈值（0.3 → 0.6或0.7）")
        print("3. 考虑使用Top-K策略：只选择概率最高的K张卡牌（K=真实卡牌数）")
        print("4. 改进损失函数：增加对预测过多的惩罚")

