"""
Stage 7.4: 精确匹配优化训练
专注提升有效卡牌匹配率和数量准确性

核心改进：
1. 卡牌位置直接监督
2. 分层预测机制
3. 强化数量约束
4. 位置权重学习
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrecisionGuandanNet(nn.Module):
    """精确匹配网络"""
    
    def __init__(self, input_dim=512, output_dim=512):
        super().__init__()
        
        # 特征提取
        self.features = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # 数量预测头（强化）
        self.count_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # 位置预测头
        self.position_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, output_dim)
        )
        
        # 位置权重学习
        self.position_weights = nn.Parameter(torch.ones(output_dim))
        
    def forward(self, x):
        features = self.features(x)
        
        # 预测数量
        count_raw = self.count_head(features) * 10  # 最多10张
        
        # 预测位置概率
        position_logits = self.position_head(features)
        
        # 应用位置权重
        weighted_logits = position_logits * self.position_weights
        
        return weighted_logits, count_raw


class PrecisionLoss(nn.Module):
    """精确匹配损失"""
    
    def __init__(self):
        super().__init__()
        
    def forward(self, position_logits, count_pred, target_actions):
        batch_size = position_logits.size(0)
        
        # 真实数量
        true_counts = target_actions.sum(dim=1).float()
        
        # 数量损失（强化）
        count_loss = nn.functional.mse_loss(count_pred.squeeze(), true_counts) * 100
        
        # 使用预测数量进行Top-K选择
        position_probs = torch.sigmoid(position_logits)
        
        total_position_loss = 0
        exact_matches = 0
        
        for i in range(batch_size):
            true_action = target_actions[i]
            true_count = int(true_counts[i].item())
            pred_count = max(1, min(int(count_pred[i].item()), position_logits.size(1)))
            
            # Top-K选择
            _, top_k_indices = torch.topk(position_probs[i], pred_count)
            pred_action = torch.zeros_like(true_action)
            pred_action[top_k_indices] = 1.0
            
            # 位置损失
            position_loss = nn.functional.binary_cross_entropy(
                pred_action, true_action, reduction='sum'
            )
            total_position_loss += position_loss
            
            # 精确匹配检查
            if torch.equal(pred_action, true_action):
                exact_matches += 1
        
        avg_position_loss = total_position_loss / batch_size
        exact_match_rate = exact_matches / batch_size
        
        # 精确匹配奖励
        match_bonus = -50 * exact_match_rate
        
        total_loss = count_loss + avg_position_loss + match_bonus
        
        return total_loss, {
            'count_loss': count_loss.item(),
            'position_loss': avg_position_loss.item(),
            'match_bonus': match_bonus,
            'exact_match_rate': exact_match_rate
        }


def train_precision_model(
    epochs: int = 60,
    batch_size: int = 32,
    learning_rate: float = 0.001
):
    """训练精确匹配模型"""
    
    logger.info("Stage 7.4: 精确匹配优化训练")
    
    # 数据加载
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=batch_size,
        max_samples=3000,
        shuffle=True
    )
    
    # 模型和优化器
    model = PrecisionGuandanNet()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=0.01)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)
    criterion = PrecisionLoss()
    
    # 训练循环
    best_match_rate = 0
    patience = 15
    patience_counter = 0
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        total_match_rate = 0
        total_predicted = 0
        total_true = 0
        
        for state_vec, action_vec, _ in dataloader:
            optimizer.zero_grad()
            
            position_logits, count_pred = model(state_vec)
            loss, metrics = criterion(position_logits, count_pred, action_vec)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            total_loss += loss.item()
            total_match_rate += metrics['exact_match_rate']
            
            # 统计预测情况
            for i in range(action_vec.size(0)):
                pred_count = max(1, min(int(count_pred[i].item()), 512))
                true_count = int(action_vec[i].sum().item())
                total_predicted += pred_count
                total_true += true_count
        
        scheduler.step()
        
        avg_loss = total_loss / len(dataloader)
        avg_match_rate = total_match_rate / len(dataloader)
        avg_pred = total_predicted / len(dataloader.dataset)
        avg_true = total_true / len(dataloader.dataset)
        
        logger.info(
            f"Epoch {epoch+1:2d}/{epochs} | "
            f"Loss: {avg_loss:.3f} | "
            f"匹配率: {avg_match_rate:.3f} | "
            f"预测: {avg_pred:.1f} | "
            f"真实: {avg_true:.1f}"
        )
        
        # 早停和保存
        if avg_match_rate > best_match_rate:
            best_match_rate = avg_match_rate
            patience_counter = 0
            torch.save({
                'model_state_dict': model.state_dict(),
                'match_rate': avg_match_rate,
                'epoch': epoch + 1
            }, "models/bc_model_stage7_precision.pth")
            if avg_match_rate > 0:
                logger.info(f"★ 新最佳匹配率: {avg_match_rate:.3f}")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"早停，最佳匹配率: {best_match_rate:.3f}")
                break
    
    return model


if __name__ == "__main__":
    model = train_precision_model()