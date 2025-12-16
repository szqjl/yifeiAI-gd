# -*- coding: utf-8 -*-
"""
阶段6：游戏导向评估器
建立以游戏胜率为导向的评估体系
"""

import os
import json
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import sys

# scipy是可选的，如果没有则使用numpy替代
try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# 修复Windows控制台编码
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class GameOrientedEvaluator:
    """
    游戏导向评估器
    综合评估指标：
    - 胜率（权重50%）
    - 策略适应性（权重20%）
    - 决策质量（权重20%）
    - 预测准确性（权重10%）
    """
    
    def __init__(self):
        self.win_rate_weight = 0.5
        self.strategy_adaptability_weight = 0.2
        self.decision_quality_weight = 0.2
        self.prediction_accuracy_weight = 0.1
        
    def evaluate_model(self, game_records: List[Dict], player_id: int = 0) -> Dict:
        """
        计算综合评估分数
        
        Args:
            game_records: 游戏记录列表，每个记录包含result字段
            player_id: 要评估的玩家ID（默认0）
            
        Returns:
            评估结果字典，包含各项指标和综合分数
        """
        # 1. 计算胜率
        win_rate, win_rate_ci = self._calculate_win_rate(game_records, player_id)
        
        # 2. 计算策略适应性
        strategy_adaptability = self._analyze_strategy_adaptability(game_records, player_id)
        
        # 3. 计算决策质量
        decision_quality = self._assess_decision_quality(game_records, player_id)
        
        # 4. 计算预测准确性
        prediction_accuracy = self._measure_prediction_accuracy(game_records, player_id)
        
        # 5. 计算综合分数
        total_score = (
            win_rate * self.win_rate_weight +
            strategy_adaptability * self.strategy_adaptability_weight +
            decision_quality * self.decision_quality_weight +
            prediction_accuracy * self.prediction_accuracy_weight
        )
        
        return {
            'win_rate': win_rate,
            'win_rate_ci': win_rate_ci,
            'strategy_adaptability': strategy_adaptability,
            'decision_quality': decision_quality,
            'prediction_accuracy': prediction_accuracy,
            'total_score': total_score,
            'weights': {
                'win_rate': self.win_rate_weight,
                'strategy_adaptability': self.strategy_adaptability_weight,
                'decision_quality': self.decision_quality_weight,
                'prediction_accuracy': self.prediction_accuracy_weight
            }
        }
    
    def _calculate_win_rate(self, game_records: List[Dict], player_id: int) -> Tuple[float, Tuple[float, float]]:
        """
        计算胜率，包括置信区间
        
        Args:
            game_records: 游戏记录列表
            player_id: 玩家ID
            
        Returns:
            (胜率, (置信区间下限, 置信区间上限))
        """
        if not game_records:
            return 0.0, (0.0, 0.0)
        
        wins = 0
        total_games = 0
        
        for record in game_records:
            # 支持两种数据格式：
            # 1. 旧格式：result.victoryNum
            # 2. 新格式：game_info.game_result 和 game_info.rank
            result = record.get('result', {})
            game_info = record.get('game_info', {})
            
            # 尝试从新格式获取结果
            if game_info:
                game_result = game_info.get('game_result')
                record_player_id = record.get('player_id', player_id)
                
                # 如果当前记录是目标玩家的记录
                if record_player_id == player_id:
                    if game_result == 'win':
                        wins += 1
                        total_games += 1
                    elif game_result == 'loss':
                        total_games += 1
                    # game_result == 'unknown' 时跳过
                    continue
            
            # 回退到旧格式：result.victoryNum
            victory_num = result.get('victoryNum', [])
            
            # 确保victory_num不是None
            if victory_num is None:
                victory_num = []
            
            if len(victory_num) > player_id:
                total_games += 1
                # victoryNum[player_id] > 0 表示该玩家获胜
                if victory_num[player_id] > 0:
                    wins += 1
        
        if total_games == 0:
            return 0.0, (0.0, 0.0)
        
        win_rate = wins / total_games
        
        # 计算95%置信区间（使用正态分布近似）
        if total_games > 1:
            z_score = 1.96  # 95%置信区间
            margin = z_score * np.sqrt(win_rate * (1 - win_rate) / total_games)
            ci_lower = max(0.0, win_rate - margin)
            ci_upper = min(1.0, win_rate + margin)
        else:
            ci_lower = 0.0
            ci_upper = 1.0
        
        return win_rate, (ci_lower, ci_upper)
    
    def _analyze_strategy_adaptability(self, game_records: List[Dict], player_id: int) -> float:
        """
        分析策略适应性
        基于策略类型的多样性和有效性
        
        Args:
            game_records: 游戏记录列表
            player_id: 玩家ID
            
        Returns:
            策略适应性分数（0-1）
        """
        if not game_records:
            return 0.0
        
        strategy_counts = defaultdict(int)
        strategy_wins = defaultdict(int)
        total_decisions = 0
        
        for record in game_records:
            # 支持两种数据格式
            result = record.get('result', {})
            game_info = record.get('game_info', {})
            
            # 尝试从新格式获取结果
            is_win = False
            if game_info:
                game_result = game_info.get('game_result')
                record_player_id = record.get('player_id', player_id)
                
                if record_player_id == player_id:
                    is_win = (game_result == 'win')
            
            # 回退到旧格式
            if not game_info or game_info.get('game_result') == 'unknown':
                victory_num = result.get('victoryNum', [])
                if victory_num is None:
                    victory_num = []
                is_win = len(victory_num) > player_id and victory_num[player_id] > 0
            
            my_decisions = record.get('my_decisions', [])
            for decision in my_decisions:
                layer = decision.get('layer', '')
                # 提取策略类型（从layer中）
                if layer and 'Strategy-' in layer:
                    strategy_type = self._extract_strategy_type(layer)
                    if strategy_type:
                        strategy_counts[strategy_type] += 1
                        total_decisions += 1
                        if is_win:
                            strategy_wins[strategy_type] += 1
        
        if total_decisions == 0:
            return 0.0
        
        # 计算策略多样性（使用熵）
        strategy_probs = [count / total_decisions for count in strategy_counts.values()]
        diversity = -sum(p * np.log(p + 1e-10) for p in strategy_probs) / np.log(len(strategy_counts) + 1)
        
        # 计算策略有效性（平均胜率）
        effectiveness = 0.0
        if strategy_wins:
            for strategy_type, wins in strategy_wins.items():
                total = strategy_counts.get(strategy_type, 1)
                effectiveness += (wins / total) * (strategy_counts[strategy_type] / total_decisions)
        
        # 综合分数：多样性 * 0.5 + 有效性 * 0.5
        adaptability = diversity * 0.5 + effectiveness * 0.5
        
        return min(1.0, max(0.0, adaptability))
    
    def _assess_decision_quality(self, game_records: List[Dict], player_id: int) -> float:
        """
        评估决策质量
        基于主动出牌率、PASS率、决策评分等
        
        Args:
            game_records: 游戏记录列表
            player_id: 玩家ID
            
        Returns:
            决策质量分数（0-1）
        """
        if not game_records:
            return 0.0
        
        total_decisions = 0
        active_decisions = 0  # 主动出牌（非PASS）
        high_score_decisions = 0  # 高分决策（score > 300）
        pass_decisions = 0
        
        for record in game_records:
            my_decisions = record.get('my_decisions', [])
            for decision in my_decisions:
                total_decisions += 1
                action = decision.get('action', [])
                score = decision.get('score', 0) or 0
                
                if isinstance(action, list) and len(action) > 0:
                    if action[0] == 'PASS':
                        pass_decisions += 1
                    else:
                        active_decisions += 1
                        if score > 300:
                            high_score_decisions += 1
        
        if total_decisions == 0:
            return 0.0
        
        # 主动出牌率
        active_rate = active_decisions / total_decisions
        
        # 高分决策率
        high_score_rate = high_score_decisions / max(1, active_decisions)
        
        # PASS率（越低越好）
        pass_rate = pass_decisions / total_decisions
        pass_penalty = 1.0 - pass_rate  # PASS率越低，惩罚越小
        
        # 综合分数：主动出牌率 * 0.4 + 高分决策率 * 0.4 + PASS惩罚 * 0.2
        quality = active_rate * 0.4 + high_score_rate * 0.4 + pass_penalty * 0.2
        
        return min(1.0, max(0.0, quality))
    
    def _measure_prediction_accuracy(self, game_records: List[Dict], player_id: int) -> float:
        """
        测量预测准确性
        基于动作预测的准确性（如果有相关数据）
        
        Args:
            game_records: 游戏记录列表
            player_id: 玩家ID
            
        Returns:
            预测准确性分数（0-1）
        """
        # 这里暂时返回一个基于决策评分的代理指标
        # 实际应该基于模型预测的准确性
        if not game_records:
            return 0.0
        
        total_decisions = 0
        high_confidence_decisions = 0
        
        for record in game_records:
            my_decisions = record.get('my_decisions', [])
            for decision in my_decisions:
                total_decisions += 1
                score = decision.get('score', 0) or 0
                # 高分决策可能表示预测更准确
                if score > 250:
                    high_confidence_decisions += 1
        
        if total_decisions == 0:
            return 0.0
        
        accuracy = high_confidence_decisions / total_decisions
        return min(1.0, max(0.0, accuracy))
    
    def _extract_strategy_type(self, layer: str) -> Optional[str]:
        """从layer字符串中提取策略类型"""
        if not layer or 'Strategy-' not in layer:
            return None
        
        # 提取策略类型（如：组牌策略、残局策略等）
        parts = layer.split(':')
        if len(parts) > 1:
            strategy_part = parts[0].replace('Strategy-', '').strip()
            return strategy_part
        
        return None
    
    def compare_models(self, model1_records: List[Dict], model2_records: List[Dict], 
                      player_id: int = 0) -> Dict:
        """
        对比两个模型的性能
        
        Args:
            model1_records: 模型1的游戏记录
            model2_records: 模型2的游戏记录
            player_id: 玩家ID
            
        Returns:
            对比结果字典
        """
        eval1 = self.evaluate_model(model1_records, player_id)
        eval2 = self.evaluate_model(model2_records, player_id)
        
        # 统计显著性检验（t检验）
        # 支持两种数据格式
        def get_win_status(record, pid):
            """获取玩家是否获胜"""
            game_info = record.get('game_info', {})
            if game_info:
                game_result = game_info.get('game_result')
                record_player_id = record.get('player_id', pid)
                if record_player_id == pid:
                    if game_result == 'win':
                        return 1
                    elif game_result == 'loss':
                        return 0
                    else:
                        return None  # unknown
            
            # 回退到旧格式
            result = record.get('result', {})
            victory_num = result.get('victoryNum', [])
            if victory_num is None:
                victory_num = []
            if len(victory_num) > pid:
                return 1 if victory_num[pid] > 0 else 0
            return None
        
        win_rates1 = [w for r in model1_records if (w := get_win_status(r, player_id)) is not None]
        win_rates2 = [w for r in model2_records if (w := get_win_status(r, player_id)) is not None]
        
        p_value = 1.0
        if len(win_rates1) > 1 and len(win_rates2) > 1:
            try:
                if HAS_SCIPY:
                    t_stat, p_value = stats.ttest_ind(win_rates1, win_rates2)
                else:
                    # 使用简化的t检验（近似）
                    mean1, mean2 = np.mean(win_rates1), np.mean(win_rates2)
                    std1, std2 = np.std(win_rates1, ddof=1), np.std(win_rates2, ddof=1)
                    n1, n2 = len(win_rates1), len(win_rates2)
                    pooled_std = np.sqrt((std1**2/n1 + std2**2/n2))
                    if pooled_std > 0:
                        t_stat = (mean1 - mean2) / pooled_std
                        # 简化的p值计算（使用正态分布近似）
                        p_value = 2 * (1 - 0.5 * (1 + np.sign(t_stat) * (1 - np.exp(-2 * t_stat**2 / np.pi))))
                    else:
                        p_value = 1.0
            except:
                p_value = 1.0
        
        return {
            'model1': eval1,
            'model2': eval2,
            'improvement': {
                'win_rate': eval1['win_rate'] - eval2['win_rate'],
                'total_score': eval1['total_score'] - eval2['total_score']
            },
            'statistical_significance': {
                'p_value': p_value,
                'significant': p_value < 0.05
            }
        }


