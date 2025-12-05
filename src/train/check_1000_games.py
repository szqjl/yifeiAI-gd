# -*- coding: utf-8 -*-
"""
检查是否达到1000个对局
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.knowledge_processor.replay_parser import ReplayParser


def check_1000_games():
    """检查是否达到1000个对局"""
    print("="*60)
    print("1000个对局目标检查")
    print("="*60)
    
    # 检查当前对局数
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    current_games = len(replays)
    target_games = 1000
    
    print(f"\n当前对局数: {current_games} 个")
    print(f"目标对局数: {target_games} 个")
    
    if current_games >= target_games:
        print(f"[OK] 已达到目标！超出 {current_games - target_games} 个对局")
    else:
        remaining = target_games - current_games
        print(f"[WARNING] 未达到目标，还差 {remaining} 个对局")
        print(f"   完成度: {current_games / target_games * 100:.1f}%")
    
    # 检查平台目录中的.rep文件
    rep_dir = r"C:\Program Files (x86)\gdgame\MobileGD\replay"
    if os.path.exists(rep_dir):
        rep_files = []
        for root, dirs, files in os.walk(rep_dir):
            for file in files:
                if file.endswith('.rep'):
                    rep_files.append(os.path.join(root, file))
        
        print(f"\n平台目录中的.rep文件数: {len(rep_files)} 个")
        
        if len(rep_files) > current_games:
            available = len(rep_files) - current_games
            print(f"可转换的对局数: 约 {available} 个")
            print(f"[OK] 有足够的原始数据可以转换！")
            
            if available >= remaining:
                print(f"\n建议:")
                print(f"  1. 使用GUI工具批量转换.rep文件")
                print(f"  2. 或者使用命令行批量转换:")
                print(f"     python -c \"from src.knowledge_processor.platform_replay_converter import convert_rep_directory; convert_rep_directory(r'{rep_dir}', 'game_records', None, 'replay_parser', True)\"")
            else:
                print(f"\n[WARNING] 原始数据不足，还需要收集更多对局")
        else:
            print(f"[WARNING] 原始数据已全部转换")
    else:
        print(f"\n[WARNING] 无法访问平台目录: {rep_dir}")
    
    # 数据统计
    print(f"\n" + "="*60)
    print("当前数据统计")
    print("="*60)
    print(f"对局文件数: {current_games} 个")
    print(f"训练样本数: {len(raw_data)} 个")
    print(f"平均每局样本数: {len(raw_data) / current_games if current_games > 0 else 0:.1f} 个")
    
    # 预估
    if current_games < target_games:
        avg_samples = len(raw_data) / current_games if current_games > 0 else 10
        estimated_total = avg_samples * target_games
        print(f"\n预估达到1000个对局时:")
        print(f"  预计训练样本数: 约 {estimated_total:.0f} 个")
        print(f"  当前样本数: {len(raw_data)} 个")
        print(f"  预计增加: 约 {estimated_total - len(raw_data):.0f} 个样本")
    
    print(f"\n" + "="*60)


if __name__ == "__main__":
    check_1000_games()

