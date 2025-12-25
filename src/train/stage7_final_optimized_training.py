"""
Stage 7.3: 最终优化版训练 - 专注完全匹配率和稳定性
基于Stage 7.2的成功基础，进一步优化完全匹配率和模型稳定性

核心改进：
1. 位置敏感的损失函数
2. 集成学习机制
3. 对抗训练增强稳定性
4. 精确匹配奖励机制
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
import random

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinalOptimizedGuandanNet(nn.Module):
    """
    最终优化版掼蛋神经网络
    
    专注完全匹配率和稳定性：
    1. 位置敏感的注意力机制
    2. 多头预测机制
    3. 不确定性量化
    4. 集成预测头
    """
    
    def __init__(self, input_dim=512, output_dim=512, dropout_rate=0.4):
        super().__init__()
        
        # 特征提取层（增强稳定性）
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),  # 使用LayerNorm提升稳定性
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.8),
            
            nn.Linear(128, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Dropout(dropout_rate * 0.6),
        )
        
        # 位置注意力机制（新增）
        self.position_attention = nn.MultiheadAttention(
            embed_dim=64, num_heads=4, dropout=0.1, batch_first=True
        )
        
        # 多头预测机制（集成学习）
        self.prediction_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(32, output_dim)
            ) for _ in range(3)  # 3个预测头
        ])
        
        # 不确定性量化头
        self.uncertainty_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, output_dim),
            nn.Sigmoid()  # 输出每个位置的不确定性
        )
        
        # 卡牌数量预测（继承Stage 7.2）
        self.card_count_predictor = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
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
        
        # 集成权重预测器
        self.ensemble_weights = nn.Sequential(
            nn.Linear(64, 16),
            nn.ReLU(),
            nn.Linear(16, 3),
            nn.Softmax(dim=-1)  # 3个预测头的权重
        )
        
    def forward(self, x):
        batch_size = x.size(0)
        
        # 特征提取
        features = self.feature_extractor(x)
        
        # 位置注意力（增强位置敏感性）
        features_reshaped = features.unsqueeze(1)  # [batch, 1, 64]
        attended_features, _ = self.position_attention(
            features_reshaped, features_reshaped, features_reshaped
        )
        features = attended_features.squeeze(1) + features  # 残差连接
        
        # 多头预测
        predictions = []
        for head in self.prediction_heads:
            pred = head(features)
            predictions.append(pred)
        
        # 集成权重
        weights = self.ensemble_weights(features)  # [batch, 3]
        
        # 加权集成预测
        ensemble_logits = torch.zeros_like(predictions[0])
        for i, pred in enumerate(predictions):
            ensemble_logits += weights[:, i:i+1] * pred
        
        # 其他输出
        card_count = self.card_count_predictor(features) * 20
        uncertainty = self.uncertainty_head(features)
        strategy_logits = self.strategy_head(features)
        
        return ensemble_logits, card_count, uncertainty, strategy_logits, predictions


class ExactMatchLoss(nn.Module):
    """
    精确匹配损失函数
    
    专门优化完全匹配率：
    1. 精确匹配奖励
    2. 位置敏感惩罚
    3. 不确定性正则化
    4. 集成一致性损失
    """
    
    def __init__(self, exact_match_weight=10.0, position_weight=5.0, uncertainty_weight=2.0):
        super().__init__()
        self.exact_match_weight = exact_match_weight
        self.position_weight = position_weight
        self.uncertainty_weight = uncertainty_weight
        
    def forward(self, ensemble_logits, target_actions, predicted_count, uncertainty, individual_predictions):
        batch_size = ensemble_logits.size(0)
        
        # 1. 使用Top-K进行预测
        ensemble_probs = torch.sigmoid(ensemble_logits)
        
        sparse_predictions = torch.zeros_like(ensemble_probs)
        exact_matches = 0
        
        for i in range(batch_size):
            k = max(1, min(int(predicted_count[i].item()), ensemble_logits.size(1)))
            
            # 考虑不确定性的Top-K选择
            adjusted_probs = ensemble_probs[i] * (1 - uncertainty[i])  # 降低不确定位置的概率
            _, top_k_indices = torch.topk(adjusted_probs, k)
            sparse_predictions[i, top_k_indices] = 1.0
            
            # 检查精确匹配
            if torch.equal(sparse_predictions[i], target_actions[i]):
                exact_matches += 1
        
        # 2. 基础BCE损失
        bce_loss = nn.functional.binary_cross_entropy(
            sparse_predictions, target_actions, reduction='mean'
        )
        
        # 3. 精确匹配奖励（负损失，鼓励精确匹配）
        exact_match_rate = exact_matches / batch_size
        exact_match_bonus = -self.exact_match_weight * exact_match_rate
        
        # 4. 位置敏感损失（惩罚错误位置的预测）
        position_errors = torch.abs(sparse_predictions - target_actions)
        position_loss = self.position_weight * position_errors.mean()
        
        # 5. 不确定性正则化（鼓励模型在困难位置表达不确定性）
        target_uncertainty = (sparse_predictions != target_actions).float()
        uncertainty_loss = self.uncertainty_weight * nn.functional.mse_loss(
            uncertainty, target_uncertainty
        )
        
        # 6. 集成一致性损失（鼓励多个预测头的一致性）
        consistency_loss = 0.0
        for i in range(len(individual_predictions)):
            for j in range(i+1, len(individual_predictions)):
                pred_i = torch.sigmoid(individual_predictions[i])
                pred_j = torch.sigmoid(individual_predictions[j])
                consistency_loss += nn.functional.mse_loss(pred_i, pred_j)
        consistency_loss = consistency_loss / (len(individual_predictions) * (len(individual_predictions) - 1) / 2)
        
        # 7. 数量监督损失
        true_count = target_actions.sum(dim=1).float()
        count_loss = nn.functional.mse_loss(predicted_count.squeeze(), true_count)
        
        # 组合损失
        total_loss = (
            bce_loss +
            exact_match_bonus +
            position_loss +
            uncertainty_loss +
            consistency_loss * 0.5 +
            count_loss * 10.0
        )
        
        return total_loss, {
            'bce_loss': bce_loss.item(),
            'exact_match_bonus': exact_match_bonus,
            'position_loss': position_loss.item(),
            'uncertainty_loss': uncertainty_loss.item(),
            'consistency_loss': consistency_loss.item(),
            'count_loss': count_loss.item(),
            'exact_match_rate': exact_match_rate
        }


def train_stage7_final_optimized_model(
    data_dir: str = "game_records",
    model_save_path: str = "models/bc_model_stage7_final_optimized.pth",
    epochs: int = 80,
    batch_size: int = 24,
    learning_rate: float = 0.00008,
    device: str = "cpu"
):
    """
    Stage 7.3 最终优化训练
    """
    
    logger.info("=" * 70)
    logger.info("Stage 7.3: 最终优化版训练 - 专注完全匹配率和稳定性")
    logger.info("=" * 70)
    
    # 加载数据
    logger.info("加载训练数据...")
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir=data_dir,
        batch_size=batch_size,
        max_samples=4000,  # 增加训练样本
        shuffle=True
    )
    
    dataset_size = len(dataloader.dataset)
    
    logger.info(f"训练样本数: {dataset_size}")
    logger.info(f"批次大小: {batch_size}")
    logger.info(f"训练轮数: {epochs}")
    logger.info(f"学习率: {learning_rate}")
    logger.info(f"优化目标: 完全匹配率>30%, 稳定性CV<0.05")
    
    # 初始化最终优化模型
    model = FinalOptimizedGuandanNet().to(device)
    
    # 优化器（更保守的设置）
    optimizer = optim.AdamW(
        model.parameters(), 
        lr=learning_rate, 
        weight_decay=0.015,
        betas=(0.9, 0.999)
    )
    
    # 学习率调度器（更平滑的衰减）
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=epochs, eta_min=1e-7
    )
    
    # 精确匹配损失函数
    criterion = ExactMatchLoss(
        exact_match_weight=20.0,  # 大幅增加精确匹配奖励
        position_weight=8.0,
        uncertainty_weight=3.0
    )
    strategy_criterion = nn.CrossEntropyLoss()
    
    # 训练循环
    model.train()
    best_exact_match_rate = 0.0
    patience = 12
    patience_counter = 0
    
    training_history = []
    
    for epoch in range(epochs):
        epoch_start_time = time.time()
        total_loss = 0.0
        total_exact_match_rate = 0.0
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
            ensemble_logits, predicted_count, uncertainty, strategy_logits, individual_predictions = model(state_vec)
            
            # 计算损失
            main_loss, loss_components = criterion(
                ensemble_logits, action_vec, predicted_count, uncertainty, individual_predictions
            )
            strategy_loss = strategy_criterion(strategy_logits, strategy_type)
            
            # 组合损失
            total_batch_loss = main_loss + 0.05 * strategy_loss
            
            # 反向传播
            optimizer.zero_grad()
            total_batch_loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.8)
            
            optimizer.step()
            
            # 累计损失和统计
            total_loss += total_batch_loss.item()
            total_exact_match_rate += loss_components['exact_match_rate']
            total_strategy_loss += strategy_loss.item()
            
            # 统计预测情况
            with torch.no_grad():
                for i in range(action_vec.size(0)):
                    k = max(1, min(int(predicted_count[i].item()), ensemble_logits.size(1)))
                    total_predicted_cards += k
                    total_true_cards += action_vec[i].sum().item()
                    batch_count += 1
        
        # 更新学习率
        scheduler.step()
        
        # 计算平均指标
        avg_loss = total_loss / len(dataloader)
        avg_exact_match_rate = total_exact_match_rate / len(dataloader)
        avg_strategy_loss = total_strategy_loss / len(dataloader)
        
        avg_predicted_cards = total_predicted_cards / batch_count
        avg_true_cards = total_true_cards / batch_count
        prediction_ratio = avg_predicted_cards / avg_true_cards if avg_true_cards > 0 else 0
        
        epoch_time = time.time() - epoch_start_time
        
        # 记录训练历史
        epoch_info = {
            "epoch": epoch + 1,
            "total_loss": avg_loss,
            "exact_match_rate": avg_exact_match_rate,
            "strategy_loss": avg_strategy_loss,
            "avg_predicted_cards": avg_predicted_cards,
            "avg_true_cards": avg_true_cards,
            "prediction_ratio": prediction_ratio,
            "learning_rate": scheduler.get_last_lr()[0],
            "epoch_time": epoch_time
        }
        training_history.append(epoch_info)
        
        # 打印进度
        logger.info(
            f"Epoch {epoch+1:3d}/{epochs} | "
            f"Loss: {avg_loss:.4f} | "
            f"精确匹配: {avg_exact_match_rate:.3f} | "
            f"预测: {avg_predicted_cards:.1f} | "
            f"真实: {avg_true_cards:.1f} | "
            f"比例: {prediction_ratio:.2f}x | "
            f"LR: {scheduler.get_last_lr()[0]:.6f}"
        )
        
        # 早停检查（基于精确匹配率）
        if avg_exact_match_rate > best_exact_match_rate:
            best_exact_match_rate = avg_exact_match_rate
            patience_counter = 0
            
            # 保存最佳模型
            torch.save({
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'epoch': epoch + 1,
                'loss': avg_loss,
                'exact_match_rate': avg_exact_match_rate,
                'training_history': training_history
            }, model_save_path)
            
            logger.info(f"★ 新的最佳精确匹配率: {avg_exact_match_rate:.3f} (目标: >0.30)")
            
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"早停触发，在第 {epoch+1} 轮停止训练")
                logger.info(f"最佳精确匹配率: {best_exact_match_rate:.3f}")
                break
    
    # 保存训练历史
    history_path = model_save_path.replace('.pth', '_training_history.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(training_history, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 70)
    logger.info("Stage 7.3 最终优化训练完成")
    logger.info(f"最佳精确匹配率: {best_exact_match_rate:.3f}")
    logger.info(f"目标达成: {'是' if best_exact_match_rate > 0.30 else '需进一步优化'}")
    logger.info(f"模型保存至: {model_save_path}")
    logger.info(f"训练历史保存至: {history_path}")
    logger.info("=" * 70)
    
    return model, training_history


if __name__ == "__main__":
    # 执行Stage 7.3最终优化训练
    model, history = train_stage7_final_optimized_model(
        epochs=80,
        batch_size=24,
        learning_rate=0.00008
    )