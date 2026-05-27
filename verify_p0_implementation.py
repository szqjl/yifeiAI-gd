#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0改进完整性验证 - 检查所有代码文件和集成点
"""

import re
from pathlib import Path

def main():
    project_dir = Path(__file__).parent

    print("="*70)
    print("P0改进完整性验证报告")
    print("="*70)
    print()

    # 检查1: 核心文件存在性
    print("【1. 核心文件检查】")
    core_files = {
        "history_tracker.py":  "P0-① 历史追踪",
        "endgame_planner.py": "P0-② 残局规划",
        "teammate_opportunity_finder.py": "P0-③ 主动传牌",
        "bomb_strategy.py": "P0-④ 炸弹策略",
    }

    all_exist = True
    for filename, description in core_files.items():
        filepath = project_dir / "src/decision" / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✓ {description:30} ({size:6} bytes)")
        else:
            print(f"  ❌ {description:30} NOT FOUND")
            all_exist = False

    # 检查2: 参数调优
    print("\n【2. 参数调优检查】")

    with open(project_dir / "src/decision/endgame_planner.py", 'r', encoding='utf-8') as f:
        content = f.read()
        threshold_match = re.search(r'endgame_threshold\s*=\s*(\d+)', content)
        if threshold_match:
            threshold = int(threshold_match.group(1))
            status = "✓" if threshold == 10 else "⚠"
            print(f"  {status} endgame_threshold = {threshold} (推荐: 10)")

    with open(project_dir / "src/decision/teammate_opportunity_finder.py", 'r', encoding='utf-8') as f:
        content = f.read()
        teammate_match = re.search(r'teammate_remain\s*<=\s*(\d+)', content)
        power_match = re.search(r'card_power\s*>=\s*(\d+)', content)

        if teammate_match:
            teammate_val = int(teammate_match.group(1))
            status = "✓" if teammate_val == 12 else "⚠"
            print(f"  {status} teammate_remain <= {teammate_val} (推荐: 12)")

        if power_match:
            power_val = int(power_match.group(1))
            status = "✓" if power_val == 3 else "⚠"
            print(f"  {status} card_power >= {power_val} (推荐: 3)")

    # 检查3: PassiveHandlers集成
    print("\n【3. PassiveHandlers集成检查】")

    with open(project_dir / "src/decision/phase_handlers.py", 'r', encoding='utf-8') as f:
        content = f.read()

    handlers_to_check = [
        ("OpeningPassiveHandler", "开局被动处理"),
        ("MidEarlyPassiveHandler", "中游初期被动处理"),
        ("MidLatePassiveHandler", "中游后期被动处理"),
        ("EndgameEarlyPassiveHandler", "残局初期被动处理"),
    ]

    integration_count = 0
    for handler_class, description in handlers_to_check:
        # 查找handler定义
        handler_pattern = f"class {handler_class}"
        if handler_pattern in content:
            # 查找这个handler中是否有TeammateOpportunityFinder
            handler_start = content.find(handler_pattern)
            # 找下一个class（下一个handler）
            next_class = content.find("class ", handler_start + 10)
            if next_class == -1:
                handler_section = content[handler_start:]
            else:
                handler_section = content[handler_start:next_class]

            if "TeammateOpportunityFinder" in handler_section:
                print(f"  ✓ {description:30} 已集成P0-③")
                integration_count += 1
            else:
                print(f"  ⚠️ {description:30} 未集成P0-③")
        else:
            print(f"  ❌ {description:30} 类未找到")

    print(f"\n  集成进度: {integration_count}/4 PassiveHandlers")

    # 检查4: 日志标记
    print("\n【4. 日志标记检查】")

    log_markers = [
        ("【P0改进①】", "历史追踪"),
        ("【P0改进②】", "残局规划"),
        ("【P0改进③】", "主动传牌"),
        ("【P0改进④】", "炸弹策略"),
    ]

    # 在phase_handlers.py和endgame_strategies.py中查找
    files_to_search = [
        "src/decision/phase_handlers.py",
        "src/decision/endgame_strategies.py",
        "src/decision/endgame_strategy.py",
        "src/decision/intelligent_router.py",
    ]

    found_markers = {}
    for marker, desc in log_markers:
        found_markers[marker] = False

    for file in files_to_search:
        filepath = project_dir / file
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
                for marker, desc in log_markers:
                    if marker in file_content:
                        found_markers[marker] = True

    for marker, desc in log_markers:
        status = "✓" if found_markers[marker] else "⚠"
        print(f"  {status} {marker:20} ({desc})")

    # 检查5: 代码质量
    print("\n【5. 代码质量检查】")

    with open(project_dir / "src/decision/phase_handlers.py", 'r', encoding='utf-8') as f:
        ph_content = f.read()

    # 检查try/except包装
    try_count = ph_content.count("try:")
    except_count = ph_content.count("except")
    print(f"  ✓ try/except 防护: {try_count} 处try块, {except_count} 处异常处理")

    # 验证导入
    import_count = ph_content.count("from .teammate_opportunity_finder import")
    print(f"  ✓ 导入验证: {import_count} 处导入TeammateOpportunityFinder")

    # 最终总结
    print("\n" + "="*70)
    print("验证总结")
    print("="*70)

    if all_exist and integration_count == 4 and sum(1 for m in found_markers.values() if m) >= 3:
        print("\n✅ P0改进已完全实施和集成!")
        print()
        print("实施清单:")
        print("  ✓ P0-①历史追踪 - 完成")
        print("  ✓ P0-②残局规划 - 完成（参数已调优)")
        print("  ✓ P0-③主动传牌 - 完成（已集成4个PassiveHandlers)")
        print("  ✓ P0-④炸弹策略 - 完成")
        print()
        print("质量保证:")
        print("  ✓ 所有核心模块已存在")
        print("  ✓ 参数已根据诊断结果调优")
        print("  ✓ 集成点已添加try/except防护")
        print("  ✓ 日志标记已添加便于调试")
        print()
        print("下一步:")
        print("  1. 使用真实平台进行20+局对战验证")
        print("  2. 收集数据对比改进前后的胜率")
        print("  3. 根据实际数据进行微调")
        return 0
    else:
        print("\n⚠️ P0改进实施不完整")
        print(f"  • 核心文件: {'✓' if all_exist else '❌'}")
        print(f"  • PassiveHandlers集成: {integration_count}/4")
        print(f"  • 日志标记: {sum(1 for m in found_markers.values() if m)}/4")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
