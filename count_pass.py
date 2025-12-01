# -*- coding: utf-8 -*-
"""
统计连续PASS次数 - 分段读取大文件
"""
import re
from collections import Counter, defaultdict

def count_pass_in_file(file_path):
    """分段读取文件并统计连续PASS"""
    pass_data = []
    
    # 分段读取文件
    chunk_size = 10000  # 每次读取10KB
    buffer = ""
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            buffer += chunk
            # 处理完整的行
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                
                if '连续pass数目' in line:
                    # 提取位置和PASS次数
                    pos_match = re.search(r'(\d+)号位打出', line)
                    pass_match = re.search(r'连续pass数目：\s*(\d+)', line)
                    greater_match = re.search(r'最大动作为(\d+)号位', line)
                    
                    if pos_match and pass_match:
                        pos = int(pos_match.group(1))
                        pass_count = int(pass_match.group(1))
                        greater = int(greater_match.group(1)) if greater_match else -1
                        
                        pass_data.append({
                            'pos': pos,
                            'pass_count': pass_count,
                            'greater': greater
                        })
    
    # 处理最后一部分
    if buffer and '连续pass数目' in buffer:
        pos_match = re.search(r'(\d+)号位打出', buffer)
        pass_match = re.search(r'连续pass数目：\s*(\d+)', buffer)
        greater_match = re.search(r'最大动作为(\d+)号位', buffer)
        
        if pos_match and pass_match:
            pos = int(pos_match.group(1))
            pass_count = int(pass_match.group(1))
            greater = int(greater_match.group(1)) if greater_match else -1
            pass_data.append({
                'pos': pos,
                'pass_count': pass_count,
                'greater': greater
            })
    
    return pass_data

# 主程序
if __name__ == '__main__':
    print("=" * 70)
    print("指标1：连续PASS次数统计")
    print("=" * 70)
    
    try:
        pass_data = count_pass_in_file('yfscore/yfscore/yfv4_vs_lalala')
        print(f"找到记录数: {len(pass_data)}")
        
        if not pass_data:
            print("未找到数据")
        else:
            # 统计分布
            counter = Counter([d['pass_count'] for d in pass_data])
            print("\n连续PASS分布:")
            for count, freq in sorted(counter.items()):
                print(f"  {count}次连续PASS: {freq}次")
            
            # 按位置统计
            yf_positions = [0, 2]
            lalala_positions = [1, 3]
            
            print("\n各位置统计:")
            pass_by_pos = defaultdict(list)
            for d in pass_data:
                pass_by_pos[d['pos']].append(d['pass_count'])
            
            for pos in sorted(pass_by_pos.keys()):
                team = "YF V4" if pos in yf_positions else "lalala"
                counter_pos = Counter(pass_by_pos[pos])
                high = sum(1 for c in pass_by_pos[pos] if c >= 2)
                print(f"\n{pos}号位 ({team}):")
                print(f"  总动作: {len(pass_by_pos[pos])}")
                print(f"  连续PASS >= 2: {high}次")
                print(f"  分布: {dict(sorted(counter_pos.items()))}")
            
            # YF V4 vs lalala
            yf_high = [d for d in pass_data if d['pos'] in yf_positions and d['pass_count'] >= 2]
            lalala_high = [d for d in pass_data if d['pos'] in lalala_positions and d['pass_count'] >= 2]
            
            print(f"\nYF V4 (0号和2号) 连续PASS >= 2: {len(yf_high)}次")
            print(f"lalala (1号和3号) 连续PASS >= 2: {len(lalala_high)}次")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

