# -*- coding: utf-8 -*-
"""
统计指标1：连续PASS次数（简化版）
直接读取文件内容进行统计
"""
import re

# 读取文件
with open('yfscore/yfscore/yfv4_vs_lalala', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("=" * 60)
print("指标1：连续PASS次数统计")
print("=" * 60)
print(f"文件总长度: {len(content)} 字符")

# 方法1：直接搜索"连续pass数目"
pass_pattern = r'连续pass数目：\s*(\d+)'
pass_matches = re.findall(pass_pattern, content)

print(f"\n找到 '连续pass数目' 记录: {len(pass_matches)} 条")

if pass_matches:
    from collections import Counter
    counter = Counter([int(m) for m in pass_matches])
    print("\n连续PASS分布:")
    for count, freq in sorted(counter.items()):
        print(f"  {count}次连续PASS: {freq}次")
    
    # 统计高连续PASS
    high_pass = sum(1 for m in pass_matches if int(m) >= 2)
    print(f"\n连续PASS >= 2的情况: {high_pass} 次")
    
    # 提取位置信息
    print("\n提取位置和PASS次数...")
    full_pattern = r'(\d+)号位打出.*?连续pass数目：\s*(\d+)'
    full_matches = re.findall(full_pattern, content, re.DOTALL)
    
    print(f"找到完整匹配: {len(full_matches)} 条")
    
    if full_matches:
        # 按位置统计
        from collections import defaultdict
        pass_by_pos = defaultdict(list)
        for pos, count in full_matches:
            pass_by_pos[int(pos)].append(int(count))
        
        print("\n各位置连续PASS统计:")
        for pos in sorted(pass_by_pos.keys()):
            counter_pos = Counter(pass_by_pos[pos])
            total = len(pass_by_pos[pos])
            high = sum(1 for c in pass_by_pos[pos] if c >= 2)
            print(f"\n{pos}号位:")
            print(f"  总动作数: {total}")
            print(f"  连续PASS >= 2: {high}次")
            print(f"  分布: {dict(sorted(counter_pos.items()))}")
        
        # YF V4 vs lalala
        yf_positions = [0, 2]
        lalala_positions = [1, 3]
        
        yf_high = [(int(p), int(c)) for p, c in full_matches if int(p) in yf_positions and int(c) >= 2]
        lalala_high = [(int(p), int(c)) for p, c in full_matches if int(p) in lalala_positions and int(c) >= 2]
        
        print(f"\nYF V4 (0号和2号) 连续PASS >= 2: {len(yf_high)} 次")
        for pos, count in yf_high[:20]:
            print(f"  {pos}号位: {count}次连续PASS")
        
        print(f"\nlalala (1号和3号) 连续PASS >= 2: {len(lalala_high)} 次")
        for pos, count in lalala_high[:20]:
            print(f"  {pos}号位: {count}次连续PASS")
else:
    print("\n未找到匹配，尝试其他方法...")
    # 检查文件内容
    if '连续pass' in content:
        print("文件中包含'连续pass'字符串")
        # 查找所有包含连续pass的行
        lines = content.split('\n')
        pass_lines = [l for l in lines if '连续pass' in l]
        print(f"包含'连续pass'的行数: {len(pass_lines)}")
        if pass_lines:
            print("前5行:")
            for i, line in enumerate(pass_lines[:5]):
                print(f"  {i+1}: {line[:100]}")

print("\n" + "=" * 60)
print("统计完成")
print("=" * 60)

