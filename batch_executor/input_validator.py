"""
输入验证和目标管理模块

提供目标场数验证、重启次数计算等功能。
"""

import math
from typing import Optional


class InputValidator:
    """输入验证和目标管理类"""
    
    DEFAULT_TARGET_GAMES = 100
    DEFAULT_SINGLE_RUN_LIMIT = 3
    
    def __init__(self, single_run_limit: int = DEFAULT_SINGLE_RUN_LIMIT):
        """
        初始化输入验证器
        
        Args:
            single_run_limit: 服务器单次运行的游戏场数限制（默认3场）
        """
        self.single_run_limit = single_run_limit
        self._target_games: Optional[int] = None
    
    def validate_target_games(self, target_games: Optional[int] = None) -> int:
        """
        验证目标场数输入
        
        验证输入为正整数，如果未提供则使用默认值。
        
        Args:
            target_games: 目标游戏场数，如果为None则使用默认值
            
        Returns:
            验证后的目标场数
            
        Raises:
            ValueError: 如果输入不是正整数
        """
        # 处理默认值
        if target_games is None:
            self._target_games = self.DEFAULT_TARGET_GAMES
            return self._target_games
        
        # 验证输入类型
        if not isinstance(target_games, int):
            raise ValueError(f"目标场数必须是整数，但得到 {type(target_games).__name__}")
        
        # 验证输入为正整数
        if target_games <= 0:
            raise ValueError(f"目标场数必须是正整数，但得到 {target_games}")
        
        # 存储目标场数
        self._target_games = target_games
        return self._target_games
    
    @property
    def target_games(self) -> Optional[int]:
        """获取当前存储的目标场数"""
        return self._target_games
    
    def calculate_restart_count(self, target_games: Optional[int] = None) -> int:
        """
        计算需要的重启次数
        
        根据目标场数和单次限制计算需要重启服务器的次数。
        使用 math.ceil() 向上取整。
        
        Args:
            target_games: 目标游戏场数，如果为None则使用已存储的值
            
        Returns:
            需要的重启次数（总运行次数 - 1）
            
        Raises:
            ValueError: 如果target_games未设置且未提供
        """
        # 确定使用哪个目标场数
        games = target_games if target_games is not None else self._target_games
        
        if games is None:
            raise ValueError("必须先设置目标场数或提供target_games参数")
        
        # 验证目标场数
        if games <= 0:
            raise ValueError(f"目标场数必须是正整数，但得到 {games}")
        
        # 计算总运行次数（向上取整）
        total_runs = math.ceil(games / self.single_run_limit)
        
        # 重启次数 = 总运行次数 - 1
        restart_count = total_runs - 1
        
        return restart_count
