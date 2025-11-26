# -*- coding: utf-8 -*-
"""
决策时间控制模块 (Decision Timer)
功能：
- 设置最大决策时间
- 超时保护机制
- 快速决策路径
- 渐进式决策（先返回可行方案，再优化）
"""

import time
from typing import Callable, Optional, Any
from functools import wraps


class DecisionTimer:
    """决策时间控制器"""
    
    def __init__(self, max_time: float = 0.8):
        """
        初始化决策计时器
        
        Args:
            max_time: 最大决策时间（秒），默认0.8秒
        """
        self.max_time = max_time
        self.start_time: Optional[float] = None
        self.elapsed_time: float = 0.0
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
        self.elapsed_time = 0.0
    
    def check_timeout(self) -> bool:
        """
        检查是否超时
        
        Returns:
            True: 已超时，False: 未超时
        """
        if self.start_time is None:
            return False
        
        self.elapsed_time = time.time() - self.start_time
        return self.elapsed_time >= self.max_time
    
    def get_remaining_time(self) -> float:
        """
        获取剩余时间
        
        Returns:
            剩余时间（秒）
        """
        if self.start_time is None:
            return self.max_time
        
        elapsed = time.time() - self.start_time
        remaining = self.max_time - elapsed
        return max(0.0, remaining)
    
    def get_elapsed_time(self) -> float:
        """
        获取已用时间
        
        Returns:
            已用时间（秒）
        """
        if self.start_time is None:
            return 0.0
        
        self.elapsed_time = time.time() - self.start_time
        return self.elapsed_time
    
    def reset(self):
        """重置计时器"""
        self.start_time = None
        self.elapsed_time = 0.0


def with_timeout(max_time: float = 0.8, default_return: Any = 0):
    """
    装饰器：为函数添加超时保护
    
    Args:
        max_time: 最大执行时间（秒）
        default_return: 超时时的默认返回值
    
    Usage:
        @with_timeout(max_time=0.8, default_return=0)
        def my_decision_function():
            # 决策逻辑
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer = DecisionTimer(max_time)
            timer.start()
            
            # 如果函数支持timer参数，传入timer
            if 'timer' in func.__code__.co_varnames:
                kwargs['timer'] = timer
            
            try:
                result = func(*args, **kwargs)
                elapsed = timer.get_elapsed_time()
                if elapsed > max_time * 0.8:
                    print(f"Warning: {func.__name__} took {elapsed:.3f}s (接近超时)")
                return result
            except TimeoutError:
                print(f"Timeout: {func.__name__} exceeded {max_time}s, returning default")
                return default_return
            except Exception as e:
                print(f"Error in {func.__name__}: {e}, returning default")
                return default_return
        
        return wrapper
    return decorator


class ProgressiveDecision:
    """渐进式决策（先返回可行方案，再优化）"""
    
    def __init__(self, timer: DecisionTimer):
        self.timer = timer
        self.best_result = None
        self.best_score = float('-inf')
    
    def update(self, result: Any, score: float):
        """
        更新最佳结果
        
        Args:
            result: 决策结果
            score: 评分
        """
        if score > self.best_score:
            self.best_score = score
            self.best_result = result
    
    def get_result(self) -> Any:
        """
        获取最佳结果
        
        Returns:
            最佳决策结果
        """
        return self.best_result if self.best_result is not None else 0
    
    def should_continue(self) -> bool:
        """
        判断是否应该继续优化
        
        Returns:
            True: 应该继续，False: 应该停止
        """
        # 如果剩余时间不足，停止优化
        remaining = self.timer.get_remaining_time()
        if remaining < 0.1:  # 剩余时间少于0.1秒
            return False
        
        # 如果已经找到很好的方案，可以停止
        if self.best_score > 100:  # 阈值可调
            return False
        
        return True

