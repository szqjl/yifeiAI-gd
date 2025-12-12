#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YF_V5 阶段5集成验证
"""

import sys
import os
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

def test_integration():
    """测试YF_V5阶段5集成"""

    print("YF_V5 阶段5集成验证")
    print("=" * 40)

    try:
        # 测试组件导入
        from src.decision.yf_v5_stage5_decision_engine import YF_V5_Stage5_DecisionEngine
        from src.communication.yf1_v5_stage5 import YF1_V5_Client
        from src.communication.yf2_v5_stage5 import YF2_V5_Client
        print("✓ 组件导入成功")

        # 测试决策引擎
        engine = YF_V5_Stage5_DecisionEngine(player_id=0)
        print("✓ 决策引擎初始化成功")

        # 测试决策功能
        test_msg = {
            'handCards': ['H3', 'H4', 'H5'],
            'actionList': ['PASS', ['Single', 'H3']]
        }
        result = engine.decide(test_msg)
        print("✓ 决策功能正常")
        print(f"  - 动作: {result['action']}")
        print(f"  - 时间: {result['decision_time']:.3f}s")
        # 测试客户端
        with patch('src.communication.yf1_v5_stage5.WebSocketManager'):
            client1 = YF1_V5_Client(player_id=0)
            print("✓ YF1客户端初始化成功")

        with patch('src.communication.yf2_v5_stage5.WebSocketManager'):
            client2 = YF2_V5_Client(player_id=2)
            print("✓ YF2客户端初始化成功")

        # 验证阶段5功能
        has_pattern = hasattr(client1.decision_engine.advanced_ai, 'pattern_recognizer')
        has_opponent = hasattr(client1.decision_engine.advanced_ai, 'opponent_model')
        has_strategy = hasattr(client1.decision_engine.advanced_ai, 'strategy_adjuster')

        print("✓ 阶段5功能验证:")
        print(f"  - 策略模式识别: {'是' if has_pattern else '否'}")
        print(f"  - 对手建模: {'是' if has_opponent else '否'}")
        print(f"  - 动态策略调整: {'是' if has_strategy else '否'}")

        all_good = all([has_pattern, has_opponent, has_strategy, result.get('stage5_enhanced', False)])

        if all_good:
            print("\n🎉 YF_V5阶段5集成成功!")
            print("AI现已具备完整的阶段5高级功能")
            return True
        else:
            print("\n⚠️ 部分功能未完全集成")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
