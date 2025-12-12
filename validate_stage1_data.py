#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段1数据质量验证
验证完善后的信息提取和策略标签提取
"""

import sys
import os
from collections import Counter, defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.knowledge_processor.replay_parser import ReplayParser


def validate_stage1_data():
    """验证阶段1的数据质量"""

    print("="*80)
    print("阶段1 数据质量验证")
    print("="*80)

    # 1. 加载数据
    parser = ReplayParser("game_records")
    replays = parser.load_replays()

    if not replays:
        print("❌ 未找到replay文件")
        return

    print(f"✅ 加载了 {len(replays)} 个replay文件")

    # 2. 提取训练数据
    print("\n📊 提取训练数据...")
    training_data = parser.extract_training_data(replays[:10])  # 测试前10个replay

    if not training_data:
        print("❌ 未提取到训练数据")
        return

    print(f"✅ 提取了 {len(training_data)} 个训练样本")

    # 3. 数据完整性检查
    print("\n🔍 数据完整性检查:")

    required_fields = [
        'hand', 'history', 'current_player', 'hands', 'last_action',
        'action_type', 'game_phase', 'cur_rank', 'player_rest_cards',
        'strategy_type', 'strategy_reason', 'strategy_effectiveness'
    ]

    field_counts = defaultdict(int)
    strategy_types = Counter()
    action_types = Counter()
    game_phases = Counter()

    for state, action in training_data:
        # 检查必需字段
        for field in required_fields:
            if field in state:
                field_counts[field] += 1

        # 统计分布
        strategy_types[state.get('strategy_type', 'unknown')] += 1
        action_types[state.get('action_type', 'unknown')] += 1
        game_phases[state.get('game_phase', 'unknown')] += 1

    # 输出字段完整性
    print("字段完整性:")
    for field in required_fields:
        count = field_counts[field]
        percentage = count / len(training_data) * 100
        status = "✅" if percentage > 95 else "⚠️" if percentage > 80 else "❌"
        print(f"  {status} {field}: {count}/{len(training_data)} ({percentage:.1f}%)")

    # 4. 数据质量分析
    print("\n📈 数据质量分析:")

    # 策略类型分布
    print("\n策略类型分布:")
    for strategy, count in strategy_types.most_common():
        percentage = count / len(training_data) * 100
        print(f"  {strategy}: {count} ({percentage:.1f}%)")

    # 动作类型分布
    print("\n动作类型分布:")
    for action, count in action_types.most_common(10):  # 只显示前10个
        percentage = count / len(training_data) * 100
        print(f"  {action}: {count} ({percentage:.1f}%)")

    # 游戏阶段分布
    print("\n游戏阶段分布:")
    phase_names = {0: '开局', 1: '中局', 2: '残局'}
    for phase, count in game_phases.most_common():
        phase_name = phase_names.get(phase, f'未知({phase})')
        percentage = count / len(training_data) * 100
        print(f"  {phase_name}: {count} ({percentage:.1f}%)")

    # 5. 样本质量检查
    print("\n🔍 样本质量检查:")

    # 检查手牌合理性
    valid_hands = 0
    for state, action in training_data:
        hand = state.get('hand', [])
        action_cards = action if isinstance(action, list) else []

        # 检查动作卡牌是否都在手牌中
        if all(card in hand for card in action_cards):
            valid_hands += 1

    hand_validity = valid_hands / len(training_data) * 100
    status = "✅" if hand_validity > 95 else "⚠️" if hand_validity > 80 else "❌"
    print(f"  {status} 手牌一致性: {valid_hands}/{len(training_data)} ({hand_validity:.1f}%)")

    # 检查剩余牌数合理性
    valid_rest_cards = 0
    for state, action in training_data:
        rest_cards = state.get('player_rest_cards', [])
        if len(rest_cards) == 4 and all(0 <= cards <= 27 for cards in rest_cards):
            # 检查总牌数是否合理（每人27张初始牌）
            total_played = sum(27 - cards for cards in rest_cards if cards <= 27)
            if 0 <= total_played <= 108:  # 最多108张牌
                valid_rest_cards += 1

    rest_validity = valid_rest_cards / len(training_data) * 100
    status = "✅" if rest_validity > 95 else "⚠️" if rest_validity > 80 else "❌"
    print(f"  {status} 剩余牌数合理性: {valid_rest_cards}/{len(training_data)} ({rest_validity:.1f}%)")

    # 6. 策略标签质量
    print("\n🎯 策略标签质量:")

    # 检查策略类型多样性
    unique_strategies = len(strategy_types)
    strategy_diversity = unique_strategies / 7 * 100  # 7种策略类型
    status = "✅" if strategy_diversity > 80 else "⚠️" if strategy_diversity > 50 else "❌"
    print(f"  {status} 策略类型多样性: {unique_strategies}/7 ({strategy_diversity:.1f}%)")

    # 检查策略效果合理性
    effectiveness_scores = []
    for state, action in training_data:
        score = state.get('strategy_effectiveness', 0)
        if isinstance(score, (int, float)):
            effectiveness_scores.append(score)

    if effectiveness_scores:
        avg_effectiveness = sum(effectiveness_scores) / len(effectiveness_scores)
        min_effectiveness = min(effectiveness_scores)
        max_effectiveness = max(effectiveness_scores)
        print(".1f")
    # 7. 总体评估
    print("\n🏆 总体评估:")

    # 计算综合质量分数
    completeness_score = sum(field_counts[field] / len(training_data) for field in required_fields) / len(required_fields) * 100
    quality_score = (hand_validity + rest_validity + strategy_diversity) / 3

    print(".1f"
    print(".1f"

    if completeness_score > 95 and quality_score > 85:
        print("✅ 阶段1数据提取和策略标签提取完全成功！")
        print("   数据质量优秀，可以进入阶段2多任务学习。")
    elif completeness_score > 90 and quality_score > 70:
        print("⚠️ 阶段1基本完成，但还有一些质量问题需要优化。")
        print("   可以进入阶段2，但建议在后续阶段继续完善数据质量。")
    else:
        print("❌ 阶段1数据质量不满足要求，需要进一步完善。")
        print("   建议重新检查数据提取逻辑和策略标签算法。")

    print("\n" + "="*80)


if __name__ == "__main__":
    validate_stage1_data()
