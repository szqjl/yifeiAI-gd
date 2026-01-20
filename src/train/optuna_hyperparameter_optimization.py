"""
Optuna 超参数优化脚本
用于自动搜索 Stage 7 训练的最优超参数

使用方法:
    python src/train/optuna_hyperparameter_optimization.py --n_trials 50
"""

import optuna
import torch
import logging
from typing import Dict, Any
import argparse
from datetime import datetime

# 导入训练函数
from stage7_optimized_training import train_stage7_optimized_model, OptimizedGuandanNet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def objective(trial: optuna.Trial) -> float:
    """
    Optuna 优化目标函数
    
    Args:
        trial: Optuna trial 对象
        
    Returns:
        优化目标值（预测质量评分，越大越好）
    """
    
    # 1. 超参数搜索空间定义
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
    batch_size = trial.suggest_categorical('batch_size', [16, 32, 64, 128])
    epochs = trial.suggest_int('epochs', 30, 100, step=10)
    
    # 损失函数超参数
    loss_alpha = trial.suggest_float('loss_alpha', 0.01, 0.2, log=True)
    loss_gamma = trial.suggest_float('loss_gamma', 2.0, 6.0)
    over_prediction_penalty = trial.suggest_float('over_prediction_penalty', 1.0, 10.0)
    sparsity_reward = trial.suggest_float('sparsity_reward', 0.5, 5.0)
    
    # 模型超参数
    dropout_rate = trial.suggest_float('dropout_rate', 0.1, 0.6)
    
    # 优化器超参数
    weight_decay = trial.suggest_float('weight_decay', 0.001, 0.1, log=True)
    
    # 损失权重
    action_loss_weight = trial.suggest_float('action_loss_weight', 0.5, 0.9)
    strategy_loss_weight = trial.suggest_float('strategy_loss_weight', 0.05, 0.3)
    threshold_loss_weight = 1.0 - action_loss_weight - strategy_loss_weight
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Trial {trial.number}: 开始优化")
    logger.info(f"超参数: lr={learning_rate:.6f}, batch={batch_size}, epochs={epochs}")
    logger.info(f"损失参数: alpha={loss_alpha:.3f}, gamma={loss_gamma:.2f}")
    logger.info(f"{'='*60}\n")
    
    try:
        # 2. 使用临时模型路径（避免覆盖）
        model_save_path = f"models/bc_model_stage7_optuna_trial_{trial.number}.pth"
        
        # 3. 修改训练函数以支持超参数（需要修改原始函数或创建包装器）
        # 这里我们创建一个简化的训练函数来支持超参数传递
        from stage7_optimized_training import (
            OptimizedGuandanNet, EnhancedFocalLoss
        )
        import torch.nn as nn
        import torch.optim as optim
        from simple_data_loader import create_simple_dataloader
        import time
        
        device = "cpu"
        
        # 加载数据
        dataloader = create_simple_dataloader(
            data_dir="game_records",
            batch_size=batch_size,
            max_samples=2000,  # 优化时使用较少样本以加快速度
            shuffle=True
        )
        
        # 初始化模型（使用优化的dropout）
        model = OptimizedGuandanNet(dropout_rate=dropout_rate).to(device)
        
        # 优化器
        optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
            betas=(0.9, 0.999)
        )
        
        # 学习率调度器
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=15, T_mult=2, eta_min=1e-7
        )
        
        # 损失函数（使用优化的超参数）
        action_criterion = EnhancedFocalLoss(
            alpha=loss_alpha,
            gamma=loss_gamma,
            over_prediction_penalty=over_prediction_penalty,
            sparsity_reward=sparsity_reward
        )
        strategy_criterion = nn.CrossEntropyLoss()
        threshold_criterion = nn.MSELoss()
        
        # 训练循环（简化版，只训练部分epochs用于评估）
        model.train()
        best_score = 0.0
        
        # 只训练部分epochs以加快优化速度
        train_epochs = min(epochs, 20)  # 优化时最多训练20轮
        
        for epoch in range(train_epochs):
            total_loss = 0.0
            total_predicted_cards = 0
            total_true_cards = 0
            batch_count = 0
            
            for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
                state_vec = state_vec.to(device)
                action_vec = action_vec.to(device)
                strategy_type = strategy_type.to(device)
                
                # 前向传播
                action_logits, adaptive_threshold, strategy_logits, sparsity_weight = model(state_vec)
                
                # 计算目标阈值
                true_action_count = action_vec.sum(dim=1).float()
                target_threshold = torch.clamp(true_action_count / (action_vec.size(1) * 2), 0.001, 0.5)
                
                # 计算损失
                action_loss = action_criterion(action_logits, action_vec, adaptive_threshold, sparsity_weight)
                strategy_loss = strategy_criterion(strategy_logits, strategy_type)
                threshold_loss = threshold_criterion(adaptive_threshold.squeeze(), target_threshold)
                
                # 组合损失
                total_batch_loss = (
                    action_loss * action_loss_weight +
                    strategy_loss * strategy_loss_weight +
                    threshold_loss * threshold_loss_weight
                )
                
                # 反向传播
                optimizer.zero_grad()
                total_batch_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.5)
                optimizer.step()
                
                total_loss += total_batch_loss.item()
                
                # 统计预测情况
                with torch.no_grad():
                    pred_probs = torch.sigmoid(action_logits)
                    threshold = adaptive_threshold.squeeze(-1) * sparsity_weight.squeeze(-1)
                    predicted_actions = (pred_probs > threshold.unsqueeze(1)).float()
                    
                    total_predicted_cards += predicted_actions.sum().item()
                    total_true_cards += action_vec.sum().item()
                    batch_count += action_vec.size(0)
            
            scheduler.step()
            
            # 计算预测质量评分
            avg_predicted_cards = total_predicted_cards / batch_count if batch_count > 0 else 0
            avg_true_cards = total_true_cards / batch_count if batch_count > 0 else 0
            avg_loss = total_loss / len(dataloader)
            
            prediction_quality_score = 1.0 / (1.0 + abs(avg_predicted_cards - avg_true_cards))
            combined_score = prediction_quality_score * (1.0 / (1.0 + avg_loss))
            
            # 记录中间结果（用于早停）
            trial.report(combined_score, epoch)
            
            # 检查是否应该提前停止
            if trial.should_prune():
                logger.info(f"Trial {trial.number} 被提前停止（Pruning）")
                raise optuna.TrialPruned()
            
            if combined_score > best_score:
                best_score = combined_score
        
        logger.info(f"Trial {trial.number} 完成，最佳评分: {best_score:.4f}")
        return best_score
        
    except Exception as e:
        logger.error(f"Trial {trial.number} 失败: {e}")
        raise


