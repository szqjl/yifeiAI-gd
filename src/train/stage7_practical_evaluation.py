"""
Stage 7 实用性评估脚本
基于问题根因分析，重新定义更实用的评估指标

新的评估指标：
1. 有效卡牌匹配率 (只考虑非零位置)
2. 近似匹配率 (允许1-2个位置误差)
3. 卡牌数量准确率 (数量预测准确性)
4. 实用性评分 (综合考虑实际应用价值)
"""

import torch
from torch.utils.data import DataLoader
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class PracticalEvaluator:
    """实用性评估器 - 重新定义评估标准"""
    
    def __init__(self, model_path: str, data_dir: str = "game_records"):
        self.model_path = model_path
        self.data_dir = data_dir
        self.device = torch.device("cpu")
        
        # 尝试加载不同版本的模型
        self.model = self._load_model()
        
    def _load_model(self):
        """智能加载模型（支持多种架构）"""
        try:
            # 首先尝试加载超级优化版本
            from stage7_ultra_optimized_training import UltraOptimizedGuandanNet
            model = UltraOptimizedGuandanNet()
            checkpoint = torch.load(self.model_path, map_location=self.device)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.eval()
            logger.info(f"成功加载超级优化模型: {self.model_path}")
            return model
        except:
            try:
                # 尝试加载基础版本
                from stage7_robust_training import RobustGuandanNet
                model = RobustGuandanNet()
                checkpoint = torch.load(self.model_path, map_location=self.device)
                model.load_state_dict(checkpoint['model_state_dict'])
                model.eval()
                logger.info(f"成功加载基础模型: {self.model_path}")
                return model
            except Exception as e:
                logger.error(f"模型加载失败: {e}")
                raise
    
    def evaluate_practical_metrics(self, num_samples: int = 1000) -> Dict:
        """评估实用性指标"""
        logger.info("评估实用性指标...")
        
        import sys
        sys.path.append('src/train')
        from simple_data_loader import create_simple_dataloader
        
        dataloader = create_simple_dataloader(
            data_dir=self.data_dir,
            batch_size=64,
            max_samples=num_samples,
            shuffle=True
        )
        
        results = {
            "total_samples": 0,
            "traditional_exact_matches": 0,
            "effective_card_matches": 0,
            "approximate_matches_1": 0,  # 允许1个位置误差
            "approximate_matches_2": 0,  # 允许2个位置误差
            "count_exact_matches": 0,
            "count_approximate_matches": 0,  # 数量误差<=1
            "avg_predicted_cards": 0.0,
            "avg_true_cards": 0.0,
            "prediction_ratio": 0.0,
            "card_level_accuracy": 0.0,
            "effective_precision": 0.0,
            "effective_recall": 0.0,
            "practical_score": 0.0
        }
        
        # 统计变量
        total_traditional_exact = 0
        total_effective_matches = 0
        total_approx_1 = 0
        total_approx_2 = 0
        total_count_exact = 0
        total_count_approx = 0
        total_predicted_cards = 0
        total_true_cards = 0
        total_card_matches = 0
        total_cards = 0
        total_effective_precision = 0
        total_effective_recall = 0
        samples_processed = 0
        
        with torch.no_grad():
            for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
                if samples_processed >= num_samples:
                    break
                
                state_vec = state_vec.to(self.device)
                action_vec = action_vec.to(self.device)
                
                # 模型预测（兼容不同架构）
                try:
                    # 超级优化版本
                    action_logits, predicted_count, sparsity_gate, _ = self.model(state_vec)
                except:
                    try:
                        # 基础版本
                        action_logits, adaptive_threshold, _ = self.model(state_vec)
                        predicted_count = torch.sum(torch.sigmoid(action_logits) > adaptive_threshold.unsqueeze(1), dim=1).float()
                    except:
                        # 最简单的预测
                        action_logits = self.model(state_vec)
                        predicted_count = torch.sum(torch.sigmoid(action_logits) > 0.5, dim=1).float()
                
                action_probs = torch.sigmoid(action_logits)
                
                for i in range(action_vec.size(0)):
                    if samples_processed >= num_samples:
                        break
                    
                    # 获取真实数据
                    true_actions = action_vec[i]
                    true_count = int(true_actions.sum().item())
                    pred_count = int(predicted_count[i].item()) if hasattr(predicted_count, 'item') else int(predicted_count[i])
                    
                    # 使用Top-K进行预测
                    k = max(1, min(pred_count, len(action_probs[i])))
                    _, top_k_indices = torch.topk(action_probs[i], k)
                    
                    predicted_actions = torch.zeros_like(true_actions)
                    predicted_actions[top_k_indices] = 1.0
                    
                    # 1. 传统完全匹配
                    if torch.equal(predicted_actions, true_actions):
                        total_traditional_exact += 1
                    
                    # 2. 有效卡牌匹配（只考虑真实有卡牌的位置）
                    true_card_positions = torch.where(true_actions == 1)[0]
                    pred_card_positions = torch.where(predicted_actions == 1)[0]
                    
                    if len(true_card_positions) > 0:
                        # 计算有效卡牌的匹配情况
                        true_set = set(true_card_positions.tolist())
                        pred_set = set(pred_card_positions.tolist())
                        
                        if true_set == pred_set:
                            total_effective_matches += 1
                        
                        # 计算精确率和召回率
                        if len(pred_set) > 0:
                            precision = len(true_set & pred_set) / len(pred_set)
                            total_effective_precision += precision
                        
                        recall = len(true_set & pred_set) / len(true_set)
                        total_effective_recall += recall
                    else:
                        # 如果真实没有卡牌，预测也没有卡牌就算匹配
                        if len(pred_card_positions) == 0:
                            total_effective_matches += 1
                        total_effective_precision += 1.0 if len(pred_card_positions) == 0 else 0.0
                        total_effective_recall += 1.0
                    
                    # 3. 近似匹配（允许少量位置误差）
                    position_errors = (predicted_actions != true_actions).sum().item()
                    if position_errors <= 1:
                        total_approx_1 += 1
                    if position_errors <= 2:
                        total_approx_2 += 1
                    
                    # 4. 数量匹配
                    if pred_count == true_count:
                        total_count_exact += 1
                    if abs(pred_count - true_count) <= 1:
                        total_count_approx += 1
                    
                    # 5. 基础统计
                    total_predicted_cards += pred_count
                    total_true_cards += true_count
                    
                    card_matches = (predicted_actions == true_actions).sum().item()
                    total_card_matches += card_matches
                    total_cards += len(true_actions)
                    
                    samples_processed += 1
        
        # 计算最终指标
        if samples_processed > 0:
            results["total_samples"] = samples_processed
            results["traditional_exact_matches"] = total_traditional_exact
            results["traditional_exact_match_rate"] = total_traditional_exact / samples_processed
            results["effective_card_matches"] = total_effective_matches
            results["effective_card_match_rate"] = total_effective_matches / samples_processed
            results["approximate_match_rate_1"] = total_approx_1 / samples_processed
            results["approximate_match_rate_2"] = total_approx_2 / samples_processed
            results["count_exact_match_rate"] = total_count_exact / samples_processed
            results["count_approximate_match_rate"] = total_count_approx / samples_processed
            results["avg_predicted_cards"] = total_predicted_cards / samples_processed
            results["avg_true_cards"] = total_true_cards / samples_processed
            results["prediction_ratio"] = (total_predicted_cards / total_true_cards) if total_true_cards > 0 else 0
            results["card_level_accuracy"] = total_card_matches / total_cards if total_cards > 0 else 0
            results["effective_precision"] = total_effective_precision / samples_processed
            results["effective_recall"] = total_effective_recall / samples_processed
            
            # 计算实用性评分
            results["practical_score"] = self._calculate_practical_score(results)
        
        return results
    
    def _calculate_practical_score(self, results: Dict) -> float:
        """计算实用性评分"""
        # 权重分配
        weights = {
            'effective_match': 0.3,      # 有效卡牌匹配最重要
            'count_accuracy': 0.25,      # 数量准确性很重要
            'prediction_ratio': 0.2,     # 预测比例控制
            'precision_recall': 0.15,    # 精确率召回率
            'approximate_match': 0.1     # 近似匹配能力
        }
        
        # 各项得分
        effective_score = results["effective_card_match_rate"]
        count_score = results["count_exact_match_rate"]
        ratio_score = max(0, 1.0 - abs(results["prediction_ratio"] - 1.0))  # 越接近1.0越好
        precision_recall_score = (results["effective_precision"] + results["effective_recall"]) / 2
        approx_score = results["approximate_match_rate_2"]
        
        practical_score = (
            effective_score * weights['effective_match'] +
            count_score * weights['count_accuracy'] +
            ratio_score * weights['prediction_ratio'] +
            precision_recall_score * weights['precision_recall'] +
            approx_score * weights['approximate_match']
        )
        
        return practical_score
    
    def comprehensive_practical_evaluation(self) -> Dict:
        """综合实用性评估"""
        logger.info("开始综合实用性评估...")
        
        start_time = time.time()
        
        # 实用性指标评估
        practical_results = self.evaluate_practical_metrics(num_samples=1500)
        
        evaluation_time = time.time() - start_time
        
        final_results = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "model_path": self.model_path,
            "evaluation_type": "Practical Evaluation",
            "evaluation_time_seconds": float(evaluation_time),
            "practical_metrics": practical_results,
            "performance_analysis": {
                "prediction_control": "Excellent" if practical_results["prediction_ratio"] < 2.0 else "Good" if practical_results["prediction_ratio"] < 5.0 else "Needs Improvement",
                "effective_matching": "Excellent" if practical_results["effective_card_match_rate"] > 0.5 else "Good" if practical_results["effective_card_match_rate"] > 0.2 else "Needs Improvement",
                "count_accuracy": "Excellent" if practical_results["count_exact_match_rate"] > 0.7 else "Good" if practical_results["count_exact_match_rate"] > 0.4 else "Needs Improvement",
                "overall_practical_value": "High" if practical_results["practical_score"] > 0.6 else "Medium" if practical_results["practical_score"] > 0.3 else "Low"
            },
            "recommendations": self._generate_recommendations(practical_results)
        }
        
        return final_results
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if results["effective_card_match_rate"] < 0.3:
            recommendations.append("提高有效卡牌匹配率：优化Top-K选择算法，增加位置敏感的损失函数")
        
        if results["count_exact_match_rate"] < 0.5:
            recommendations.append("改进数量预测：增强卡牌数量监督学习，调整数量预测头架构")
        
        if results["prediction_ratio"] > 2.0:
            recommendations.append("控制预测过度：增加稀疏性约束，调整损失函数权重")
        
        if results["effective_precision"] < 0.7:
            recommendations.append("提升预测精确率：减少假阳性预测，优化阈值选择机制")
        
        if results["effective_recall"] < 0.7:
            recommendations.append("提升预测召回率：减少假阴性预测，增强特征提取能力")
        
        if results["practical_score"] > 0.6:
            recommendations.append("模型已达到实用水平，可考虑部署测试")
        
        return recommendations


