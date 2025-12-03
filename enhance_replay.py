#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
enhance游戏回放生成器 - 整合服务器日志、客户端记录和平台比赛记录

用法：
python enhance_replay.py [服务器日志路径|平台比赛记录路径] [客户端记录路径]

功能：
1. 解析服务器日志，提取完整的出牌过程
2. 解析平台比赛记录，提取游戏数据
3. 加载客户端记录，获取AI决策过程
4. 合并数据，生成增强的游戏回放文件
5. 支持GUI可视化回放
"""

import sys
import os
from pathlib import Path
from typing import List

# 设置路径
sys.path.insert(0, str(Path(__file__).parent / "src"))
os.environ['PYTHONPATH'] = str(Path(__file__).parent / "src")

from communication.server_log_parser import ServerLogParser
from communication.platform_replay_parser import PlatformReplayParser
from communication.game_recorder import GameRecorder


def main():
    """主函数"""
    print("=" * 80)
    print("增强游戏回放生成器")
    print("=" * 80)
    
    # 解析命令行参数
    server_log_path = None
    client_records_path = None
    
    if len(sys.argv) >= 2:
        server_log_path = sys.argv[1]
    if len(sys.argv) >= 3:
        client_records_path = sys.argv[2]
    
    # 默认路径
    if not server_log_path:
        server_log_path = "src/communication/Testscore/服务端"
        print(f"使用默认服务器日志路径: {server_log_path}")
    
    if not client_records_path:
        client_records_path = "game_records"
        print(f"使用默认客户端记录路径: {client_records_path}")
    
    # 检查路径是否存在
    if not Path(server_log_path).exists():
        print(f"错误: 服务器日志路径不存在: {server_log_path}")
        return 1
    
    if not Path(client_records_path).exists():
        print(f"错误: 客户端记录路径不存在: {client_records_path}")
        return 1
    
    # 判断文件类型，选择对应的解析器
    file_ext = Path(server_log_path).suffix.lower()
    server_data = {}
    
    if file_ext == '.rep':
        # 解析平台比赛记录
        print(f"\n正在解析平台比赛记录: {server_log_path}")
        parser = PlatformReplayParser()
        platform_data = parser.parse_platform_replay(server_log_path)
        server_data = parser.convert_to_system_format(platform_data)
    else:
        # 解析服务器日志
        print(f"\n正在解析服务器日志: {server_log_path}")
        parser = ServerLogParser()
        server_data = parser.parse_log_file(server_log_path)
    
    print(f"解析到 {len(server_data['server_actions'])} 个动作")
    print(f"游戏ID: {server_data['game_id']}")
    print(f"开始时间: {server_data['start_time']}")
    print(f"结束时间: {server_data['end_time']}")
    print(f"游戏时长: {server_data['duration']:.1f}秒")
    
    # 加载客户端记录
    print(f"\n正在加载客户端记录: {client_records_path}")
    client_records = []
    
    # 遍历所有JSON文件
    for json_file in Path(client_records_path).glob("*.json"):
        try:
            game_data = GameRecorder.load_game(json_file)
            client_records.append(game_data)
            print(f"✓ 加载成功: {json_file.name}")
        except Exception as e:
            print(f"✗ 加载失败: {json_file.name} - {e}")
    
    if not client_records:
        print("错误: 没有加载到客户端记录")
        return 1
    
    # 合并数据，使用ServerLogParser的merge_with_client_records方法
    print("\n正在合并数据...")
    merge_parser = ServerLogParser()
    merged_data = merge_parser.merge_with_client_records(server_data, client_records)
    
    print(f"合并后数据: {len(merged_data['actions'])} 个动作")
    print(f"包含 {len(merged_data['client_decisions'])} 个客户端的决策记录")
    print(f"初始手牌覆盖 {len(merged_data['all_players_hands'])} 个玩家")
    
    # 生成回放文件
    output_path = Path("game_records") / f"enhanced_{merged_data['game_id']}.json"
    print(f"\n正在生成增强回放文件: {output_path}")
    parser.generate_replay_file(merged_data, str(output_path))
    
    print(f"✓ 增强回放文件生成成功: {output_path}")
    print(f"\n可以使用以下命令查看回放:")
    print(f"python replay_gui.py")
    print(f"或直接运行 REPLAY_GAME.bat")
    
    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
