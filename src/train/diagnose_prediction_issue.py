# -*- coding: utf-8 -*-
"""
诊断预测问题：详细分析为什么完全匹配准确率为0.00%
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
    print("诊断预测问题")
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
    dataloader = DataLoader(dataset, batch_size=1, shuffle=False)
    
    print("分析前10个样本的详细情况:")
    print()
    
    sample_count = 0
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
                
                # 使用阈值预测
                threshold = 0.3
                predictions = (scaled_probs > threshold).float()
                
                # 使用Top-K预测
                true_count = int(actions[0].sum().item())
                k = max(1, true_count) if true_count > 0 else 1
                topk_values, topk_indices = torch.topk(scaled_probs, k, dim=1)
                predictions_topk = torch.zeros_like(scaled_probs)
                predictions_topk.scatter_(1, topk_indices, 1.0)
                
                true_indices = torch.nonzero(actions[0] > 0.5, as_tuple=False).squeeze().tolist()
                pred_indices_threshold = torch.nonzero(predictions[0] > 0.5, as_tuple=False).squeeze().tolist()
                pred_indices_topk = torch.nonzero(predictions_topk[0] > 0.5, as_tuple=False).squeeze().tolist()
                
                if not isinstance(true_indices, list):
                    true_indices = [true_indices] if true_indices is not None else []
                if not isinstance(pred_indices_threshold, list):
                    pred_indices_threshold = [pred_indices_threshold] if pred_indices_threshold is not None else []
                if not isinstance(pred_indices_topk, list):
                    pred_indices_topk = [pred_indices_topk] if pred_indices_topk is not None else []
                
                sample_count += 1
                
                print(f"样本 {sample_count}:")
                print(f"  真实卡牌数: {len(true_indices)}, 卡牌索引: {true_indices[:10]}{'...' if len(true_indices) > 10 else ''}")
                print(f"  阈值预测数: {len(pred_indices_threshold)}, 卡牌索引: {pred_indices_threshold[:10]}{'...' if len(pred_indices_threshold) > 10 else ''}")
                print(f"  Top-K预测数: {len(pred_indices_topk)}, 卡牌索引: {pred_indices_topk[:10]}{'...' if len(pred_indices_topk) > 10 else ''}")
                
                # 检查匹配情况
                true_set = set(true_indices)
                pred_set_threshold = set(pred_indices_threshold)
                pred_set_topk = set(pred_indices_topk)
                
                match_threshold = len(true_set & pred_set_threshold)
                match_topk = len(true_set & pred_set_topk)
                
                print(f"  阈值预测匹配: {match_threshold}/{len(true_indices)} 张卡牌")
                print(f"  Top-K预测匹配: {match_topk}/{len(true_indices)} 张卡牌")
                
                # 显示概率最高的卡牌
                top_probs, top_indices = torch.topk(scaled_probs[0], min(10, len(scaled_probs[0])), dim=0)
                print(f"  概率最高的10张卡牌: {top_indices.cpu().tolist()}")
                print(f"  对应概率: {top_probs.cpu().tolist()}")
                print()
                
                if sample_count >= 10:
                    break
    
    print("="*60)
    print("诊断完成")
    print("="*60)

