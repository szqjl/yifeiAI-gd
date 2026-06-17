"""
M1 vs Client 胜率评估器
用于评估训练后的模型能否帮助M1战胜client

评估方式：
1. 使用训练好的模型生成决策建议
2. M1结合模型建议做出最终决策
3. 与client进行对战测试
4. 统计胜率并分析
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class M1VsClientEvaluator:
    """M1 vs Client 胜率评估器"""
    
    def __init__(self, model_path: str = None):
        """
        初始化评估器
        
        Args:
            model_path: 训练好的模型路径
        """
        self.model_path = model_path
        self.game_records_dir = Path("game_records")
        
    def evaluate_win_rate(
        self, 
        num_games: int = 50,
        opponent_type: str = "client",
        player_id: int = 0
    ) -> Dict:
        """
        评估M1 vs Client的胜率
        
        Args:
            num_games: 测试对局数
            opponent_type: 对手类型 ("client", "v4", "v5")
            player_id: 玩家ID
            
        Returns:
            评估结果字典
        """
        logger.info(f"开始评估 M1 vs {opponent_type}")
        logger.info(f"测试对局数: {num_games}")
        
        # 加载游戏记录
        game_records = self._load_game_records(opponent_type, player_id, num_games)
        
        if not game_records:
            logger.warning("未找到游戏记录，请先进行对战测试")
            return {
                "win_rate": 0.0,
                "total_games": 0,
                "wins": 0,
                "losses": 0,
                "opponent_type": opponent_type,
                "decision_quality": {},
                "status": "no_records",
                "message": "需要先进行对战测试生成游戏记录"
            }
        
        # 计算胜率
        win_rate, wins, total = self._calculate_win_rate(game_records, player_id)
        
        # 分析决策质量
        decision_quality = self._analyze_decision_quality(game_records, player_id)
        
        result = {
            "win_rate": win_rate,
            "total_games": total,
            "wins": wins,
            "losses": total - wins,
            "opponent_type": opponent_type,
            "decision_quality": decision_quality,
            "status": "success" if win_rate > 0.5 else "needs_improvement"
        }
        
        logger.info(f"评估完成: 胜率={win_rate:.2%}, 胜局={wins}/{total}")
        
        return result
    
    def _load_game_records(
        self, 
        opponent_type: str, 
        player_id: int, 
        limit: int = None
    ) -> List[Dict]:
        """加载游戏记录"""
        records = []
        
        # 查找包含M1和指定对手的记录
        # 支持多种文件名格式：
        # 1. *yf1_m1*client*.json
        # 2. *yf1_m1*opponent*.json (opponent_1_3, opponent_2_4等)
        # 3. *yf1_m1*.json (所有yf1_m1记录，因为opponent信息在文件内容中)
        patterns = [
            f"*yf1_m1*{opponent_type}*.json",
            f"*yf1_m1*opponent*.json",  # 兼容opponent格式
            "*yf1_m1*.json",  # 如果前两个找不到，使用这个（然后过滤）
        ]
        
        record_files = []
        for pattern in patterns:
            found = list(self.game_records_dir.glob(pattern))
            if found:
                record_files.extend(found)
                if pattern != "*yf1_m1*.json":  # 如果找到了特定格式，就不需要通用格式了
                    break
        
        # 去重
        record_files = list(set(record_files))
        
        # 按修改时间排序，最新的在前
        record_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        if limit and len(record_files) > limit:
            record_files = record_files[:limit]
        
        logger.info(f"找到 {len(record_files)} 个游戏记录文件")
        
        for file_path in record_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 支持列表格式（多个游戏记录）和单个字典格式
                    if isinstance(data, list):
                        # 如果是列表，过滤出player_id匹配的记录
                        for item in data:
                            if isinstance(item, dict):
                                item_player_id = item.get('player_id')
                                if item_player_id == player_id or item_player_id is None:
                                    records.append(item)
                    else:
                        # 单个字典，检查player_id
                        record_player_id = data.get('player_id')
                        if record_player_id == player_id or record_player_id is None:
                            records.append(data)
            except Exception as e:
                logger.warning(f"加载记录失败 {file_path}: {e}")
        
        logger.info(f"成功加载 {len(records)} 个游戏记录（player_id={player_id}）")
        return records
    
    def _calculate_win_rate(
        self, 
        game_records: List[Dict], 
        player_id: int
    ) -> Tuple[float, int, int]:
        """计算胜率"""
        wins = 0
        total = 0
        
        for record in game_records:
            # 支持新格式（game_info）
            game_info = record.get('game_info', {})
            if game_info and isinstance(game_info, dict):
                # 尝试从game_info获取结果
                game_result = game_info.get('game_result')
                record_player_id = record.get('player_id', player_id)
                
                # 如果game_result存在，使用它
                if game_result in ['win', 'loss']:
                    if record_player_id == player_id:
                        if game_result == 'win':
                            wins += 1
                        total += 1
                    continue
                
                # 尝试从game_info的其他字段获取结果
                team_result = game_info.get('team_result')  # 可能包含 'win' 或 'loss'
                if team_result in ['win', 'loss']:
                    # 需要判断player_id属于哪个队伍
                    # 0和2是Team A，1和3是Team B
                    team_a_players = [0, 2]
                    team_b_players = [1, 3]
                    if player_id in team_a_players:
                        team = 'A'
                    elif player_id in team_b_players:
                        team = 'B'
                    else:
                        continue
                    
                    # 检查team_result是否匹配
                    if (team == 'A' and team_result == 'win') or (team == 'B' and team_result == 'loss'):
                        wins += 1
                    total += 1
                    continue
            
            # 回退到旧格式（result.victoryNum）
            result = record.get('result', {})
            if isinstance(result, dict):
                victory_num = result.get('victoryNum', [])
                
                if victory_num and isinstance(victory_num, list) and len(victory_num) > player_id:
                    total += 1
                    if victory_num[player_id] > 0:
                        wins += 1
                    continue
            
            # 如果都没有，尝试从actions推断（最后手段）
            # 这里可以添加更多推断逻辑
            logger.debug(f"无法从记录中提取胜率信息: {list(record.keys())}")
        
        win_rate = wins / total if total > 0 else 0.0
        return win_rate, wins, total
    
    def _analyze_decision_quality(
        self, 
        game_records: List[Dict], 
        player_id: int
    ) -> Dict:
        """分析决策质量"""
        if not game_records:
            return {}
        
        # 统计决策信息
        total_decisions = 0
        pass_count = 0
        action_count = 0
        
        for record in game_records:
            decisions = record.get('my_decisions', [])
            for decision in decisions:
                total_decisions += 1
                action = decision.get('action', [])
                if not action or all(c == 0 for c in action):
                    pass_count += 1
                else:
                    action_count += 1
        
        pass_ratio = pass_count / total_decisions if total_decisions > 0 else 0.0
        
        return {
            "total_decisions": total_decisions,
            "pass_count": pass_count,
            "action_count": action_count,
            "pass_ratio": pass_ratio
        }
    
    def compare_with_baseline(self, baseline_win_rate: float = 0.45) -> Dict:
        """
        与基线对比
        
        Args:
            baseline_win_rate: 基线胜率（M1原始胜率）
            
        Returns:
            对比结果
        """
        result = self.evaluate_win_rate()
        current_win_rate = result['win_rate']
        
        improvement = current_win_rate - baseline_win_rate
        improvement_percent = (improvement / baseline_win_rate * 100) if baseline_win_rate > 0 else 0
        
        return {
            "baseline_win_rate": baseline_win_rate,
            "current_win_rate": current_win_rate,
            "improvement": improvement,
            "improvement_percent": improvement_percent,
            "meets_target": current_win_rate > 0.5,
            "status": "success" if current_win_rate > 0.5 else "needs_improvement"
        }


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="M1 vs Client 胜率评估")
    parser.add_argument("--num_games", type=int, default=50, help="测试对局数")
    parser.add_argument("--opponent", type=str, default="client", 
                       choices=["client", "v4", "v5"], help="对手类型")
    parser.add_argument("--model_path", type=str, default=None, help="模型路径")
    
    args = parser.parse_args()
    
    evaluator = M1VsClientEvaluator(model_path=args.model_path)
    result = evaluator.evaluate_win_rate(
        num_games=args.num_games,
        opponent_type=args.opponent
    )
    
    print("\n" + "="*60)
    print("M1 vs Client 评估结果")
    print("="*60)
    print(f"胜率: {result.get('win_rate', 0.0):.2%}")
    print(f"胜局: {result.get('wins', 0)}/{result.get('total_games', 0)}")
    print(f"状态: {result.get('status', 'unknown')}")
    decision_quality = result.get('decision_quality', {})
    if decision_quality:
        print(f"决策质量: {decision_quality}")
    else:
        print("决策质量: N/A")
    if 'message' in result:
        print(f"提示: {result['message']}")
    print("="*60)