def optimize_hyperparameters(
    n_trials: int = 50,
    study_name: str = None,
    storage: str = None,
    direction: str = "maximize"
):
    """
    执行超参数优化
    
    Args:
        n_trials: 优化试验次数
        study_name: 研究名称（用于恢复优化）
        storage: 存储路径（SQLite数据库）
        direction: 优化方向（maximize 或 minimize）
    """
    
    if study_name is None:
        study_name = f"stage7_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if storage is None:
        storage = f"sqlite:///optuna_studies/{study_name}.db"
    
    logger.info("=" * 60)
    logger.info("Optuna 超参数优化")
    logger.info("=" * 60)
    logger.info(f"研究名称: {study_name}")
    logger.info(f"试验次数: {n_trials}")
    logger.info(f"优化方向: {direction}")
    logger.info("=" * 60)
    
    # 创建或加载研究
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction=direction,
        load_if_exists=True,
        pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=5)
    )
    
    # 执行优化
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    
    # 输出最佳结果
    logger.info("\n" + "=" * 60)
    logger.info("优化完成！最佳超参数:")
    logger.info("=" * 60)
    for key, value in study.best_params.items():
        logger.info(f"  {key}: {value}")
    logger.info(f"\n最佳评分: {study.best_value:.4f}")
    logger.info("=" * 60)
    
    # 保存结果
    import json
    from pathlib import Path
    
    results_dir = Path("optuna_results")
    results_dir.mkdir(exist_ok=True)
    
    results_file = results_dir / f"{study_name}_best_params.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "best_params": study.best_params,
            "best_value": study.best_value,
            "n_trials": len(study.trials),
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"最佳参数已保存至: {results_file}")
    
    # 可视化优化过程（如果安装了plotly）
    try:
        import plotly
        fig = optuna.visualization.plot_optimization_history(study)
        fig.write_html(str(results_dir / f"{study_name}_optimization_history.html"))
        logger.info(f"优化历史图表已保存至: {results_dir / f'{study_name}_optimization_history.html'}")
    except ImportError:
        logger.info("plotly 未安装，跳过可视化")
    
    return study


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optuna 超参数优化")
    parser.add_argument("--n_trials", type=int, default=50, help="优化试验次数")
    parser.add_argument("--study_name", type=str, default=None, help="研究名称")
    parser.add_argument("--storage", type=str, default=None, help="存储路径（SQLite）")
    
    args = parser.parse_args()
    
    optimize_hyperparameters(
        n_trials=args.n_trials,
        study_name=args.study_name,
        storage=args.storage
    )
