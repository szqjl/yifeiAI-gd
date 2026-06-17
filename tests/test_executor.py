"""
测试执行器模块

测试ExecutionState的状态保存和加载功能。
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
from batch_executor.executor import ExecutionState


# 生成随机的ExecutionState对象
@st.composite
def execution_state_strategy(draw):
    """生成随机的ExecutionState对象"""
    target_games = draw(st.integers(min_value=1, max_value=10000))
    completed_games = draw(st.integers(min_value=0, max_value=target_games))
    restart_count = draw(st.integers(min_value=0, max_value=100))
    current_batch = draw(st.integers(min_value=1, max_value=100))
    
    # 生成合理的时间戳
    base_time = datetime(2024, 1, 1)
    start_offset = draw(st.integers(min_value=0, max_value=365*24*60*60))
    start_time = base_time + timedelta(seconds=start_offset)
    
    # last_update应该在start_time之后
    update_offset = draw(st.integers(min_value=0, max_value=24*60*60))
    last_update = start_time + timedelta(seconds=update_offset)
    
    return ExecutionState(
        target_games=target_games,
        completed_games=completed_games,
        restart_count=restart_count,
        current_batch=current_batch,
        start_time=start_time,
        last_update=last_update
    )


@given(state=execution_state_strategy())
@settings(deadline=500)
def test_property_state_save_completeness(state):
    """
    **Feature: batch-game-execution, Property 16: 状态保存完整性**
    **Validates: Requirements 6.4**
    
    Property: For any 执行状态，保存后重新加载应该得到相同的状态（round trip）
    
    这个测试验证：
    1. 任何ExecutionState对象都可以被保存到文件
    2. 从文件加载后的状态与原始状态完全相同
    3. 所有字段（包括datetime对象）都被正确保存和恢复
    """
    import tempfile
    import os
    
    # 创建临时文件
    fd, temp_file = tempfile.mkstemp()
    os.close(fd)
    
    try:
        # 保存状态
        state.save(temp_file)
        
        # 加载状态
        loaded_state = ExecutionState.load(temp_file)
        
        # 验证所有字段都相同
        assert loaded_state.target_games == state.target_games
        assert loaded_state.completed_games == state.completed_games
        assert loaded_state.restart_count == state.restart_count
        assert loaded_state.current_batch == state.current_batch
        assert loaded_state.start_time == state.start_time
        assert loaded_state.last_update == state.last_update
        
        # 验证整个对象相等
        assert loaded_state == state
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
