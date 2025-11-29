# -*- coding: utf-8 -*-
"""
Task 5 验证脚本：测试 _try_decision_engine() 方法
"""

import sys
import logging
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4


def test_1_normal_call():
    """测试1：正常调用成功"""
    print("\n测试1：正常调用成功")
    
    # 创建引擎实例
    config = {}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟DecisionEngine
    mock_decision_engine = Mock()
    mock_decision_engine.decide = Mock(return_value=2)
    engine.decision_engine = mock_decision_engine
    
    # 准备测试消息
    message = {
        "actionList": [
            ["PASS"],
            ["SINGLE", "3", ["H3"]],
            ["SINGLE", "4", ["H4"]],
            ["SINGLE", "5", ["H5"]]
        ]
    }
    
    # 调用方法
    result = engine._try_decision_engine(message)
    
    # 验证结果
    assert result == 2, f"Expected 2, got {result}"
    assert mock_decision_engine.decide.called, "DecisionEngine.decide should be called"
    
    print("✓ 测试1通过")


def test_2_invalid_return_value():
    """测试2：DecisionEngine返回无效值"""
    print("\n测试2：DecisionEngine返回无效值")
    
    # 测试2a：返回超出范围的索引
    config = {}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    mock_decision_engine = Mock()
    mock_decision_engine.decide = Mock(return_value=10)  # 超出范围
    engine.decision_engine = mock_decision_engine
    
    message = {
        "actionList": [
            ["PASS"],
            ["SINGLE", "3", ["H3"]]
        ]
    }
    
    result = engine._try_decision_engine(message)
    assert result is None, f"Expected None for out-of-range action, got {result}"
    
    # 测试2b：返回负数
    mock_decision_engine.decide = Mock(return_value=-1)
    result = engine._try_decision_engine(message)
    assert result is None, f"Expected None for negative action, got {result}"
    
    # 测试2c：返回非整数
    mock_decision_engine.decide = Mock(return_value="invalid")
    result = engine._try_decision_engine(message)
    assert result is None, f"Expected None for non-integer action, got {result}"
    
    print("✓ 测试2通过")


def test_3_exception_handling():
    """测试3：DecisionEngine抛出异常"""
    print("\n测试3：DecisionEngine抛出异常")
    
    config = {}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟DecisionEngine抛出异常
    mock_decision_engine = Mock()
    mock_decision_engine.decide = Mock(side_effect=RuntimeError("Test error"))
    engine.decision_engine = mock_decision_engine
    
    message = {
        "actionList": [
            ["PASS"],
            ["SINGLE", "3", ["H3"]]
        ]
    }
    
    # 调用方法，应该捕获异常并返回None
    result = engine._try_decision_engine(message)
    
    assert result is None, f"Expected None when exception occurs, got {result}"
    
    print("✓ 测试3通过")


def test_4_logging():
    """测试4：日志输出正确"""
    print("\n测试4：日志输出正确")
    
    config = {}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 设置日志捕获
    log_messages = []
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            log_messages.append({
                'level': record.levelname,
                'message': record.getMessage()
            })
    
    handler = LogCapture()
    engine.logger.addHandler(handler)
    
    # 测试4a：成功情况 - 应该没有警告或错误
    mock_decision_engine = Mock()
    mock_decision_engine.decide = Mock(return_value=1)
    engine.decision_engine = mock_decision_engine
    
    message = {
        "actionList": [
            ["PASS"],
            ["SINGLE", "3", ["H3"]]
        ]
    }
    
    log_messages.clear()
    result = engine._try_decision_engine(message)
    
    # 成功时不应该有ERROR日志
    error_logs = [log for log in log_messages if log['level'] == 'ERROR']
    assert len(error_logs) == 0, f"Should not have ERROR logs on success, got {error_logs}"
    
    # 测试4b：失败情况 - 应该有ERROR日志
    mock_decision_engine.decide = Mock(side_effect=RuntimeError("Test error"))
    
    log_messages.clear()
    result = engine._try_decision_engine(message)
    
    # 失败时应该有ERROR日志
    error_logs = [log for log in log_messages if log['level'] == 'ERROR']
    assert len(error_logs) > 0, "Should have ERROR log on failure"
    assert "DecisionEngine decision error" in error_logs[0]['message'], \
        f"Error log should mention DecisionEngine, got: {error_logs[0]['message']}"
    
    print("✓ 测试4通过")


def test_5_return_type():
    """测试5：返回值类型正确"""
    print("\n测试5：返回值类型正确")
    
    config = {}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    mock_decision_engine = Mock()
    engine.decision_engine = mock_decision_engine
    
    message = {
        "actionList": [
            ["PASS"],
            ["SINGLE", "3", ["H3"]]
        ]
    }
    
    # 测试5a：成功时返回int
    mock_decision_engine.decide = Mock(return_value=1)
    result = engine._try_decision_engine(message)
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    
    # 测试5b：失败时返回None
    mock_decision_engine.decide = Mock(side_effect=RuntimeError("Test error"))
    result = engine._try_decision_engine(message)
    assert result is None, f"Expected None on failure, got {result}"
    
    # 测试5c：空actionList时返回0
    mock_decision_engine.decide = Mock(return_value=0)
    message_empty = {"actionList": []}
    result = engine._try_decision_engine(message_empty)
    assert result == 0, f"Expected 0 for empty actionList, got {result}"
    
    print("✓ 测试5通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Task 5 验证：_try_decision_engine() 方法测试")
    print("=" * 60)
    
    # 设置日志级别，避免干扰测试输出
    logging.getLogger().setLevel(logging.CRITICAL)
    
    tests = [
        test_1_normal_call,
        test_2_invalid_return_value,
        test_3_exception_handling,
        test_4_logging,
        test_5_return_type
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ 测试异常: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果：通过 {passed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
