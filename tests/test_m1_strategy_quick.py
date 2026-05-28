# -*- coding: utf-8 -*-
"""
M1策略系统快捷测试脚本
功能：
- 快速测试M1策略系统的各个组件
- 不需要启动完整游戏服务器
- 可以单独测试决策逻辑、策略引擎、手牌分析等
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from typing import Dict, List
import json

def test_strategy_engine():
    """测试策略引擎"""
    print("=" * 60)
    print("测试1: 策略引擎初始化")
    print("=" * 60)
    
    try:
        from src.decision.strategy_engine import (
            TeammateProtectionStrategy,
            PrioritySystem,
            CardValueSystem
        )
        
        config = {"curRank": "2"}
        
        # 测试队友保护策略
        print("\n1.1 测试TeammateProtectionStrategy...")
        protection = TeammateProtectionStrategy(config)
        print("   ✓ TeammateProtectionStrategy 初始化成功")
        
        # 测试优先级系统
        print("\n1.2 测试PrioritySystem...")
        priority = PrioritySystem(config)
        print("   ✓ PrioritySystem 初始化成功")
        
        # 测试牌值系统
        print("\n1.3 测试CardValueSystem...")
        card_value = CardValueSystem("2")
        print("   ✓ CardValueSystem 初始化成功")
        
        print("\n✅ 策略引擎测试通过！")
        return True
    except Exception as e:
        print(f"\n❌ 策略引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hand_structure_analyzer():
    """测试手牌结构分析器"""
    print("\n" + "=" * 60)
    print("测试2: 手牌结构分析器")
    print("=" * 60)
    
    try:
        from src.decision.hand_structure_analyzer import HandStructureAnalyzer
        
        analyzer = HandStructureAnalyzer()
        
        # 测试手牌分析
        test_handcards = [
            ['H', '3'], ['C', '3'], ['S', '5'], ['D', '5'],
            ['H', '7'], ['C', '7'], ['D', '7'], ['S', '9'],
            ['H', 'J'], ['C', 'K'], ['D', 'A'], ['S', '2']
        ]
        
        print(f"\n2.1 测试手牌分析（{len(test_handcards)}张牌）...")
        structure = analyzer.analyze(test_handcards, "2")
        
        print(f"   - 单张成员: {len(structure.get('single_member', []))} 张")
        print(f"   - 对子成员: {len(structure.get('pair_member', []))} 张")
        print(f"   - 三张成员: {len(structure.get('trip_member', []))} 张")
        print(f"   - 灵活性评分: {structure.get('flexibility_score', 0):.2f}")
        print(f"   - 威胁等级: {structure.get('threat_level', 0):.2f}")
        
        print("\n✅ 手牌结构分析器测试通过！")
        return True
    except Exception as e:
        print(f"\n❌ 手牌结构分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase_handlers():
    """测试阶段处理器"""
    print("\n" + "=" * 60)
    print("测试3: 阶段处理器")
    print("=" * 60)
    
    try:
        from src.decision.phase_handlers import (
            OpeningActiveHandler,
            OpeningPassiveHandler,
            EndgameLateActiveHandler
        )
        
        config = {"curRank": "2"}
        
        # 测试开局主动处理器
        print("\n3.1 测试OpeningActiveHandler...")
        opening_active = OpeningActiveHandler(config)
        print("   ✓ OpeningActiveHandler 初始化成功")
        
        # 测试开局被动处理器
        print("\n3.2 测试OpeningPassiveHandler...")
        opening_passive = OpeningPassiveHandler(config)
        print("   ✓ OpeningPassiveHandler 初始化成功")
        
        # 测试残局后期处理器
        print("\n3.3 测试EndgameLateActiveHandler...")
        endgame_late = EndgameLateActiveHandler(config)
        print("   ✓ EndgameLateActiveHandler 初始化成功")
        
        print("\n✅ 阶段处理器测试通过！")
        return True
    except Exception as e:
        print(f"\n❌ 阶段处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_card_type_handlers():
    """测试牌型处理器"""
    print("\n" + "=" * 60)
    print("测试4: 牌型处理器")
    print("=" * 60)
    
    try:
        from src.decision.card_type_handler_factory import (
            CardTypeHandlerFactory,
            SingleHandler,
            PairHandler
        )
        
        config = {"curRank": "2"}
        
        # 测试工厂方法
        print("\n4.1 测试CardTypeHandlerFactory...")
        single_handler = CardTypeHandlerFactory.get_handler("Single", config)
        pair_handler = CardTypeHandlerFactory.get_handler("Pair", config)
        
        if single_handler and pair_handler:
            print("   ✓ CardTypeHandlerFactory 工作正常")
        else:
            print("   ❌ CardTypeHandlerFactory 返回None")
            return False
        
        # 测试单张处理器
        print("\n4.2 测试SingleHandler...")
        if isinstance(single_handler, SingleHandler):
            print("   ✓ SingleHandler 创建成功")
        else:
            print("   ❌ SingleHandler 类型错误")
            return False
        
        # 测试对子处理器
        print("\n4.3 测试PairHandler...")
        if isinstance(pair_handler, PairHandler):
            print("   ✓ PairHandler 创建成功")
        else:
            print("   ❌ PairHandler 类型错误")
            return False
        
        print("\n✅ 牌型处理器测试通过！")
        return True
    except Exception as e:
        print(f"\n❌ 牌型处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_endgame_strategies():
    """测试残局策略"""
    print("\n" + "=" * 60)
    print("测试5: 残局策略")
    print("=" * 60)
    
    try:
        from src.decision.endgame_strategies import (
            RushStrategy,
            DefendStrategy,
            CooperateStrategy,
            ControlStrategy,
            EndgameStrategySelector
        )
        
        config = {"curRank": "2"}
        
        # 测试冲刺策略
        print("\n5.1 测试RushStrategy...")
        rush = RushStrategy(config)
        print("   ✓ RushStrategy 初始化成功")
        
        # 测试防守策略
        print("\n5.2 测试DefendStrategy...")
        defend = DefendStrategy(config)
        print("   ✓ DefendStrategy 初始化成功")
        
        # 测试配合策略
        print("\n5.3 测试CooperateStrategy...")
        cooperate = CooperateStrategy(config)
        print("   ✓ CooperateStrategy 初始化成功")
        
        # 测试控制策略
        print("\n5.4 测试ControlStrategy...")
        control = ControlStrategy(config)
        print("   ✓ ControlStrategy 初始化成功")
        
        # 测试策略选择器
        print("\n5.5 测试EndgameStrategySelector...")
        selector = EndgameStrategySelector(config)
        print("   ✓ EndgameStrategySelector 初始化成功")
        
        print("\n✅ 残局策略测试通过！")
        return True
    except Exception as e:
        print(f"\n❌ 残局策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_decision_engine():
    """测试决策引擎"""
    print("\n" + "=" * 60)
    print("测试6: M1决策引擎")
    print("=" * 60)
    
    try:
        from src.decision.rule_based_decision_engine_m1 import RuleBasedDecisionEngineM1
        
        config = {
            "max_decision_time": 0.8,
            "enable_logging": True,
            "curRank": "2"
        }
        
        print("\n6.1 测试RuleBasedDecisionEngineM1初始化...")
        engine = RuleBasedDecisionEngineM1(0, config)
        print("   ✓ RuleBasedDecisionEngineM1 初始化成功")
        
        # 测试阶段信息获取
        print("\n6.2 测试阶段信息获取...")
        test_message = {
            "handCards": [['H', '3'], ['C', '3'], ['S', '5']] * 9,  # 27张牌
            "curRank": "2",
            "myPos": 0,
            "stage": "play"
        }
        phase_info = engine.get_phase_info(test_message)
        print(f"   - 游戏阶段: {phase_info.get('game_phase', 'unknown')}")
        print(f"   - 处理器键: {phase_info.get('handler_key', 'unknown')}")
        print(f"   - 剩余牌数: {phase_info.get('my_remain', 0)}")
        
        print("\n✅ M1决策引擎测试通过！")
        return True
    except Exception as e:
        print(f"\n❌ M1决策引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("M1策略系统快捷测试")
    print("=" * 60)
    print("\n本脚本将测试M1策略系统的各个组件，无需启动游戏服务器。")
    print("测试内容：")
    print("  1. 策略引擎（TeammateProtection, PrioritySystem, CardValueSystem）")
    print("  2. 手牌结构分析器（HandStructureAnalyzer）")
    print("  3. 阶段处理器（OpeningHandler, EndgameHandler等）")
    print("  4. 牌型处理器（SingleHandler, PairHandler等）")
    print("  5. 残局策略（RushStrategy, DefendStrategy等）")
    print("  6. M1决策引擎（RuleBasedDecisionEngineM1）")
    print("\n开始测试...\n")
    
    results = []
    
    # 运行所有测试
    results.append(("策略引擎", test_strategy_engine()))
    results.append(("手牌结构分析器", test_hand_structure_analyzer()))
    results.append(("阶段处理器", test_phase_handlers()))
    results.append(("牌型处理器", test_card_type_handlers()))
    results.append(("残局策略", test_endgame_strategies()))
    results.append(("M1决策引擎", test_decision_engine()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(results)} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")
    
    if failed == 0:
        print("\n🎉 所有测试通过！M1策略系统工作正常。")
        print("\n💡 下一步：")
        print("  1. 运行 START_M1_GUI.bat 进行完整对局测试")
        print("  2. 观察日志文件 logs/yf1_m1_*.log 查看详细决策过程")
        print("  3. 根据实战结果调整策略参数")
    else:
        print(f"\n⚠️  有 {failed} 项测试失败，请检查错误信息。")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

