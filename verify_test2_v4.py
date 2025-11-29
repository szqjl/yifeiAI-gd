# -*- coding: utf-8 -*-
"""
验证Test2_V4客户端实现
测试客户端初始化、基本功能和与Test1_V4的一致性
"""
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_import():
    """测试导入Test2_V4客户端"""
    print("=" * 60)
    print("测试1: 导入Test2_V4客户端")
    print("=" * 60)
    
    try:
        from src.communication.Test2_V4 import Test2V4Client
        print("✓ 成功导入Test2V4Client")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_initialization():
    """测试客户端初始化"""
    print("\n" + "=" * 60)
    print("测试2: 客户端初始化")
    print("=" * 60)
    
    try:
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建客户端实例
        client = Test2V4Client(player_id=1)
        
        # 验证属性
        assert client.user_info == "Test2_V4", "user_info不匹配"
        assert client.player_id == 1, "player_id不匹配"
        assert client.decision_engine is not None, "decision_engine未初始化"
        assert client.websocket is None, "websocket应该初始为None"
        
        print("✓ 客户端初始化成功")
        print(f"  - user_info: {client.user_info}")
        print(f"  - player_id: {client.player_id}")
        print(f"  - decision_engine: {type(client.decision_engine).__name__}")
        print(f"  - config: {client.config}")
        
        return True
    
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_decision_engine():
    """测试决策引擎初始化"""
    print("\n" + "=" * 60)
    print("测试3: 决策引擎初始化")
    print("=" * 60)
    
    try:
        from src.communication.Test2_V4 import Test2V4Client
        from src.decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
        
        # 创建客户端
        client = Test2V4Client(player_id=1)
        
        # 验证决策引擎类型
        assert isinstance(client.decision_engine, HybridDecisionEngineV4), \
            "decision_engine类型不正确"
        
        # 验证决策引擎配置
        assert client.decision_engine.player_id == 1, "player_id不匹配"
        assert client.decision_engine.config is not None, "config未设置"
        
        print("✓ 决策引擎初始化成功")
        print(f"  - 类型: {type(client.decision_engine).__name__}")
        print(f"  - player_id: {client.decision_engine.player_id}")
        print(f"  - 统计: {client.decision_engine.get_statistics()}")
        
        return True
    
    except Exception as e:
        print(f"✗ 决策引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_consistency_with_test1():
    """测试与Test1_V4的一致性"""
    print("\n" + "=" * 60)
    print("测试4: 与Test1_V4的一致性")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建两个客户端
        client1 = Test1V4Client(player_id=0)
        client2 = Test2V4Client(player_id=1)
        
        # 验证类结构一致性
        test1_methods = set(dir(client1))
        test2_methods = set(dir(client2))
        
        # 检查关键方法是否都存在
        key_methods = [
            'connect', 'handle_messages', 'handle_act_message',
            'handle_notify_message', 'send_action', 'cleanup',
            'handle_game_start', 'handle_game_result', 'print_engine_statistics'
        ]
        
        for method in key_methods:
            assert method in test1_methods, f"Test1缺少方法: {method}"
            assert method in test2_methods, f"Test2缺少方法: {method}"
        
        # 验证配置一致性
        assert client1.config == client2.config, "配置不一致"
        
        # 验证决策引擎类型一致
        assert type(client1.decision_engine) == type(client2.decision_engine), \
            "决策引擎类型不一致"
        
        print("✓ 与Test1_V4一致性验证通过")
        print(f"  - 共同方法数: {len(test1_methods & test2_methods)}")
        print(f"  - 关键方法: {len(key_methods)} 个全部存在")
        print(f"  - 配置一致: ✓")
        print(f"  - 决策引擎类型一致: ✓")
        
        return True
    
    except Exception as e:
        print(f"✗ 一致性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_decision():
    """测试模拟决策"""
    print("\n" + "=" * 60)
    print("测试5: 模拟决策")
    print("=" * 60)
    
    try:
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建客户端
        client = Test2V4Client(player_id=1)
        
        # 创建模拟消息
        mock_message = {
            "type": "act",
            "stage": "playing",
            "actionList": [
                ["PASS", "", "PASS"],
                ["Single", "4", ["H4"]],
                ["Single", "5", ["S5"]]
            ],
            "handCards": ["H4", "S5", "D6"],
            "curAction": ["PASS", "", "PASS"],
            "publicInfo": [
                {"rest": 10, "playArea": None},
                {"rest": 10, "playArea": None},
                {"rest": 10, "playArea": None},
                {"rest": 10, "playArea": None}
            ]
        }
        
        # 调用决策引擎
        action = client.decision_engine.decide(mock_message)
        
        # 验证返回值
        assert isinstance(action, int), "返回值应该是整数"
        assert 0 <= action < len(mock_message["actionList"]), \
            f"返回值{action}超出范围[0, {len(mock_message['actionList'])})"
        
        print("✓ 模拟决策成功")
        print(f"  - 动作列表长度: {len(mock_message['actionList'])}")
        print(f"  - 选择的动作索引: {action}")
        print(f"  - 选择的动作: {mock_message['actionList'][action]}")
        
        # 打印统计
        stats = client.decision_engine.get_statistics()
        print(f"  - 决策统计: 总决策={stats['total_decisions']}")
        
        return True
    
    except Exception as e:
        print(f"✗ 模拟决策失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_team_setup():
    """测试Test1和Test2作为队友的设置"""
    print("\n" + "=" * 60)
    print("测试6: Test1和Test2队友设置")
    print("=" * 60)
    
    try:
        from src.communication.Test1_V4 import Test1V4Client
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建队友客户端
        test1 = Test1V4Client(player_id=0)
        test2 = Test2V4Client(player_id=1)
        
        # 验证玩家位置
        assert test1.player_id == 0, "Test1应该是player 0"
        assert test2.player_id == 1, "Test2应该是player 1"
        
        # 在掼蛋中，0和2是队友，1和3是队友
        # 所以Test1(0)和Test2(1)不是队友，但可以一起对战
        print("✓ 队友设置验证通过")
        print(f"  - Test1 player_id: {test1.player_id}")
        print(f"  - Test2 player_id: {test2.player_id}")
        print(f"  - 注意: 在掼蛋中，0和2是队友，1和3是队友")
        print(f"  - Test1_V4和Test2_V4可以作为对手或配合测试")
        
        return True
    
    except Exception as e:
        print(f"✗ 队友设置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_independent_instances():
    """测试独立实例"""
    print("\n" + "=" * 60)
    print("测试7: 独立实例验证")
    print("=" * 60)
    
    try:
        from src.communication.Test2_V4 import Test2V4Client
        
        # 创建多个Test2实例
        client1 = Test2V4Client(player_id=1)
        client2 = Test2V4Client(player_id=1)
        
        # 验证实例独立性
        assert client1 is not client2, "实例应该不同"
        assert client1.decision_engine is not client2.decision_engine, \
            "决策引擎应该独立"
        assert client1.user_info != client2.user_info, "user_info应该不同"
        
        print("✓ 独立实例验证通过")
        print(f"  - 实例1: {client1.user_info}")
        print(f"  - 实例2: {client2.user_info}")
        print(f"  - 决策引擎独立: ✓")
        
        return True
    
    except Exception as e:
        print(f"✗ 独立实例测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Test2_V4 客户端验证")
    print("=" * 60)
    
    tests = [
        ("导入测试", test_import),
        ("初始化测试", test_initialization),
        ("决策引擎测试", test_decision_engine),
        ("与Test1一致性测试", test_consistency_with_test1),
        ("模拟决策测试", test_mock_decision),
        ("队友设置测试", test_team_setup),
        ("独立实例测试", test_independent_instances)
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
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("✓ 所有测试通过!")
    else:
        print(f"✗ {total - passed} 个测试失败")
    
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
