# -*- coding: utf-8 -*-
"""
验证 Task 1.1: 关键规则层集成
确保与现有系统兼容
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4


def verify_backward_compatibility():
    """验证向后兼容性"""
    print("="*60)
    print("验证向后兼容性")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    # 正常消息（无紧急情况）应该继续走原有流程
    normal_message = {
        "myPos": 0,
        "greaterPos": 1,
        "curPos": 1,
        "stage": "playing",
        "type": "passive",
        "publicInfo": [
            {"rest": 15},
            {"rest": 18},
            {"rest": 20},
            {"rest": 16}
        ],
        "curAction": ["Single", "5", [["H", "5"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "7", [["S", "7"]]]
        ],
        "handCards": "S7,D8,H9"
    }
    
    # 关键规则不应该触发
    critical_result = engine._apply_critical_rules(normal_message)
    
    if critical_result is None:
        print("✓ 正常情况下关键规则不触发，保持原有流程")
        return True
    else:
        print(f"✗ 关键规则意外触发: {critical_result}")
        return False


def verify_statistics_tracking():
    """验证统计系统"""
    print("\n" + "="*60)
    print("验证统计系统")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    # 触发关键规则
    critical_message = {
        "myPos": 0,
        "greaterPos": 2,
        "curPos": 2,
        "stage": "playing",
        "type": "passive",
        "publicInfo": [
            {"rest": 10},
            {"rest": 15},
            {"rest": 2},
            {"rest": 12}
        ],
        "curAction": ["Single", "A", [["H", "A"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "2", [["S", "2"]]]
        ],
        "handCards": "S2,D3"
    }
    
    result = engine.decide(critical_message)
    stats = engine.get_statistics()
    
    print(f"决策结果: {result}")
    print(f"总决策次数: {stats['total_decisions']}")
    print(f"CriticalRules 成功次数: {stats['layer_usage']['CriticalRules']['success']}")
    
    if stats['layer_usage']['CriticalRules']['success'] == 1:
        print("✓ 统计系统正常工作")
        return True
    else:
        print("✗ 统计系统异常")
        return False


def verify_layer_priority():
    """验证层优先级"""
    print("\n" + "="*60)
    print("验证层优先级")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    # 队友保护优先级高于对手压制
    message = {
        "myPos": 0,
        "greaterPos": 2,  # 队友控场
        "curPos": 2,
        "stage": "playing",
        "type": "passive",
        "publicInfo": [
            {"rest": 10},
            {"rest": 3},   # 对手也快走完
            {"rest": 2},   # 但队友更快
            {"rest": 12}
        ],
        "curAction": ["Single", "A", [["H", "A"]]],
        "actionList": [
            ["PASS", "", "PASS"],
            ["Single", "2", [["S", "2"]]]
        ],
        "handCards": "S2"
    }
    
    result = engine._apply_critical_rules(message)
    
    if result == 0:
        print("✓ 队友保护优先级正确（PASS）")
        return True
    else:
        print(f"✗ 优先级错误，应该PASS但返回 {result}")
        return False


def verify_edge_cases():
    """验证边界情况"""
    print("\n" + "="*60)
    print("验证边界情况")
    print("="*60)
    
    engine = HybridDecisionEngineV4(player_id=0, config={})
    
    test_cases = [
        {
            "name": "空动作列表",
            "message": {
                "myPos": 0,
                "publicInfo": [],
                "actionList": []
            },
            "expected": None
        },
        {
            "name": "缺少publicInfo",
            "message": {
                "myPos": 0,
                "actionList": [["PASS", "", "PASS"]]
            },
            "expected": None
        },
        {
            "name": "只有PASS动作",
            "message": {
                "myPos": 0,
                "greaterPos": 1,
                "publicInfo": [
                    {"rest": 10},
                    {"rest": 2},
                    {"rest": 15},
                    {"rest": 12}
                ],
                "actionList": [["PASS", "", "PASS"]]
            },
            "expected": None  # 无法压制
        }
    ]
    
    all_passed = True
    for case in test_cases:
        result = engine._apply_critical_rules(case["message"])
        if result == case["expected"]:
            print(f"✓ {case['name']}: 正确")
        else:
            print(f"✗ {case['name']}: 期望 {case['expected']}, 实际 {result}")
            all_passed = False
    
    return all_passed


def main():
    """主验证流程"""
    print("\n" + "="*60)
    print("Task 1.1 验证套件")
    print("="*60)
    
    tests = [
        ("向后兼容性", verify_backward_compatibility),
        ("统计系统", verify_statistics_tracking),
        ("层优先级", verify_layer_priority),
        ("边界情况", verify_edge_cases),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ 验证 '{name}' 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"{status} {name}")
    
    print(f"\n总计: {passed_count}/{total_count} 验证通过")
    
    if passed_count == total_count:
        print("\n✅ Task 1.1 验证通过，可以提交!")
        return True
    else:
        print(f"\n⚠️  有 {total_count - passed_count} 个验证失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
