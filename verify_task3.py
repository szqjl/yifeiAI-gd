# -*- coding: utf-8 -*-
"""
验证任务3：LalalaAdapter数据转换功能
Verify Task 3: LalalaAdapter Data Conversion

测试内容：
1. _convert_cards() - 字符串到列表的转换
2. _convert_play_area() - playArea的所有卡牌类型处理
3. 幂等性 - convert(convert(x)) == convert(x)
4. 玩家位置映射
5. 错误处理
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from communication.lalala_adapter_v4 import LalalaAdapter
import copy


def test_convert_cards():
    """测试 _convert_cards() 方法"""
    print("\n" + "=" * 60)
    print("测试1: _convert_cards() - 牌格式转换")
    print("=" * 60)
    
    adapter = LalalaAdapter(0)
    
    test_cases = [
        # (输入, 期望输出, 描述)
        ("H4,S5,D6", [["H", "4"], ["S", "5"], ["D", "6"]], "逗号分隔字符串"),
        (["H4", "S5", "D6"], [["H", "4"], ["S", "5"], ["D", "6"]], "字符串列表"),
        ([["H", "4"], ["S", "5"]], [["H", "4"], ["S", "5"]], "已转换格式"),
        ("", [], "空字符串"),
        ([], [], "空列表"),
        (None, [], "None值"),
        ("R", [["R", "R"]], "大王"),
        ("B", [["B", "B"]], "小王"),
        ("H10,S10", [["H", "T"], ["S", "T"]], "10转换为T"),
        (["HT", "ST"], [["H", "T"], ["S", "T"]], "T保持不变"),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_data, expected, description) in enumerate(test_cases, 1):
        try:
            result = adapter._convert_cards(input_data)
            if result == expected:
                print(f"✓ 测试 {i}: {description}")
                passed += 1
            else:
                print(f"✗ 测试 {i}: {description}")
                print(f"  输入: {input_data}")
                print(f"  期望: {expected}")
                print(f"  实际: {result}")
                failed += 1
        except Exception as e:
            print(f"✗ 测试 {i}: {description} - 异常: {e}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_idempotence():
    """测试幂等性：convert(convert(x)) == convert(x)"""
    print("\n" + "=" * 60)
    print("测试2: 幂等性 - convert(convert(x)) == convert(x)")
    print("=" * 60)
    
    adapter = LalalaAdapter(0)
    
    test_cases = [
        "H4,S5,D6",
        ["H4", "S5"],
        [["H", "4"]],
        "R,B",
    ]
    
    passed = 0
    failed = 0
    
    for i, input_data in enumerate(test_cases, 1):
        try:
            result1 = adapter._convert_cards(input_data)
            result2 = adapter._convert_cards(result1)
            
            if result1 == result2:
                print(f"✓ 测试 {i}: {input_data}")
                passed += 1
            else:
                print(f"✗ 测试 {i}: {input_data}")
                print(f"  第一次转换: {result1}")
                print(f"  第二次转换: {result2}")
                failed += 1
        except Exception as e:
            print(f"✗ 测试 {i}: {input_data} - 异常: {e}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_convert_action():
    """测试 _convert_action() 方法"""
    print("\n" + "=" * 60)
    print("测试3: _convert_action() - 动作转换")
    print("=" * 60)
    
    adapter = LalalaAdapter(0)
    
    test_cases = [
        # (输入, 期望输出, 描述)
        (
            ["Single", "4", ["H4"]],
            ["Single", "4", [["H", "4"]]],
            "单张"
        ),
        (
            ["Pair", "5", ["H5", "S5"]],
            ["Pair", "5", [["H", "5"], ["S", "5"]]],
            "对子"
        ),
        (
            ["PASS", "PASS", "PASS"],
            ["PASS", "PASS", "PASS"],
            "PASS动作"
        ),
        (
            ["ThreeWithTwo", "8", ["H8", "C8", "D8", "C2", "D2"]],
            ["ThreeWithTwo", "8", [["H", "8"], ["C", "8"], ["D", "8"], ["C", "2"], ["D", "2"]]],
            "三带二"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_data, expected, description) in enumerate(test_cases, 1):
        try:
            result = adapter._convert_action(input_data)
            if result == expected:
                print(f"✓ 测试 {i}: {description}")
                passed += 1
            else:
                print(f"✗ 测试 {i}: {description}")
                print(f"  输入: {input_data}")
                print(f"  期望: {expected}")
                print(f"  实际: {result}")
                failed += 1
        except Exception as e:
            print(f"✗ 测试 {i}: {description} - 异常: {e}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_convert_public_info():
    """测试 _convert_public_info() 方法"""
    print("\n" + "=" * 60)
    print("测试4: _convert_public_info() - publicInfo转换")
    print("=" * 60)
    
    adapter = LalalaAdapter(0)
    
    # 测试用例：包含各种playArea格式
    public_info = [
        {"rest": 27, "playArea": None},
        {"rest": 25, "playArea": ["Single", "4", ["H4"]]},
        {"rest": 23, "playArea": ["Pair", "5", ["H5", "S5"]]},
        {"rest": 20, "playArea": ["PASS", "", "PASS"]},
    ]
    
    try:
        result = adapter._convert_public_info(public_info)
        
        # 检查结果
        checks = [
            (result[0]["playArea"] is None, "玩家0: playArea为None"),
            (result[1]["playArea"][2] == [["H", "4"]], "玩家1: Single转换正确"),
            (result[2]["playArea"][2] == [["H", "5"], ["S", "5"]], "玩家2: Pair转换正确"),
            (result[3]["playArea"][2] == "PASS", "玩家3: PASS保持不变"),
        ]
        
        passed = 0
        failed = 0
        
        for i, (condition, description) in enumerate(checks, 1):
            if condition:
                print(f"✓ 检查 {i}: {description}")
                passed += 1
            else:
                print(f"✗ 检查 {i}: {description}")
                print(f"  实际结果: {result}")
                failed += 1
        
        print(f"\n结果: {passed} 通过, {failed} 失败")
        return failed == 0
        
    except Exception as e:
        print(f"✗ 测试失败 - 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_player_position_mapping():
    """测试玩家位置映射"""
    print("\n" + "=" * 60)
    print("测试5: _convert_player_positions() - 玩家位置映射")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for player_id in range(4):
        adapter = LalalaAdapter(player_id)
        message = {"stage": "play", "type": "act"}
        
        result = adapter._convert_player_positions(message)
        
        if result.get("myPos") == player_id:
            print(f"✓ 玩家 {player_id}: myPos正确设置为 {player_id}")
            passed += 1
        else:
            print(f"✗ 玩家 {player_id}: myPos应为 {player_id}, 实际为 {result.get('myPos')}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试6: 错误处理")
    print("=" * 60)
    
    adapter = LalalaAdapter(0)
    
    test_cases = [
        # (输入, 应该抛出异常, 描述)
        (123, True, "无效类型（整数）"),
        ({"invalid": "dict"}, True, "无效类型（字典）"),
        ([""], False, "空字符串列表（应返回空列表）"),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_data, should_raise, description) in enumerate(test_cases, 1):
        try:
            result = adapter._convert_cards(input_data)
            if should_raise:
                print(f"✗ 测试 {i}: {description} - 应该抛出异常但没有")
                print(f"  返回值: {result}")
                failed += 1
            else:
                print(f"✓ 测试 {i}: {description} - 正确处理")
                passed += 1
        except (ValueError, TypeError) as e:
            if should_raise:
                print(f"✓ 测试 {i}: {description} - 正确抛出异常")
                print(f"  异常信息: {e}")
                passed += 1
            else:
                print(f"✗ 测试 {i}: {description} - 不应该抛出异常")
                print(f"  异常: {e}")
                failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_full_message_conversion():
    """测试完整消息转换"""
    print("\n" + "=" * 60)
    print("测试7: 完整消息转换")
    print("=" * 60)
    
    adapter = LalalaAdapter(0)
    
    # 模拟真实的游戏消息
    message = {
        "type": "act",
        "stage": "play",
        "handCards": ["H4", "S5", "D6", "C7"],
        "curAction": ["Single", "3", ["H3"]],
        "greaterAction": ["Single", "3", ["H3"]],
        "actionList": [
            ["PASS", "PASS", "PASS"],
            ["Single", "4", ["H4"]],
            ["Single", "5", ["S5"]],
        ],
        "publicInfo": [
            {"rest": 27, "playArea": None},
            {"rest": 26, "playArea": ["Single", "3", ["H3"]]},
            {"rest": 27, "playArea": None},
            {"rest": 27, "playArea": None},
        ],
    }
    
    try:
        # 深拷贝以保护原始数据
        message_copy = copy.deepcopy(message)
        result = adapter._convert_message(message_copy)
        
        # 验证转换结果
        checks = [
            (result["handCards"] == [["H", "4"], ["S", "5"], ["D", "6"], ["C", "7"]], "handCards转换正确"),
            (result["curAction"][2] == [["H", "3"]], "curAction转换正确"),
            (result["greaterAction"][2] == [["H", "3"]], "greaterAction转换正确"),
            (result["actionList"][1][2] == [["H", "4"]], "actionList转换正确"),
            (result["publicInfo"][1]["playArea"][2] == [["H", "3"]], "publicInfo转换正确"),
            (message["handCards"] == ["H4", "S5", "D6", "C7"], "原始消息未被修改"),
        ]
        
        passed = 0
        failed = 0
        
        for i, (condition, description) in enumerate(checks, 1):
            if condition:
                print(f"✓ 检查 {i}: {description}")
                passed += 1
            else:
                print(f"✗ 检查 {i}: {description}")
                failed += 1
        
        print(f"\n结果: {passed} 通过, {failed} 失败")
        return failed == 0
        
    except Exception as e:
        print(f"✗ 测试失败 - 异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("任务3验证：LalalaAdapter数据转换功能")
    print("=" * 60)
    
    tests = [
        ("牌格式转换", test_convert_cards),
        ("幂等性", test_idempotence),
        ("动作转换", test_convert_action),
        ("publicInfo转换", test_convert_public_info),
        ("玩家位置映射", test_player_position_mapping),
        ("错误处理", test_error_handling),
        ("完整消息转换", test_full_message_conversion),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 执行失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("✓ 任务3验证通过！")
        print("=" * 60)
        return 0
    else:
        print("✗ 任务3验证失败，请检查上述错误")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit(main())
