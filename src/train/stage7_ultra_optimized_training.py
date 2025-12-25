"""
Stage 7.2: 超级优化版训练 - 彻底解决预测过度问题
针对512卡牌全预测问题的根本性修复

核心改进：
1. 完全重新设计损失函数，极大惩罚过度预测
2. 使用更激进的稀疏性约束
3. 改进阈值机制，使用动态稀疏性目标
4. 添加卡牌数量直接监督
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UltraOptimizedGuandanNet(nn.Module):
    """
    超级优化版掼蛋神经网络
    
    彻底解决预测过度问题：
    1. 添加卡牌数量预测头
    2. 更强的稀疏性架构
    3. 多阶段预测机制
    """
    
    def __init__(self, input_dim=512, output_dim=512, dropout_rate=0.5):
        super().__init__()
        
        # 特征提取层（更强的稀疏性）
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 256),  # 减少特征维度，增加稀疏性
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.5),
        )
        
        # 卡牌数量预测头（新增 - 直接预测需要多少张卡牌）
        self.card_count_predictor = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()  # 输出0-1，需要乘以最大卡牌数
        )
        
        # 动作预测头（更保守）
        self.action_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(32, output_dim),
        )
        
        # 稀疏性控制器（更激进）
        self.sparsity_gate = nn.Sequential(
            nn.Linear(64, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        
        # 策略分类头
        self.strategy_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 8)
        )
        
    def forward(self, x):
        # 特征提取
        features = self.feature_extractor(x)
        
        # 多任务输出
        action_logits = self.action_head(features)
        card_count = self.card_count_predictor(features) * 20  # 最多20张卡牌
        sparsity_gate = self.sparsity_gate(features)
        strategy_logits = self.strategy_head(features)
        
        return action_logits, card_count, sparsity_gate, strategy_logits


class UltraSparseLoss(nn.Module):
    """
    超级稀疏损失函数
    
    彻底解决预测过度问题：
    1. 极大的过度预测惩罚（指数级）
    2. 卡牌数量直接监督
    3. Top-K选择机制
    """
    
    def __init__(self, over_prediction_penalty=100.0, count_loss_weight=10.0):
        super().__init__()
        self.over_prediction_penalty = over_prediction_penalty
        self.count_loss_weight = count_loss_weight
        
    def forward(self, action_logits, target_actions, predicted_count, sparsity_gate):
        batch_size = action_logits.size(0)
        
        # 1. 计算真实卡牌数量
        true_count = target_actions.sum(dim=1).float()
        
        # 2. 卡牌数量监督损失
        count_loss = nn.functional.mse_loss(predicted_count.squeeze(), true_count)
        
        # 3. 使用预测的卡牌数量进行Top-K选择
        action_probs = torch.sigmoid(action_logits)
        
        # 对每个样本，只选择概率最高的K张卡牌
        sparse_predictions = torch.zeros_like(action_probs)
        
        for i in range(batch_size):
            k = max(1, min(int(predicted_count[i].item()), action_logits.size(1)))
            
            # 获取Top-K索引
            _, top_k_indices = torch.topk(action_probs[i], k)
            sparse_predictions[i, top_k_indices] = 1.0
        
        # 4. 计算稀疏预测的BCE损失
        sparse_bce_loss = nn.functional.binary_cross_entropy(
            sparse_predictions, target_actions, reduction='mean'
        )
        
        # 5. 极大的过度预测惩罚
        predicted_card_count = sparse_predictions.sum(dim=1)
        over_prediction = torch.relu(predicted_card_count - true_count)
        
        # 指数级惩罚
        over_prediction_penalty = self.over_prediction_penalty * torch.exp(over_prediction)
        over_prediction_loss = over_prediction_penalty.mean()
        
        # 6. 稀疏性奖励
        sparsity_bonus = -torch.log(predicted_card_count + 1e-8).mean()
        
        # 7. 组合损失
        total_loss = (
            sparse_bce_loss +
            self.count_loss_weight * count_loss +
            over_prediction_loss +
            sparsity_bonus
        )
        
        return total_loss, {
            'bce_loss': sparse_bce_loss.item(),
            'count_loss': count_loss.item(),
            'over_prediction_loss': over_prediction_loss.item(),
            'sparsity_bonus': sparsity_bonus.item()
        }


def train_stage7_ultra_optimized_model(
    data_dir: str = "game_records",
    model_save_path: str = "models/bc_model_stage7_ultra_optimized.pth",
    epochs: int = 50,
    batch_size: int = 16,  # 减小批次大小，更精细的训练
    learning_rate: float = 0.0001,
    device: str = "cpu"
):
    """
    Stage 7.2 超级优化训练
    """
    
    logger.info("=" * 60)
    logger.info("Stage 7.2: 超级优化版训练 - 彻底解决预测过度")
    logger.info("=" * 60)
    
    # 加载数据
    logger.info("加载训练数据...")
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir=data_dir,
        batch_size=batch_size,
        max_samples=3000,
        shuffle=True
    )
    
    dataset_size = len(dataloader.dataset)
    
    logger.info(f"训练样本数: {dataset_size}")
    logger.info(f"批次大小: {batch_size}")
    logger.info(f"训练轮数: {epochs}")
    logger.info(f"学习率: {learning_rate}")
    logger.info(f"核心目标: 彻底解决512卡牌全预测问题")
    
    # 初始化超级优化模型
    model = UltraOptimizedGuandanNet().to(device)
    
    # 优化器
    optimizer = optim.Adam(
        model.parameters(), 
        lr=learning_rate, 
        weight_decay=0.01
    )
    
    # 学习率调度器
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5
    )
    
    # 超级稀疏损失函数
    criterion = UltraSparseLoss(
        over_prediction_penalty=1000.0,  # 极大惩罚
        count_loss_weight=50.0  # 强化数量监督
    )
    strategy_criterion = nn.CrossEntropyLoss()
    
    # 训练循环
    model.train()
    best_prediction_ratio = float('inf')
    patience = 10
    patience_counter = 0
    
    training_history = []
    
    for epoch in range(epochs):
        epoch_start_time = time.time()
        total_loss = 0.0
        total_bce_loss = 0.0
        total_count_loss = 0.0
        total_over_prediction_loss = 0.0
        total_strategy_loss = 0.0
        
        # 统计预测情况
        total_predicted_cards = 0
        total_true_cards = 0
        batch_count = 0
        
        for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
            state_vec = state_vec.to(device)
            action_vec = action_vec.to(device)
            strategy_type = strategy_type.to(device)
            
            # 前向传播
            action_logits, predicted_count, sparsity_gate, strategy_logits = model(state_vec)
            
            # 计算损失
            main_loss, loss_components = criterion(
                action_logits, action_vec, predicted_count, sparsity_gate
            )
            strategy_loss = strategy_criterion(strategy_logits, strategy_type)
            
            # 组合损失
            total_batch_loss = main_loss + 0.1 * strategy_loss
            
            # 反向传播
            optimizer.zero_grad()
            total_batch_loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            
            # 累计损失
            total_loss += total_batch_loss.item()
            total_bce_loss += loss_components['bce_loss']
            total_count_loss += loss_components['count_loss']
            total_over_prediction_loss += loss_components['over_prediction_loss']
            total_strategy_loss += strategy_loss.item()
            
            # 统计预测情况（使用Top-K预测）
            with torch.no_grad():
                action_probs = torch.sigmoid(action_logits)
                
                for i in range(action_vec.size(0)):
                    k = max(1, min(int(predicted_count[i].item()), action_logits.size(1)))
                    _, top_k_indices = torch.topk(action_probs[i], k)
                    
                    total_predicted_cards += k
                    total_true_cards += action_vec[i].sum().item()
                    batch_count += 1
        
        # 更新学习率
        avg_loss = total_loss / len(dataloader)
        scheduler.step(avg_loss)
        
        # 计算平均损失和预测统计
        avg_bce_loss = total_bce_loss / len(dataloader)
        avg_count_loss = total_count_loss / len(dataloader)
        avg_over_prediction_loss = total_over_prediction_loss / len(dataloader)
        avg_strategy_loss = total_strategy_loss / len(dataloader)
        
        avg_predicted_cards = total_predicted_cards / batch_count
        avg_true_cards = total_true_cards / batch_count
        prediction_ratio = avg_predicted_cards / avg_true_cards if avg_true_cards > 0 else float('inf')
        
        epoch_time = time.time() - epoch_start_time
        
        # 记录训练历史
        epoch_info = {
            "epoch": epoch + 1,
            "total_loss": avg_loss,
            "bce_loss": avg_bce_loss,
            "count_loss": avg_count_loss,
            "over_prediction_loss": avg_over_prediction_loss,
            "strategy_loss": avg_strategy_loss,
            "avg_predicted_cards": avg_predicted_cards,
            "avg_true_cards": avg_true_cards,
            "prediction_ratio": prediction_ratio,
            "learning_rate": optimizer.param_groups[0]['lr'],
            "epoch_time": epoch_time
        }
        training_history.append(epoch_info)
        
        # 打印进度
        logger.info(
            f"Epoch {epoch+1:3d}/{epochs} | "
            f"Loss: {avg_loss:.4f} | "
            f"BCE: {avg_bce_loss:.4f} | "
            f"Count: {avg_count_loss:.4f} | "
            f"预测: {avg_predicted_cards:.1f} | "
            f"真实: {avg_true_cards:.1f} | "
            f"比例: {prediction_ratio:.1f}x | "
            f"LR: {optimizer.param_groups[0]['lr']:.6f}"
        )
        
        # 早停检查（基于预测比例）
        if prediction_ratio < best_prediction_ratio:
            best_prediction_ratio = prediction_ratio
            patience_counter = 0
            
            # 保存最佳模型
            torch.save({
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'epoch': epoch + 1,
                'loss': avg_loss,
                'prediction_ratio': prediction_ratio,
                'training_history': training_history
            }, model_save_path)
            
            logger.info(f"★ 新的最佳预测比例: {prediction_ratio:.2f}x (目标: <3.0x)")
            
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"早停触发，在第 {epoch+1} 轮停止训练")
                logger.info(f"最佳预测比例: {best_prediction_ratio:.2f}x")
                break
    
    # 保存训练历史
    history_path = model_save_path.replace('.pth', '_training_history.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(training_history, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 60)
    logger.info("Stage 7.2 超级优化训练完成")
    logger.info(f"最佳预测比例: {best_prediction_ratio:.2f}x")
    logger.info(f"改进效果: {'显著' if best_prediction_ratio < 10 else '需进一步优化'}")
    logger.info(f"模型保存至: {model_save_path}")
    logger.info(f"训练历史保存至: {history_path}")
    logger.info("=" * 60)
    
    return model, training_history


if __name__ == "__main__":
    # 执行Stage 7.2超级优化训练
    model, history = train_stage7_ultra_optimized_model(
        epochs=50,
        batch_size=16,
        learning_rate=0.0001
    )