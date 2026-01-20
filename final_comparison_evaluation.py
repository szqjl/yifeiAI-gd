"""
最终对比评估 - 所有训练方法的综合对比
Stage 7.7 vs 真实胜率导向 vs Stage 8策略学习

评估维度：
1. 完全匹配率
2. 胜率预测能力  
3. 实用性评分
4. 训练效率
"""

import torch
import torch.nn as nn
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 模型架构定义
class BreakthroughNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(512, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 512)
        )
    def forward(self, x):
        return self.net(x)

class RealWinRateNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(512, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU()
        )
        self.action_head = nn.Sequential(nn.Linear(32, 512))
        self.win_rate_head = nn.Sequential(nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1), nn.Sigmoid())
    def forward(self, x):
        features = self.features(x)
        return {'action_logits': self.action_head(features), 'win_rate': self.win_rate_head(features)}

class AdvancedWinRateNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.shared_features = nn.Sequential(
            nn.Linear(512, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.ReLU()
        )
        self.action_branch = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 512))
        self.win_rate_branch = nn.Sequential(
            nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1), nn.Sigmoid()
        )
        self.value_branch = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1), nn.Tanh())
    def forward(self, x):
        shared = self.shared_features(x)
        return {
            'action_logits': self.action_branch(shared),
            'win_rate': self.win_rate_branch(shared),
            'action_value': self.value_branch(shared)
        }

class UltimateWinRateNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(512, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU()
        )
        self.action_head = nn.Sequential(nn.Linear(32, 512))
        self.position_win_rate = nn.Sequential(
            nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1), nn.Sigmoid()
        )
        self.action_value = nn.Sequential(
            nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1), nn.Tanh()
        )
        self.long_term_reward = nn.Sequential(
            nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1), nn.Tanh()
        )
    def forward(self, x):
        features = self.features(x)
        return {
            'action_logits': self.action_head(features),
            'position_win_rate': self.position_win_rate(features),
            'action_value': self.action_value(features),
            'long_term_reward': self.long_term_reward(features)
        }

class StrategyLearningNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(512, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU()
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


def evaluate_model(model, model_name, dataloader):
    """评估单个模型"""
    model.eval()
    
    total_samples = 0
    exact_matches = 0
    win_rate_predictions = []
    
    with torch.no_grad():
        for state_vec, action_vec, _ in dataloader:
            if isinstance(model, BreakthroughNet):
                # Stage 7.7模型
                action_logits = model(state_vec)
                pred_probs = torch.sigmoid(action_logits)
                
            else:
                # 其他模型
                predictions = model(state_vec)
                action_logits = predictions['action_logits']
                pred_probs = torch.sigmoid(action_logits)
                
                # 收集胜率预测
                if 'win_rate' in predictions:
                    win_rate_predictions.extend(predictions['win_rate'].squeeze().tolist())
                elif 'position_win_rate' in predictions:
                    win_rate_predictions.extend(predictions['position_win_rate'].squeeze().tolist())
            
            # 计算完全匹配率
            for i in range(action_vec.size(0)):
                true_count = int(action_vec[i].sum().item())
                
                if true_count == 0:
                    if pred_probs[i].max() < 0.3:
                        exact_matches += 1
                else:
                    _, top_k_indices = torch.topk(pred_probs[i], true_count)
                    pred_action = torch.zeros_like(action_vec[i])
                    pred_action[top_k_indices] = 1.0
                    
                    if torch.equal(pred_action, action_vec[i]):
                        exact_matches += 1
                
                total_samples += 1
    
    match_rate = exact_matches / total_samples
    
    # 胜率预测分析
    win_rate_analysis = {}
    if win_rate_predictions:
        win_rate_analysis = {
            'mean': np.mean(win_rate_predictions),
            'std': np.std(win_rate_predictions),
            'min': np.min(win_rate_predictions),
            'max': np.max(win_rate_predictions)
        }
    
    return {
        'model_name': model_name,
        'match_rate': match_rate,
        'total_samples': total_samples,
        'win_rate_analysis': win_rate_analysis
    }


def final_comparison():
    """最终对比评估"""
    
    logger.info("=" * 80)
    logger.info("最终对比评估 - 所有训练方法综合对比")
    logger.info("=" * 80)
    
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
    
    logger.info(f"评估数据: {len(dataloader.dataset)} 个样本")
    
    # 模型列表
    models_to_evaluate = [
        {
            'name': 'Stage 7.7 突破性模型',
            'path': 'models/bc_model_stage7_breakthrough.pth',
            'class': BreakthroughNet,
            'description': '27.3%匹配率突破，解决预测过度问题'
        },
        {
            'name': '真实胜率导向模型',
            'path': 'models/bc_model_real_win_rate.pth',
            'class': RealWinRateNet,
            'description': '基于szqjl真实比赛胜负结果训练'
        },
        {
            'name': 'Stage 8 策略学习模型',
            'path': 'models/bc_model_stage8_strategy_learning.pth',
            'class': StrategyLearningNet,
            'description': '多任务策略理解学习'
        },
        {
            'name': '先进胜率导向模型',
            'path': 'models/bc_model_advanced_win_rate.pth',
            'class': AdvancedWinRateNet,
            'description': '超越Stage 5的先进胜率导向方法'
        },
        {
            'name': '终极胜率导向模型',
            'path': 'models/bc_model_ultimate_win_rate.pth',
            'class': UltimateWinRateNet,
            'description': 'Stage 7.7架构 + 真实胜负数据，19.2%匹配率'
        }
    ]
    
    results = []
    
    # 评估每个模型
    for model_info in models_to_evaluate:
        try:
            model = model_info['class']()
            checkpoint = torch.load(model_info['path'], map_location='cpu')
            model.load_state_dict(checkpoint['model_state_dict'])
            
            result = evaluate_model(model, model_info['name'], dataloader)
            result['description'] = model_info['description']
            results.append(result)
            
            logger.info(f"✅ {model_info['name']} 评估完成")
            
        except Exception as e:
            logger.warning(f"❌ {model_info['name']} 加载失败: {e}")
            continue
    
    # 结果分析
    logger.info("\n" + "=" * 80)
    logger.info("评估结果对比")
    logger.info("=" * 80)
    
    # 按匹配率排序
    results.sort(key=lambda x: x['match_rate'], reverse=True)
    
    for i, result in enumerate(results, 1):
        logger.info(f"\n{i}. {result['model_name']}")
        logger.info(f"   描述: {result['description']}")
        logger.info(f"   完全匹配率: {result['match_rate']:.1%}")
        
        if result['win_rate_analysis']:
            wr = result['win_rate_analysis']
            logger.info(f"   胜率预测: 均值={wr['mean']:.3f}, 标准差={wr['std']:.3f}")
        else:
            logger.info(f"   胜率预测: 不支持")
    
    # 综合评分
    logger.info(f"\n" + "=" * 50)
    logger.info("综合评分 (匹配率 + 胜率预测能力)")
    logger.info("=" * 50)
    
    for result in results:
        # 综合评分计算
        match_score = result['match_rate']
        
        # 胜率预测评分
        win_rate_score = 0
        if result['win_rate_analysis']:
            wr = result['win_rate_analysis']
            # 评估胜率预测的合理性（均值接近0.5，标准差适中）
            mean_score = 1.0 - abs(wr['mean'] - 0.5) * 2  # 越接近0.5越好
            std_score = min(1.0, wr['std'] * 3)  # 标准差适中
            win_rate_score = (mean_score + std_score) / 2
        
        # 综合评分
        comprehensive_score = match_score * 0.7 + win_rate_score * 0.3
        
        logger.info(f"{result['model_name']}: {comprehensive_score:.3f}")
        logger.info(f"  - 匹配率贡献: {match_score:.3f}")
        logger.info(f"  - 胜率预测贡献: {win_rate_score:.3f}")
    
    # 推荐结论
    logger.info(f"\n" + "=" * 50)
    logger.info("推荐结论")
    logger.info("=" * 50)
    
    if results:
        best_model = results[0]
        logger.info(f"🏆 最佳模型: {best_model['model_name']}")
        logger.info(f"📊 完全匹配率: {best_model['match_rate']:.1%}")
        
        if best_model['match_rate'] > 0.25:
            logger.info("✅ 已达到实用水平，建议部署测试")
        elif best_model['match_rate'] > 0.15:
            logger.info("⚠️ 接近实用水平，可考虑有限部署")
        else:
            logger.info("❌ 需要进一步优化")
        
        # 具体建议
        if best_model['model_name'] == 'Stage 7.7 突破性模型':
            logger.info("💡 建议: Stage 7.7已解决核心技术问题，可直接部署")
        elif '胜率导向' in best_model['model_name']:
            logger.info("💡 建议: 胜率导向方法有潜力，需要更多真实数据")
        else:
            logger.info("💡 建议: 继续优化策略理解能力")
    
    logger.info("=" * 80)
    
    return results


if __name__ == "__main__":
    results = final_comparison()