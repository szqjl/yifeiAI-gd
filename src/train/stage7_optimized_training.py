"""
Stage 7.1: 针对预测过度问题的优化训练
基于Stage 7评估结果的针对性改进

主要优化：
1. 强化过度预测惩罚机制
2. 调整损失函数权重
3. 改进自适应阈值策略
4. 增加稀疏性正则化
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


class OptimizedGuandanNet(nn.Module):
    """
    优化版掼蛋神经网络
    
    针对预测过度问题的改进：
    1. 更强的稀疏性约束
    2. 改进的阈值预测机制
    3. 多层次特征提取
    """
    
    def __init__(self, input_dim=512, output_dim=512, dropout_rate=0.4):
        super().__init__()
        
        # 特征提取层（增强稀疏性）
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            # 添加稀疏性约束层
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.5),
        )
        
        # 残差连接层
        self.residual_block = nn.Sequential(
            nn.Linear(256, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.3),
            nn.Linear(256, 256),
            nn.BatchNorm1d(256),
        )
        
        # 动作预测头（更保守的预测）
        self.action_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.3),
            nn.Linear(128, output_dim),
        )
        
        # 改进的阈值预测器（更敏感的阈值控制）
        self.threshold_predictor = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # 策略分类头
        self.strategy_head = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.3),
            nn.Linear(128, 8)  # 8种策略类型
        )
        
        # 稀疏性控制器（新增）
        self.sparsity_controller = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()  # 输出稀疏性权重
        )
        
    def forward(self, x):
        # 特征提取
        features = self.feature_extractor(x)
        
        # 残差连接
        residual = self.residual_block(features)
        features = features + residual
        features = torch.relu(features)
        
        # 多任务输出
        action_logits = self.action_head(features)
        adaptive_threshold = self.threshold_predictor(features)
        strategy_logits = self.strategy_head(features)
        sparsity_weight = self.sparsity_controller(features)
        
        return action_logits, adaptive_threshold, strategy_logits, sparsity_weight


class EnhancedFocalLoss(nn.Module):
    """
    增强版焦点损失函数
    
    针对预测过度问题的改进：
    1. 大幅增加过度预测惩罚
    2. 动态调整正负样本权重
    3. 添加稀疏性奖励机制
    """
    
    def __init__(self, alpha=0.1, gamma=3.0, over_prediction_penalty=2.0, sparsity_reward=1.0):
        super().__init__()
        self.alpha = alpha  # 降低正样本权重，减少过度预测
        self.gamma = gamma  # 增加gamma，更关注困难样本
        self.over_prediction_penalty = over_prediction_penalty  # 大幅增加过度预测惩罚
        self.sparsity_reward = sparsity_reward  # 稀疏性奖励
        
    def forward(self, pred_logits, target, adaptive_threshold, sparsity_weight):
        # 使用自适应阈值和稀疏性权重
        threshold = adaptive_threshold.squeeze(-1) * sparsity_weight.squeeze(-1)
        
        # 计算概率
        pred_probs = torch.sigmoid(pred_logits)
        
        # 计算基础BCE损失
        bce_loss = nn.functional.binary_cross_entropy_with_logits(
            pred_logits, target, reduction='none'
        )
        
        # 计算焦点权重
        pt = torch.where(target == 1, pred_probs, 1 - pred_probs)
        focal_weight = (1 - pt) ** self.gamma
        
        # 计算alpha权重（更偏向负样本）
        alpha_weight = torch.where(target == 1, self.alpha, 1 - self.alpha)
        
        # 计算过度预测惩罚（大幅增强）
        pred_count = (pred_probs > threshold.unsqueeze(1)).sum(dim=1).float()
        true_count = target.sum(dim=1).float()
        
        # 非线性过度预测惩罚
        over_prediction = torch.relu(pred_count - true_count)
        over_prediction_penalty = self.over_prediction_penalty * (over_prediction ** 2)  # 平方惩罚
        
        # 稀疏性奖励（奖励预测少量卡牌）
        sparsity_bonus = self.sparsity_reward * torch.exp(-pred_count / 10.0)  # 指数奖励
        
        # 组合损失
        focal_loss = alpha_weight * focal_weight * bce_loss
        focal_loss = focal_loss.mean()
        
        total_penalty = over_prediction_penalty.mean()
        total_bonus = sparsity_bonus.mean()
        
        return focal_loss + total_penalty - total_bonus


def train_stage7_optimized_model(
    data_dir: str = "game_records",
    model_save_path: str = "models/bc_model_stage7_optimized.pth",
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 0.00005,  # 降低学习率，更稳定的训练
    device: str = "cpu"
):
    """
    Stage 7.1 优化训练
    """
    
    logger.info("=" * 60)
    logger.info("Stage 7.1: 优化版鲁棒性增强训练")
    logger.info("=" * 60)
    
    # 加载数据
    logger.info("加载训练数据...")
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir=data_dir,
        batch_size=batch_size,
        max_samples=5000,  # 适中的样本数量
        shuffle=True
    )
    
    dataset_size = len(dataloader.dataset)
    
    logger.info(f"训练样本数: {dataset_size}")
    logger.info(f"批次大小: {batch_size}")
    logger.info(f"训练轮数: {epochs}")
    logger.info(f"学习率: {learning_rate}")
    logger.info(f"优化目标: 减少预测过度，提高精确率")
    
    # 初始化优化模型
    model = OptimizedGuandanNet().to(device)
    
    # 优化器（更保守的设置）
    optimizer = optim.AdamW(
        model.parameters(), 
        lr=learning_rate, 
        weight_decay=0.02,  # 增加权重衰减
        betas=(0.9, 0.999)
    )
    
    # 学习率调度器（更平缓的衰减）
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=15, T_mult=2, eta_min=1e-7
    )
    
    # 损失函数（针对过度预测优化）
    action_criterion = EnhancedFocalLoss(
        alpha=0.05,  # 大幅降低正样本权重
        gamma=4.0,   # 增加难样本关注度
        over_prediction_penalty=5.0,  # 大幅增加过度预测惩罚
        sparsity_reward=2.0  # 增加稀疏性奖励
    )
    strategy_criterion = nn.CrossEntropyLoss()
    threshold_criterion = nn.MSELoss()
    
    # 训练循环
    model.train()
    best_loss = float('inf')
    patience = 15  # 增加耐心值
    patience_counter = 0
    
    training_history = []
    
    for epoch in range(epochs):
        epoch_start_time = time.time()
        total_loss = 0.0
        action_loss_sum = 0.0
        strategy_loss_sum = 0.0
        threshold_loss_sum = 0.0
        
        # 统计预测情况
        total_predicted_cards = 0
        total_true_cards = 0
        batch_count = 0
        
        for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
            state_vec = state_vec.to(device)
            action_vec = action_vec.to(device)
            strategy_type = strategy_type.to(device)
            
            # 前向传播
            action_logits, adaptive_threshold, strategy_logits, sparsity_weight = model(state_vec)
            
            # 计算目标阈值（更保守的阈值）
            true_action_count = action_vec.sum(dim=1).float()
            # 使用更小的目标阈值，鼓励稀疏预测
            target_threshold = torch.clamp(true_action_count / (action_vec.size(1) * 2), 0.001, 0.5)
            
            # 计算损失
            action_loss = action_criterion(action_logits, action_vec, adaptive_threshold, sparsity_weight)
            strategy_loss = strategy_criterion(strategy_logits, strategy_type)
            threshold_loss = threshold_criterion(adaptive_threshold.squeeze(), target_threshold)
            
            # 组合损失（调整权重，更关注动作预测）
            total_batch_loss = (
                action_loss * 0.8 +      # 增加动作损失权重
                strategy_loss * 0.1 +    # 降低策略损失权重
                threshold_loss * 0.1     # 保持阈值损失权重
            )
            
            # 反向传播
            optimizer.zero_grad()
            total_batch_loss.backward()
            
            # 梯度裁剪（更严格）
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.5)
            
            optimizer.step()
            
            # 累计损失
            total_loss += total_batch_loss.item()
            action_loss_sum += action_loss.item()
            strategy_loss_sum += strategy_loss.item()
            threshold_loss_sum += threshold_loss.item()
            
            # 统计预测情况
            with torch.no_grad():
                pred_probs = torch.sigmoid(action_logits)
                threshold = adaptive_threshold.squeeze(-1) * sparsity_weight.squeeze(-1)
                predicted_actions = (pred_probs > threshold.unsqueeze(1)).float()
                
                total_predicted_cards += predicted_actions.sum().item()
                total_true_cards += action_vec.sum().item()
                batch_count += action_vec.size(0)
        
        # 更新学习率
        scheduler.step()
        
        # 计算平均损失和预测统计
        avg_loss = total_loss / len(dataloader)
        avg_action_loss = action_loss_sum / len(dataloader)
        avg_strategy_loss = strategy_loss_sum / len(dataloader)
        avg_threshold_loss = threshold_loss_sum / len(dataloader)
        
        avg_predicted_cards = total_predicted_cards / batch_count
        avg_true_cards = total_true_cards / batch_count
        
        epoch_time = time.time() - epoch_start_time
        
        # 记录训练历史
        epoch_info = {
            "epoch": epoch + 1,
            "total_loss": avg_loss,
            "action_loss": avg_action_loss,
            "strategy_loss": avg_strategy_loss,
            "threshold_loss": avg_threshold_loss,
            "avg_predicted_cards": avg_predicted_cards,
            "avg_true_cards": avg_true_cards,
            "prediction_ratio": avg_predicted_cards / avg_true_cards if avg_true_cards > 0 else 0,
            "learning_rate": scheduler.get_last_lr()[0],
            "epoch_time": epoch_time
        }
        training_history.append(epoch_info)
        
        # 打印进度（包含预测统计）
        if (epoch + 1) % 5 == 0 or epoch < 10:
            logger.info(
                f"Epoch {epoch+1:3d}/{epochs} | "
                f"Loss: {avg_loss:.4f} | "
                f"Action: {avg_action_loss:.4f} | "
                f"预测卡牌: {avg_predicted_cards:.1f} | "
                f"真实卡牌: {avg_true_cards:.1f} | "
                f"比例: {avg_predicted_cards/avg_true_cards:.1f}x | "
                f"LR: {scheduler.get_last_lr()[0]:.6f} | "
                f"Time: {epoch_time:.1f}s"
            )
        
        # 早停检查（基于预测质量）
        prediction_quality_score = 1.0 / (1.0 + abs(avg_predicted_cards - avg_true_cards))
        combined_score = prediction_quality_score * (1.0 / (1.0 + avg_loss))
        
        if combined_score > best_loss:
            best_loss = combined_score
            patience_counter = 0
            
            # 保存最佳模型
            torch.save({
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'epoch': epoch + 1,
                'loss': avg_loss,
                'prediction_quality': prediction_quality_score,
                'training_history': training_history
            }, model_save_path)
            
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"早停触发，在第 {epoch+1} 轮停止训练")
                logger.info(f"最佳预测质量评分: {best_loss:.4f}")
                break
    
    # 保存训练历史
    history_path = model_save_path.replace('.pth', '_training_history.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(training_history, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 60)
    logger.info("Stage 7.1 优化训练完成")
    logger.info(f"最佳预测质量评分: {best_loss:.4f}")
    logger.info(f"模型保存至: {model_save_path}")
    logger.info(f"训练历史保存至: {history_path}")
    logger.info("=" * 60)
    
    return model, training_history


if __name__ == "__main__":
    # 执行Stage 7.1优化训练
    model, history = train_stage7_optimized_model(
        epochs=100,
        batch_size=32,
        learning_rate=0.00005
    )