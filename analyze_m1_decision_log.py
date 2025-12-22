# -*- coding: utf-8 -*-
"""
M1决策日志分析工具
功能：
- 分析M1决策日志，提取关键决策信息
- 统计决策模式、阶段分布、策略使用情况
"""

import sys
from pathlib import Path
import re
from collections import defaultdict, Counter
from datetime import datetime

def analyze_log_file(log_file: Path):
    """分析单个日志文件"""
    print(f"\n{'='*60}")
    print(f"分析日志文件: {log_file.name}")
    print(f"{'='*60}\n")
    
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 统计信息
    stats = {
        'total_decisions': 0,
        'phase_distribution': Counter(),
        'handler_distribution': Counter(),
        'action_types': Counter(),
        'teammate_protection_count': 0,
        'pass_count': 0,
        'play_count': 0,
        'decision_times': [],
        'strategy_suggestions': [],
    }
    
    # 分析每一行
    for i, line in enumerate(lines):
        # 统计阶段分布
        if 'Phase:' in line:
            stats['total_decisions'] += 1
            # 提取阶段信息
            phase_match = re.search(r'Phase: (\w+), Handler: (\w+), 剩余牌数: (\d+)', line)
            if phase_match:
                phase = phase_match.group(1)
                handler = phase_match.group(2)
                remain = int(phase_match.group(3))
                stats['phase_distribution'][phase] += 1
                stats['handler_distribution'][handler] += 1
        
        # 统计动作类型
        if '选择动作:' in line or 'Selected action' in line:
            # 提取动作类型
            action_match = re.search(r'动作类型: (\w+)', line)
            if action_match:
                action_type = action_match.group(1)
                stats['action_types'][action_type] += 1
                if action_type == 'PASS':
                    stats['pass_count'] += 1
                else:
                    stats['play_count'] += 1
        
        # 统计队友保护
        if 'Teammate played' in line or '队友' in line:
            stats['teammate_protection_count'] += 1
        
        # 提取策略建议
        if 'suggestion:' in line or '建议' in line:
            suggestion_match = re.search(r"suggestion: ({[^}]+})", line)
            if suggestion_match:
                stats['strategy_suggestions'].append(suggestion_match.group(1))
    
    # 输出统计结果
    print(f"📊 决策统计:")
    print(f"  总决策次数: {stats['total_decisions']}")
    print(f"  出牌次数: {stats['play_count']}")
    print(f"  PASS次数: {stats['pass_count']}")
    if stats['total_decisions'] > 0:
        pass_rate = stats['pass_count'] / stats['total_decisions'] * 100
        print(f"  PASS率: {pass_rate:.1f}%")
    
    print(f"\n📈 阶段分布:")
    for phase, count in stats['phase_distribution'].most_common():
        percentage = count / stats['total_decisions'] * 100 if stats['total_decisions'] > 0 else 0
        print(f"  {phase}: {count}次 ({percentage:.1f}%)")
    
    print(f"\n🎯 处理器分布:")
    for handler, count in stats['handler_distribution'].most_common():
        percentage = count / stats['total_decisions'] * 100 if stats['total_decisions'] > 0 else 0
        print(f"  {handler}: {count}次 ({percentage:.1f}%)")
    
    print(f"\n🃏 动作类型分布:")
    for action_type, count in stats['action_types'].most_common(10):
        percentage = count / stats['total_decisions'] * 100 if stats['total_decisions'] > 0 else 0
        print(f"  {action_type}: {count}次 ({percentage:.1f}%)")
    
    print(f"\n🤝 队友保护:")
    print(f"  触发次数: {stats['teammate_protection_count']}")
    
    # 分析决策质量
    print(f"\n📋 决策质量分析:")
    if stats['pass_count'] > stats['play_count']:
        print(f"  ⚠️  警告: PASS次数({stats['pass_count']}) > 出牌次数({stats['play_count']})")
        print(f"  💡 建议: 检查被动出牌逻辑，确保能正确压制对手")
    else:
        print(f"  ✅ 正常: 出牌次数({stats['play_count']}) > PASS次数({stats['pass_count']})")
    
    # 分析阶段分布合理性
    opening_count = stats['phase_distribution'].get('opening', 0)
    endgame_count = stats['phase_distribution'].get('endgame_late', 0) + stats['phase_distribution'].get('endgame_early', 0)
    if opening_count > 0 and endgame_count == 0:
        print(f"  ⚠️  警告: 游戏可能未进行到残局阶段")
    
    return stats


def main():
    """主函数"""
    print("="*60)
    print("M1决策日志分析工具")
    print("="*60)
    
    # 查找最新的M1日志文件
    log_dir = Path("logs")
    if not log_dir.exists():
        print(f"❌ 日志目录不存在: {log_dir}")
        return
    
    # 查找所有M1日志文件
    m1_logs = sorted(log_dir.glob("yf1_m1_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not m1_logs:
        print("❌ 未找到M1日志文件")
        return
    
    print(f"\n找到 {len(m1_logs)} 个M1日志文件")
    print("分析最新的日志文件...\n")
    
    # 分析最新的日志文件
    latest_log = m1_logs[0]
    stats = analyze_log_file(latest_log)
    
    # 如果有多个日志文件，提供选择
    if len(m1_logs) > 1:
        print(f"\n💡 提示: 还有 {len(m1_logs)-1} 个日志文件，可以分析其他文件")
    
    print(f"\n{'='*60}")
    print("分析完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

