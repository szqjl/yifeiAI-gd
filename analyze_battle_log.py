# -*- coding: utf-8 -*-
"""
分析对战日志：提取连续PASS和队友识别问题
"""
import re
from collections import defaultdict, Counter

def analyze_battle_log(file_path):
    """分析对战日志"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 1. 提取连续PASS统计
    pass_pattern = r'连续pass数目：\s*(\d+)'
    pass_counts = re.findall(pass_pattern, content)
    pass_counter = Counter([int(c) for c in pass_counts])
    
    print("=" * 60)
    print("1. 连续PASS统计")
    print("=" * 60)
    print(f"总PASS记录数: {len(pass_counts)}")
    print(f"连续PASS分布:")
    for count, freq in sorted(pass_counter.items()):
        print(f"  {count}次连续PASS: {freq}次")
    
    # 2. 提取高连续PASS的情况
    high_pass_pattern = r'(\d+)号位打出.*?连续pass数目：\s*(\d+)'
    matches = re.findall(high_pass_pattern, content)
    high_passes = [(int(m[0]), int(m[1])) for m in matches if int(m[1]) >= 2]
    
    print(f"\n连续PASS >= 2的情况共 {len(high_passes)} 次:")
    for pos, count in high_passes[:30]:
        print(f"  {pos}号位: {count}次连续PASS")
    
    # 3. 分析队友识别问题
    # 队友关系: 0和2是队友, 1和3是队友
    print("\n" + "=" * 60)
    print("2. 队友识别分析")
    print("=" * 60)
    
    # 提取每次出牌的信息
    action_pattern = r'(\d+)号位打出(.*?)，\s*最大动作为(\d+)号位'
    actions = re.findall(action_pattern, content)
    
    teammate_mistakes = []
    teammate_correct = []
    
    for i, (actor, action, greater) in enumerate(actions):
        actor = int(actor)
        greater = int(greater)
        
        # 判断是否是队友关系
        is_teammate = ((actor == 0 and greater == 2) or 
                      (actor == 2 and greater == 0) or
                      (actor == 1 and greater == 3) or
                      (actor == 3 and greater == 1))
        
        if is_teammate:
            # 查找下一个动作
            if i + 1 < len(actions):
                next_actor, next_action, _ = actions[i + 1]
                next_actor = int(next_actor)
                
                # 如果下一个出牌的是对手，说明队友出牌后对手接牌了
                is_opponent = ((actor == 0 and next_actor in [1, 3]) or
                              (actor == 2 and next_actor in [1, 3]) or
                              (actor == 1 and next_actor in [0, 2]) or
                              (actor == 3 and next_actor in [0, 2]))
                
                if is_opponent and 'PASS' not in next_action:
                    # 队友控场后，对手出牌了（可能是误认队友）
                    teammate_mistakes.append({
                        'round': i,
                        'teammate_pos': greater,
                        'actor_pos': actor,
                        'action': action,
                        'next_actor': next_actor,
                        'next_action': next_action
                    })
                elif 'PASS' in next_action:
                    teammate_correct.append({
                        'round': i,
                        'teammate_pos': greater,
                        'actor_pos': actor,
                        'action': action
                    })
    
    print(f"\n队友控场后，对手出牌的情况（可能误认队友）: {len(teammate_mistakes)} 次")
    for mistake in teammate_mistakes[:20]:
        print(f"  队友{mistake['teammate_pos']}号控场后，{mistake['actor_pos']}号出牌，"
              f"但{mistake['next_actor']}号（对手）接牌了")
    
    print(f"\n队友控场后，正确PASS的情况: {len(teammate_correct)} 次")
    
    # 4. 分析YF V4的PASS行为
    print("\n" + "=" * 60)
    print("3. YF V4 (0号和2号) 的PASS行为分析")
    print("=" * 60)
    
    yf_passes = []
    for pos, count in high_passes:
        if pos in [0, 2]:  # YF V4的位置
            yf_passes.append((pos, count))
    
    print(f"YF V4高连续PASS次数: {len(yf_passes)}")
    for pos, count in yf_passes[:20]:
        print(f"  {pos}号位: {count}次连续PASS")
    
    # 5. 分析残局阶段的PASS
    print("\n" + "=" * 60)
    print("4. 残局阶段分析（剩余牌数 <= 5）")
    print("=" * 60)
    
    endgame_pattern = r'下家还有(\d+)张牌'
    endgame_matches = re.findall(endgame_pattern, content)
    endgame_situations = []
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '下家还有' in line:
            cards_left = re.search(r'下家还有(\d+)张牌', line)
            if cards_left:
                cards = int(cards_left.group(1))
                if cards <= 5:
                    # 查找前后的动作
                    context_start = max(0, i - 5)
                    context_end = min(len(lines), i + 5)
                    context = '\n'.join(lines[context_start:context_end])
                    endgame_situations.append({
                        'line': i,
                        'cards_left': cards,
                        'context': context
                    })
    
    print(f"残局情况（剩余牌 <= 5）: {len(endgame_situations)} 次")
    for situation in endgame_situations[:10]:
        print(f"\n  行{situation['line']}: 剩余{situation['cards_left']}张牌")
        # 提取关键信息
        if '0号位' in situation['context'] or '2号位' in situation['context']:
            print(f"    涉及YF V4")
    
    return {
        'pass_stats': pass_counter,
        'high_passes': high_passes,
        'teammate_mistakes': teammate_mistakes,
        'teammate_correct': teammate_correct,
        'yf_passes': yf_passes,
        'endgame_situations': endgame_situations
    }

if __name__ == '__main__':
    result = analyze_battle_log('yfscore/yfscore/yfv4_vs_lalala')
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)

