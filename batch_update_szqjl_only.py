#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新szqjl的JSON数据，从.rep文件补充比赛结果
专门针对szqjl记录，改进查找逻辑
"""

import json
import os
import sys
from pathlib import Path

# 修复Windows控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

# 动态导入1312转换器
import importlib.util
converter_path = os.path.join(os.path.dirname(__file__), 'src', 'knowledge_processor', '1312_replay_converter.py')
spec = importlib.util.spec_from_file_location("replay_1312_converter", converter_path)
converter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter_module)
Replay1312Converter = converter_module.Replay1312Converter

def main():
    """主函数"""
    data_dir = r"D:\YiFeiAI-GD\game_records"
    
    if not os.path.exists(data_dir):
        print(f"❌ 目录不存在: {data_dir}")
        return
    
    print("=" * 80)
    print("批量更新szqjl的JSON数据 - 从.rep文件补充比赛结果")
    print("=" * 80)
    print(f"\n数据目录: {data_dir}\n")
    
    # 初始化转换器
    converter = Replay1312Converter()
    
    # 只处理包含szqjl的文件
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and 'szqjl' in f.lower()]
    
    print(f"找到 {len(json_files)} 个szqjl相关的JSON文件")
    print("开始更新...\n")
    
    # 统计信息
    stats = {
        'total': len(json_files),
        'updated': 0,
        'already_has_result': 0,
        'no_rep_file': 0,
        'no_result': 0,
        'errors': 0
    }
    
    # 处理每个文件
    for i, json_file in enumerate(json_files, 1):
        json_path = os.path.join(data_dir, json_file)
        
        if i % 50 == 0:
            print(f"进度: {i}/{len(json_files)} ({i*100//len(json_files)}%)")
        
        try:
            # 读取现有JSON数据
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            player_id = data.get('player_id')
            if player_id is None:
                stats['errors'] += 1
                continue
            
            # 检查是否已有结果
            game_info = data.get('game_info', {})
            if game_info.get('game_result') not in ['unknown', None]:
                stats['already_has_result'] += 1
                continue
            
            # 查找对应的.rep文件
            rep_file = converter.find_corresponding_rep_file(json_path)
            
            if not rep_file or not os.path.exists(rep_file):
                stats['no_rep_file'] += 1
                if i <= 10:  # 显示前10个未找到的文件
                    print(f"⚠️ 未找到.rep文件: {json_file}")
                continue
            
            # 从.rep文件提取比赛结果
            rep_result = converter.extract_result_from_rep_file(rep_file, player_id)
            
            if not rep_result or not rep_result.get('result'):
                stats['no_result'] += 1
                continue
            
            # 更新game_info
            if 'game_info' not in data:
                data['game_info'] = {}
            
            game_info = data['game_info']
            
            # 更新比赛结果
            game_info['game_result'] = rep_result['result']
            
            # 添加排名信息
            if rep_result.get('rank'):
                game_info['rank'] = rep_result['rank']
                rank_names = {1: "头游", 2: "二游", 3: "三游", 4: "四游"}
                game_info['rank_name'] = rank_names.get(rep_result['rank'], f"第{rep_result['rank']}名")
            
            if rep_result.get('ranks'):
                game_info['all_ranks'] = rep_result['ranks']
            
            # 添加更新元数据
            if '_conversion_meta' not in data:
                data['_conversion_meta'] = {}
            
            data['_conversion_meta']['result_updated_from_rep'] = True
            data['_conversion_meta']['rep_file'] = rep_file
            
            # 保存更新后的数据
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            stats['updated'] += 1
            if i <= 10:  # 显示前10个更新结果
                print(f"✅ {json_file}: 结果={rep_result['result']}, 排名={rep_result.get('rank')}")
        
        except Exception as e:
            stats['errors'] += 1
            if i <= 10:
                print(f"❌ {json_file}: {str(e)}")
    
    # 打印统计结果
    print("\n" + "=" * 80)
    print("更新完成统计")
    print("=" * 80)
    print(f"总文件数: {stats['total']}")
    print(f"✅ 成功更新: {stats['updated']}")
    print(f"ℹ️ 已有结果（无需更新）: {stats['already_has_result']}")
    print(f"⚠️ 未找到.rep文件: {stats['no_rep_file']}")
    print(f"⚠️ 无法提取结果: {stats['no_result']}")
    print(f"❌ 错误: {stats['errors']}")
    
    print("\n" + "=" * 80)
    print("建议")
    print("=" * 80)
    
    if stats['updated'] > 0:
        print(f"✅ 成功更新了 {stats['updated']} 个szqjl文件")
        print("   这些文件现在包含真实的比赛结果和排名信息")
    
    if stats['no_rep_file'] > 0:
        print(f"\n⚠️ 有 {stats['no_rep_file']} 个文件未找到对应的.rep文件")
        print("   可能原因：")
        print("   1. .rep文件不在默认位置")
        print("   2. 文件名格式不匹配")
        print("   3. 时间戳差异较大")

if __name__ == "__main__":
    main()

