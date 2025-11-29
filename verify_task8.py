# -*- coding: utf-8 -*-
"""
验证任务8：异常处理和后备链
测试HybridDecisionEngineV4的4层决策机制
"""

import sys
import logging
from unittest.mock import Mock, patch

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

def test_layer1_success():
    """测试1: Layer 1成功，不应调用其他层"""
    print("\n" + "="*60)
    print("测试1: Layer 1 (lalala) 成功")
    print("="*60)
    
    from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    
    # 创建引擎
    config = {"performance_threshold": 1.0}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟消息
    message = {
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "4", [["H", "4"]]],
            ["Single", "5", [["S", "5"]]]
        ],
        "handCards": [["H", "4"], ["S", "5"]],
        "stage": "play"
    }
    
    # Mock lalala adapter返回成功
    with patch.object(engine, '_try_lalala', return_value=1):
        with patch.object(engine, '_try_decision_engine') as mock_de:
            with patch.object(engine, '_try_knowledge_enhanced') as mock_ke:
                action = engine.decide(message)
                
                # 验证
                assert action == 1, f"Expected action=1, got {action}"
                assert not mock_de.called, "DecisionEngine should not be called"
                assert not mock_ke.called, "KnowledgeEnhanced should not be called"
                
                # 验证统计
                stats = engine.get_statistics()
                assert stats["layer_usage"]["lalala"]["success"] == 1
                assert stats["layer_usage"]["DecisionEngine"]["success"] == 0
                
                print("✓ Layer 1成功，其他层未被调用")
                print(f"✓ 统计数据正确: {stats['layer_usage']['lalala']}")
                return True


def test_layer1_to_layer2_fallback():
    """测试2: Layer 1失败，fallback到Layer 2"""
    print("\n" + "="*60)
    print("测试2: Layer 1失败 → Layer 2成功")
    print("="*60)
    
    from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    
    # 创建引擎
    config = {"performance_threshold": 1.0}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟消息
    message = {
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "4", [["H", "4"]]]
        ],
        "handCards": [["H", "4"]],
        "stage": "play"
    }
    
    # Mock Layer 1失败，Layer 2成功
    with patch.object(engine, '_try_lalala', side_effect=Exception("lalala error")):
        with patch.object(engine, '_try_decision_engine', return_value=1):
            with patch.object(engine, '_try_knowledge_enhanced') as mock_ke:
                action = engine.decide(message)
                
                # 验证
                assert action == 1, f"Expected action=1, got {action}"
                assert not mock_ke.called, "KnowledgeEnhanced should not be called"
                
                # 验证统计
                stats = engine.get_statistics()
                assert stats["layer_usage"]["lalala"]["failure"] == 1
                assert stats["layer_usage"]["DecisionEngine"]["success"] == 1
                
                print("✓ Layer 1失败，成功fallback到Layer 2")
                print(f"✓ lalala失败统计: {stats['layer_usage']['lalala']}")
                print(f"✓ DecisionEngine成功统计: {stats['layer_usage']['DecisionEngine']}")
                return True


def test_layer1_2_to_layer3_fallback():
    """测试3: Layer 1-2失败，fallback到Layer 3"""
    print("\n" + "="*60)
    print("测试3: Layer 1-2失败 → Layer 3成功")
    print("="*60)
    
    from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    
    # 创建引擎
    config = {"performance_threshold": 1.0}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟消息
    message = {
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "4", [["H", "4"]]]
        ],
        "handCards": [["H", "4"]],
        "stage": "play"
    }
    
    # Mock Layer 1-2失败，Layer 3成功
    with patch.object(engine, '_try_lalala', return_value=None):
        with patch.object(engine, '_try_decision_engine', side_effect=ValueError("DE error")):
            with patch.object(engine, '_try_knowledge_enhanced', return_value=1):
                action = engine.decide(message)
                
                # 验证
                assert action == 1, f"Expected action=1, got {action}"
                
                # 验证统计
                stats = engine.get_statistics()
                assert stats["layer_usage"]["lalala"]["failure"] == 1
                assert stats["layer_usage"]["DecisionEngine"]["failure"] == 1
                assert stats["layer_usage"]["KnowledgeEnhanced"]["success"] == 1
                
                print("✓ Layer 1-2失败，成功fallback到Layer 3")
                print(f"✓ KnowledgeEnhanced成功统计: {stats['layer_usage']['KnowledgeEnhanced']}")
                return True


