"""
Stage 8 策略理解评估
测试模型是否真正从动作克隆转向策略理解
"""

import torch
import torch.nn as nn
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyLearningNet(nn.Module):
    """Stage 8 策略学习网络（复制架构用于加载）"""
    
    def __init__(self):
        super().__init__()
        
        self.features = nn.Sequential(
            nn.Linear(512, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        
        self.action_head = nn.Sequential(nn.Linear(32, 512))
        self.strategy_head = nn.Sequential(nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 8))
        self.reason_head = nn.Sequential(nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 26))
        self.win_rate_head = nn.Sequential(nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1), nn.Sigmoid())
        self.effectiveness_head = nn.Sequential(nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1), nn.Sigmoid())
        
    def forward(self, x):
        features = self.features(x)
        return {
            'action_logits': self.action_head(features),
            'strategy_logits': self.strategy_head(features),
            'reason_logits': self.reason_head(features),
            'win_rate': self.win_rate_head(features),
            'effectiveness': self.effectiveness_head(features)
        }


def evaluate_strategy_understanding():
    """评估策略理解能力"""
    
    # 加载Stage 8模型
    model = StrategyLearningNet()
    try:
        checkpoint = torch.load("models/bc_model_stage8_strategy_learning.pth")
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        logger.info("Stage 8模型加载成功")
    except:
        logger.error("Stage 8模型加载失败")
        return
    
    # 加载对比模型（Stage 7.7）
    import sys
    sys.path.append('src/train')
    from stage7_breakthrough_training import BreakthroughNet
    stage7_model = BreakthroughNet()
    stage7_model.load_state_dict(torch.load("models/bc_model_stage7_breakthrough.pth"))
    stage7_model.eval()
    
    # 加载数据
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=32,
        max_samples=500,
        shuffle=False
    )
    
    # 评估指标
    stage8_results = {
        'exact_matches': 0,
        'strategy_predictions': [],
        'win_rate_predictions': [],
        'effectiveness_predictions': [],
        'total_samples': 0
    }
    
    stage7_results = {
        'exact_matches': 0,
        'total_samples': 0
    }
    
    with torch.no_grad():
        for state_vec, action_vec, strategy_type in dataloader:
            # Stage 8预测
            stage8_pred = model(state_vec)
            stage8_action_probs = torch.sigmoid(stage8_pred['action_logits'])
            
            # Stage 7预测
            stage7_logits = stage7_model(state_vec)
            stage7_probs = torch.sigmoid(stage7_logits)
            
            for i in range(action_vec.size(0)):
                true_action = action_vec[i]
                true_count = int(true_action.sum().item())
                
                # Stage 8评估
                if true_count == 0:
                    if stage8_action_probs[i].max() < 0.3:
                        stage8_results['exact_matches'] += 1
                else:
                    _, top_k_indices = torch.topk(stage8_action_probs[i], true_count)
                    pred_action = torch.zeros_like(true_action)
                    pred_action[top_k_indices] = 1.0
                    
                    if torch.equal(pred_action, true_action):
                        stage8_results['exact_matches'] += 1
                
                # 收集策略理解指标
                stage8_results['strategy_predictions'].append(
                    torch.softmax(stage8_pred['strategy_logits'][i], dim=0).numpy()
                )
                stage8_results['win_rate_predictions'].append(
                    stage8_pred['win_rate'][i].item()
                )
                stage8_results['effectiveness_predictions'].append(
                    stage8_pred['effectiveness'][i].item()
                )
                stage8_results['total_samples'] += 1
                
                # Stage 7评估
                if true_count == 0:
                    if stage7_probs[i].max() < 0.3:
                        stage7_results['exact_matches'] += 1
                else:
                    _, top_k_indices = torch.topk(stage7_probs[i], true_count)
                    pred_action = torch.zeros_like(true_action)
                    pred_action[top_k_indices] = 1.0
                    
                    if torch.equal(pred_action, true_action):
                        stage7_results['exact_matches'] += 1
                
                stage7_results['total_samples'] += 1
    
    # 计算结果
    stage8_match_rate = stage8_results['exact_matches'] / stage8_results['total_samples']
    stage7_match_rate = stage7_results['exact_matches'] / stage7_results['total_samples']
    
    # 策略理解分析
    strategy_diversity = np.std(stage8_results['strategy_predictions'])
    win_rate_variance = np.var(stage8_results['win_rate_predictions'])
    effectiveness_mean = np.mean(stage8_results['effectiveness_predictions'])
    
    logger.info("=" * 60)
    logger.info("Stage 8 vs Stage 7 对比评估")
    logger.info("=" * 60)
    logger.info(f"Stage 8 完全匹配率: {stage8_match_rate:.1%}")
    logger.info(f"Stage 7 完全匹配率: {stage7_match_rate:.1%}")
    logger.info(f"匹配率变化: {(stage8_match_rate - stage7_match_rate):.1%}")
    
    logger.info(f"\nStage 8 策略理解能力:")
    logger.info(f"策略预测多样性: {strategy_diversity:.3f}")
    logger.info(f"胜率预测方差: {win_rate_variance:.3f}")
    logger.info(f"策略有效性均值: {effectiveness_mean:.3f}")
    
    # 综合评估
    strategy_understanding_score = (
        min(1.0, strategy_diversity * 2) * 0.3 +  # 策略多样性
        min(1.0, win_rate_variance * 10) * 0.3 +  # 胜率预测能力
        effectiveness_mean * 0.4  # 策略有效性理解
    )
    
    logger.info(f"\n策略理解综合评分: {strategy_understanding_score:.3f}")
    
    if strategy_understanding_score > 0.6:
        logger.info("🎉 Stage 8成功实现策略理解突破！")
    elif strategy_understanding_score > 0.4:
        logger.info("✅ Stage 8在策略理解方面有所进步")
    else:
        logger.info("❌ Stage 8仍需进一步优化策略理解能力")
    
    # 实用性评估
    if stage8_match_rate > stage7_match_rate and strategy_understanding_score > 0.4:
        logger.info("📈 Stage 8在技术指标和策略理解方面都有提升")
        deployment_ready = True
    else:
        logger.info("🔧 Stage 8需要进一步优化")
        deployment_ready = False
    
    logger.info(f"\n部署就绪: {'是' if deployment_ready else '否'}")
    logger.info("=" * 60)
    
    return {
        'stage8_match_rate': stage8_match_rate,
        'stage7_match_rate': stage7_match_rate,
        'strategy_understanding_score': strategy_understanding_score,
        'deployment_ready': deployment_ready
    }


if __name__ == "__main__":
    results = evaluate_strategy_understanding()