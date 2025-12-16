#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析现有JSON数据的完整性
检查是否需要从.rep文件重新转换或补充数据
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

# 修复Windows控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def analyze_json_file(json_path):
    """分析单个JSON文件"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analysis = {
            'file': os.path.basename(json_path),
            'has_game_result': False,
            'game_result': None,
            'has_rank': False,
            'rank': None,
            'has_all_ranks': False,
            'all_ranks': None,
            'has_conversion_meta': False,
            'needs_update': False
        }
        
        # 检查game_info
        game_info = data.get('game_info', {})
        if 'game_result' in game_info:
            analysis['has_game_result'] = True
            analysis['game_result'] = game_info['game_result']
            if game_info['game_result'] == 'unknown':
                analysis['needs_update'] = True
        
        if 'rank' in game_info:
            analysis['has_rank'] = True
            analysis['rank'] = game_info['rank']
        
        if 'all_ranks' in game_info:
            analysis['has_all_ranks'] = True
            analysis['all_ranks'] = game_info['all_ranks']
        
        # 检查转换元数据
        if '_conversion_meta' in data:
            analysis['has_conversion_meta'] = True
        
        return analysis
        
    except Exception as e:
        return {
            'file': os.path.basename(json_path),
            'error': str(e),
            'needs_update': True
        }

def main():
    """主函数"""
    data_dir = r"D:\YiFeiAI-GD\game_records"
    
    if not os.path.exists(data_dir):
        print(f"❌ 目录不存在: {data_dir}")
        return
    
    print("=" * 80)
    print("现有JSON数据完整性分析")
    print("=" * 80)
    print(f"\n分析目录: {data_dir}\n")
    
    # 统计信息
    stats = {
        'total_files': 0,
        'has_result': 0,
        'has_real_result': 0,  # 不是"unknown"的结果
        'has_rank': 0,
        'has_all_ranks': 0,
        'needs_update': 0,
        'errors': 0
    }
    
    # 分析所有JSON文件
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    stats['total_files'] = len(json_files)
    
    print(f"找到 {len(json_files)} 个JSON文件\n")
    print("正在分析...\n")
    
    sample_analyses = []
    for json_file in json_files[:20]:  # 先分析前20个
        json_path = os.path.join(data_dir, json_file)
        analysis = analyze_json_file(json_path)
        
        if 'error' in analysis:
            stats['errors'] += 1
            continue
        
        if analysis['has_game_result']:
            stats['has_result'] += 1
            if analysis['game_result'] != 'unknown':
                stats['has_real_result'] += 1
        
        if analysis['has_rank']:
            stats['has_rank'] += 1
        
        if analysis['has_all_ranks']:
            stats['has_all_ranks'] += 1
        
        if analysis['needs_update']:
            stats['needs_update'] += 1
        
        sample_analyses.append(analysis)
    
    # 打印统计结果
    print("=" * 80)
    print("统计结果（前20个文件）")
    print("=" * 80)
    print(f"总文件数: {stats['total_files']}")
    print(f"有game_result字段: {stats['has_result']}")
    print(f"有真实结果（不是unknown）: {stats['has_real_result']}")
    print(f"有rank字段: {stats['has_rank']}")
    print(f"有all_ranks字段: {stats['has_all_ranks']}")
    print(f"需要更新: {stats['needs_update']}")
    print(f"错误文件: {stats['errors']}")
    
    # 打印示例分析
    print("\n" + "=" * 80)
    print("示例文件分析（前5个）")
    print("=" * 80)
    for analysis in sample_analyses[:5]:
        print(f"\n文件: {analysis['file']}")
        print(f"  有game_result: {analysis['has_game_result']} ({analysis['game_result']})")
        print(f"  有rank: {analysis['has_rank']} ({analysis['rank']})")
        print(f"  有all_ranks: {analysis['has_all_ranks']}")
        print(f"  需要更新: {analysis['needs_update']}")
    
    # 建议
    print("\n" + "=" * 80)
    print("建议")
    print("=" * 80)
    
    if stats['has_real_result'] == 0:
        print("❌ 所有文件都没有真实的比赛结果（都是'unknown'）")
        print("   建议：从.rep文件重新转换或补充比赛结果")
    elif stats['has_real_result'] < stats['has_result']:
        print(f"⚠️ 部分文件（{stats['has_result'] - stats['has_real_result']}个）没有真实的比赛结果")
        print("   建议：补充缺失的比赛结果")
    else:
        print("✅ 所有文件都有真实的比赛结果")
        print("   不需要重新转换")
    
    if stats['has_rank'] == 0:
        print("\n❌ 没有文件包含排名信息（rank字段）")
        print("   建议：从.rep文件补充排名信息")
    
    if stats['needs_update'] > 0:
        print(f"\n⚠️ 有 {stats['needs_update']} 个文件需要更新")
        print("   建议：运行批量更新脚本补充缺失信息")

if __name__ == "__main__":
    main()

