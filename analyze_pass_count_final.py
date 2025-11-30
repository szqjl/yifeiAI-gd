# -*- coding: utf-8 -*-
"""
统计指标1：连续PASS次数
连续pass数目：表示当前玩家出牌时，之前已经连续有多少个玩家PASS了
"""
import re
from collections import Counter, defaultdict

def analyze_pass_count(file_path):
    """统计连续PASS次数"""
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # 如果文件只有1行，尝试按换行符分割
    if len(lines) == 1:
        content = lines[0]
        lines = content.split('\n')
    
    print("=" * 70)
    print("指标1：连续PASS次数统计")
    print("=" * 70)
    print(f"文件总行数: {len(lines)}")
    
    # 提取所有包含"连续pass数目"的行
    pass_data = []
    for i, line in enumerate(lines):
        if '连续pass数目' in line:
            # 提取位置和PASS次数
            # 格式: X号位打出[...]， 最大动作为Y号位... 连续pass数目： Z
            pos_match = re.search(r'(\d+)号位打出', line)
            pass_match = re.search(r'连续pass数目：\s*(\d+)', line)
            greater_match = re.search(r'最大动作为(\d+)号位', line)
            
            if pos_match and pass_match:
                pos = int(pos_match.group(1))
                pass_count = int(pass_match.group(1))
                greater = int(greater_match.group(1)) if greater_match else -1
                
                pass_data.append({
                    'line': i + 1,
                    'pos': pos,
                    'pass_count': pass_count,
                    'greater': greater,
                    'line_content': line.strip()[:100]
                })
    
    print(f"找到包含'连续pass数目'的记录: {len(pass_data)} 条")
    
    if not pass_data:
        print("未找到数据，检查文件格式...")
        return
    
    # 统计连续PASS分布
    pass_counter = Counter([d['pass_count'] for d in pass_data])
    print("\n连续PASS分布:")
    for count, freq in sorted(pass_counter.items()):
        print(f"  {count}次连续PASS: {freq}次")
    
    # 按位置统计
    yf_positions = [0, 2]  # YF V4
    lalala_positions = [1, 3]  # lalala
    
    print("\n" + "=" * 70)
    print("各位置连续PASS统计")
    print("=" * 70)
    
    pass_by_pos = defaultdict(list)
    for d in pass_data:
        pass_by_pos[d['pos']].append(d['pass_count'])
    
    for pos in sorted(pass_by_pos.keys()):
        counter = Counter(pass_by_pos[pos])
        total = len(pass_by_pos[pos])
        high_pass = sum(1 for c in pass_by_pos[pos] if c >= 2)
        
        team = "YF V4" if pos in yf_positions else "lalala"
        print(f"\n{pos}号位 ({team}):")
        print(f"  总动作数: {total}")
        print(f"  连续PASS >= 2的次数: {high_pass}")
        print(f"  连续PASS分布: {dict(sorted(counter.items()))}")
    
    # YF V4 vs lalala 对比
    print("\n" + "=" * 70)
    print("YF V4 vs lalala 对比")
    print("=" * 70)
    
    yf_high_passes = [d for d in pass_data if d['pos'] in yf_positions and d['pass_count'] >= 2]
    lalala_high_passes = [d for d in pass_data if d['pos'] in lalala_positions and d['pass_count'] >= 2]
    
    print(f"\nYF V4 (0号和2号) 连续PASS >= 2的情况: {len(yf_high_passes)} 次")
    for d in yf_high_passes[:30]:
        print(f"  行{d['line']}: {d['pos']}号位, {d['pass_count']}次连续PASS, "
              f"最大动作持有者: {d['greater']}号位")
    
    print(f"\nlalala (1号和3号) 连续PASS >= 2的情况: {len(lalala_high_passes)} 次")
    for d in lalala_high_passes[:30]:
        print(f"  行{d['line']}: {d['pos']}号位, {d['pass_count']}次连续PASS, "
              f"最大动作持有者: {d['greater']}号位")
    
    # 分析高连续PASS时的最大动作持有者
    print("\n" + "=" * 70)
    print("高连续PASS时的控场分析 (连续PASS >= 2)")
    print("=" * 70)
    
    high_pass_control = defaultdict(int)
    for d in pass_data:
        if d['pass_count'] >= 2 and d['greater'] != -1:
            high_pass_control[d['greater']] += 1
    
    print("\n各位置在高连续PASS时的控场次数:")
    for pos in sorted(high_pass_control.keys()):
        team = "YF V4" if pos in yf_positions else "lalala"
        print(f"  {pos}号位 ({team}): {high_pass_control[pos]}次")
    
    return {
        'total_records': len(pass_data),
        'pass_distribution': dict(pass_counter),
        'yf_high_passes': len(yf_high_passes),
        'lalala_high_passes': len(lalala_high_passes),
        'control_stats': dict(high_pass_control)
    }

if __name__ == '__main__':
    result = analyze_pass_count('yfscore/yfscore/yfv4_vs_lalala')
    print("\n" + "=" * 70)
    print("统计完成")
    print("=" * 70)
    if result:
        print(f"\n关键数据:")
        print(f"- 总记录数: {result['total_records']}")
        print(f"- YF V4高连续PASS: {result['yf_high_passes']}次")
        print(f"- lalala高连续PASS: {result['lalala_high_passes']}次")