def evaluate_game_records(data_dir: str = "game_records", player_id: int = 0):
    """
    评估游戏记录
    
    Args:
        data_dir: 游戏记录目录
        player_id: 玩家ID
    """
    print("="*60)
    print("阶段6：游戏导向评估")
    print("="*60)
    
    # 加载游戏记录
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    
    if not replays:
        print(f"[ERROR] 未找到游戏记录: {data_dir}")
        return
    
    print(f"加载了 {len(replays)} 个游戏记录\n")
    
    # 创建评估器
    evaluator = GameOrientedEvaluator()
    
    # 评估
    results = evaluator.evaluate_model(replays, player_id)
    
    # 打印结果
    print("评估结果：")
    print(f"  胜率: {results['win_rate']:.2%} (95% CI: {results['win_rate_ci'][0]:.2%} - {results['win_rate_ci'][1]:.2%})")
    print(f"  策略适应性: {results['strategy_adaptability']:.2%}")
    print(f"  决策质量: {results['decision_quality']:.2%}")
    print(f"  预测准确性: {results['prediction_accuracy']:.2%}")
    print(f"  综合分数: {results['total_score']:.2%}")
    print(f"\n权重配置:")
    print(f"  胜率: {results['weights']['win_rate']:.1%}")
    print(f"  策略适应性: {results['weights']['strategy_adaptability']:.1%}")
    print(f"  决策质量: {results['weights']['decision_quality']:.1%}")
    print(f"  预测准确性: {results['weights']['prediction_accuracy']:.1%}")
    
    return results


if __name__ == "__main__":
    from src.knowledge_processor.replay_parser import ReplayParser
    evaluate_game_records()

