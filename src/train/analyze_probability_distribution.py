# -*- coding: utf-8 -*-
"""
分析模型输出概率分布，确定最优缩放因子
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


def analyze_probability_distribution(model_path="models/bc_model_v1.pth", data_dir="game_records"):
    """分析概率分布，确定最优缩放因子"""
    
    print("="*60)
    print("概率分布分析")
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
    
    # 收集概率值
    all_probs = []
    all_true_counts = []
    
    with torch.no_grad():
        for states, actions in dataloader:
            states = states.to(device)
            actions = actions.to(device)
            
            logits = model(states)
            probs = torch.sigmoid(logits)
            all_probs.append(probs.cpu())
            
            # 统计真实卡牌数
            true_counts = actions.sum(dim=1).cpu().numpy()
            all_true_counts.extend(true_counts.tolist())
    
    all_probs = torch.cat(all_probs, dim=0)
    
    # 分析原始概率
    print("\n原始概率分析（未缩放）:")
    print(f"  平均概率: {all_probs.mean().item():.6f}")
    print(f"  中位数概率: {all_probs.median().item():.6f}")
    print(f"  最大概率: {all_probs.max().item():.6f}")
    print(f"  最小概率: {all_probs.min().item():.6f}")
    print(f"  标准差: {all_probs.std().item():.6f}")
    
    # 分析不同阈值下的预测
    print("\n不同阈值下的预测卡牌数（未缩放）:")
    for threshold in [0.1, 0.2, 0.3, 0.4, 0.5]:
        pred_counts = (all_probs > threshold).sum(dim=1).float().mean().item()
        print(f"  阈值 {threshold}: 平均 {pred_counts:.2f} 张")
    
    # 分析不同缩放因子
    print("\n不同缩放因子下的预测卡牌数（阈值0.3）:")
    true_avg = np.mean(all_true_counts)
    print(f"  真实平均卡牌数: {true_avg:.2f} 张")
    
    best_scale = None
    best_diff = float('inf')
    
    for scale in [10, 20, 30, 40, 50, 60, 70, 80, 100]:
        probs_scaled = all_probs * scale
        probs_clamped = torch.clamp(probs_scaled, 0, 1)
        pred_counts = (probs_clamped > 0.3).sum(dim=1).float().mean().item()
        diff = abs(pred_counts - true_avg)
        
        print(f"  缩放因子 {scale:3d}: 平均 {pred_counts:6.2f} 张 (差异: {diff:6.2f})")
        
        if diff < best_diff:
            best_diff = diff
            best_scale = scale
    
    print(f"\n最优缩放因子: {best_scale} (差异最小: {best_diff:.2f})")
    
    # 分析最优缩放因子下的准确率
    if best_scale:
        print(f"\n使用缩放因子 {best_scale} 的详细分析:")
        probs_scaled = all_probs * best_scale
        probs_clamped = torch.clamp(probs_scaled, 0, 1)
        
        # 计算准确率
        correct = 0
        total = 0
        for i, (state, action) in enumerate(dataloader):
            state = state.to(device)
            action = action.to(device)
            
            logits = model(state)
            probs = torch.sigmoid(logits)
            probs_scaled = probs * best_scale
            probs_clamped = torch.clamp(probs_scaled, 0, 1)
            predictions = (probs_clamped > 0.3).float()
            
            exact_match = (predictions == action).all(dim=1)
            correct += exact_match.sum().item()
            total += len(state)
        
        accuracy = correct / total if total > 0 else 0
        print(f"  完全匹配准确率: {accuracy:.2%}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="分析概率分布")
    parser.add_argument("--model", default="models/bc_model_v1.pth", help="模型文件路径")
    parser.add_argument("--data", default="game_records", help="测试数据目录")
    args = parser.parse_args()
    
    analyze_probability_distribution(args.model, args.data)

