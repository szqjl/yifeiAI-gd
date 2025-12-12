#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的阶段1数据验证
"""

import sys
import os
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.knowledge_processor.replay_parser import ReplayParser


def simple_validation():
    """简化的数据验证"""

    print("阶段1 数据质量验证")
    print("=" * 50)

    # 加载数据
    parser = ReplayParser("game_records")
    replays = parser.load_replays()

    if not replays:
        print("未找到replay文件")
        return

    print(f"加载了 {len(replays)} 个replay文件")

    # 提取训练数据
    training_data = parser.extract_training_data(replays[:5])  # 测试前5个

    if not training_data:
        print("未提取到训练数据")
        return

    print(f"提取了 {len(training_data)} 个训练样本")

    # 检查必需字段
    required_fields = [
        'hand', 'history', 'current_player', 'hands', 'last_action',
        'action_type', 'game_phase', 'cur_rank', 'player_rest_cards',
        'strategy_type', 'strategy_reason', 'strategy_effectiveness'
    ]

    field_present = {field: 0 for field in required_fields}
    strategy_types = Counter()
    action_types = Counter()

    for state, action in training_data:
        for field in required_fields:
            if field in state and state[field] is not None:
                field_present[field] += 1

        strategy_types[state.get('strategy_type', 'unknown')] += 1
        action_types[state.get('action_type', 'unknown')] += 1

    # 输出结果
    print("\n字段完整性:")
    total = len(training_data)
    for field in required_fields:
        count = field_present[field]
        percentage = count / total * 100
        status = "✅" if percentage > 90 else "⚠️" if percentage > 70 else "❌"
        print(f"  {status} {field}: {count}/{total} ({percentage:.1f}%)")

    print("\n策略类型分布:")
    for strategy, count in strategy_types.most_common():
        percentage = count / total * 100
        print(f"  {strategy}: {count} ({percentage:.1f}%)")

    print("\n动作类型分布:")
    for action, count in action_types.most_common(5):
        percentage = count / total * 100
        print(f"  {action}: {count} ({percentage:.1f}%)")

    # 质量评估
    completeness = sum(field_present[f] for f in required_fields) / (len(required_fields) * total) * 100
    strategy_diversity = len(strategy_types) / 7 * 100  # 7种策略类型

    print("
质量评分:"    print(".1f"    print(".1f"
    if completeness > 95 and strategy_diversity > 80:
        print("✅ 阶段1数据提取和策略标签提取完全成功！")
    elif completeness > 90 and strategy_diversity > 50:
        print("⚠️ 阶段1基本完成，可以进入阶段2")
    else:
        print("❌ 需要进一步完善数据提取")

    print("=" * 50)


if __name__ == "__main__":
    simple_validation()
