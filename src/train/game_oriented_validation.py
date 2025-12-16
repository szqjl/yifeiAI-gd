# -*- coding: utf-8 -*-
"""
阶段6：游戏导向训练验证
对比实验和稳定性测试
"""

import os
import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import sys

# 修复Windows控制台编码
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.train.game_oriented_evaluator import GameOrientedEvaluator
from src.knowledge_processor.replay_parser import ReplayParser


class GameOrientedValidator:
    """
    游戏导向训练验证器
    执行对比实验和稳定性测试
    """
    
    def __init__(self):
        self.evaluator = GameOrientedEvaluator()
    
    def compare_models(self, model1_records: List[Dict], model2_records: List[Dict],
                      model1_name: str = "模型1", model2_name: str = "模型2",
                      player_id: int = 0) -> Dict:
        """
        对比两个模型的性能
        
        Args:
            model1_records: 模型1的游戏记录
            model2_records: 模型2的游戏记录
            model1_name: 模型1名称
            model2_name: 模型2名称
            player_id: 玩家ID
            
        Returns:
            对比结果字典
        """
        print("="*60)
        print(f"模型对比: {model1_name} vs {model2_name}")
        print("="*60)
        
        eval1 = self.evaluator.evaluate_model(model1_records, player_id)
        eval2 = self.evaluator.evaluate_model(model2_records, player_id)
        
        # 计算改进幅度
        improvement = {
            'win_rate': eval1['win_rate'] - eval2['win_rate'],
            'strategy_adaptability': eval1['strategy_adaptability'] - eval2['strategy_adaptability'],
            'decision_quality': eval1['decision_quality'] - eval2['decision_quality'],
            'prediction_accuracy': eval1['prediction_accuracy'] - eval2['prediction_accuracy'],
            'total_score': eval1['total_score'] - eval2['total_score']
        }
        
        # 打印对比结果
        print(f"\n{model1_name}:")
        print(f"  胜率: {eval1['win_rate']:.2%} (95% CI: {eval1['win_rate_ci'][0]:.2%} - {eval1['win_rate_ci'][1]:.2%})")
        print(f"  策略适应性: {eval1['strategy_adaptability']:.2%}")
        print(f"  决策质量: {eval1['decision_quality']:.2%}")
        print(f"  预测准确性: {eval1['prediction_accuracy']:.2%}")
        print(f"  综合分数: {eval1['total_score']:.2%}")
        
        print(f"\n{model2_name}:")
        print(f"  胜率: {eval2['win_rate']:.2%} (95% CI: {eval2['win_rate_ci'][0]:.2%} - {eval2['win_rate_ci'][1]:.2%})")
        print(f"  策略适应性: {eval2['strategy_adaptability']:.2%}")
        print(f"  决策质量: {eval2['decision_quality']:.2%}")
        print(f"  预测准确性: {eval2['prediction_accuracy']:.2%}")
        print(f"  综合分数: {eval2['total_score']:.2%}")
        
        print(f"\n改进幅度 ({model1_name} - {model2_name}):")
        print(f"  胜率: {improvement['win_rate']:+.2%}")
        print(f"  策略适应性: {improvement['strategy_adaptability']:+.2%}")
        print(f"  决策质量: {improvement['decision_quality']:+.2%}")
        print(f"  预测准确性: {improvement['prediction_accuracy']:+.2%}")
        print(f"  综合分数: {improvement['total_score']:+.2%}")
        
        return {
            'model1': eval1,
            'model2': eval2,
            'improvement': improvement
        }
    
    def stability_test(self, game_records: List[Dict], player_id: int = 0,
                      num_rounds: int = 10) -> Dict:
        """
        稳定性测试：多轮对局的胜率稳定性
        
        Args:
            game_records: 游戏记录列表
            player_id: 玩家ID
            num_rounds: 测试轮数
            
        Returns:
            稳定性测试结果
        """
        print("="*60)
        print(f"稳定性测试 ({num_rounds} 轮)")
        print("="*60)
        
        if len(game_records) < num_rounds:
            print(f"[WARNING] 游戏记录数({len(game_records)})少于测试轮数({num_rounds})，使用所有记录")
            num_rounds = len(game_records)
        
        # 随机采样多轮
        round_results = []
        games_per_round = len(game_records) // num_rounds
        
        for round_idx in range(num_rounds):
            start_idx = round_idx * games_per_round
            end_idx = start_idx + games_per_round if round_idx < num_rounds - 1 else len(game_records)
            round_records = game_records[start_idx:end_idx]
            
            eval_result = self.evaluator.evaluate_model(round_records, player_id)
            round_results.append({
                'round': round_idx + 1,
                'win_rate': eval_result['win_rate'],
                'total_score': eval_result['total_score'],
                'num_games': len(round_records)
            })
        
        # 计算统计指标
        win_rates = [r['win_rate'] for r in round_results]
        total_scores = [r['total_score'] for r in round_results]
        
        mean_win_rate = np.mean(win_rates)
        std_win_rate = np.std(win_rates)
        mean_total_score = np.mean(total_scores)
        std_total_score = np.std(total_scores)
        
        # 计算变异系数（CV = std / mean）
        cv_win_rate = std_win_rate / mean_win_rate if mean_win_rate > 0 else 0.0
        cv_total_score = std_total_score / mean_total_score if mean_total_score > 0 else 0.0
        
        print(f"\n稳定性指标:")
        print(f"  胜率: 均值={mean_win_rate:.2%}, 标准差={std_win_rate:.2%}, 变异系数={cv_win_rate:.3f}")
        print(f"  综合分数: 均值={mean_total_score:.2%}, 标准差={std_total_score:.2%}, 变异系数={cv_total_score:.3f}")
        
        print(f"\n各轮结果:")
        for result in round_results:
            print(f"  第{result['round']}轮: 胜率={result['win_rate']:.2%}, 综合分数={result['total_score']:.2%}, 对局数={result['num_games']}")
        
        # 稳定性评估
        is_stable = cv_win_rate < 0.3 and cv_total_score < 0.3  # 变异系数<0.3认为稳定
        
        return {
            'round_results': round_results,
            'statistics': {
                'mean_win_rate': mean_win_rate,
                'std_win_rate': std_win_rate,
                'cv_win_rate': cv_win_rate,
                'mean_total_score': mean_total_score,
                'std_total_score': std_total_score,
                'cv_total_score': cv_total_score
            },
            'is_stable': is_stable
        }
    
    def adaptability_test(self, game_records: List[Dict], player_id: int = 0) -> Dict:
        """
        适应性测试：面对不同对手的适应性
        
        Args:
            game_records: 游戏记录列表
            player_id: 玩家ID
            
        Returns:
            适应性测试结果
        """
        print("="*60)
        print("适应性测试：面对不同对手")
        print("="*60)
        
        # 按对手类型分组（这里简化处理，实际可以根据对手ID或对手类型分组）
        opponent_groups = defaultdict(list)
        
        for record in game_records:
            # 提取对手信息（简化：使用游戏ID的前缀作为对手标识）
            game_id = record.get('game_id', 'unknown')
            # 确保game_id不是None
            if game_id is None:
                game_id = 'unknown'
            opponent_key = game_id[:10] if len(game_id) > 10 else 'unknown'
            opponent_groups[opponent_key].append(record)
        
        print(f"识别了 {len(opponent_groups)} 组不同的对手\n")
        
        # 评估每组对手的表现
        group_results = []
        for opponent_key, records in opponent_groups.items():
            if len(records) >= 5:  # 至少5局才统计
                eval_result = self.evaluator.evaluate_model(records, player_id)
                group_results.append({
                    'opponent': opponent_key,
                    'num_games': len(records),
                    'win_rate': eval_result['win_rate'],
                    'total_score': eval_result['total_score']
                })
        
        # 计算胜率波动
        if group_results:
            win_rates = [r['win_rate'] for r in group_results]
            mean_win_rate = np.mean(win_rates)
            std_win_rate = np.std(win_rates)
            min_win_rate = np.min(win_rates)
            max_win_rate = np.max(win_rates)
            win_rate_range = max_win_rate - min_win_rate
            
            print(f"胜率统计:")
            print(f"  均值: {mean_win_rate:.2%}")
            print(f"  标准差: {std_win_rate:.2%}")
            print(f"  范围: {min_win_rate:.2%} - {max_win_rate:.2%} (波动={win_rate_range:.2%})")
            
            # 适应性评估：波动<15%认为适应性强
            is_adaptive = win_rate_range < 0.15
            
            print(f"\n各组对手表现:")
            for result in sorted(group_results, key=lambda x: x['win_rate'], reverse=True):
                print(f"  {result['opponent']}: 胜率={result['win_rate']:.2%}, 综合分数={result['total_score']:.2%}, 对局数={result['num_games']}")
            
            return {
                'group_results': group_results,
                'statistics': {
                    'mean_win_rate': mean_win_rate,
                    'std_win_rate': std_win_rate,
                    'win_rate_range': win_rate_range
                },
                'is_adaptive': is_adaptive
            }
        else:
            print("[WARNING] 没有足够的对手组进行适应性测试")
            return {'is_adaptive': False}
    
    def comprehensive_validation(self, game_records: List[Dict], 
                                 baseline_records: Optional[List[Dict]] = None,
                                 player_id: int = 0) -> Dict:
        """
        综合验证：执行所有测试
        
        Args:
            game_records: 当前模型的游戏记录
            baseline_records: 基线模型的游戏记录（可选）
            player_id: 玩家ID
            
        Returns:
            综合验证结果
        """
        print("="*60)
        print("阶段6：游戏导向训练综合验证")
        print("="*60)
        
        results = {}
        
        # 1. 基础评估
        print("\n1. 基础评估")
        print("-" * 60)
        eval_result = self.evaluator.evaluate_model(game_records, player_id)
        results['evaluation'] = eval_result
        
        # 2. 对比实验（如果有基线）
        if baseline_records:
            print("\n2. 对比实验")
            print("-" * 60)
            comparison = self.compare_models(
                game_records, baseline_records,
                "阶段6模型", "阶段5模型", player_id
            )
            results['comparison'] = comparison
        
        # 3. 稳定性测试
        print("\n3. 稳定性测试")
        print("-" * 60)
        stability = self.stability_test(game_records, player_id, num_rounds=10)
        results['stability'] = stability
        
        # 4. 适应性测试
        print("\n4. 适应性测试")
        print("-" * 60)
        adaptability = self.adaptability_test(game_records, player_id)
        results['adaptability'] = adaptability
        
        # 5. 综合结论
        print("\n5. 综合结论")
        print("-" * 60)
        is_improved = False
        if baseline_records:
            improvement = results['comparison']['improvement']
            is_improved = improvement['win_rate'] > 0.05  # 胜率提升>5%
        
        is_stable = results['stability']['is_stable']
        is_adaptive = results['adaptability'].get('is_adaptive', False)
        
        print(f"  胜率提升: {'是' if is_improved else '否'}")
        print(f"  稳定性: {'良好' if is_stable else '需改进'}")
        print(f"  适应性: {'良好' if is_adaptive else '需改进'}")
        
        results['summary'] = {
            'is_improved': is_improved,
            'is_stable': is_stable,
            'is_adaptive': is_adaptive,
            'overall_pass': is_improved and is_stable and is_adaptive
        }
        
        return results


def validate_game_records(data_dir: str = "game_records", 
                          baseline_dir: Optional[str] = None,
                          player_id: int = 0):
    """
    验证游戏记录
    
    Args:
        data_dir: 当前模型的游戏记录目录
        baseline_dir: 基线模型的游戏记录目录（可选）
        player_id: 玩家ID
    """
    # 加载当前模型记录
    parser = ReplayParser(data_dir)
    current_records = parser.load_replays()
    
    # 加载基线记录（如果有）
    baseline_records = None
    if baseline_dir:
        baseline_parser = ReplayParser(baseline_dir)
        baseline_records = baseline_parser.load_replays()
    
    # 执行综合验证
    validator = GameOrientedValidator()
    results = validator.comprehensive_validation(
        current_records, baseline_records, player_id
    )
    
    return results


if __name__ == "__main__":
    from typing import Optional
    validate_game_records()

