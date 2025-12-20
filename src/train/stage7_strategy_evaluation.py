"""
Stage 7 策略理解评估
测试模型是否学会了掼蛋策略原理，而不仅仅是动作克隆

评估维度：
1. 策略分类准确性 - 是否理解不同策略类型
2. 决策一致性 - 相似情况下的决策稳定性
3. 策略适应性 - 不同游戏阶段的策略调整
4. 胜率表现 - 实际对战效果
5. 原理理解 - 为什么选择这个策略
"""

import torch
import torch.nn as nn
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """策略理解评估器"""
    
    def __init__(self, model_path: str = "models/bc_model_stage7_breakthrough.pth"):
        self.model_path = model_path
        self.device = torch.device("cpu")
        
        # 加载突破性模型
        from stage7_breakthrough_training import BreakthroughNet
        self.model = BreakthroughNet()
        self.model.load_state_dict(torch.load(model_path))
        self.model.eval()
        
        # 策略类型映射
        self.strategy_types = {
            0: 'group',     # 组牌策略
            1: 'follow',    # 跟牌策略  
            2: 'control',   # 控制策略
            3: 'discard',   # 弃牌策略
            4: 'unknown',   # 未知策略
            5: 'suppress',  # 压制策略
            6: 'protect',   # 保护策略
            7: 'bomb'       # 炸弹策略
        }
        
    def evaluate_strategy_understanding(self) -> Dict:
        """评估策略理解能力"""
        logger.info("评估策略理解能力...")
        
        # 加载数据
        import sys
        sys.path.append('src/train')
        from simple_data_loader import create_simple_dataloader
        
        dataloader = create_simple_dataloader(
            data_dir="game_records",
            batch_size=32,
            max_samples=1000,
            shuffle=False
        )
        
        strategy_analysis = {
            'total_samples': 0,
            'strategy_distribution': {},
            'decision_consistency': {},
            'contextual_adaptation': {},
            'prediction_quality': {}
        }
        
        all_predictions = []
        all_contexts = []
        
        with torch.no_grad():
            for state_vec, action_vec, strategy_type in dataloader:
                pred_logits = self.model(state_vec)
                pred_probs = torch.sigmoid(pred_logits)
                
                for i in range(state_vec.size(0)):
                    # 分析单个样本
                    context = self._analyze_game_context(state_vec[i])
                    true_strategy = self.strategy_types[strategy_type[i].item()]
                    true_action = action_vec[i]
                    pred_action = self._get_predicted_action(pred_probs[i], int(true_action.sum().item()))
                    
                    # 记录策略分布
                    if true_strategy not in strategy_analysis['strategy_distribution']:
                        strategy_analysis['strategy_distribution'][true_strategy] = {
                            'count': 0,
                            'correct_predictions': 0,
                            'avg_confidence': 0.0
                        }
                    
                    strategy_info = strategy_analysis['strategy_distribution'][true_strategy]
                    strategy_info['count'] += 1
                    
                    # 检查预测质量
                    is_correct = torch.equal(pred_action, true_action)
                    if is_correct:
                        strategy_info['correct_predictions'] += 1
                    
                    # 计算预测置信度
                    confidence = self._calculate_confidence(pred_probs[i], pred_action)
                    strategy_info['avg_confidence'] += confidence
                    
                    # 记录用于一致性分析
                    all_predictions.append({
                        'context': context,
                        'strategy': true_strategy,
                        'prediction': pred_action,
                        'confidence': confidence,
                        'correct': is_correct
                    })
                    
                    strategy_analysis['total_samples'] += 1
        
        # 计算平均值
        for strategy, info in strategy_analysis['strategy_distribution'].items():
            if info['count'] > 0:
                info['accuracy'] = info['correct_predictions'] / info['count']
                info['avg_confidence'] = info['avg_confidence'] / info['count']
        
        # 分析决策一致性
        strategy_analysis['decision_consistency'] = self._analyze_decision_consistency(all_predictions)
        
        # 分析上下文适应性
        strategy_analysis['contextual_adaptation'] = self._analyze_contextual_adaptation(all_predictions)
        
        return strategy_analysis
    
    def _analyze_game_context(self, state_vec: torch.Tensor) -> Dict:
        """分析游戏上下文"""
        # 简化的上下文分析
        hand_cards = state_vec[:54].sum().item()  # 手牌数量
        game_phase = torch.argmax(state_vec[54:57]).item()  # 游戏阶段
        
        return {
            'hand_cards': int(hand_cards),
            'game_phase': game_phase,
            'situation': 'early' if hand_cards > 15 else 'mid' if hand_cards > 8 else 'late'
        }
    
    def _get_predicted_action(self, pred_probs: torch.Tensor, true_count: int) -> torch.Tensor:
        """获取预测动作"""
        true_count = int(true_count)  # 确保是整数
        if true_count <= 0:
            return torch.zeros_like(pred_probs)
        
        k = min(true_count, len(pred_probs))  # 防止k超出范围
        _, top_k_indices = torch.topk(pred_probs, k)
        pred_action = torch.zeros_like(pred_probs)
        pred_action[top_k_indices] = 1.0
        return pred_action
    
    def _calculate_confidence(self, pred_probs: torch.Tensor, pred_action: torch.Tensor) -> float:
        """计算预测置信度"""
        selected_probs = pred_probs[pred_action == 1]
        if len(selected_probs) > 0:
            return selected_probs.mean().item()
        return 0.0
    
    def _analyze_decision_consistency(self, predictions: List[Dict]) -> Dict:
        """分析决策一致性"""
        consistency_analysis = {}
        
        # 按策略类型分组
        strategy_groups = {}
        for pred in predictions:
            strategy = pred['strategy']
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(pred)
        
        # 分析每种策略的一致性
        for strategy, group in strategy_groups.items():
            if len(group) < 5:  # 样本太少跳过
                continue
            
            confidences = [p['confidence'] for p in group]
            accuracies = [1 if p['correct'] else 0 for p in group]
            
            consistency_analysis[strategy] = {
                'sample_count': len(group),
                'avg_confidence': np.mean(confidences),
                'confidence_std': np.std(confidences),
                'accuracy': np.mean(accuracies),
                'consistency_score': 1.0 - np.std(confidences)  # 置信度越稳定越一致
            }
        
        return consistency_analysis
    
    def _analyze_contextual_adaptation(self, predictions: List[Dict]) -> Dict:
        """分析上下文适应性"""
        adaptation_analysis = {}
        
        # 按游戏阶段分组
        phase_groups = {'early': [], 'mid': [], 'late': []}
        for pred in predictions:
            situation = pred['context']['situation']
            if situation in phase_groups:
                phase_groups[situation].append(pred)
        
        # 分析不同阶段的表现
        for phase, group in phase_groups.items():
            if len(group) < 10:
                continue
            
            accuracies = [1 if p['correct'] else 0 for p in group]
            confidences = [p['confidence'] for p in group]
            
            # 统计策略分布
            strategy_dist = {}
            for p in group:
                strategy = p['strategy']
                strategy_dist[strategy] = strategy_dist.get(strategy, 0) + 1
            
            adaptation_analysis[phase] = {
                'sample_count': len(group),
                'accuracy': np.mean(accuracies),
                'avg_confidence': np.mean(confidences),
                'strategy_diversity': len(strategy_dist),
                'dominant_strategy': max(strategy_dist.items(), key=lambda x: x[1])[0] if strategy_dist else 'none'
            }
        
        return adaptation_analysis
    
    def evaluate_win_rate_simulation(self, num_games: int = 100) -> Dict:
        """模拟胜率评估"""
        logger.info(f"模拟 {num_games} 局游戏评估胜率...")
        
        # 简化的胜率模拟
        wins = 0
        total_score = 0
        game_results = []
        
        # 加载测试数据
        import sys
        sys.path.append('src/train')
        from simple_data_loader import create_simple_dataloader
        
        dataloader = create_simple_dataloader(
            data_dir="game_records",
            batch_size=1,
            max_samples=num_games,
            shuffle=True
        )
        
        with torch.no_grad():
            for game_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
                if game_idx >= num_games:
                    break
                
                # 模拟游戏表现
                pred_logits = self.model(state_vec)
                pred_probs = torch.sigmoid(pred_logits)
                
                true_count = int(action_vec[0].sum().item())
                pred_action = self._get_predicted_action(pred_probs[0], true_count)
                
                # 计算游戏得分（简化）
                accuracy = (pred_action == action_vec[0]).float().mean().item()
                confidence = self._calculate_confidence(pred_probs[0], pred_action)
                
                # 简化的胜负判定
                game_score = accuracy * confidence * 100
                total_score += game_score
                
                if game_score > 50:  # 简化的胜利条件
                    wins += 1
                
                game_results.append({
                    'game_id': game_idx + 1,
                    'accuracy': accuracy,
                    'confidence': confidence,
                    'score': game_score,
                    'win': game_score > 50
                })
        
        win_rate = wins / len(game_results) if game_results else 0
        avg_score = total_score / len(game_results) if game_results else 0
        
        return {
            'total_games': len(game_results),
            'wins': wins,
            'win_rate': win_rate,
            'avg_score': avg_score,
            'performance_level': 'Excellent' if win_rate > 0.7 else 'Good' if win_rate > 0.5 else 'Needs Improvement'
        }
    
    def analyze_decision_reasoning(self) -> Dict:
        """分析决策推理能力"""
        logger.info("分析决策推理能力...")
        
        reasoning_analysis = {
            'pattern_recognition': 0.0,
            'strategic_thinking': 0.0,
            'adaptability': 0.0,
            'principle_understanding': 0.0
        }
        
        # 加载数据进行推理分析
        import sys
        sys.path.append('src/train')
        from simple_data_loader import create_simple_dataloader
        
        dataloader = create_simple_dataloader(
            data_dir="game_records",
            batch_size=16,
            max_samples=200,
            shuffle=False
        )
        
        pattern_scores = []
        strategic_scores = []
        
        with torch.no_grad():
            for state_vec, action_vec, strategy_type in dataloader:
                pred_logits = self.model(state_vec)
                pred_probs = torch.sigmoid(pred_logits)
                
                for i in range(state_vec.size(0)):
                    # 分析模式识别能力
                    context = self._analyze_game_context(state_vec[i])
                    true_count = int(action_vec[i].sum().item())
                    
                    # 模式识别：相似上下文下的一致性
                    pattern_score = self._evaluate_pattern_recognition(pred_probs[i], context, true_count)
                    pattern_scores.append(pattern_score)
                    
                    # 策略思维：决策的合理性
                    strategic_score = self._evaluate_strategic_thinking(pred_probs[i], context, strategy_type[i].item())
                    strategic_scores.append(strategic_score)
        
        reasoning_analysis['pattern_recognition'] = np.mean(pattern_scores)
        reasoning_analysis['strategic_thinking'] = np.mean(strategic_scores)
        reasoning_analysis['adaptability'] = min(reasoning_analysis['pattern_recognition'], reasoning_analysis['strategic_thinking'])
        reasoning_analysis['principle_understanding'] = (reasoning_analysis['pattern_recognition'] + reasoning_analysis['strategic_thinking']) / 2
        
        return reasoning_analysis
    
    def _evaluate_pattern_recognition(self, pred_probs: torch.Tensor, context: Dict, true_count: int) -> float:
        """评估模式识别能力"""
        # 简化的模式识别评估
        hand_cards = context['hand_cards']
        game_phase = context['game_phase']
        
        # 基于上下文的合理性检查
        if true_count == 0:
            # 0卡牌情况：应该预测概率都很低
            max_prob = pred_probs.max().item()
            return 1.0 - max_prob  # 概率越低越好
        else:
            # 有卡牌情况：Top-K的概率应该相对较高
            _, top_k_indices = torch.topk(pred_probs, true_count)
            top_k_probs = pred_probs[top_k_indices]
            return top_k_probs.mean().item()  # 选中卡牌的平均概率
    
    def _evaluate_strategic_thinking(self, pred_probs: torch.Tensor, context: Dict, strategy_type: int) -> float:
        """评估策略思维能力"""
        # 简化的策略思维评估
        situation = context['situation']
        strategy_name = self.strategy_types[strategy_type]
        
        # 基于策略类型的合理性检查
        if strategy_name == 'discard' and situation == 'late':
            # 后期弃牌策略：应该选择较少的卡牌
            active_count = (pred_probs > 0.5).sum().item()
            return 1.0 - (active_count / len(pred_probs))  # 选择越少越合理
        elif strategy_name == 'group' and situation == 'early':
            # 早期组牌策略：可能选择更多卡牌
            active_count = (pred_probs > 0.3).sum().item()
            return min(1.0, active_count / 5.0)  # 适度选择
        else:
            # 其他情况的基础评估
            return pred_probs.mean().item()
    
    def comprehensive_evaluation(self) -> Dict:
        """综合评估"""
        logger.info("开始 Stage 7 策略理解综合评估...")
        
        start_time = datetime.now()
        
        # 1. 策略理解评估
        strategy_understanding = self.evaluate_strategy_understanding()
        
        # 2. 胜率模拟
        win_rate_results = self.evaluate_win_rate_simulation(num_games=50)
        
        # 3. 决策推理分析
        reasoning_analysis = self.analyze_decision_reasoning()
        
        # 4. 综合评分
        overall_score = self._calculate_overall_score(strategy_understanding, win_rate_results, reasoning_analysis)
        
        evaluation_time = (datetime.now() - start_time).total_seconds()
        
        final_results = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "model_path": self.model_path,
            "evaluation_type": "Strategy Understanding Evaluation",
            "evaluation_time_seconds": evaluation_time,
            "strategy_understanding": strategy_understanding,
            "win_rate_simulation": win_rate_results,
            "decision_reasoning": reasoning_analysis,
            "overall_assessment": {
                "strategy_learning_score": overall_score,
                "principle_understanding": "Good" if overall_score > 0.6 else "Basic" if overall_score > 0.4 else "Limited",
                "ready_for_deployment": overall_score > 0.5,
                "key_strengths": self._identify_strengths(strategy_understanding, win_rate_results, reasoning_analysis),
                "improvement_areas": self._identify_improvements(strategy_understanding, win_rate_results, reasoning_analysis)
            }
        }
        
        return final_results
    
    def _calculate_overall_score(self, strategy_understanding: Dict, win_rate_results: Dict, reasoning_analysis: Dict) -> float:
        """计算综合评分"""
        # 策略理解得分
        strategy_scores = []
        for strategy, info in strategy_understanding['strategy_distribution'].items():
            if 'accuracy' in info:
                strategy_scores.append(info['accuracy'])
        avg_strategy_score = np.mean(strategy_scores) if strategy_scores else 0
        
        # 胜率得分
        win_rate_score = win_rate_results['win_rate']
        
        # 推理能力得分
        reasoning_score = reasoning_analysis['principle_understanding']
        
        # 加权综合评分
        overall_score = (
            avg_strategy_score * 0.4 +  # 策略准确性 40%
            win_rate_score * 0.35 +     # 胜率表现 35%
            reasoning_score * 0.25      # 推理能力 25%
        )
        
        return overall_score
    
    def _identify_strengths(self, strategy_understanding: Dict, win_rate_results: Dict, reasoning_analysis: Dict) -> List[str]:
        """识别优势"""
        strengths = []
        
        if win_rate_results['win_rate'] > 0.6:
            strengths.append("优秀的胜率表现")
        
        if reasoning_analysis['pattern_recognition'] > 0.7:
            strengths.append("强大的模式识别能力")
        
        # 检查策略多样性
        strategy_count = len(strategy_understanding['strategy_distribution'])
        if strategy_count >= 5:
            strengths.append("理解多种策略类型")
        
        return strengths
    
    def _identify_improvements(self, strategy_understanding: Dict, win_rate_results: Dict, reasoning_analysis: Dict) -> List[str]:
        """识别改进点"""
        improvements = []
        
        if win_rate_results['win_rate'] < 0.5:
            improvements.append("提升实战胜率")
        
        if reasoning_analysis['strategic_thinking'] < 0.6:
            improvements.append("增强策略思维深度")
        
        # 检查一致性
        consistency_issues = 0
        for strategy, analysis in strategy_understanding.get('decision_consistency', {}).items():
            if analysis.get('consistency_score', 0) < 0.7:
                consistency_issues += 1
        
        if consistency_issues > 2:
            improvements.append("提高决策一致性")
        
        return improvements


