"""
Stage 7.5: 针对性训练 - 基于数据分析的直接优化
针对55%的0卡牌样本和30%的1卡牌样本进行专门优化
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TargetedGuandanNet(nn.Module):
    """针对性网络 - 专门处理0-5张卡牌的预测"""
    
    def __init__(self):
        super().__init__()
        
        # 简化特征提取
        self.features = nn.Sequential(
            nn.Linear(512, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        
        # 数量分类器（0-5张卡牌）
        self.count_classifier = nn.Sequential(
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 6),  # 0,1,2,3,4,5张
            nn.Softmax(dim=-1)
        )
        
        # 位置预测器（针对每种数量）
        self.position_predictors = nn.ModuleList([
            nn.Linear(32, 512) for _ in range(6)  # 6个预测器
        ])
        
    def forward(self, x):
        features = self.features(x)
        
        # 预测数量分布
        count_probs = self.count_classifier(features)
        
        # 预测位置（加权组合）
        position_logits = torch.zeros(x.size(0), 512, device=x.device)
        
        for i in range(6):
            pos_logits = self.position_predictors[i](features)
            position_logits += count_probs[:, i:i+1] * pos_logits
        
        return position_logits, count_probs


class TargetedLoss(nn.Module):
    """针对性损失函数"""
    
    def __init__(self):
        super().__init__()
        
    def forward(self, position_logits, count_probs, target_actions):
        batch_size = position_logits.size(0)
        
        # 真实数量（限制在0-5范围内）
        true_counts = target_actions.sum(dim=1).long()
        true_counts = torch.clamp(true_counts, 0, 5)  # 限制范围
        
        # 数量分类损失
        count_loss = nn.functional.cross_entropy(count_probs, true_counts) * 10
        
        # 位置预测损失
        position_loss = 0
        exact_matches = 0
        
        for i in range(batch_size):
            true_count = true_counts[i].item()
            
            if true_count == 0:
                # 0张卡牌：所有位置都应该是0
                pred_probs = torch.sigmoid(position_logits[i])
                pos_loss = pred_probs.sum()  # 惩罚任何非零预测
            else:
                # 有卡牌：使用Top-K
                _, top_k_indices = torch.topk(position_logits[i], true_count)
                pred_action = torch.zeros_like(target_actions[i])
                pred_action[top_k_indices] = 1.0
                
                pos_loss = nn.functional.binary_cross_entropy(
                    pred_action, target_actions[i], reduction='sum'
                )
                
                # 检查精确匹配
                if torch.equal(pred_action, target_actions[i]):
                    exact_matches += 1
            
            position_loss += pos_loss
        
        position_loss = position_loss / batch_size
        exact_match_rate = exact_matches / batch_size
        
        # 精确匹配奖励
        match_bonus = -100 * exact_match_rate
        
        total_loss = count_loss + position_loss + match_bonus
        
        return total_loss, {
            'count_loss': count_loss.item(),
            'position_loss': position_loss.item(),
            'exact_match_rate': exact_match_rate
        }


def train_targeted_model():
    """训练针对性模型"""
    
    logger.info("Stage 7.5: 针对性训练")
    
    # 数据加载
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=64,
        max_samples=2000,
        shuffle=True
    )
    
    model = TargetedGuandanNet()
    optimizer = optim.Adam(model.parameters(), lr=0.003)
    criterion = TargetedLoss()
    
    best_match_rate = 0
    
    for epoch in range(40):
        model.train()
        total_loss = 0
        total_match_rate = 0
        count_correct = 0
        total_samples = 0
        
        for state_vec, action_vec, _ in dataloader:
            optimizer.zero_grad()
            
            position_logits, count_probs = model(state_vec)
            loss, metrics = criterion(position_logits, count_probs, action_vec)
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            total_match_rate += metrics['exact_match_rate']
            
            # 统计数量预测准确率
            true_counts = action_vec.sum(dim=1).long()
            true_counts = torch.clamp(true_counts, 0, 5)
            pred_counts = count_probs.argmax(dim=1)
            count_correct += (pred_counts == true_counts).sum().item()
            total_samples += action_vec.size(0)
        
        avg_loss = total_loss / len(dataloader)
        avg_match_rate = total_match_rate / len(dataloader)
        count_accuracy = count_correct / total_samples
        
        logger.info(
            f"Epoch {epoch+1:2d}/40 | "
            f"Loss: {avg_loss:.2f} | "
            f"匹配率: {avg_match_rate:.3f} | "
            f"数量准确率: {count_accuracy:.3f}"
        )
        
        if avg_match_rate > best_match_rate:
            best_match_rate = avg_match_rate
            torch.save(model.state_dict(), "models/bc_model_stage7_targeted.pth")
            if avg_match_rate > 0:
                logger.info(f"★ 匹配率: {avg_match_rate:.3f}")
    
    logger.info(f"最终最佳匹配率: {best_match_rate:.3f}")
    return model


if __name__ == "__main__":
    model = train_targeted_model()