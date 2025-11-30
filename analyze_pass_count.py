# -*- coding: utf-8 -*-
"""
统计指标1：连续PASS次数
"""
import re
from collections import Counter

def analyze_pass_count(file_path):
    """统计连续PASS次数"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取所有"连续pass数目：X"的记录
    pattern = r'(\d+)号位打出.*?连续pass数目：\s*(\d+)'
    matches = re.findall(pattern, content)
    
    print("=" * 60)
    print("指标1：连续PASS次数统计")
    print("=" * 60)
    print(f"总记录数: {len(matches)}")
    
    if not matches:
        print("未找到匹配的记录，检查文件格式...")
        # 尝试更简单的模式
        simple_pattern = r'连续pass数目：\s*(\d+)'
        simple_matches = re.findall(simple_pattern, content)
        print(f"找到 '连续pass数目' 出现次数: {len(simple_matches)}")
        if simple_matches:
            counter = Counter([int(m) for m in simple_matches])
            print("连续PASS分布:")
            for count, freq in sorted(counter.items()):
                print(f"  {count}次连续PASS: {freq}次")
        return
    
    # 按位置统计
    pass_by_pos = defaultdict(list)
    for pos, count in matches:
        pass_by_pos[int(pos)].append(int(count))
    
    # 统计每个位置的连续PASS分布
    print("\n各位置连续PASS统计:")
    for pos in sorted(pass_by_pos.keys()):
        counter = Counter(pass_by_pos[pos])
        total = len(pass_by_pos[pos])
        high_pass = sum(1 for c in pass_by_pos[pos] if c >= 2)
        print(f"\n{pos}号位:")
        print(f"  总动作数: {total}")
        print(f"  连续PASS >= 2的次数: {high_pass}")
        print(f"  连续PASS分布:")
        for count, freq in sorted(counter.items()):
            print(f"    {count}次连续PASS: {freq}次")
    
    # YF V4 (0号和2号) vs lalala (1号和3号)
    print("\n" + "=" * 60)
    print("YF V4 vs lalala 对比")
    print("=" * 60)
    
    yf_positions = [0, 2]
    lalala_positions = [1, 3]
    
    yf_high_passes = []
    lalala_high_passes = []
    
    for pos, count in matches:
        pos_int = int(pos)
        count_int = int(count)
        if pos_int in yf_positions and count_int >= 2:
            yf_high_passes.append((pos_int, count_int))
        elif pos_int in lalala_positions and count_int >= 2:
            lalala_high_passes.append((pos_int, count_int))
    
    print(f"\nYF V4 (0号和2号) 连续PASS >= 2的情况: {len(yf_high_passes)} 次")
    for pos, count in yf_high_passes[:30]:
        print(f"  {pos}号位: {count}次连续PASS")
    
    print(f"\nlalala (1号和3号) 连续PASS >= 2的情况: {len(lalala_high_passes)} 次")
    for pos, count in lalala_high_passes[:30]:
        print(f"  {pos}号位: {count}次连续PASS")
    
    return {
        'total_records': len(matches),
        'yf_high_passes': len(yf_high_passes),
        'lalala_high_passes': len(lalala_high_passes)
    }

if __name__ == '__main__':
    from collections import defaultdict
    result = analyze_pass_count('yfscore/yfscore/yfv4_vs_lalala')
    print("\n" + "=" * 60)
    print("统计完成")
    print("=" * 60)

