#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析.rep文件中的比赛结果信息
提取头游、二游、三游、四游等排名信息
"""

import xml.etree.ElementTree as ET
import sys
import os

# 修复Windows控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def analyze_rep_file(rep_path):
    """分析.rep文件，提取比赛结果"""
    try:
        tree = ET.parse(rep_path)
        root = tree.getroot()
        
        # 提取玩家信息
        players = {}
        players_elem = root.find("players")
        if players_elem:
            for player in players_elem.findall("player"):
                seat = int(player.get("seat"))
                players[seat] = {
                    'id': player.get("id"),
                    'name': player.get("name"),
                    'nickname': player.get("nickname"),
                    'seat': seat
                }
        
        # 提取记录者信息
        record_player_id = root.get("playerid")
        record_seat = None
        for seat, player_info in players.items():
            if player_info['id'] == record_player_id:
                record_seat = seat
                break
        
        # 提取Rank动作（排名信息）
        ranks = {}  # {rank: seat}
        actions_elem = root.find("actions")
        if actions_elem:
            for action in actions_elem.findall("action"):
                action_name = action.get("name")
                seat = action.get("seat")
                data = action.get("data", "")
                
                if action_name == "Rank" and seat is not None:
                    rank = int(data) if data.isdigit() else 0
                    seat_num = int(seat)
                    ranks[rank] = seat_num
                    
                    # 打印排名信息
                    player_info = players.get(seat_num, {})
                    rank_names = {1: "头游", 2: "二游", 3: "三游", 4: "四游"}
                    rank_name = rank_names.get(rank, f"第{rank}名")
                    print(f"  {rank_name}: Seat {seat_num} - {player_info.get('nickname', player_info.get('name', 'Unknown'))}")
        
        # 提取GameEnd动作
        game_end_result = None
        for action in actions_elem.findall("action"):
            if action.get("name") == "GameEnd":
                game_end_result = action.get("data", "")
                break
        
        # 分析结果
        result = {
            'players': players,
            'record_seat': record_seat,
            'ranks': ranks,
            'game_end_result': game_end_result,
            'has_complete_results': len(ranks) >= 2  # 至少有头游和二游
        }
        
        return result
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函数"""
    rep_file = r"C:\Program Files (x86)\gdgame\MobileGD\replay\szqjl_2024-02-04_12_20_23_\_2024-02-04_12_15_56.rep"
    
    if not os.path.exists(rep_file):
        print(f"❌ 文件不存在: {rep_file}")
        return
    
    print("=" * 80)
    print("1312 .rep文件比赛结果分析")
    print("=" * 80)
    print(f"\n文件: {os.path.basename(rep_file)}")
    print()
    
    result = analyze_rep_file(rep_file)
    
    if result:
        print("\n📊 比赛结果:")
        print("-" * 80)
        
        if result['ranks']:
            print("\n排名信息（从Rank动作提取）:")
            for rank in sorted(result['ranks'].keys()):
                seat = result['ranks'][rank]
                player_info = result['players'].get(seat, {})
                rank_names = {1: "头游", 2: "二游", 3: "三游", 4: "四游"}
                rank_name = rank_names.get(rank, f"第{rank}名")
                print(f"  ✅ {rank_name}: Seat {seat} - {player_info.get('nickname', player_info.get('name', 'Unknown'))}")
        else:
            print("  ❌ 未找到Rank动作")
        
        if result['game_end_result']:
            print(f"\n游戏结束状态:")
            record_player = result['players'].get(result['record_seat'], {})
            if result['game_end_result'] == "WON":
                print(f"  ✅ 记录者（Seat {result['record_seat']} - {record_player.get('nickname', 'Unknown')}）获胜")
            elif result['game_end_result'] == "LOST":
                print(f"  ❌ 记录者（Seat {result['record_seat']} - {record_player.get('nickname', 'Unknown')}）失败")
            else:
                print(f"  ⚠️ 游戏结束状态: {result['game_end_result']}")
        
        print("\n" + "=" * 80)
        print("📝 总结:")
        print("=" * 80)
        
        if result['has_complete_results']:
            print("✅ .rep文件包含完整的比赛结果信息！")
            print("   - 包含Rank动作，显示每个玩家的排名（头游、二游等）")
            print("   - 包含GameEnd动作，显示游戏结束状态")
            print("\n💡 建议:")
            print("   1. 使用.rep文件转换器提取比赛结果")
            print("   2. 将比赛结果合并到JSON数据中")
            print("   3. 确保训练数据包含真实的比赛结果")
        else:
            print("⚠️ .rep文件可能不包含完整的比赛结果信息")
            print("   建议检查文件是否完整")
        
        # 输出详细结果字典
        print("\n" + "=" * 80)
        print("详细结果:")
        print("=" * 80)
        print(f"排名映射: {result['ranks']}")
        print(f"记录者Seat: {result['record_seat']}")
        print(f"游戏结束状态: {result['game_end_result']}")
        print(f"结果完整性: {result['has_complete_results']}")

if __name__ == "__main__":
    main()