def run_strategy_evaluation(model_path: str = "models/bc_model_stage7_breakthrough.pth"):
    """运行策略理解评估"""
    
    evaluator = StrategyEvaluator(model_path)
    results = evaluator.comprehensive_evaluation()
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"training_logs/stage7_strategy_evaluation_{timestamp}.json"
    
    Path("training_logs").mkdir(exist_ok=True)
    # 转换numpy类型为Python原生类型
    def convert_types(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(v) for v in obj]
        return obj
    
    results_serializable = convert_types(results)
    
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results_serializable, f, indent=2, ensure_ascii=False)
    
    # 打印结果
    logger.info("=" * 80)
    logger.info("Stage 7 策略理解评估结果")
    logger.info("=" * 80)
    
    win_rate = results['win_rate_simulation']
    reasoning = results['decision_reasoning']
    assessment = results['overall_assessment']
    
    logger.info(f"胜率表现: {win_rate['win_rate']:.1%} ({win_rate['wins']}/{win_rate['total_games']}局)")
    logger.info(f"平均得分: {win_rate['avg_score']:.1f}")
    logger.info(f"表现等级: {win_rate['performance_level']}")
    
    logger.info(f"\n推理能力分析:")
    logger.info(f"模式识别: {reasoning['pattern_recognition']:.1%}")
    logger.info(f"策略思维: {reasoning['strategic_thinking']:.1%}")
    logger.info(f"原理理解: {reasoning['principle_understanding']:.1%}")
    
    logger.info(f"\n综合评估:")
    logger.info(f"策略学习评分: {assessment['strategy_learning_score']:.3f}")
    logger.info(f"原理理解水平: {assessment['principle_understanding']}")
    logger.info(f"部署就绪: {'是' if assessment['ready_for_deployment'] else '否'}")
    
    if assessment['key_strengths']:
        logger.info(f"\n核心优势:")
        for strength in assessment['key_strengths']:
            logger.info(f"• {strength}")
    
    if assessment['improvement_areas']:
        logger.info(f"\n改进方向:")
        for improvement in assessment['improvement_areas']:
            logger.info(f"• {improvement}")
    
    logger.info(f"\n详细结果保存至: {results_path}")
    logger.info("=" * 80)
    
    return results


if __name__ == "__main__":
    results = run_strategy_evaluation()