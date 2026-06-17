"""
输入验证模块测试

测试目标场数验证、重启次数计算等功能。
"""

import math
import pytest
from hypothesis import given, strategies as st, settings

from batch_executor.input_validator import InputValidator


class TestTargetGamesValidation:
    """测试目标场数验证功能"""
    
    @given(target_games=st.integers(min_value=1, max_value=100000).filter(lambda n: n % 3 == 0))
    @settings(max_examples=100)
    def test_property_target_games_validation(self, target_games):
        """
        **Feature: batch-game-execution, Property 5: 目标场数验证**
        **Validates: Requirements 1.1**
        
        For any 正整数输入，系统应该接受并正确存储该值作为目标场数
        """
        validator = InputValidator()
        
        # 验证输入
        result = validator.validate_target_games(target_games)
        
        # 验证：返回值应该等于输入值
        assert result == target_games, \
            f"Expected validate_target_games to return {target_games}, but got {result}"
        
        # 验证：目标场数应该被正确存储
        assert validator.target_games == target_games, \
            f"Expected target_games property to be {target_games}, but got {validator.target_games}"
    
    def test_default_target_games(self):
        """测试默认目标场数"""
        validator = InputValidator()
        
        # 不提供参数时应该使用默认值
        result = validator.validate_target_games(None)
        
        assert result == InputValidator.DEFAULT_TARGET_GAMES
        assert validator.target_games == InputValidator.DEFAULT_TARGET_GAMES
    
    def test_default_target_games_no_argument(self):
        """测试不传参数时使用默认值"""
        validator = InputValidator()
        
        # 不传参数时应该使用默认值
        result = validator.validate_target_games()
        
        assert result == InputValidator.DEFAULT_TARGET_GAMES
        assert validator.target_games == InputValidator.DEFAULT_TARGET_GAMES
    
    def test_target_games_must_be_multiple_of_session_limit(self):
        """v1006 批跑目标须为 single_run_limit（3）的倍数"""
        validator = InputValidator()
        with pytest.raises(ValueError) as exc_info:
            validator.validate_target_games(10)
        assert "倍数" in str(exc_info.value)
        assert validator.validate_target_games(9) == 9
        assert validator.validate_target_games(12) == 12


class TestInvalidInputRejection:
    """测试无效输入拒绝功能"""
    
    @given(
        invalid_input=st.one_of(
            st.integers(max_value=0),  # 非正整数：零和负数
            st.integers(min_value=-1000, max_value=-1)  # 负数
        )
    )
    @settings(max_examples=100)
    def test_property_invalid_input_rejection(self, invalid_input):
        """
        **Feature: batch-game-execution, Property 7: 无效输入拒绝**
        **Validates: Requirements 1.5**
        
        For any 非正整数输入（负数、零），系统应该拒绝该输入
        """
        validator = InputValidator()
        
        # 验证：应该抛出ValueError
        with pytest.raises(ValueError) as exc_info:
            validator.validate_target_games(invalid_input)
        
        # 验证：错误消息应该提示输入必须是正整数
        error_message = str(exc_info.value)
        assert "正整数" in error_message, \
            f"Error message should mention '正整数', but got: {error_message}"
    
    @given(
        invalid_type=st.one_of(
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
            st.lists(st.integers()),
            st.dictionaries(st.text(), st.integers())
        )
    )
    @settings(max_examples=100)
    def test_property_non_integer_rejection(self, invalid_type):
        """
        测试非整数类型输入被拒绝
        
        For any 非整数类型输入，系统应该拒绝该输入
        """
        validator = InputValidator()
        
        # 验证：应该抛出ValueError
        with pytest.raises(ValueError) as exc_info:
            validator.validate_target_games(invalid_type)
        
        # 验证：错误消息应该提示输入必须是整数
        error_message = str(exc_info.value)
        assert "整数" in error_message, \
            f"Error message should mention '整数', but got: {error_message}"


class TestRestartCountCalculation:
    """测试重启次数计算功能"""
    
    @given(
        target_games=st.integers(min_value=1, max_value=10000),
        single_run_limit=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_property_restart_count_calculation(self, target_games, single_run_limit):
        """
        **Feature: batch-game-execution, Property 6: 重启次数计算**
        **Validates: Requirements 1.2**
        
        For any 目标场数和单次限制，重启次数应该等于 ceil(目标场数 / 单次限制) - 1
        """
        validator = InputValidator(single_run_limit=single_run_limit)
        
        # 计算重启次数
        restart_count = validator.calculate_restart_count(target_games)
        
        # 计算期望的重启次数
        expected_total_runs = math.ceil(target_games / single_run_limit)
        expected_restart_count = expected_total_runs - 1
        
        # 验证：重启次数应该等于期望值
        assert restart_count == expected_restart_count, \
            f"For target_games={target_games}, single_run_limit={single_run_limit}: " \
            f"expected restart_count={expected_restart_count}, but got {restart_count}"
    
    def test_restart_count_with_stored_target(self):
        """测试使用已存储的目标场数计算重启次数"""
        validator = InputValidator(single_run_limit=3)
        
        # 先验证并存储目标场数
        validator.validate_target_games(99)
        
        # 不传参数时应该使用已存储的值
        restart_count = validator.calculate_restart_count()
        
        # 99场，每次3场，需要33次运行，32次重启
        expected = math.ceil(99 / 3) - 1
        assert restart_count == expected
    
    def test_restart_count_without_target_raises_error(self):
        """测试未设置目标场数时计算重启次数应该抛出错误"""
        validator = InputValidator()
        
        # 未设置目标场数时应该抛出ValueError
        with pytest.raises(ValueError) as exc_info:
            validator.calculate_restart_count()
        
        error_message = str(exc_info.value)
        assert "目标场数" in error_message
    
    def test_restart_count_examples(self):
        """测试一些具体的重启次数计算示例"""
        validator = InputValidator(single_run_limit=3)
        
        # 3场：需要1次运行，0次重启
        assert validator.calculate_restart_count(3) == 0
        
        # 4场：须为 3 的倍数，validate 会拒绝；calculate_restart_count(6) 仍可用于数学
        assert validator.calculate_restart_count(6) == 1
        
        # 9场：需要3次运行，2次重启
        assert validator.calculate_restart_count(9) == 2
        
        # 99场：需要33次运行，32次重启
        assert validator.calculate_restart_count(99) == 32
