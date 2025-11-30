# -*- coding: utf-8 -*-
"""
分析对战日志：提取连续PASS和队友识别问题
YF V4: 0号位(yf1_v4) 和 2号位(yf2_v4) 是队友
lalala: 1号位 和 3号位 是队友
"""
import re
from collections import defaultdict, Counter

def analyze_battle_log(file_path):
    """分析对战日志"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # YF V4位置: 0号和2号
    # lalala位置: 1号和3号
    yf_positions = [0, 2]
    lalala_positions = [1, 3]
    
    print("=" * 70)
    print("对战日志分析：YF V4 vs lalala")
    print("=" * 70)
    print(f"YF V4位置: {yf_positions} (0号=yf1_v4, 2号=yf2_v4)")
    print(f"lalala位置: {lalala_positions}")
    print()
    
    # 1. 提取连续PASS统计
    print("=" * 70)
    print("1. 连续PASS统计")
    print("=" * 70)
    
    pass_data = []
    for line in lines:
        if '连续pass数目' in line:
            # 提取位置和PASS次数
            pos_match = re.search(r'(\d+)号位打出', line)
            pass_match = re.search(r'连续pass数目：\s*(\d+)', line)
            if pos_match and pass_match:
                pos = int(pos_match.group(1))
                pass_count = int(pass_match.group(1))
                pass_data.append((pos, pass_count))
    
    pass_counter = Counter([count for _, count in pass_data])
    print(f"总PASS记录数: {len(pass_data)}")
    print(f"连续PASS分布:")
    for count, freq in sorted(pass_counter.items()):
        print(f"  {count}次连续PASS: {freq}次")
    
    # YF V4的高连续PASS
    yf_high_passes = [(pos, count) for pos, count in pass_data if pos in yf_positions and count >= 2]
    lalala_high_passes = [(pos, count) for pos, count in pass_data if pos in lalala_positions and count >= 2]
    
    print(f"\nYF V4 (0号和2号) 连续PASS >= 2的情况: {len(yf_high_passes)} 次")
    for pos, count in yf_high_passes[:20]:
        print(f"  {pos}号位: {count}次连续PASS")
    
    print(f"\nlalala (1号和3号) 连续PASS >= 2的情况: {len(lalala_high_passes)} 次")
    for pos, count in lalala_high_passes[:20]:
        print(f"  {pos}号位: {count}次连续PASS")
    
    # 2. 分析队友识别问题
    print("\n" + "=" * 70)
    print("2. 队友识别分析（关键问题）")
    print("=" * 70)
    
    # 提取每次出牌的信息：位置、动作、最大动作持有者
    actions = []
    for i, line in enumerate(lines):
        if '号位打出' in line and '最大动作为' in line:
            # 格式: X号位打出[...]， 最大动作为Y号位
            pos_match = re.search(r'(\d+)号位打出', line)
            greater_match = re.search(r'最大动作为(\d+)号位', line)
            action_match = re.search(r'打出(.*?)，', line)
            
            if pos_match and greater_match:
                pos = int(pos_match.group(1))
                greater = int(greater_match.group(1))
                action = action_match.group(1) if action_match else ""
                actions.append({
                    'line_num': i + 1,
                    'pos': pos,
                    'greater': greater,
                    'action': action,
                    'line': line.strip()
                })
    
    # 分析队友控场后的行为
    teammate_mistakes = []  # 队友控场后，YF V4出牌压制队友
    teammate_correct = []   # 队友控场后，YF V4正确PASS
    opponent_suppression = []  # 对手控场后，YF V4正确压制
    
    for i, action in enumerate(actions):
        pos = action['pos']
        greater = action['greater']
        
        # 判断是否是队友控场
        # YF V4: 0和2是队友
        is_teammate_control = ((pos in yf_positions and greater in yf_positions and pos != greater) or
                              (pos in lalala_positions and greater in lalala_positions and pos != greater))
        
        # 判断是否是对手控场
        is_opponent_control = ((pos in yf_positions and greater in lalala_positions) or
                              (pos in lalala_positions and greater in yf_positions))
        
        if is_teammate_control and pos in yf_positions:
            # YF V4的队友控场了
            # 查找下一个动作
            if i + 1 < len(actions):
                next_action = actions[i + 1]
                next_pos = next_action['pos']
                
                # 如果下一个出牌的是YF V4自己，说明队友控场后YF V4出牌了（可能是误认）
                if next_pos in yf_positions and next_pos != greater:
                    # 队友控场后，YF V4出牌了（可能是误认队友）
                    teammate_mistakes.append({
                        'line': action['line_num'],
                        'teammate_pos': greater,
                        'yf_pos': next_pos,
                        'action': action['action'],
                        'next_action': next_action['action']
                    })
                elif 'PASS' in next_action['action']:
                    # 队友控场后，YF V4正确PASS
                    teammate_correct.append({
                        'line': action['line_num'],
                        'teammate_pos': greater,
                        'yf_pos': next_pos if next_pos in yf_positions else None,
                        'action': action['action']
                    })
        
        if is_opponent_control and pos in yf_positions:
            # 对手控场，YF V4应该压制
            if i + 1 < len(actions):
                next_action = actions[i + 1]
                next_pos = next_action['pos']
                if next_pos in yf_positions and 'PASS' not in next_action['action']:
                    # YF V4正确压制对手
                    opponent_suppression.append({
                        'line': action['line_num'],
                        'opponent_pos': greater,
                        'yf_pos': next_pos,
                        'action': action['action'],
                        'suppression_action': next_action['action']
                    })
    
    print(f"\n【问题1】队友控场后，YF V4出牌压制队友（误认队友）: {len(teammate_mistakes)} 次")
    for mistake in teammate_mistakes[:15]:
        print(f"  行{mistake['line']}: 队友{mistake['teammate_pos']}号控场后，"
              f"YF V4({mistake['yf_pos']}号)出牌: {mistake['next_action'][:50]}")
    
    print(f"\n【正确】队友控场后，YF V4正确PASS: {len(teammate_correct)} 次")
    for correct in teammate_correct[:10]:
        print(f"  行{correct['line']}: 队友{correct['teammate_pos']}号控场后，YF V4正确PASS")
    
    print(f"\n【正确】对手控场后，YF V4正确压制: {len(opponent_suppression)} 次")
    for sup in opponent_suppression[:10]:
        print(f"  行{sup['line']}: 对手{sup['opponent_pos']}号控场后，"
              f"YF V4({sup['yf_pos']}号)压制: {sup['suppression_action'][:50]}")
    
    # 3. 分析残局阶段
    print("\n" + "=" * 70)
    print("3. 残局阶段分析（剩余牌数 <= 5）")
    print("=" * 70)
    
    endgame_situations = []
    for i, line in enumerate(lines):
        if '下家还有' in line:
            cards_match = re.search(r'下家还有(\d+)张牌', line)
            if cards_match:
                cards = int(cards_match.group(1))
                if cards <= 5:
                    # 查找前后的动作
                    context_start = max(0, i - 3)
                    context_end = min(len(lines), i + 3)
                    context_lines = lines[context_start:context_end]
                    
                    # 查找YF V4的动作
                    yf_actions = []
                    for ctx_line in context_lines:
                        for yf_pos in yf_positions:
                            if f'{yf_pos}号位打出' in ctx_line:
                                yf_actions.append(ctx_line.strip())
                    
                    endgame_situations.append({
                        'line': i + 1,
                        'cards_left': cards,
                        'yf_actions': yf_actions
                    })
    
    print(f"残局情况（剩余牌 <= 5）: {len(endgame_situations)} 次")
    for situation in endgame_situations[:15]:
        print(f"\n  行{situation['line']}: 剩余{situation['cards_left']}张牌")
        if situation['yf_actions']:
            print(f"    YF V4动作:")
            for action in situation['yf_actions']:
                print(f"      {action[:80]}")
    
    # 4. 统计YF V4的PASS率
    print("\n" + "=" * 70)
    print("4. YF V4 PASS率统计")
    print("=" * 70)
    
    yf_total_actions = len([a for a in actions if a['pos'] in yf_positions])
    yf_pass_actions = len([a for a in actions if a['pos'] in yf_positions and 'PASS' in a['action']])
    
    lalala_total_actions = len([a for a in actions if a['pos'] in lalala_positions])
    lalala_pass_actions = len([a for a in actions if a['pos'] in lalala_positions and 'PASS' in a['action']])
    
    print(f"YF V4总动作数: {yf_total_actions}")
    print(f"YF V4 PASS次数: {yf_pass_actions}")
    print(f"YF V4 PASS率: {yf_pass_actions/yf_total_actions*100:.1f}%" if yf_total_actions > 0 else "N/A")
    
    print(f"\nlalala总动作数: {lalala_total_actions}")
    print(f"lalala PASS次数: {lalala_pass_actions}")
    print(f"lalala PASS率: {lalala_pass_actions/lalala_total_actions*100:.1f}%" if lalala_total_actions > 0 else "N/A")
    
    # 5. 分析关键决策点
    print("\n" + "=" * 70)
    print("5. 关键决策点分析")
    print("=" * 70)
    
    # 查找队友快走完时的决策
    teammate_near_end = []
    for i, action in enumerate(actions):
        if action['pos'] in yf_positions:
            # 查找当前剩余牌数信息
            # 在action前后查找"下家还有X张牌"
            for j in range(max(0, i-5), min(len(lines), i+5)):
                if '下家还有' in lines[j]:
                    cards_match = re.search(r'下家还有(\d+)张牌', lines[j])
                    if cards_match:
                        cards = int(cards_match.group(1))
                        # 判断是否是队友（2号位对0号位，0号位对2号位）
                        teammate_cards = cards  # 简化：假设是队友的牌数
                        if teammate_cards <= 3:
                            teammate_near_end.append({
                                'line': action['line_num'],
                                'yf_pos': action['pos'],
                                'teammate_cards': teammate_cards,
                                'action': action['action']
                            })
                        break
    
    print(f"队友剩余牌 <= 3时，YF V4的决策: {len(teammate_near_end)} 次")
    for decision in teammate_near_end[:15]:
        pass_status = "PASS" if 'PASS' in decision['action'] else "出牌"
        print(f"  行{decision['line']}: YF V4({decision['yf_pos']}号) {pass_status}, "
              f"队友剩余{decision['teammate_cards']}张")
    
    return {
        'pass_stats': pass_counter,
        'yf_high_passes': yf_high_passes,
        'teammate_mistakes': teammate_mistakes,
        'teammate_correct': teammate_correct,
        'opponent_suppression': opponent_suppression,
        'endgame_situations': endgame_situations,
        'yf_pass_rate': yf_pass_actions/yf_total_actions if yf_total_actions > 0 else 0
    }

if __name__ == '__main__':
    result = analyze_battle_log('yfscore/yfscore/yfv4_vs_lalala')
    print("\n" + "=" * 70)
    print("分析完成")
    print("=" * 70)
    print(f"\n关键发现:")
    print(f"- YF V4误认队友次数: {len(result['teammate_mistakes'])}")
    print(f"- YF V4正确PASS次数: {len(result['teammate_correct'])}")
    print(f"- YF V4 PASS率: {result['yf_pass_rate']*100:.1f}%")

