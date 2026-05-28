"""
测试战绩跟踪器模块
"""

import json
import os
import tempfile
from hypothesis import given, strategies as st
import pytest

from batch_executor.tracker import ScoreTracker, GameScore


class TestScoreTracker:
    """测试 ScoreTracker 类"""
    
    @given(st.lists(st.sampled_from(["team_a", "team_b"]), min_size=0, max_size=100))
    def test_property_game_result_recording(self, game_results):
        """
        **Feature: batch-game-execution, Property 10: 游戏结果记录**
        **Validates: Requirements 3.1**
        
        For any 游戏结果（team_a或team_b获胜），战绩跟踪器应该正确增加对应队伍的胜场数
        """
        tracker = ScoreTracker(save_file="dummy.json")
        
        # 记录所有游戏结果
        for winner in game_results:
            tracker.record_game(winner)
        
        # 验证统计正确
        expected_team_a = game_results.count("team_a")
        expected_team_b = game_results.count("team_b")
        expected_total = len(game_results)
        
        assert tracker.team_a_wins == expected_team_a, \
            f"team_a wins should be {expected_team_a}, got {tracker.team_a_wins}"
        assert tracker.team_b_wins == expected_team_b, \
            f"team_b wins should be {expected_team_b}, got {tracker.team_b_wins}"
        assert tracker.total_games == expected_total, \
            f"total games should be {expected_total}, got {tracker.total_games}"
    
    def test_record_game_invalid_winner(self):
        """测试记录无效的获胜者"""
        tracker = ScoreTracker(save_file="dummy.json")
        
        with pytest.raises(ValueError, match="Invalid winner"):
            tracker.record_game("invalid_team")
    
    @given(
        team_a_wins=st.integers(min_value=0, max_value=1000),
        team_b_wins=st.integers(min_value=0, max_value=1000)
    )
    def test_property_persistence_round_trip(self, team_a_wins, team_b_wins):
        """
        **Feature: batch-game-execution, Property 11: 战绩持久化**
        **Validates: Requirements 3.2, 3.5**
        
        For any 战绩数据，保存后重新加载应该得到相同的数据（round trip）
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            # 创建tracker并设置数据
            tracker1 = ScoreTracker(save_file=temp_file)
            tracker1.team_a_wins = team_a_wins
            tracker1.team_b_wins = team_b_wins
            tracker1.total_games = team_a_wins + team_b_wins
            
            # 保存
            tracker1.save()
            
            # 创建新tracker并加载
            tracker2 = ScoreTracker(save_file=temp_file)
            tracker2.load()
            
            # 验证数据一致
            assert tracker2.team_a_wins == team_a_wins, \
                f"team_a_wins should be {team_a_wins}, got {tracker2.team_a_wins}"
            assert tracker2.team_b_wins == team_b_wins, \
                f"team_b_wins should be {team_b_wins}, got {tracker2.team_b_wins}"
            assert tracker2.total_games == team_a_wins + team_b_wins, \
                f"total_games should be {team_a_wins + team_b_wins}, got {tracker2.total_games}"
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @given(
        team_a_wins=st.integers(min_value=0, max_value=1000),
        team_b_wins=st.integers(min_value=0, max_value=1000)
    )
    def test_property_report_calculation(self, team_a_wins, team_b_wins):
        """
        **Feature: batch-game-execution, Property 12: 战绩报告计算**
        **Validates: Requirements 3.3**
        
        For any 战绩数据，生成的报告应该包含正确的总胜场数、总负场数和胜率
        """
        tracker = ScoreTracker(save_file="dummy.json")
        tracker.team_a_wins = team_a_wins
        tracker.team_b_wins = team_b_wins
        tracker.total_games = team_a_wins + team_b_wins
        
        report = tracker.generate_report()
        
        # 验证报告包含所有必要信息
        assert str(tracker.total_games) in report, \
            f"Report should contain total games {tracker.total_games}"
        assert str(team_a_wins) in report, \
            f"Report should contain team_a wins {team_a_wins}"
        assert str(team_b_wins) in report, \
            f"Report should contain team_b wins {team_b_wins}"
        
        # 验证胜率计算
        if tracker.total_games > 0:
            expected_a_rate = (team_a_wins / tracker.total_games) * 100
            expected_b_rate = (team_b_wins / tracker.total_games) * 100
            
            # 检查胜率是否在报告中（允许格式化差异）
            assert f"{expected_a_rate:.2f}" in report or f"{expected_a_rate:.1f}" in report, \
                f"Report should contain team_a win rate around {expected_a_rate:.2f}%"
            assert f"{expected_b_rate:.2f}" in report or f"{expected_b_rate:.1f}" in report, \
                f"Report should contain team_b win rate around {expected_b_rate:.2f}%"
