#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断GUI卡住问题
检查数据加载、模块导入等可能导致卡住的原因
"""

import sys
import os
import time

# 修复Windows控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 80)
print("GUI卡住问题诊断工具")
print("=" * 80)
print()

# 1. 检查数据目录
print("1. 检查数据目录...")
data_dir = r"D:\YiFeiAI-GD\game_records"
if os.path.exists(data_dir):
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    print(f"   ✅ 数据目录存在: {data_dir}")
    print(f"   📊 JSON文件数量: {len(json_files)}")
    if len(json_files) > 1000:
        print(f"   ⚠️ 文件数量较多，加载可能需要较长时间")
else:
    print(f"   ❌ 数据目录不存在: {data_dir}")
print()

# 2. 测试模块导入
print("2. 测试模块导入...")
try:
    print("   📦 导入ReplayParser...")
    start_time = time.time()
    from src.knowledge_processor.replay_parser import ReplayParser
    import_time = time.time() - start_time
    print(f"   ✅ ReplayParser导入成功 (耗时: {import_time:.2f}秒)")
except Exception as e:
    print(f"   ❌ ReplayParser导入失败: {e}")
    import traceback
    traceback.print_exc()
print()

# 3. 测试数据加载（少量文件）
print("3. 测试数据加载（前10个文件）...")
try:
    parser = ReplayParser(data_dir)
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')][:10]
    
    print(f"   📖 测试加载 {len(json_files)} 个文件...")
    start_time = time.time()
    test_replays = []
    for i, filename in enumerate(json_files, 1):
        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
                test_replays.append(data)
            if i % 5 == 0:
                print(f"   ⏳ 已加载 {i}/{len(json_files)} 个文件...")
        except Exception as e:
            print(f"   ⚠️ 加载失败 {filename}: {e}")
    
    load_time = time.time() - start_time
    print(f"   ✅ 测试加载完成 (耗时: {load_time:.2f}秒)")
    print(f"   📊 平均每个文件: {load_time/len(json_files)*1000:.2f}毫秒")
    
    # 估算全部文件加载时间
    total_files = len([f for f in os.listdir(data_dir) if f.endswith('.json')])
    estimated_time = (load_time / len(json_files)) * total_files
    print(f"   ⏱️ 估算全部 {total_files} 个文件加载时间: {estimated_time:.1f}秒 ({estimated_time/60:.1f}分钟)")
    
except Exception as e:
    print(f"   ❌ 数据加载测试失败: {e}")
    import traceback
    traceback.print_exc()
print()

# 4. 测试train_bc导入
print("4. 测试train_bc函数导入...")
try:
    print("   📦 导入train_bc...")
    start_time = time.time()
    from src.train.pretrain import train_bc
    import_time = time.time() - start_time
    print(f"   ✅ train_bc导入成功 (耗时: {import_time:.2f}秒)")
except Exception as e:
    print(f"   ❌ train_bc导入失败: {e}")
    import traceback
    traceback.print_exc()
print()

# 5. 建议
print("=" * 80)
print("诊断建议")
print("=" * 80)
print()
print("如果GUI在'启用动态阈值调整: True'后卡住，可能的原因：")
print()
print("1. ⏳ 数据加载中（最可能）")
print("   - game_records目录有4000+个文件")
print("   - 加载所有文件需要较长时间")
print("   - 建议：等待1-2分钟，GUI应该会继续响应")
print()
print("2. 🔄 模块导入中")
print("   - train_bc或相关模块导入较慢")
print("   - 建议：检查是否有模块导入错误")
print()
print("3. 💾 内存不足")
print("   - 加载大量数据可能导致内存不足")
print("   - 建议：关闭其他程序，释放内存")
print()
print("解决方案：")
print("1. ✅ 等待：数据加载完成后GUI会自动继续")
print("2. ✅ 查看日志：训练监控标签页会显示加载进度")
print("3. ✅ 减少数据量：使用max_samples参数限制训练样本数")
print("4. ✅ 分批训练：将数据分成多个目录，分批训练")
print()

