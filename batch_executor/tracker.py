"""
战绩跟踪模块

用于跟踪和累计多次运行的游戏战绩。
"""

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GameScore:
    """游戏战绩"""
    team_a_wins: int
    team_b_wins: int
    total_games: int
    timestamp: datetime
    
    def win_rate(self, team: str) -> float:
        """计算胜率"""
        if self.total_games == 0:
            return 0.0
        wins = self.team_a_wins if team == "team_a" else self.team_b_wins
        return wins / self.total_games


class ScoreTracker:
    """跟踪和累计游戏战绩"""
    
    def __init__(self, save_file: str):
        self.save_file = save_file
        self.team_a_wins = 0
        self.team_b_wins = 0
        self.total_games = 0
    
    def record_game(self, winner: str) -> None:
        """记录一场游戏结果
        
        Args:
            winner: 获胜队伍，"team_a" 或 "team_b"
        
        Raises:
            ValueError: 如果winner不是"team_a"或"team_b"
        """
        if winner not in ["team_a", "team_b"]:
            raise ValueError(f"Invalid winner: {winner}. Must be 'team_a' or 'team_b'")
        
        if winner == "team_a":
            self.team_a_wins += 1
        else:
            self.team_b_wins += 1
        
        self.total_games += 1
    
    def save(self) -> None:
        """持久化战绩到文件
        
        使用临时文件+原子重命名确保数据安全
        """
        data = {
            "team_a_wins": self.team_a_wins,
            "team_b_wins": self.team_b_wins,
            "total_games": self.total_games
        }
        
        # 使用临时文件确保原子性
        dir_name = os.path.dirname(self.save_file) or "."
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=dir_name,
            delete=False,
            suffix='.tmp'
        ) as tmp_file:
            json.dump(data, tmp_file, indent=2)
            tmp_name = tmp_file.name
        
        # 原子重命名
        os.replace(tmp_name, self.save_file)
    
    def load(self) -> None:
        """从文件恢复战绩
        
        如果文件不存在，保持当前状态不变
        """
        if not os.path.exists(self.save_file):
            return
        
        with open(self.save_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.team_a_wins = data.get("team_a_wins", 0)
        self.team_b_wins = data.get("team_b_wins", 0)
        self.total_games = data.get("total_games", 0)
    
    def generate_report(self) -> str:
        """生成战绩报告
        
        Returns:
            格式化的战绩报告字符串，包含总胜场数、总负场数和胜率
        """
        if self.total_games == 0:
            return "战绩报告:\n  总场数: 0\n  Team A: 0胜 (0.00%)\n  Team B: 0胜 (0.00%)"
        
        team_a_rate = (self.team_a_wins / self.total_games) * 100
        team_b_rate = (self.team_b_wins / self.total_games) * 100
        
        report = f"""战绩报告:
  总场数: {self.total_games}
  Team A: {self.team_a_wins}胜 ({team_a_rate:.2f}%)
  Team B: {self.team_b_wins}胜 ({team_b_rate:.2f}%)"""
        
        return report