def run_practical_evaluation(model_path: str = "models/bc_model_stage7_ultra_optimized.pth"):
    """运行实用性评估"""
    
    evaluator = PracticalEvaluator(model_path)
    results = evaluator.comprehensive_practical_evaluation()
    
    # 保存评估结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"training_logs/stage7_practical_evaluation_{timestamp}.json"
    
    Path("training_logs").mkdir(exist_ok=True)
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 打印结果摘要
    logger.info("=" * 80)
    logger.info("Stage 7 实用性评估结果")
    logger.info("=" * 80)
    
    practical = results['practical_metrics']
    analysis = results['performance_analysis']
    
    logger.info(f"评估样本数: {practical['total_samples']}")
    logger.info(f"传统完全匹配率: {practical['traditional_exact_match_rate']:.2%}")
    logger.info(f"有效卡牌匹配率: {practical['effective_card_match_rate']:.2%} ⭐")
    logger.info(f"近似匹配率(±1): {practical['approximate_match_rate_1']:.2%}")
    logger.info(f"近似匹配率(±2): {practical['approximate_match_rate_2']:.2%}")
    logger.info(f"数量精确匹配率: {practical['count_exact_match_rate']:.2%} ⭐")
    logger.info(f"数量近似匹配率: {practical['count_approximate_match_rate']:.2%}")
    logger.info(f"预测比例: {practical['prediction_ratio']:.2f}x")
    logger.info(f"有效精确率: {practical['effective_precision']:.2%}")
    logger.info(f"有效召回率: {practical['effective_recall']:.2%}")
    logger.info(f"实用性评分: {practical['practical_score']:.3f} ⭐")
    
    logger.info(f"\n性能分析:")
    logger.info(f"预测控制: {analysis['prediction_control']}")
    logger.info(f"有效匹配: {analysis['effective_matching']}")
    logger.info(f"数量准确性: {analysis['count_accuracy']}")
    logger.info(f"整体实用价值: {analysis['overall_practical_value']}")
    
    if results['recommendations']:
        logger.info(f"\n改进建议:")
        for i, rec in enumerate(results['recommendations'], 1):
            logger.info(f"{i}. {rec}")
    
    logger.info(f"\n评估结果保存至: {results_path}")
    logger.info("=" * 80)
    
    return results


if __name__ == "__main__":
    # 运行实用性评估
    logging.basicConfig(level=logging.INFO)
    results = run_practical_evaluation()