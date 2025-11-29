# -*- coding: utf-8 -*-
"""
验证Task 10和Task 11的集成
检查Test1_V4和Test2_V4是否有冲突
"""
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_both_imports():
    """测试1: 同时导入两个客户端"""
    print("=" * 60)
    print("测试1: 同时导入Test1_V4和Test2_V4")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        print("✓ 成功同时导入Test1V4Client和Test2V4Client")
        print(f"  - Test1V4Client: {Test1V4Client}")
        print(f"  - Test2V4Client: {Test2V4Client}")
        
        # 验证是不同的类
        assert Test1V4Client != Test2V4Client, "两个类不应该相同"
        print("✓ 两个类是独立的")
        
        return True
    
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simultaneous_initialization():
    """测试2: 同时初始化两个客户端"""
    print("\n" + "=" * 60)
    print("测试2: 同时初始化两个客户端")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 同时创建两个客户端
        client1 = Test1V4Client(player_id=0)
        client2 = Test2V4Client(player_id=1)
        
        print("✓ 成功同时初始化两个客户端")
        print(f"  - Test1: player_id={client1.player_id}, user_info={client1.user_info}")
        print(f"  - Test2: player_id={client2.player_id}, user_info={client2.user_info}")
        
        # 验证player_id不同
        assert client1.player_id == 0, "Test1应该是player 0"
        assert client2.player_id == 1, "Test2应该是player 1"
        assert client1.player_id != client2.player_id, "player_id应该不同"
        
        print("✓ player_id正确且不冲突")
        
        return True
    
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_decision_engine_isolation():
    """测试3: 决策引擎隔离"""
    print("\n" + "=" * 60)
    print("测试3: 决策引擎状态隔离")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建两个客户端
        client1 = Test1V4Client(player_id=0)
        client2 = Test2V4Client(player_id=1)
        
        # 验证决策引擎是独立的
        assert client1.decision_engine is not client2.decision_engine, \
            "决策引擎应该是独立的实例"
        
        # 验证决策引擎的player_id正确
        assert client1.decision_engine.player_id == 0, "Test1的引擎应该是player 0"
        assert client2.decision_engine.player_id == 1, "Test2的引擎应该是player 1"
        
        print("✓ 决策引擎完全隔离")
        print(f"  - Test1引擎: {id(client1.decision_engine)}, player_id={client1.decision_engine.player_id}")
        print(f"  - Test2引擎: {id(client2.decision_engine)}, player_id={client2.decision_engine.player_id}")
        
        return True
    
    except Exception as e:
        print(f"✗ 隔离测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concurrent_decisions():
    """测试4: 并发决策"""
    print("\n" + "=" * 60)
    print("测试4: 并发决策测试")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建两个客户端
        client1 = Test1V4Client(player_id=0)
        client2 = Test2V4Client(player_id=1)
        
        # 创建模拟消息
        mock_message = {
            "type": "act",
            "stage": "playing",
            "actionList": [
                ["PASS", "", "PASS"],
                ["Single", "4", ["H4"]],
                ["Single", "5", ["S5"]],
                ["Single", "6", ["D6"]]
            ],
            "handCards": ["H4", "S5", "D6", "C7"],
            "curAction": ["PASS", "", "PASS"],
            "publicInfo": [
                {"rest": 10, "playArea": None},
                {"rest": 10, "playArea": None},
                {"rest": 10, "playArea": None},
                {"rest": 10, "playArea": None}
            ]
        }
        
        # 两个客户端同时做决策
        action1 = client1.decision_engine.decide(mock_message)
        action2 = client2.decision_engine.decide(mock_message)
        
        # 验证返回值有效
        assert isinstance(action1, int), "Test1返回值应该是整数"
        assert isinstance(action2, int), "Test2返回值应该是整数"
        assert 0 <= action1 < len(mock_message["actionList"]), "Test1动作索引超出范围"
        assert 0 <= action2 < len(mock_message["actionList"]), "Test2动作索引超出范围"
        
        print("✓ 并发决策成功")
        print(f"  - Test1选择: action={action1} ({mock_message['actionList'][action1][0]})")
        print(f"  - Test2选择: action={action2} ({mock_message['actionList'][action2][0]})")
        
        # 获取统计信息
        stats1 = client1.decision_engine.get_statistics()
        stats2 = client2.decision_engine.get_statistics()
        
        print(f"  - Test1决策次数: {stats1['total_decisions']}")
        print(f"  - Test2决策次数: {stats2['total_decisions']}")
        
        # 验证统计独立
        assert stats1['total_decisions'] == 1, "Test1应该有1次决策"
        assert stats2['total_decisions'] == 1, "Test2应该有1次决策"
        
        print("✓ 统计信息独立")
        
        return True
    
    except Exception as e:
        print(f"✗ 并发决策失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics_isolation():
    """测试5: 统计信息隔离"""
    print("\n" + "=" * 60)
    print("测试5: 统计信息隔离")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建两个客户端
        client1 = Test1V4Client(player_id=0)
        client2 = Test2V4Client(player_id=1)
        
        # 模拟消息
        mock_message = {
            "type": "act",
            "actionList": [["PASS", "", "PASS"], ["Single", "4", ["H4"]]],
            "handCards": ["H4"],
            "publicInfo": [{"rest": 10, "playArea": None}] * 4
        }
        
        # Test1做3次决策
        for i in range(3):
            client1.decision_engine.decide(mock_message)
        
        # Test2做5次决策
        for i in range(5):
            client2.decision_engine.decide(mock_message)
        
        # 获取统计
        stats1 = client1.decision_engine.get_statistics()
        stats2 = client2.decision_engine.get_statistics()
        
        # 验证统计独立
        assert stats1['total_decisions'] == 3, f"Test1应该有3次决策，实际{stats1['total_decisions']}"
        assert stats2['total_decisions'] == 5, f"Test2应该有5次决策，实际{stats2['total_decisions']}"
        
        print("✓ 统计信息完全隔离")
        print(f"  - Test1: {stats1['total_decisions']} 次决策")
        print(f"  - Test2: {stats2['total_decisions']} 次决策")
        
        # 重置Test1统计
        client1.decision_engine.reset_statistics()
        stats1_after = client1.decision_engine.get_statistics()
        stats2_after = client2.decision_engine.get_statistics()
        
        # 验证重置只影响Test1
        assert stats1_after['total_decisions'] == 0, "Test1统计应该被重置"
        assert stats2_after['total_decisions'] == 5, "Test2统计不应该被影响"
        
        print("✓ 统计重置独立")
        print(f"  - Test1重置后: {stats1_after['total_decisions']} 次")
        print(f"  - Test2不受影响: {stats2_after['total_decisions']} 次")
        
        return True
    
    except Exception as e:
        print(f"✗ 统计隔离测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logger_isolation():
    """测试6: 日志隔离"""
    print("\n" + "=" * 60)
    print("测试6: 日志系统隔离")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建两个客户端
        client1 = Test1V4Client(player_id=0)
        client2 = Test2V4Client(player_id=1)
        
        # 验证logger是独立的
        assert client1.logger is not client2.logger, "logger应该是独立的"
        
        # 验证logger名称不同
        assert client1.logger.name != client2.logger.name, "logger名称应该不同"
        
        print("✓ 日志系统完全隔离")
        print(f"  - Test1 logger: {client1.logger.name}")
        print(f"  - Test2 logger: {client2.logger.name}")
        
        return True
    
    except Exception as e:
        print(f"✗ 日志隔离测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_structure_consistency():
    """测试7: 类结构一致性"""
    print("\n" + "=" * 60)
    print("测试7: 类结构一致性")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 获取类的方法
        test1_methods = set(dir(Test1V4Client))
        test2_methods = set(dir(Test2V4Client))
        
        # 检查方法是否一致
        test1_only = test1_methods - test2_methods
        test2_only = test2_methods - test1_methods
        common = test1_methods & test2_methods
        
        print(f"✓ 类结构分析:")
        print(f"  - 共同方法/属性: {len(common)} 个")
        print(f"  - Test1独有: {len(test1_only)} 个")
        print(f"  - Test2独有: {len(test2_only)} 个")
        
        if test1_only:
            print(f"  - Test1独有项: {test1_only}")
        if test2_only:
            print(f"  - Test2独有项: {test2_only}")
        
        # 验证关键方法都存在
        key_methods = ['__init__', 'connect', 'decision_engine', 'logger']
        for method in key_methods:
            assert method in test1_methods, f"Test1缺少: {method}"
            assert method in test2_methods, f"Test2缺少: {method}"
        
        print("✓ 关键方法都存在")
        
        return True
    
    except Exception as e:
        print(f"✗ 结构一致性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有集成测试"""
    print("\n" + "=" * 60)
    print("Task 10 & 11 集成验证")
    print("检查Test1_V4和Test2_V4是否有冲突")
    print("=" * 60)
    
    tests = [
        ("同时导入", test_both_imports),
        ("同时初始化", test_simultaneous_initialization),
        ("决策引擎隔离", test_decision_engine_isolation),
        ("并发决策", test_concurrent_decisions),
        ("统计信息隔离", test_statistics_isolation),
        ("日志系统隔离", test_logger_isolation),
        ("类结构一致性", test_class_structure_consistency)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name}执行异常: {e}")
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("集成测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("✓ 所有集成测试通过!")
        print("✓ Test1_V4和Test2_V4没有冲突")
        print("✓ 可以安全地同时使用")
    else:
        print(f"✗ {total - passed} 个测试失败")
        print("⚠ 存在潜在冲突，需要修复")
    
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
