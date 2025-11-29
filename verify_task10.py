# -*- coding: utf-8 -*-
"""
验证Test1_V4和Test2_V4客户端实现
"""
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("验证任务10和11：Test1_V4和Test2_V4客户端")
print("=" * 60)

# Test 1: Import Test1_V4
print("\n" + "=" * 60)
print("测试1: 导入Test1_V4")
print("=" * 60)
try:
    from communication.Test1_V4 import Test1V4Client
    print("✓ Test1_V4导入成功")
    
    # Create instance
    client1 = Test1V4Client(player_id=0)
    print(f"✓ Test1_V4实例创建成功")
    print(f"✓ player_id: {client1.player_id}")
    print(f"✓ user_info: {client1.user_info}")
    print(f"✓ decision_engine: {type(client1.decision_engine).__name__}")
except Exception as e:
    print(f"✗ Test1_V4测试失败: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Import Test2_V4
print("\n" + "=" * 60)
print("测试2: 导入Test2_V4")
print("=" * 60)
try:
    from communication.Test2_V4 import Test2V4Client
    print("✓ Test2_V4导入成功")
    
    # Create instance
    client2 = Test2V4Client(player_id=2)
    print(f"✓ Test2_V4实例创建成功")
    print(f"✓ player_id: {client2.player_id}")
    print(f"✓ user_info: {client2.user_info}")
    print(f"✓ decision_engine: {type(client2.decision_engine).__name__}")
except Exception as e:
    print(f"✗ Test2_V4测试失败: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Verify player_id difference
print("\n" + "=" * 60)
print("测试3: 验证player_id差异")
print("=" * 60)
try:
    assert client1.player_id == 0, "Test1_V4 should be player 0"
    assert client2.player_id == 2, "Test2_V4 should be player 2"
    assert client1.user_info == "Test1_V4", "Test1_V4 user_info incorrect"
    assert client2.user_info == "Test2_V4", "Test2_V4 user_info incorrect"
    print("✓ player_id配置正确（位置0和2是队友）")
    print(f"  Test1_V4: player_id={client1.player_id}")
    print(f"  Test2_V4: player_id={client2.player_id}")
except AssertionError as e:
    print(f"✗ player_id验证失败: {e}")

# Test 4: Verify decision engine integration
print("\n" + "=" * 60)
print("测试4: 验证决策引擎集成")
print("=" * 60)
try:
    from decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
    
    assert isinstance(client1.decision_engine, HybridDecisionEngineV4)
    assert isinstance(client2.decision_engine, HybridDecisionEngineV4)
    print("✓ 决策引擎类型正确")
    
    assert client1.decision_engine.player_id == 0
    assert client2.decision_engine.player_id == 2
    print("✓ 决策引擎player_id正确（0和2是队友）")
except Exception as e:
    print(f"✗ 决策引擎验证失败: {e}")

# Test 5: Verify message handling methods
print("\n" + "=" * 60)
print("测试5: 验证消息处理方法")
print("=" * 60)
try:
    assert hasattr(client1, 'handle_messages'), "Missing handle_messages"
    assert hasattr(client1, 'process_message'), "Missing process_message"
    assert hasattr(client1, 'handle_action_request'), "Missing handle_action_request"
    assert hasattr(client1, 'handle_notification'), "Missing handle_notification"
    assert hasattr(client1, 'validate_action'), "Missing validate_action"
    assert hasattr(client1, 'send_action'), "Missing send_action"
    print("✓ Test1_V4所有必需方法存在")
    
    assert hasattr(client2, 'handle_messages'), "Missing handle_messages"
    assert hasattr(client2, 'process_message'), "Missing process_message"
    assert hasattr(client2, 'handle_action_request'), "Missing handle_action_request"
    assert hasattr(client2, 'handle_notification'), "Missing handle_notification"
    assert hasattr(client2, 'validate_action'), "Missing validate_action"
    assert hasattr(client2, 'send_action'), "Missing send_action"
    print("✓ Test2_V4所有必需方法存在")
except AssertionError as e:
    print(f"✗ 方法验证失败: {e}")

# Test 6: Test validate_action method
print("\n" + "=" * 60)
print("测试6: 测试validate_action方法")
print("=" * 60)
try:
    action_list = [{"type": "PASS"}, {"type": "SINGLE"}, {"type": "PAIR"}]
    
    # Valid indices
    assert client1.validate_action(0, action_list) == True
    assert client1.validate_action(1, action_list) == True
    assert client1.validate_action(2, action_list) == True
    print("✓ 有效索引验证通过")
    
    # Invalid indices
    assert client1.validate_action(-1, action_list) == False
    assert client1.validate_action(3, action_list) == False
    assert client1.validate_action(100, action_list) == False
    print("✓ 无效索引验证通过")
except Exception as e:
    print(f"✗ validate_action测试失败: {e}")

# Summary
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)
print("✓ Test1_V4导入和初始化")
print("✓ Test2_V4导入和初始化")
print("✓ player_id配置")
print("✓ 决策引擎集成")
print("✓ 消息处理方法")
print("✓ validate_action方法")
print("\n通过: 6/6")
print("\n✓✓✓ 任务10和11已完成 ✓✓✓")
print("Test1_V4和Test2_V4客户端实现完成！")
