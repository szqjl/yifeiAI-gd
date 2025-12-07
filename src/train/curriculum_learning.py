# -*- coding: utf-8 -*-
"""
课程学习模块
实现难度递增的训练策略
"""

import sys
import os
import numpy as np

# **修复**：设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


class CurriculumScheduler:
    """课程学习调度器"""
    
    def __init__(self):
        """初始化课程学习调度器"""
        self.curriculum = [
            {
                'name': 'easy',
                'description': '简单难度',
                'opponent_strength': 0.3,  # 对手强度（0-1）
                'min_episodes': 0,
                'max_episodes': 200,
                'features': {
                    'enable_bombs': False,  # 禁用炸弹
                    'enable_complex_patterns': False,  # 禁用复杂牌型
                }
            },
            {
                'name': 'medium',
                'description': '中等难度',
                'opponent_strength': 0.6,
                'min_episodes': 200,
                'max_episodes': 600,
                'features': {
                    'enable_bombs': True,
                    'enable_complex_patterns': False,
                }
            },
            {
                'name': 'hard',
                'description': '困难难度',
                'opponent_strength': 0.9,
                'min_episodes': 600,
                'max_episodes': 1000,
                'features': {
                    'enable_bombs': True,
                    'enable_complex_patterns': True,
                }
            },
            {
                'name': 'expert',
                'description': '专家难度',
                'opponent_strength': 1.0,
                'min_episodes': 1000,
                'max_episodes': float('inf'),
                'features': {
                    'enable_bombs': True,
                    'enable_complex_patterns': True,
                }
            }
        ]
        self.current_stage = 0
    
    def get_current_curriculum(self, episode):
        """
        获取当前课程配置
        
        Args:
            episode: 当前回合数
        
        Returns:
            curriculum: 当前课程配置
        """
        # 根据回合数确定当前阶段
        for i, stage in enumerate(self.curriculum):
            if stage['min_episodes'] <= episode < stage['max_episodes']:
                self.current_stage = i
                return stage
        
        # 如果超出所有阶段，返回最后一个阶段
        self.current_stage = len(self.curriculum) - 1
        return self.curriculum[-1]
    
    def get_opponent_strength(self, episode):
        """获取对手强度（0-1）"""
        curriculum = self.get_current_curriculum(episode)
        return curriculum['opponent_strength']
    
    def should_enable_feature(self, episode, feature_name):
        """检查是否应该启用某个功能"""
        curriculum = self.get_current_curriculum(episode)
        return curriculum['features'].get(feature_name, True)
    
    def get_stage_name(self, episode):
        """获取当前阶段名称"""
        curriculum = self.get_current_curriculum(episode)
        return curriculum['name']
    
    def get_progress(self, episode):
        """获取课程学习进度（0-1）"""
        curriculum = self.get_current_curriculum(episode)
        if curriculum['max_episodes'] == float('inf'):
            return 1.0
        
        stage_range = curriculum['max_episodes'] - curriculum['min_episodes']
        if stage_range == 0:
            return 1.0
        
        progress = (episode - curriculum['min_episodes']) / stage_range
        return min(1.0, max(0.0, progress))


class AdaptiveDifficultyAdjuster:
    """自适应难度调整器"""
    
    def __init__(self, initial_difficulty=0.5, min_difficulty=0.3, max_difficulty=1.0):
        """
        初始化自适应难度调整器
        
        Args:
            initial_difficulty: 初始难度
            min_difficulty: 最小难度
            max_difficulty: 最大难度
        """
        self.current_difficulty = initial_difficulty
        self.min_difficulty = min_difficulty
        self.max_difficulty = max_difficulty
        self.win_rate_history = []
        self.window_size = 50  # 用于计算胜率的窗口大小
    
    def update_win_rate(self, win_rate):
        """更新胜率历史"""
        self.win_rate_history.append(win_rate)
        if len(self.win_rate_history) > self.window_size:
            self.win_rate_history.pop(0)
    
    def adjust_difficulty(self):
        """根据胜率调整难度"""
        if len(self.win_rate_history) < 10:
            return self.current_difficulty
        
        avg_win_rate = np.mean(self.win_rate_history[-10:])
        
        # 如果胜率太高（>70%），增加难度
        if avg_win_rate > 0.7:
            self.current_difficulty = min(self.max_difficulty, self.current_difficulty + 0.05)
        # 如果胜率太低（<30%），降低难度
        elif avg_win_rate < 0.3:
            self.current_difficulty = max(self.min_difficulty, self.current_difficulty - 0.05)
        
        return self.current_difficulty
    
    def get_difficulty(self):
        """获取当前难度"""
        return self.current_difficulty


if __name__ == "__main__":
    # 示例：课程学习
    scheduler = CurriculumScheduler()
    
    print("课程学习配置:")
    for stage in scheduler.curriculum:
        print(f"  {stage['name']}: {stage['description']}")
        print(f"    回合范围: {stage['min_episodes']}-{stage['max_episodes']}")
        print(f"    对手强度: {stage['opponent_strength']}")
        print()
    
    # 测试不同回合的课程配置
    test_episodes = [0, 100, 300, 500, 800, 1200]
    print("课程学习进度:")
    for episode in test_episodes:
        curriculum = scheduler.get_current_curriculum(episode)
        progress = scheduler.get_progress(episode)
        print(f"  Episode {episode}: {curriculum['name']} (进度: {progress:.1%})")

