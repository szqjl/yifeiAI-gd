"""
Stage 7 评估脚本
专门针对稳定性和预测准确性的综合评估
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

from stage7_robust_training import RobustGuandanNet

logger = logging.getLogger(__name__)


class Stage7Evaluator:
    """Stage 7 模型评估器"""
    
    def __init__(self, model_path: str, data_dir: str = "game_records"):
        self.model_path = model_path
        self.data_dir = data_dir
        self.device = torch.device("cpu")
        
        # 加载模型
        self.model = self._load_model()
        
    def _load_model(self):
        """加载训练好的模型"""
        model = RobustGuandanNet()
        
        try:
            checkpoint = torch.load(self.model_path, map_location=self.device)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.eval()
            logger.info(f"模型加载成功: {self.model_path}")
            return model
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
    
    def evaluate_prediction_accuracy(self, num_samples: int = 1000) -> Dict:
        """评估预测准确性"""
        logger.info("评估预测准确性...")
        
        from simple_data_loader import create_simple_dataloader
        
        dataloader = create_simple_dataloader(
            data_dir=self.data_dir,
            batch_size=64,
            max_samples=num_samples,
            shuffle=True
        )
        
        results = {
            "total_samples": 0,
            "exact_matches": 0,
            "card_level_accuracy": 0.0,
            "avg_predicted_cards": 0.0,
            "avg_true_cards": 0.0,
            "over_prediction_ratio": 0.0,
            "under_prediction_ratio": 0.0,
            "threshold_accuracy": 0.0
        }
        
        total_exact_matches = 0
        total_card_matches = 0
        total_cards = 0
        total_predicted_cards = 0
        total_true_cards = 0
        over_predictions = 0
        under_predictions = 0
        threshold_errors = []
        
        samples_processed = 0
        
        with torch.no_grad():
            for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
                if samples_processed >= num_samples:
                    break
                
                state_vec = state_vec.to(self.device)
                action_vec = action_vec.to(self.device)
                
                # 模型预测
                action_logits, adaptive_threshold, _ = self.model(state_vec)
                
                # 使用自适应阈值进行预测
                action_probs = torch.sigmoid(action_logits)
                threshold = adaptive_threshold.squeeze(-1)
                
                for i in range(action_vec.size(0)):
                    if samples_processed >= num_samples:
                        break
                    
                    # 单个样本的预测和真实值
                    pred_probs = action_probs[i]
                    true_actions = action_vec[i]
                    sample_threshold = threshold[i].item()
                    
                    # 使用自适应阈值进行预测
                    predicted_actions = (pred_probs > sample_threshold).float()
                    
                    # 计算指标
                    exact_match = torch.equal(predicted_actions, true_actions)
                    if exact_match:
                        total_exact_matches += 1
                    
                    # 卡牌级别准确性
                    card_matches = (predicted_actions == true_actions).sum().item()
                    total_card_matches += card_matches
                    total_cards += len(true_actions)
                    
                    # 预测卡牌数量
                    pred_count = predicted_actions.sum().item()
                    true_count = true_actions.sum().item()
                    
                    total_predicted_cards += pred_count
                    total_true_cards += true_count
                    
                    # 过度/不足预测
                    if pred_count > true_count:
                        over_predictions += 1
                    elif pred_count < true_count:
                        under_predictions += 1
                    
                    # 阈值准确性（理想阈值 vs 预测阈值）
                    ideal_threshold = true_count / len(true_actions) if len(true_actions) > 0 else 0
                    threshold_error = abs(sample_threshold - ideal_threshold)
                    threshold_errors.append(threshold_error)
                    
                    samples_processed += 1
        
        # 计算最终指标
        results["total_samples"] = samples_processed
        results["exact_matches"] = total_exact_matches
        results["exact_match_rate"] = total_exact_matches / samples_processed
        results["card_level_accuracy"] = total_card_matches / total_cards
        results["avg_predicted_cards"] = total_predicted_cards / samples_processed
        results["avg_true_cards"] = total_true_cards / samples_processed
        results["over_prediction_ratio"] = over_predictions / samples_processed
        results["under_prediction_ratio"] = under_predictions / samples_processed
        results["threshold_accuracy"] = 1.0 - np.mean(threshold_errors)
        
        return results
    
    def evaluate_stability(self, num_rounds: int = 10, samples_per_round: int = 100) -> Dict:
        """评估模型稳定性"""
        logger.info(f"评估模型稳定性 ({num_rounds} 轮)...")
        
        from simple_data_loader import create_simple_dataloader
        
        # 创建完整数据集用于稳定性测试
        full_dataloader = create_simple_dataloader(
            data_dir=self.data_dir,
            batch_size=32,
            max_samples=num_rounds * samples_per_round * 2,  # 确保有足够的数据
            shuffle=False
        )
        dataset = full_dataloader.dataset
        
        round_results = []
        
        for round_idx in range(num_rounds):
            logger.info(f"稳定性测试 - 第 {round_idx + 1}/{num_rounds} 轮")
            
            # 每轮使用不同的数据子集
            start_idx = (round_idx * samples_per_round) % len(dataset)
            end_idx = min(start_idx + samples_per_round, len(dataset))
            
            subset_indices = list(range(start_idx, end_idx))
            subset = torch.utils.data.Subset(dataset, subset_indices)
            dataloader = DataLoader(subset, batch_size=32, shuffle=False)
            
            round_metrics = self._evaluate_round(dataloader)
            round_results.append({
                "round": round_idx + 1,
                "exact_match_rate": round_metrics["exact_match_rate"],
                "card_accuracy": round_metrics["card_accuracy"],
                "avg_predicted_cards": round_metrics["avg_predicted_cards"],
                "samples": len(subset)
            })
        
        # 计算稳定性指标
        exact_match_rates = [r["exact_match_rate"] for r in round_results]
        card_accuracies = [r["card_accuracy"] for r in round_results]
        
        stability_metrics = {
            "round_results": round_results,
            "exact_match_stability": {
                "mean": np.mean(exact_match_rates),
                "std": np.std(exact_match_rates),
                "cv": np.std(exact_match_rates) / np.mean(exact_match_rates) if np.mean(exact_match_rates) > 0 else float('inf'),
                "min": np.min(exact_match_rates),
                "max": np.max(exact_match_rates)
            },
            "card_accuracy_stability": {
                "mean": np.mean(card_accuracies),
                "std": np.std(card_accuracies),
                "cv": np.std(card_accuracies) / np.mean(card_accuracies) if np.mean(card_accuracies) > 0 else float('inf'),
                "min": np.min(card_accuracies),
                "max": np.max(card_accuracies)
            },
            "is_stable": bool(np.std(exact_match_rates) < 0.05 and np.std(card_accuracies) < 0.02)
        }
        
        return stability_metrics
    
    def _evaluate_round(self, dataloader) -> Dict:
        """评估单轮性能"""
        total_samples = 0
        exact_matches = 0
        card_matches = 0
        total_cards = 0
        total_predicted_cards = 0
        
        with torch.no_grad():
            for state_vec, action_vec, _ in dataloader:
                state_vec = state_vec.to(self.device)
                action_vec = action_vec.to(self.device)
                
                action_logits, adaptive_threshold, _ = self.model(state_vec)
                action_probs = torch.sigmoid(action_logits)
                threshold = adaptive_threshold.squeeze(-1)
                
                for i in range(action_vec.size(0)):
                    pred_probs = action_probs[i]
                    true_actions = action_vec[i]
                    sample_threshold = threshold[i].item()
                    
                    predicted_actions = (pred_probs > sample_threshold).float()
                    
                    if torch.equal(predicted_actions, true_actions):
                        exact_matches += 1
                    
                    card_matches += (predicted_actions == true_actions).sum().item()
                    total_cards += len(true_actions)
                    total_predicted_cards += predicted_actions.sum().item()
                    total_samples += 1
        
        return {
            "exact_match_rate": exact_matches / total_samples if total_samples > 0 else 0,
            "card_accuracy": card_matches / total_cards if total_cards > 0 else 0,
            "avg_predicted_cards": total_predicted_cards / total_samples if total_samples > 0 else 0
        }
    
    def comprehensive_evaluation(self) -> Dict:
        """综合评估"""
        logger.info("开始 Stage 7 综合评估...")
        
        start_time = time.time()
        
        # 1. 预测准确性评估
        accuracy_results = self.evaluate_prediction_accuracy(num_samples=2000)
        
        # 2. 稳定性评估
        stability_results = self.evaluate_stability(num_rounds=10, samples_per_round=200)
        
        # 3. 综合评分
        comprehensive_score = self._calculate_comprehensive_score(
            accuracy_results, stability_results
        )
        
        evaluation_time = time.time() - start_time
        
        final_results = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "model_path": self.model_path,
            "evaluation_time_seconds": float(evaluation_time),
            "accuracy_evaluation": accuracy_results,
            "stability_evaluation": stability_results,
            "comprehensive_score": float(comprehensive_score),
            "summary": {
                "is_improved": bool(comprehensive_score > 0.6),
                "is_stable": stability_results["is_stable"],
                "prediction_quality": "Good" if accuracy_results["exact_match_rate"] > 0.3 else "Needs Improvement",
                "overall_pass": bool(comprehensive_score > 0.6 and stability_results["is_stable"])
            }
        }
        
        return final_results
    
    def _calculate_comprehensive_score(self, accuracy_results: Dict, stability_results: Dict) -> float:
        """计算综合评分"""
        # 准确性权重 (40%)
        accuracy_score = (
            accuracy_results["exact_match_rate"] * 0.5 +
            accuracy_results["card_level_accuracy"] * 0.3 +
            accuracy_results["threshold_accuracy"] * 0.2
        )
        
        # 稳定性权重 (30%)
        stability_score = 1.0 / (1.0 + stability_results["exact_match_stability"]["cv"])
        
        # 预测质量权重 (30%)
        prediction_quality = 1.0 - min(1.0, accuracy_results["over_prediction_ratio"])
        
        comprehensive_score = (
            accuracy_score * 0.4 +
            stability_score * 0.3 +
            prediction_quality * 0.3
        )
        
        return comprehensive_score


def run_stage7_evaluation(model_path: str = "models/bc_model_stage7_robust.pth"):
    """运行 Stage 7 评估"""
    
    evaluator = Stage7Evaluator(model_path)
    results = evaluator.comprehensive_evaluation()
    
    # 保存评估结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"training_logs/stage7_evaluation_{timestamp}.json"
    
    Path("training_logs").mkdir(exist_ok=True)
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 打印结果摘要
    logger.info("=" * 60)
    logger.info("Stage 7 评估结果摘要")
    logger.info("=" * 60)
    logger.info(f"完全匹配率: {results['accuracy_evaluation']['exact_match_rate']:.2%}")
    logger.info(f"卡牌级准确率: {results['accuracy_evaluation']['card_level_accuracy']:.2%}")
    logger.info(f"平均预测卡牌数: {results['accuracy_evaluation']['avg_predicted_cards']:.1f}")
    logger.info(f"平均真实卡牌数: {results['accuracy_evaluation']['avg_true_cards']:.1f}")
    logger.info(f"阈值准确性: {results['accuracy_evaluation']['threshold_accuracy']:.2%}")
    logger.info(f"稳定性: {'通过' if results['stability_evaluation']['is_stable'] else '需改进'}")
    logger.info(f"综合评分: {results['comprehensive_score']:.3f}")
    logger.info(f"整体评价: {'通过' if results['summary']['overall_pass'] else '需改进'}")
    logger.info(f"评估结果保存至: {results_path}")
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    # 运行评估
    results = run_stage7_evaluation()