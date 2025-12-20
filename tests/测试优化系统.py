#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YF掼蛋优化系统综合测试
测试残局策略、队友保护、动态优先级
"""

import sys
import time
import tracemalloc
sys.path.insert(0, 'src')

from decision.endgame_strategy import EndgameStrategyEnhanced, _is_endgame_enhanced
from decision.cooperation import (
    TeammateProtectionStrategy, HighValueProtectionRule,
    LowCardCountProtectionRule, CriticalStageProtectionRule,
    BombProtectionRule, ProtectionContext
)
from decision.multi_factor_evaluator import (
    DynamicPrioritySystem, NextPlayerAdjuster, PassCountAdjuster,
    EndgameAdjuster, TeammateAdjuster, PriorityContext
)


class TestResults:
    """测试结果收集器"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, name):
        self.passed += 1
        print(f"  ✅ {name}")
    
    def add_fail(self, name, reason):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ❌ {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n总计: {self.passed}/{total} 通过")
        if self.errors:
            print("失败项:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        return self.failed == 0


def test_endgame_detection():
    """测试残局检测"""
    print("\n=== 残局检测测试 ===")
    results = TestResults()
    
    # 测试1: 冲刺型残局
    msg = {"myPos": 0, "handCards": ["H3", "H4", "H5"],
           "publicInfo": [{"rest": 3}, {"rest": 15}, {"rest": 3}, {"rest": 12}]}
    is_end, etype = _is_endgame_enhanced(msg)
    if is_end and etype == "rush":
        results.add_pass("冲刺型残局检测")
    else:
        results.add_fail("冲刺型残局检测", f"got {etype}")
    
    # 测试2: 防守型残局
    msg = {"myPos": 0, "handCards": ["H3", "H4", "H5", "H6", "H7", "H8"],
           "publicInfo": [{"rest": 6}, {"rest": 10}, {"rest": 4}, {"rest": 10}]}
    is_end, etype = _is_endgame_enhanced(msg)
    if is_end and etype == "defend":
        results.add_pass("防守型残局检测")
    else:
        results.add_fail("防守型残局检测", f"got {etype}")
    
    # 测试3: 非残局
    msg = {"myPos": 0, "handCards": list(range(20)),
           "publicInfo": [{"rest": 20}, {"rest": 20}, {"rest": 20}, {"rest": 20}]}
    is_end, etype = _is_endgame_enhanced(msg)
    if not is_end or etype == "normal":
        results.add_pass("非残局检测")
    else:
        results.add_fail("非残局检测", f"got is_end={is_end}, type={etype}")
    
    return results


def test_teammate_protection():
    """测试队友保护"""
    print("\n=== 队友保护测试 ===")
    results = TestResults()
    strategy = TeammateProtectionStrategy()
    
    # 测试1: 高价值牌保护
    rule = HighValueProtectionRule()
    ctx = ProtectionContext(teammate_action=["Single", "A", ["HA"]])
    should, score, _ = rule.evaluate(ctx)
    if should and score >= 0.7:
        results.add_pass("高价值牌保护(A)")
    else:
        results.add_fail("高价值牌保护(A)", f"should={should}, score={score}")
    
    # 测试2: 炸弹绝对保护
    rule = BombProtectionRule()
    ctx = ProtectionContext(teammate_action=["Bomb", "7", ["H7", "D7", "C7", "S7"]])
    should, score, _ = rule.evaluate(ctx)
    if should and score == 1.0:
        results.add_pass("炸弹绝对保护")
    else:
        results.add_fail("炸弹绝对保护", f"should={should}, score={score}")
    
    # 测试3: 低牌数保护
    rule = LowCardCountProtectionRule()
    ctx = ProtectionContext(teammate_remain=3)
    should, score, _ = rule.evaluate(ctx)
    if should and score >= 0.8:
        results.add_pass("低牌数保护(3张)")
    else:
        results.add_fail("低牌数保护(3张)", f"should={should}, score={score}")
    
    # 测试4: 综合评估
    msg = {"myPos": 0, "handCards": ["H3", "H4", "H5"],
           "publicInfo": [{"rest": 10}, {"rest": 8}, {"rest": 4}, {"rest": 8}]}
    teammate_action = ["Single", "2", ["H2"]]
    should, details = strategy.should_protect(msg, teammate_action)
    if should and len(details['triggered_rules']) >= 2:
        results.add_pass("综合评估(多规则触发)")
    else:
        results.add_fail("综合评估", f"rules={details.get('triggered_rules', [])}")
    
    return results


def test_dynamic_priority():
    """测试动态优先级"""
    print("\n=== 动态优先级测试 ===")
    results = TestResults()
    system = DynamicPrioritySystem()
    
    action_list = [
        ["PASS", "", []],
        ["Single", "3", ["H3"]],
        ["Single", "A", ["HA"]],
        ["Bomb", "7", ["H7", "D7", "C7", "S7"]]
    ]
    base_scores = [0.0, 0.5, 0.6, 0.8]
    
    # 测试1: 下家1张牌时降低单张优先级
    msg = {"myPos": 0, "handCards": ["H3", "HA"],
           "publicInfo": [{"rest": 2}, {"rest": 1}, {"rest": 10}, {"rest": 10}],
           "actionHistory": []}
    adjusted = system.adjust_priorities(base_scores, action_list, msg)
    if adjusted[1] < base_scores[1] and adjusted[2] < base_scores[2]:
        results.add_pass("下家1张牌降低单张优先级")
    else:
        results.add_fail("下家1张牌降低单张优先级", f"adjusted={adjusted}")
    
    # 测试2: 连续PASS提高出牌优先级
    msg = {"myPos": 0, "handCards": ["H3", "HA"],
           "publicInfo": [{"rest": 10}, {"rest": 10}, {"rest": 10}, {"rest": 10}],
           "actionHistory": [["PASS"], ["PASS"], ["PASS"], ["PASS"], ["PASS"], ["PASS"]]}
    adjusted = system.adjust_priorities(base_scores, action_list, msg)
    if adjusted[1] > base_scores[1]:
        results.add_pass("连续PASS提高出牌优先级")
    else:
        results.add_fail("连续PASS提高出牌优先级", f"adjusted={adjusted}")
    
    # 测试3: 队友领先提高PASS优先级
    msg = {"myPos": 0, "handCards": ["H3", "HA"],
           "publicInfo": [{"rest": 10}, {"rest": 15}, {"rest": 3}, {"rest": 15}],
           "actionHistory": []}
    adjusted = system.adjust_priorities(base_scores, action_list, msg)
    if adjusted[0] > base_scores[0]:
        results.add_pass("队友领先提高PASS优先级")
    else:
        results.add_fail("队友领先提高PASS优先级", f"PASS score={adjusted[0]}")
    
    return results


def test_performance():
    """测试性能"""
    print("\n=== 性能测试 ===")
    results = TestResults()
    
    msg = {"myPos": 0, "handCards": list(range(10)),
           "publicInfo": [{"rest": 10}, {"rest": 8}, {"rest": 5}, {"rest": 12}],
           "actionHistory": []}
    action_list = [["PASS"], ["Single", "3", ["H3"]], ["Pair", "5", ["H5", "D5"]]]
    base_scores = [0.0, 0.5, 0.6]
    
    iterations = 1000
    
    # 残局检测性能
    start = time.perf_counter()
    for _ in range(iterations):
        _is_endgame_enhanced(msg)
    elapsed = (time.perf_counter() - start) * 1000 / iterations
    if elapsed < 1.0:
        results.add_pass(f"残局检测性能 ({elapsed:.4f}ms)")
    else:
        results.add_fail("残局检测性能", f"{elapsed:.4f}ms > 1ms")
    
    # 队友保护性能
    strategy = TeammateProtectionStrategy()
    start = time.perf_counter()
    for _ in range(iterations):
        strategy.should_protect(msg, ["Single", "A", ["HA"]])
    elapsed = (time.perf_counter() - start) * 1000 / iterations
    if elapsed < 1.0:
        results.add_pass(f"队友保护性能 ({elapsed:.4f}ms)")
    else:
        results.add_fail("队友保护性能", f"{elapsed:.4f}ms > 1ms")
    
    # 动态优先级性能
    system = DynamicPrioritySystem()
    start = time.perf_counter()
    for _ in range(iterations):
        system.adjust_priorities(base_scores, action_list, msg)
    elapsed = (time.perf_counter() - start) * 1000 / iterations
    if elapsed < 1.0:
        results.add_pass(f"动态优先级性能 ({elapsed:.4f}ms)")
    else:
        results.add_fail("动态优先级性能", f"{elapsed:.4f}ms > 1ms")
    
    return results


def test_memory():
    """测试内存使用"""
    print("\n=== 内存测试 ===")
    results = TestResults()
    
    tracemalloc.start()
    
    # 创建实例
    endgame = EndgameStrategyEnhanced()
    protection = TeammateProtectionStrategy()
    priority = DynamicPrioritySystem()
    
    # 执行1000次操作
    msg = {"myPos": 0, "handCards": list(range(10)),
           "publicInfo": [{"rest": 10}, {"rest": 8}, {"rest": 5}, {"rest": 12}],
           "actionHistory": []}
    
    for _ in range(1000):
        _is_endgame_enhanced(msg)
        protection.should_protect(msg, ["Single", "A", ["HA"]])
        priority.adjust_priorities([0.0, 0.5, 0.6], [["PASS"], ["Single", "3", ["H3"]]], msg)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    peak_mb = peak / 1024 / 1024
    if peak_mb < 10:
        results.add_pass(f"内存使用 (峰值: {peak_mb:.2f}MB)")
    else:
        results.add_fail("内存使用", f"峰值 {peak_mb:.2f}MB > 10MB")
    
    return results


def main():
    """运行所有测试"""
    print("=" * 60)
    print("YF掼蛋优化系统综合测试")
    print("=" * 60)
    
    all_results = []
    all_results.append(test_endgame_detection())
    all_results.append(test_teammate_protection())
    all_results.append(test_dynamic_priority())
    all_results.append(test_performance())
    all_results.append(test_memory())
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    
    print(f"总计: {total_passed}/{total_passed + total_failed} 通过")
    
    if total_failed == 0:
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print(f"\n❌ {total_failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