def test_layer1_2_3_to_layer4_fallback():
    """测试4: Layer 1-3失败，fallback到Layer 4"""
    print("\n" + "="*60)
    print("测试4: Layer 1-3失败 → Layer 4 (Random)")
    print("="*60)
    
    from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    
    # 创建引擎
    config = {"performance_threshold": 1.0}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟消息
    message = {
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "4", [["H", "4"]]],
            ["Single", "5", [["S", "5"]]]
        ],
        "handCards": [["H", "4"], ["S", "5"]],
        "stage": "play"
    }
    
    # Mock Layer 1-3全部失败
    with patch.object(engine, '_try_lalala', return_value=None):
        with patch.object(engine, '_try_decision_engine', return_value=None):
            with patch.object(engine, '_try_knowledge_enhanced', side_effect=RuntimeError("KE error")):
                action = engine.decide(message)
                
                # 验证
                assert 0 <= action < len(message["actionList"]), f"Invalid action: {action}"
                
                # 验证统计
                stats = engine.get_statistics()
                assert stats["layer_usage"]["lalala"]["failure"] == 1
                assert stats["layer_usage"]["DecisionEngine"]["failure"] == 1
                assert stats["layer_usage"]["KnowledgeEnhanced"]["failure"] == 1
                assert stats["layer_usage"]["Random"]["success"] == 1
                
                print(f"✓ Layer 1-3全部失败，Layer 4返回有效动作: {action}")
                print(f"✓ Random成功统计: {stats['layer_usage']['Random']}")
                return True


def test_layer4_always_succeeds():
    """测试5: Layer 4总是返回有效动作"""
    print("\n" + "="*60)
    print("测试5: Layer 4保证总是成功")
    print("="*60)
    
    from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    
    # 创建引擎
    config = {"performance_threshold": 1.0}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 测试各种边界情况
    test_cases = [
        {
            "name": "正常actionList",
            "message": {
                "actionList": [["PASS", "", "PASS"], ["Single", "4", [["H", "4"]]]],
                "handCards": [["H", "4"]]
            }
        },
        {
            "name": "空actionList",
            "message": {
                "actionList": [],
                "handCards": []
            }
        },
        {
            "name": "只有PASS",
            "message": {
                "actionList": [["PASS", "", "PASS"]],
                "handCards": []
            }
        },
        {
            "name": "多个动作",
            "message": {
                "actionList": [
                    ["PASS", "", "PASS"],
                    ["Single", "4", [["H", "4"]]],
                    ["Single", "5", [["S", "5"]]],
                    ["Pair", "6", [["D", "6"], ["C", "6"]]]
                ],
                "handCards": [["H", "4"], ["S", "5"], ["D", "6"], ["C", "6"]]
            }
        }
    ]
    
    all_passed = True
    for test_case in test_cases:
        try:
            action = engine._random_valid_action(test_case["message"])
            action_list = test_case["message"]["actionList"]
            
            if action_list:
                assert 0 <= action < len(action_list), f"Invalid action: {action}"
            else:
                assert action == 0, f"Expected 0 for empty list, got {action}"
            
            print(f"  ✓ {test_case['name']}: action={action}")
        except Exception as e:
            print(f"  ✗ {test_case['name']}: {e}")
            all_passed = False
    
    if all_passed:
        print("✓ Layer 4在所有情况下都返回有效动作")
        return True
    else:
        print("✗ Layer 4在某些情况下失败")
        return False


