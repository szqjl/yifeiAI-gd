"""
Stage 7: 鲁棒性增强训练
基于Stage6评估结果的问题修复和优化

主要改进：
1. 解决稳定性问题 - 防止连续对战中的性能崩溃
2. 修复预测过度问题 - 大幅减少预测卡牌数量
3. 增强数据利用 - 优化特征工程和损失函数
4. 提升决策质量 - 改进模型架构和训练策略
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


class RobustGuandanNet(nn.Module):
    """
    鲁棒性增强的掼蛋神经网络
    
    改进点：
    1. 添加Dropout和BatchNorm提升稳定性
    2. 使用残差连接防止梯度消失
    3. 多尺度特征提取
    4. 自适应阈值机制
    """
    
    def __init__(self, input_dim=512, output_dim=512, dropout_rate=0.3):
        super().__init__()
        
        # 特征提取层（多尺度）
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
        )
        
        # 残差连接层
        self.residual_block = nn.Sequential(
            nn.Linear(512, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(512, 512),
            nn.BatchNorm1d(512),
        )
        
        # 动作预测头（改进的输出层）
        self.action_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(256, output_dim),
        )
        
        # 自适应阈值预测器
        self.threshold_predictor = nn.Sequential(
            nn.Linear(512, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()  # 输出0-1之间的阈值
        )
        
        # 策略分类头
        self.strategy_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(128, 5)  # 5种策略类型
        )
        
    def forward(self, x):
        # 特征提取
        features = self.feature_extractor(x)
        
        # 残差连接
        residual = self.residual_block(features)
        features = features + residual  # 残差连接
        features = torch.relu(features)
        
        # 多任务输出
        action_logits = self.action_head(features)
        adaptive_threshold = self.threshold_predictor(features)
        strategy_logits = self.strategy_head(features)
        
        return action_logits, adaptive_threshold, strategy_logits


class AdaptiveFocalLoss(nn.Module):
    """
    自适应焦点损失函数
    
    解决预测过度问题：
    1. 动态调整正负样本权重
    2. 根据预测置信度调整损失
    3. 惩罚过度预测
    """
    
    def __init__(self, alpha=0.25, gamma=2.0, reduction='mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
        
    def forward(self, pred_logits, target, adaptive_threshold):
        # 使用自适应阈值
        threshold = adaptive_threshold.squeeze(-1)  # [batch_size]
        
        # 计算概率
        pred_probs = torch.sigmoid(pred_logits)
        
        # 计算基础BCE损失
        bce_loss = nn.functional.binary_cross_entropy_with_logits(
            pred_logits, target, reduction='none'
        )
        
        # 计算焦点权重
        pt = torch.where(target == 1, pred_probs, 1 - pred_probs)
        focal_weight = (1 - pt) ** self.gamma
        
        # 计算alpha权重
        alpha_weight = torch.where(target == 1, self.alpha, 1 - self.alpha)
        
        # 计算过度预测惩罚
        pred_count = (pred_probs > threshold.unsqueeze(1)).sum(dim=1).float()
        true_count = target.sum(dim=1).float()
        over_prediction_penalty = torch.relu(pred_count - true_count) * 0.1
        
        # 组合损失
        focal_loss = alpha_weight * focal_weight * bce_loss
        
        if self.reduction == 'mean':
            focal_loss = focal_loss.mean()
            over_prediction_penalty = over_prediction_penalty.mean()
        
        return focal_loss + over_prediction_penalty


def train_stage7_robust_model(
    data_dir: str = "game_records",
    model_save_path: str = "models/bc_model_stage7_robust.pth",
    epochs: int = 200,
    batch_size: int = 32,
    learning_rate: float = 0.0001,
    device: str = "cpu"
):
    """
    Stage 7 鲁棒性增强训练
    """
    
    logger.info("=" * 60)
    logger.info("Stage 7: 鲁棒性增强训练")
    logger.info("=" * 60)
    
    # 加载数据
    logger.info("加载训练数据...")
    from enhanced_data_loader import create_enhanced_dataloader
    
    dataloader = create_enhanced_dataloader(
        data_dir=data_dir,
        batch_size=batch_size,
        enable_augmentation=True,
        balance_strategy=True,
        shuffle=True
    )
    
    dataset_size = len(dataloader.dataset)
    
    logger.info(f"训练样本数: {dataset_size}")
    logger.info(f"批次大小: {batch_size}")
    logger.info(f"训练轮数: {epochs}")
    logger.info(f"数据增强: 启用")
    logger.info(f"策略平衡: 启用")
    
    # 初始化模型
    model = RobustGuandanNet().to(device)
    
    # 优化器（使用AdamW，更好的权重衰减）
    optimizer = optim.AdamW(
        model.parameters(), 
        lr=learning_rate, 
        weight_decay=0.01,
        betas=(0.9, 0.999)
    )
    
    # 学习率调度器（余弦退火）
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=20, T_mult=2, eta_min=1e-6
    )
    
    # 损失函数
    action_criterion = AdaptiveFocalLoss(alpha=0.3, gamma=2.0)
    strategy_criterion = nn.CrossEntropyLoss()
    threshold_criterion = nn.MSELoss()
    
    # 训练循环
    model.train()
    best_loss = float('inf')
    patience = 20
    patience_counter = 0
    
    training_history = []
    
    for epoch in range(epochs):
        epoch_start_time = time.time()
        total_loss = 0.0
        action_loss_sum = 0.0
        strategy_loss_sum = 0.0
        threshold_loss_sum = 0.0
        
        for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
            state_vec = state_vec.to(device)
            action_vec = action_vec.to(device)
            strategy_type = strategy_type.to(device)
            
            # 前向传播
            action_logits, adaptive_threshold, strategy_logits = model(state_vec)
            
            # 计算目标阈值（基于真实动作数量）
            true_action_count = action_vec.sum(dim=1).float()
            target_threshold = torch.clamp(true_action_count / action_vec.size(1), 0.01, 0.99)
            
            # 计算损失
            action_loss = action_criterion(action_logits, action_vec, adaptive_threshold)
            strategy_loss = strategy_criterion(strategy_logits, strategy_type)
            threshold_loss = threshold_criterion(adaptive_threshold.squeeze(), target_threshold)
            
            # 组合损失（动态权重）
            total_batch_loss = (
                action_loss * 0.7 + 
                strategy_loss * 0.2 + 
                threshold_loss * 0.1
            )
            
            # 反向传播
            optimizer.zero_grad()
            total_batch_loss.backward()
            
            # 梯度裁剪（防止梯度爆炸）
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            
            # 累计损失
            total_loss += total_batch_loss.item()
            action_loss_sum += action_loss.item()
            strategy_loss_sum += strategy_loss.item()
            threshold_loss_sum += threshold_loss.item()
        
        # 更新学习率
        scheduler.step()
        
        # 计算平均损失
        avg_loss = total_loss / len(dataloader)
        avg_action_loss = action_loss_sum / len(dataloader)
        avg_strategy_loss = strategy_loss_sum / len(dataloader)
        avg_threshold_loss = threshold_loss_sum / len(dataloader)
        
        epoch_time = time.time() - epoch_start_time
        
        # 记录训练历史
        epoch_info = {
            "epoch": epoch + 1,
            "total_loss": avg_loss,
            "action_loss": avg_action_loss,
            "strategy_loss": avg_strategy_loss,
            "threshold_loss": avg_threshold_loss,
            "learning_rate": scheduler.get_last_lr()[0],
            "epoch_time": epoch_time
        }
        training_history.append(epoch_info)
        
        # 打印进度
        if (epoch + 1) % 10 == 0 or epoch < 10:
            logger.info(
                f"Epoch {epoch+1:3d}/{epochs} | "
                f"Loss: {avg_loss:.4f} | "
                f"Action: {avg_action_loss:.4f} | "
                f"Strategy: {avg_strategy_loss:.4f} | "
                f"Threshold: {avg_threshold_loss:.4f} | "
                f"LR: {scheduler.get_last_lr()[0]:.6f} | "
                f"Time: {epoch_time:.1f}s"
            )
        
        # 早停检查
        if avg_loss < best_loss:
            best_loss = avg_loss
            patience_counter = 0
            
            # 保存最佳模型
            torch.save({
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'epoch': epoch + 1,
                'loss': best_loss,
                'training_history': training_history
            }, model_save_path)
            
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"早停触发，在第 {epoch+1} 轮停止训练")
                break
    
    # 保存训练历史
    history_path = model_save_path.replace('.pth', '_training_history.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(training_history, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 60)
    logger.info("Stage 7 训练完成")
    logger.info(f"最佳损失: {best_loss:.4f}")
    logger.info(f"模型保存至: {model_save_path}")
    logger.info(f"训练历史保存至: {history_path}")
    logger.info("=" * 60)
    
    return model, training_history


if __name__ == "__main__":
    # 执行Stage 7训练
    model, history = train_stage7_robust_model(
        epochs=200,
        batch_size=32,
        learning_rate=0.0001
    )