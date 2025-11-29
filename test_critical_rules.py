# -*- coding: utf-8 -*-
"""
测试关键规则层 (Critical Rules Layer)
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4


def test_teammate_protection():
    """测试队友保护规则"""
    print("\n" + "="*60)
    print("测试 1: 队友保护规则")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    # 场景：队友（位置2）剩余3张牌，且是最大牌持有者
    message = {
        "myPos": 0,
        "greaterPos": 2,  # 队友是最大牌持有者
        "curPos": 2,
        "stage": "playing",
        "type": "passive",
        "publicInfo": [
            {"rest": 10},  # 我方剩余10张
            {"rest": 15},  # 对手1剩余15张
            {"rest": 3},   # 队友剩余3张 (关键!)
            {"rest": 12}   # 对手2剩余12张
        ],
        "curAction": ["Single", "A", [["H", "A"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "2", [["S", "2"]]],
            ["Single", "B", [["B", "B"]]]
        ]
    }
    
    result = engine._apply_critical_rules(message)
    
    if result == 0:
        print("✓ 测试通过: 队友剩余3张牌，触发保护规则，返回 PASS (0)")
    else:
        print(f"✗ 测试失败: 期望返回 0 (PASS)，实际返回 {result}")
    
    return result == 0


def test_opponent_suppression():
    """测试对手压制规则"""
    print("\n" + "="*60)
    print("测试 2: 对手压制规则")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    # 场景：下家（位置1）剩余2张牌
    message = {
        "myPos": 0,
        "greaterPos": 1,  # 对手是最大牌持有者
        "curPos": 1,
        "stage": "playing",
        "type": "passive",
        "publicInfo": [
            {"rest": 10},  # 我方剩余10张
            {"rest": 2},   # 对手1剩余2张 (危险!)
            {"rest": 15},  # 队友剩余15张
            {"rest": 12}   # 对手2剩余12张
        ],
        "curAction": ["Single", "K", [["H", "K"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "A", [["S", "A"]]],
            ["Single", "2", [["D", "2"]]]
        ]
    }
    
    result = engine._apply_critical_rules(message)
    
    if result is not None and result != 0:
        print(f"✓ 测试通过: 对手剩余2张牌，触发压制规则，返回动作 {result}")
        print(f"  选择的动作: {message['actionList'][result]}")
    else:
        print(f"✗ 测试失败: 期望返回非0动作，实际返回 {result}")
    
    return result is not None and result != 0


def test_no_critical_rule():
    """测试无关键规则触发的情况"""
    print("\n" + "="*60)
    print("测试 3: 无关键规则触发")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    # 场景：正常游戏状态，无紧急情况
    message = {
        "myPos": 0,
        "greaterPos": 1,
        "curPos": 1,
        "stage": "playing",
        "type": "passive",
        "publicInfo": [
            {"rest": 15},  # 我方剩余15张
            {"rest": 18},  # 对手1剩余18张
            {"rest": 20},  # 队友剩余20张
            {"rest": 16}   # 对手2剩余16张
        ],
        "curAction": ["Single", "5", [["H", "5"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "7", [["S", "7"]]],
            ["Single", "K", [["D", "K"]]]
        ]
    }
    
    result = engine._apply_critical_rules(message)
    
    if result is None:
        print("✓ 测试通过: 无紧急情况，返回 None，继续正常决策流程")
    else:
        print(f"✗ 测试失败: 期望返回 None，实际返回 {result}")
    
    return result is None


def test_card_value_conversion():
    """测试牌值转换"""
    print("\n" + "="*60)
    print("测试 4: 牌值转换")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    test_cases = [
        ("3", 3),
        ("7", 7),
        ("T", 10),
        ("10", 10),
        ("J", 11),
        ("Q", 12),
        ("K", 13),
        ("A", 14),
        ("2", 15),
        ("B", 16),
        ("R", 17),
    ]
    
    all_passed = True
    for rank, expected_value in test_cases:
        result = engine._get_card_value(rank)
        if result == expected_value:
            print(f"✓ {rank} -> {result}")
        else:
            print(f"✗ {rank} -> {result} (期望: {expected_value})")
            all_passed = False
    
    return all_passed


def test_find_best_beat_action():
    """测试寻找最佳压制动作"""
    print("\n" + "="*60)
    print("测试 5: 寻找最佳压制动作")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    # 场景：当前牌是K，我们有A和2
    message = {
        "curAction": ["Single", "K", [["H", "K"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "A", [["S", "A"]]],  # 应该选这个（最小的能压制的牌）
            ["Single", "2", [["D", "2"]]],
            ["Bomb", "5", [["H", "5"], ["S", "5"], ["D", "5"], ["C", "5"]]]
        ]
    }
    
    result = engine._find_best_beat_action(message, message["actionList"])
    
    if result == 1:
        print(f"✓ 测试通过: 选择了A (索引1) 来压制K")
        print(f"  选择的动作: {message['actionList'][result]}")
    else:
        print(f"✗ 测试失败: 期望返回 1 (A)，实际返回 {result}")
        if result is not None:
            print(f"  选择的动作: {message['actionList'][result]}")
    
    return result == 1


def test_integration():
    """集成测试：完整决策流程"""
    print("\n" + "="*60)
    print("测试 6: 集成测试 - 完整决策流程")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={"performance_threshold": 1.0})
    
    # 场景：队友快走完了
    message = {
        "myPos": 0,
        "greaterPos": 2,
        "curPos": 2,
        "stage": "playing",
        "type": "passive",
        "publicInfo": [
            {"rest": 10},
            {"rest": 15},
            {"rest": 2},   # 队友剩余2张
            {"rest": 12}
        ],
        "curAction": ["Single", "A", [["H", "A"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "2", [["S", "2"]]]
        ],
        "handCards": "S2,D3,H4"
    }
    
    try:
        result = engine.decide(message)
        print(f"✓ 决策成功: 返回动作 {result}")
        print(f"  选择的动作: {message['actionList'][result]}")
        
        # 检查统计
        stats = engine.get_statistics()
        print(f"\n统计信息:")
        print(f"  总决策次数: {stats['total_decisions']}")
        print(f"  层使用情况:")
        for layer, usage in stats['layer_usage'].items():
            if usage['success'] > 0 or usage['failure'] > 0:
                print(f"    {layer}: 成功={usage['success']}, 失败={usage['failure']}")
        
        return result == 0  # 应该返回PASS
        
    except Exception as e:
        print(f"✗ 决策失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("关键规则层测试套件")
    print("="*60)
    
    tests = [
        ("队友保护规则", test_teammate_protection),
        ("对手压制规则", test_opponent_suppression),
        ("无关键规则触发", test_no_critical_rule),
        ("牌值转换", test_card_value_conversion),
        ("寻找最佳压制动作", test_find_best_beat_action),
        ("集成测试", test_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过!")
        return True
    else:
        print(f"\n⚠️  有 {total_count - passed_count} 个测试失败")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