def test_statistics_recording():
    """测试6: 统计数据正确记录"""
    print("\n" + "="*60)
    print("测试6: 统计数据记录")
    print("="*60)
    
    from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    
    # 创建引擎
    config = {"performance_threshold": 1.0}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟消息
    message = {
        "actionList": [["PASS", "", "PASS"], ["Single", "4", [["H", "4"]]]],
        "handCards": [["H", "4"]],
        "stage": "play"
    }
    
    # 执行多次决策，模拟不同的成功/失败场景
    # 决策1: Layer 1成功
    with patch.object(engine, '_try_lalala', return_value=1):
        engine.decide(message)
    
    # 决策2: Layer 1失败，Layer 2成功
    with patch.object(engine, '_try_lalala', return_value=None):
        with patch.object(engine, '_try_decision_engine', return_value=0):
            engine.decide(message)
    
    # 决策3: Layer 1成功
    with patch.object(engine, '_try_lalala', return_value=1):
        engine.decide(message)
    
    # 验证统计
    stats = engine.get_statistics()
    
    print(f"总决策次数: {stats['total_decisions']}")
    print(f"lalala: {stats['layer_usage']['lalala']}")
    print(f"DecisionEngine: {stats['layer_usage']['DecisionEngine']}")
    
    assert stats['total_decisions'] == 3, f"Expected 3 decisions, got {stats['total_decisions']}"
    assert stats['layer_usage']['lalala']['success'] == 2, "Expected 2 lalala successes"
    assert stats['layer_usage']['lalala']['failure'] == 1, "Expected 1 lalala failure"
    assert stats['layer_usage']['DecisionEngine']['success'] == 1, "Expected 1 DE success"
    
    # 测试成功率计算
    lalala_rate = stats['success_rates']['lalala']
    expected_rate = 2 / 3  # 2 successes out of 3 attempts
    assert abs(lalala_rate - expected_rate) < 0.01, f"Expected rate ~{expected_rate}, got {lalala_rate}"
    
    print(f"✓ lalala成功率: {lalala_rate:.2%}")
    print("✓ 统计数据记录正确")
    
    # 测试重置
    engine.reset_statistics()
    stats = engine.get_statistics()
    assert stats['total_decisions'] == 0, "Statistics not reset"
    print("✓ 统计重置功能正常")
    
    return True


def test_performance_monitoring():
    """测试7: 性能监控和警告"""
    print("\n" + "="*60)
    print("测试7: 性能监控")
    print("="*60)
    
    from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    import time
    
    # 创建引擎，设置较低的阈值
    config = {"performance_threshold": 0.1}
    engine = HybridDecisionEngineV4(player_id=0, config=config)
    
    # 模拟消息
    message = {
        "actionList": [["PASS", "", "PASS"], ["Single", "4", [["H", "4"]]]],
        "handCards": [["H", "4"]],
        "stage": "play"
    }
    
    # Mock一个慢速的Layer 1
    def slow_lalala(msg):
        time.sleep(0.15)  # 超过阈值
        return 1
    
    with patch.object(engine, '_try_lalala', side_effect=slow_lalala):
        action = engine.decide(message)
        
        # 验证决策成功
        assert action == 1, f"Expected action=1, got {action}"
        
        # 验证统计中记录了耗时
        stats = engine.get_statistics()
        assert stats['layer_usage']['lalala']['total_time'] > 0.1
        
        print(f"✓ 慢速决策被检测: {stats['layer_usage']['lalala']['total_time']:.3f}s")
        print("✓ 性能监控正常工作")
        return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("验证任务8：异常处理和后备链")
    print("="*60)
    
    tests = [
        ("Layer 1成功", test_layer1_success),
        ("Layer 1→2 fallback", test_layer1_to_layer2_fallback),
        ("Layer 1-2→3 fallback", test_layer1_2_to_layer3_fallback),
        ("Layer 1-3→4 fallback", test_layer1_2_3_to_layer4_fallback),
        ("Layer 4总是成功", test_layer4_always_succeeds),
        ("统计数据记录", test_statistics_recording),
        ("性能监控", test_performance_monitoring)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("\n✓✓✓ 任务8已完成 ✓✓✓")
        print("所有异常处理和后备链测试通过！")
        return True
    else:
        print(f"\n✗ 还有 {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
