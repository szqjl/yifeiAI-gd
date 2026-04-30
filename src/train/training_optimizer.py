"""
训练框架优化器
根据训练结果自动优化训练框架参数

功能：
1. 分析训练结果
2. 识别问题（过拟合、欠拟合、预测过度等）
3. 自动调整训练参数
4. 生成优化建议
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class TrainingOptimizer:
    """训练框架优化器"""
    
    def __init__(self, training_history_path: str = None):
        """
        初始化优化器
        
        Args:
            training_history_path: 训练历史文件路径
        """
        self.training_history_path = training_history_path
        self.training_history = None
        
        if training_history_path:
            self.load_history(training_history_path)
    
    def load_history(self, history_path: str):
        """加载训练历史"""
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                self.training_history = json.load(f)
            logger.info(f"已加载训练历史: {history_path}")
        except Exception as e:
            logger.error(f"加载训练历史失败: {e}")
            self.training_history = None
    
    def analyze_training_results(self) -> Dict:
        """
        分析训练结果
        
        Returns:
            分析结果字典
        """
        if not self.training_history:
            return {"error": "未加载训练历史"}
        
        epochs = [e['epoch'] for e in self.training_history]
        losses = [e['total_loss'] for e in self.training_history]
        predicted_cards = [e.get('avg_predicted_cards', 0) for e in self.training_history]
        true_cards = [e.get('avg_true_cards', 0) for e in self.training_history]
        
        # 分析损失趋势
        loss_trend = self._analyze_trend(losses)
        
        # 分析预测准确性
        prediction_ratio = [p/t if t > 0 else 0 for p, t in zip(predicted_cards, true_cards)]
        avg_ratio = np.mean(prediction_ratio[-10:]) if len(prediction_ratio) >= 10 else np.mean(prediction_ratio)
        
        # 识别问题
        issues = self._identify_issues(losses, prediction_ratio, avg_ratio)
        
        # 生成优化建议
        recommendations = self._generate_recommendations(issues, loss_trend, avg_ratio)
        
        return {
            "total_epochs": len(epochs),
            "final_loss": losses[-1] if losses else 0,
            "loss_trend": loss_trend,
            "avg_prediction_ratio": avg_ratio,
            "issues": issues,
            "recommendations": recommendations
        }
    
    def _analyze_trend(self, values: List[float]) -> str:
        """分析趋势"""
        if len(values) < 10:
            return "insufficient_data"
        
        recent = values[-10:]
        early = values[:10]
        
        recent_avg = np.mean(recent)
        early_avg = np.mean(early)
        
        if recent_avg < early_avg * 0.9:
            return "decreasing"  # 下降趋势
        elif recent_avg > early_avg * 1.1:
            return "increasing"  # 上升趋势
        else:
            return "stable"  # 稳定
    
    def _identify_issues(
        self, 
        losses: List[float], 
        prediction_ratio: List[float],
        avg_ratio: float
    ) -> List[str]:
        """识别问题"""
        issues = []
        
        # 检查过拟合
        if len(losses) >= 20:
            train_loss = np.mean(losses[-10:])
            if train_loss < 0.01:
                issues.append("可能过拟合：训练损失过低")
        
        # 检查预测过度
        if avg_ratio > 2.0:
            issues.append(f"预测过度：预测卡牌数是真实卡牌数的{avg_ratio:.1f}倍")
        elif avg_ratio < 0.5:
            issues.append(f"预测不足：预测卡牌数只有真实卡牌数的{avg_ratio:.1f}倍")
        
        # 检查损失不收敛
        if len(losses) >= 30:
            recent_std = np.std(losses[-10:])
            if recent_std > np.mean(losses[-10:]) * 0.5:
                issues.append("损失波动大：可能学习率过高或批次大小不合适")
        
        return issues
    
    def _generate_recommendations(
        self, 
        issues: List[str], 
        loss_trend: str,
        avg_ratio: float
    ) -> Dict:
        """生成优化建议"""
        recommendations = {
            "learning_rate": None,
            "batch_size": None,
            "epochs": None,
            "loss_weights": None,
            "other": []
        }
        
        # 根据问题调整学习率
        if "学习率过高" in str(issues) or loss_trend == "increasing":
            recommendations["learning_rate"] = "降低学习率（当前 * 0.5）"
        
        if loss_trend == "stable" and len(issues) > 0:
            recommendations["learning_rate"] = "增加学习率（当前 * 1.5）"
        
        # 根据预测比例调整
        if avg_ratio > 2.0:
            recommendations["loss_weights"] = "增加过度预测惩罚权重（当前 * 1.5）"
            recommendations["other"].append("考虑增加稀疏性正则化")
        elif avg_ratio < 0.5:
            recommendations["loss_weights"] = "降低过度预测惩罚权重（当前 * 0.7）"
            recommendations["other"].append("考虑降低预测阈值")
        
        # 根据损失趋势调整批次大小
        if loss_trend == "increasing":
            recommendations["batch_size"] = "减小批次大小（当前 * 0.8）"
        elif loss_trend == "stable":
            recommendations["batch_size"] = "增加批次大小（当前 * 1.2）"
        
        return recommendations
    
    def optimize_parameters(
        self, 
        current_params: Dict
    ) -> Dict:
        """
        优化训练参数
        
        Args:
            current_params: 当前训练参数
            
        Returns:
            优化后的参数
        """
        analysis = self.analyze_training_results()
        recommendations = analysis.get("recommendations", {})
        
        optimized = current_params.copy()
        
        # 应用学习率建议
        if recommendations.get("learning_rate"):
            if "降低" in recommendations["learning_rate"]:
                optimized["learning_rate"] = current_params.get("learning_rate", 0.00005) * 0.5
            elif "增加" in recommendations["learning_rate"]:
                optimized["learning_rate"] = current_params.get("learning_rate", 0.00005) * 1.5
        
        # 应用批次大小建议
        if recommendations.get("batch_size"):
            if "减小" in recommendations["batch_size"]:
                optimized["batch_size"] = int(current_params.get("batch_size", 32) * 0.8)
            elif "增加" in recommendations["batch_size"]:
                optimized["batch_size"] = int(current_params.get("batch_size", 32) * 1.2)
        
        return optimized


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="训练框架优化器")
    parser.add_argument("--history", type=str, required=True, help="训练历史文件路径")
    parser.add_argument("--optimize", action="store_true", help="生成优化后的参数")
    
    args = parser.parse_args()
    
    optimizer = TrainingOptimizer(args.history)
    analysis = optimizer.analyze_training_results()
    
    print("\n" + "="*60)
    print("训练结果分析")
    print("="*60)
    print(f"训练轮数: {analysis.get('total_epochs', 0)}")
    print(f"最终损失: {analysis.get('final_loss', 0):.4f}")
    print(f"损失趋势: {analysis.get('loss_trend', 'unknown')}")
    print(f"平均预测比例: {analysis.get('avg_prediction_ratio', 0):.2f}")
    
    issues = analysis.get('issues', [])
    if issues:
        print(f"\n识别的问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n未发现明显问题")
    
    recommendations = analysis.get('recommendations', {})
    if recommendations:
        print(f"\n优化建议:")
        for key, value in recommendations.items():
            if value:
                print(f"  {key}: {value}")
    
    print("="*60)
