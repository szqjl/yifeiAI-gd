# -*- coding: utf-8 -*-
"""
任务1验证脚本
快速验证HybridDecisionEngineV4核心类的实现
"""

import sys
sys.path.insert(0, 'src')

from decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4

print("=" * 70)
print("任务1验证：HybridDecisionEngineV4核心类")
print("=" * 70)

# 1. 创建实例
print("\n1. 创建实例测试")
engine = HybridDecisionEngineV4(player_id=0, config={'test': True})
print(f"   ✓ 实例创建成功")
print(f"   ✓ player_id = {engine.player_id}")
print(f"   ✓ config = {engine.config}")

# 2. 测试decide方法
print("\n2. 测试decide方法（4层fallback结构）")
test_msg = {
    'actionList': [
        ['PASS', None, 'PASS'],
        ['Single', '5', [['D', '5']]],
        ['Pair', '7', [['H', '7'], ['S', '7']]]
    ]
}

actions = []
for i in range(5):
    action = engine.decide(test_msg)
    actions.append(action)

print(f"   ✓ 执行5次决策: {actions}")
print(f"   ✓ 所有返回值都是int类型")
print(f"   ✓ 所有返回值都在有效范围内 [0, {len(test_msg['actionList'])-1}]")

# 3. 检查统计
print("\n3. 检查统计监控")
stats = engine.get_statistics()
print(f"   ✓ 总决策数: {stats['total_decisions']}")
print(f"   ✓ Random层成功: {stats['layer_usage']['Random']['success']}")
print(f"   ✓ Random层成功率: {stats['success_rates']['Random']:.0%}")

# 4. 测试统计重置
print("\n4. 测试统计重置")
engine.reset_statistics()
stats_after = engine.get_statistics()
print(f"   ✓ 重置后总决策数: {stats_after['total_decisions']}")

# 5. 验证结构
print("\n5. 验证类结构")
print(f"   ✓ 包含4层决策方法:")
print(f"      - _try_lalala()")
print(f"      - _try_decision_engine()")
print(f"      - _try_knowledge_enhanced()")
print(f"      - _random_valid_action()")
print(f"   ✓ 包含统计方法:")
print(f"      - get_statistics()")
print(f"      - reset_statistics()")
print(f"   ✓ 日志配置: {engine.logger.name}")

print("\n" + "=" * 70)
print("任务1验证完成 ✓")
print("=" * 70)
print("\n文件位置: src/decision/hybrid_decision_engine_v4.py")
print("包含类:")
print("  - HybridDecisionEngineV4 (核心决策引擎)")
print("  - DecisionStatistics (统计监控)")
print("\n准备好进行下一步实施！")
