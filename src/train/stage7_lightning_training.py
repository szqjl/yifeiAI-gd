"""
Stage 7 PyTorch Lightning 版本
使用 PyTorch Lightning 简化训练代码，提供更好的训练管理

优势：
1. 自动混合精度训练
2. 分布式训练支持
3. 自动模型检查点
4. 早停机制
5. 学习率调度
6. 与 wandb 集成
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping, LearningRateMonitor
from pytorch_lightning.loggers import WandbLogger
from typing import Optional, Dict, Any
import logging

# 导入模型和损失函数
from stage7_optimized_training import OptimizedGuandanNet, EnhancedFocalLoss

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GuandanLightningModule(pl.LightningModule):
    """
    掼蛋AI PyTorch Lightning 模块
    """
    
    def __init__(
        self,
        learning_rate: float = 0.00005,
        batch_size: int = 32,
        loss_alpha: float = 0.05,
        loss_gamma: float = 4.0,
        over_prediction_penalty: float = 5.0,
        sparsity_reward: float = 2.0,
        weight_decay: float = 0.02,
        dropout_rate: float = 0.4,
        action_loss_weight: float = 0.8,
        strategy_loss_weight: float = 0.1,
        threshold_loss_weight: float = 0.1,
    ):
        super().__init__()
        self.save_hyperparameters()
        
        # 模型
        self.model = OptimizedGuandanNet(dropout_rate=dropout_rate)
        
        # 损失函数
        self.action_criterion = EnhancedFocalLoss(
            alpha=loss_alpha,
            gamma=loss_gamma,
            over_prediction_penalty=over_prediction_penalty,
            sparsity_reward=sparsity_reward
        )
        self.strategy_criterion = nn.CrossEntropyLoss()
        self.threshold_criterion = nn.MSELoss()
        
        # 损失权重
        self.action_loss_weight = action_loss_weight
        self.strategy_loss_weight = strategy_loss_weight
        self.threshold_loss_weight = threshold_loss_weight
        
        # 训练指标
        self.training_step_outputs = []
        self.validation_step_outputs = []
    
    def forward(self, x):
        """前向传播"""
        return self.model(x)
    
    def training_step(self, batch, batch_idx):
        """训练步骤"""
        state_vec, action_vec, strategy_type = batch
        
        # 前向传播
        action_logits, adaptive_threshold, strategy_logits, sparsity_weight = self.model(state_vec)
        
        # 计算目标阈值
        true_action_count = action_vec.sum(dim=1).float()
        target_threshold = torch.clamp(
            true_action_count / (action_vec.size(1) * 2), 
            0.001, 0.5
        )
        
        # 计算损失
        action_loss = self.action_criterion(
            action_logits, action_vec, adaptive_threshold, sparsity_weight
        )
        strategy_loss = self.strategy_criterion(strategy_logits, strategy_type)
        threshold_loss = self.threshold_criterion(
            adaptive_threshold.squeeze(), target_threshold
        )
        
        # 组合损失
        total_loss = (
            action_loss * self.action_loss_weight +
            strategy_loss * self.strategy_loss_weight +
            threshold_loss * self.threshold_loss_weight
        )
        
        # 计算预测统计
        with torch.no_grad():
            pred_probs = torch.sigmoid(action_logits)
            threshold = adaptive_threshold.squeeze(-1) * sparsity_weight.squeeze(-1)
            predicted_actions = (pred_probs > threshold.unsqueeze(1)).float()
            
            predicted_cards = predicted_actions.sum().item()
            true_cards = action_vec.sum().item()
            prediction_ratio = predicted_cards / true_cards if true_cards > 0 else 0
            
            prediction_quality_score = 1.0 / (1.0 + abs(predicted_cards - true_cards))
        
        # 记录指标
        self.log('train/loss', total_loss, on_step=True, on_epoch=True, prog_bar=True)
        self.log('train/action_loss', action_loss, on_step=True, on_epoch=True)
        self.log('train/strategy_loss', strategy_loss, on_step=True, on_epoch=True)
        self.log('train/threshold_loss', threshold_loss, on_step=True, on_epoch=True)
        self.log('train/predicted_cards', predicted_cards, on_step=True, on_epoch=True)
        self.log('train/true_cards', true_cards, on_step=True, on_epoch=True)
        self.log('train/prediction_ratio', prediction_ratio, on_step=True, on_epoch=True)
        self.log('train/prediction_quality', prediction_quality_score, on_step=True, on_epoch=True)
        
        # 保存输出用于epoch结束时的计算
        self.training_step_outputs.append({
            'loss': total_loss.item(),
            'predicted_cards': predicted_cards,
            'true_cards': true_cards,
            'prediction_quality': prediction_quality_score,
        })
        
        return total_loss
    
    def validation_step(self, batch, batch_idx):
        """验证步骤"""
        state_vec, action_vec, strategy_type = batch
        
        # 前向传播
        action_logits, adaptive_threshold, strategy_logits, sparsity_weight = self.model(state_vec)
        
        # 计算目标阈值
        true_action_count = action_vec.sum(dim=1).float()
        target_threshold = torch.clamp(
            true_action_count / (action_vec.size(1) * 2), 
            0.001, 0.5
        )
        
        # 计算损失
        action_loss = self.action_criterion(
            action_logits, action_vec, adaptive_threshold, sparsity_weight
        )
        strategy_loss = self.strategy_criterion(strategy_logits, strategy_type)
        threshold_loss = self.threshold_criterion(
            adaptive_threshold.squeeze(), target_threshold
        )
        
        total_loss = (
            action_loss * self.action_loss_weight +
            strategy_loss * self.strategy_loss_weight +
            threshold_loss * self.threshold_loss_weight
        )
        
        # 计算预测统计
        with torch.no_grad():
            pred_probs = torch.sigmoid(action_logits)
            threshold = adaptive_threshold.squeeze(-1) * sparsity_weight.squeeze(-1)
            predicted_actions = (pred_probs > threshold.unsqueeze(1)).float()
            
            predicted_cards = predicted_actions.sum().item()
            true_cards = action_vec.sum().item()
            prediction_ratio = predicted_cards / true_cards if true_cards > 0 else 0
            
            prediction_quality_score = 1.0 / (1.0 + abs(predicted_cards - true_cards))
        
        # 记录指标
        self.log('val/loss', total_loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log('val/action_loss', action_loss, on_step=False, on_epoch=True)
        self.log('val/prediction_quality', prediction_quality_score, on_step=False, on_epoch=True)
        self.log('val/prediction_ratio', prediction_ratio, on_step=False, on_epoch=True)
        
        self.validation_step_outputs.append({
            'loss': total_loss.item(),
            'predicted_cards': predicted_cards,
            'true_cards': true_cards,
            'prediction_quality': prediction_quality_score,
        })
        
        return total_loss
    
    def on_train_epoch_end(self):
        """训练epoch结束时的处理"""
        # 计算epoch级别的指标
        if self.training_step_outputs:
            avg_predicted = sum(o['predicted_cards'] for o in self.training_step_outputs) / len(self.training_step_outputs)
            avg_true = sum(o['true_cards'] for o in self.training_step_outputs) / len(self.training_step_outputs)
            avg_quality = sum(o['prediction_quality'] for o in self.training_step_outputs) / len(self.training_step_outputs)
            
            self.log('train/epoch_predicted_cards', avg_predicted, on_epoch=True)
            self.log('train/epoch_true_cards', avg_true, on_epoch=True)
            self.log('train/epoch_prediction_quality', avg_quality, on_epoch=True)
            
            self.training_step_outputs.clear()
    
    def on_validation_epoch_end(self):
        """验证epoch结束时的处理"""
        if self.validation_step_outputs:
            avg_predicted = sum(o['predicted_cards'] for o in self.validation_step_outputs) / len(self.validation_step_outputs)
            avg_true = sum(o['true_cards'] for o in self.validation_step_outputs) / len(self.validation_step_outputs)
            avg_quality = sum(o['prediction_quality'] for o in self.validation_step_outputs) / len(self.validation_step_outputs)
            
            self.log('val/epoch_predicted_cards', avg_predicted, on_epoch=True)
            self.log('val/epoch_true_cards', avg_true, on_epoch=True)
            self.log('val/epoch_prediction_quality', avg_quality, on_epoch=True)
            
            self.validation_step_outputs.clear()
    
    def configure_optimizers(self):
        """配置优化器和学习率调度器"""
        optimizer = optim.AdamW(
            self.parameters(),
            lr=self.hparams.learning_rate,
            weight_decay=self.hparams.weight_decay,
            betas=(0.9, 0.999)
        )
        
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=15, T_mult=2, eta_min=1e-7
        )
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "interval": "epoch",
                "frequency": 1,
            }
        }


def train_with_lightning(
    data_dir: str = "game_records",
    model_save_dir: str = "models/lightning_checkpoints",
    max_epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 0.00005,
    use_wandb: bool = True,
    wandb_project: str = "yifei-ai-gd",
    wandb_name: str = None,
    accelerator: str = "cpu",
    devices: int = 1,
    precision: str = "32",  # "16" for mixed precision
    num_workers: int = 0,
    **model_kwargs
):
    """
    使用 PyTorch Lightning 训练模型
    
    Args:
        data_dir: 数据目录
        model_save_dir: 模型保存目录
        max_epochs: 最大训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        use_wandb: 是否使用 wandb
        wandb_project: wandb 项目名称
        wandb_name: wandb 运行名称
        accelerator: 加速器类型（cpu, gpu, cuda等）
        devices: 设备数量
        precision: 精度（32, 16, bf16）
        num_workers: 数据加载器工作进程数
        **model_kwargs: 传递给模型的额外参数
    """
    
    from simple_data_loader import create_simple_dataloader
    from datetime import datetime
    
    logger.info("=" * 60)
    logger.info("Stage 7 PyTorch Lightning 训练")
    logger.info("=" * 60)
    
    # 加载数据
    logger.info("加载训练数据...")
    train_dataloader = create_simple_dataloader(
        data_dir=data_dir,
        batch_size=batch_size,
        max_samples=5000,
        shuffle=True
    )
    
    # 创建验证集（使用部分训练数据）
    val_dataloader = create_simple_dataloader(
        data_dir=data_dir,
        batch_size=batch_size,
        max_samples=1000,
        shuffle=False
    )
    
    logger.info(f"训练样本数: {len(train_dataloader.dataset)}")
    logger.info(f"验证样本数: {len(val_dataloader.dataset)}")
    
    # 创建 Lightning 模块
    model = GuandanLightningModule(
        learning_rate=learning_rate,
        batch_size=batch_size,
        **model_kwargs
    )
    
    # 配置日志记录器
    loggers = []
    if use_wandb:
        try:
            if wandb_name is None:
                wandb_name = f"stage7_lightning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            wandb_logger = WandbLogger(
                project=wandb_project,
                name=wandb_name,
                log_model=True,  # 自动记录模型
            )
            loggers.append(wandb_logger)
            logger.info(f"✅ Wandb 日志记录器已配置: {wandb_project}/{wandb_name}")
        except ImportError:
            logger.warning("⚠️ Wandb 未安装，跳过 wandb 日志记录")
    
    # 配置回调函数
    callbacks = [
        # 模型检查点（保存最佳模型）
        ModelCheckpoint(
            dirpath=model_save_dir,
            filename='best-{epoch:02d}-{val/prediction_quality:.4f}',
            monitor='val/prediction_quality',
            mode='max',
            save_top_k=3,
            save_last=True,
            verbose=True,
        ),
        
        # 早停机制
        EarlyStopping(
            monitor='val/prediction_quality',
            mode='max',
            patience=15,
            min_delta=0.001,
            verbose=True,
        ),
        
        # 学习率监控
        LearningRateMonitor(logging_interval='epoch'),
    ]
    
    # 创建训练器
    trainer = pl.Trainer(
        max_epochs=max_epochs,
        accelerator=accelerator,
        devices=devices,
        precision=precision,
        callbacks=callbacks,
        logger=loggers,
        log_every_n_steps=10,
        enable_progress_bar=True,
        enable_model_summary=True,
        gradient_clip_val=0.5,  # 梯度裁剪
        gradient_clip_algorithm="norm",
    )
    
    # 开始训练
    logger.info("开始训练...")
    trainer.fit(
        model=model,
        train_dataloaders=train_dataloader,
        val_dataloaders=val_dataloader,
    )
    
    logger.info("=" * 60)
    logger.info("训练完成！")
    logger.info(f"最佳模型保存在: {model_save_dir}")
    logger.info("=" * 60)
    
    return model, trainer


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PyTorch Lightning 训练脚本")
    parser.add_argument("--data_dir", type=str, default="game_records", help="数据目录")
    parser.add_argument("--model_save_dir", type=str, default="models/lightning_checkpoints", help="模型保存目录")
    parser.add_argument("--max_epochs", type=int, default=100, help="最大训练轮数")
    parser.add_argument("--batch_size", type=int, default=32, help="批次大小")
    parser.add_argument("--learning_rate", type=float, default=0.00005, help="学习率")
    parser.add_argument("--use_wandb", action="store_true", help="使用 wandb")
    parser.add_argument("--wandb_project", type=str, default="yifei-ai-gd", help="wandb 项目名称")
    parser.add_argument("--wandb_name", type=str, default=None, help="wandb 运行名称")
    parser.add_argument("--accelerator", type=str, default="cpu", help="加速器类型")
    parser.add_argument("--devices", type=int, default=1, help="设备数量")
    parser.add_argument("--precision", type=str, default="32", help="精度（32, 16, bf16）")
    
    args = parser.parse_args()
    
    train_with_lightning(
        data_dir=args.data_dir,
        model_save_dir=args.model_save_dir,
        max_epochs=args.max_epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        use_wandb=args.use_wandb,
        wandb_project=args.wandb_project,
        wandb_name=args.wandb_name,
        accelerator=args.accelerator,
        devices=args.devices,
        precision=args.precision,
    )
