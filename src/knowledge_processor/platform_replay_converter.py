# -*- coding: utf-8 -*-
"""
平台.rep文件转换为训练数据格式
将平台XML格式的.rep文件转换为可用于预训练的JSON格式
"""

import sys
import os
import xml.etree.ElementTree as ET
import json
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def parse_card_string(card_str: str) -> List[str]:
    """
    解析卡牌字符串，转换为标准格式
    例如: "RRC3C3SAHAHAHKHKHQHQSJCTDTS9D9S8C8D7D7S6H6D6S5H5D5C4C4"
    转换为: ["RR", "C3", "C3", "SA", "HA", "HA", ...]
    
    注意：平台格式中：
    - 大王：RR
    - 小王：rr
    - 需要转换为标准格式：R（大王）、B（小王）
    """
    cards = []
    i = 0
    while i < len(card_str):
        # 检查是否是大小王
        if i + 2 <= len(card_str) and card_str[i:i+2] == "RR":
            cards.append("R")  # 大王
            i += 2
        elif i + 2 <= len(card_str) and card_str[i:i+2] == "rr":
            cards.append("B")  # 小王
            i += 2
        elif i + 2 <= len(card_str):
            # 普通卡牌：花色+点数
            suit = card_str[i]
            rank = card_str[i+1]
            cards.append(f"{suit}{rank}")
            i += 2
        else:
            i += 1
    return cards

def parse_action_data(action_name: str, data: str) -> tuple:
    """
    解析动作数据
    返回: (action_type, cards_list)
    """
    if action_name == "Pass":
        return "PASS", []
    elif action_name == "Discard":
        # 解析卡牌字符串
        cards = parse_card_string(data)
        return "Discard", cards
    elif action_name == "dispatch":
        # 发牌，解析初始手牌
        cards = parse_card_string(data)
        return "dispatch", cards
    else:
        return action_name, []

def get_winner_from_rep(rep_path: str) -> int:
    """
    从.rep文件中识别获胜玩家
    
    规则：
    1. 查找最后一个Rank动作，data="2"的玩家是获胜者（升到2级）
    2. 如果没有Rank="2"，查找GameEnd动作判断
    
    Returns:
        获胜玩家的seat，如果无法确定则返回None
    """
    try:
        tree = ET.parse(rep_path)
        root = tree.getroot()
        actions_elem = root.find("actions")
        
        if actions_elem:
            winner_seat = None
            last_rank_2_seat = None
            
            for action in actions_elem.findall("action"):
                action_name = action.get("name")
                seat = action.get("seat")
                data = action.get("data", "")
                
                # 查找Rank动作，data="2"表示升到2级（获胜）
                if action_name == "Rank" and data == "2" and seat is not None:
                    last_rank_2_seat = int(seat)
                
                # 查找GameEnd动作
                if action_name == "GameEnd":
                    # 如果data="WON"，记录者（playerid对应的seat）获胜
                    # 如果data="LOST"，记录者失败
                    if data == "WON":
                        # 需要找到记录者的seat
                        playerid = root.get("playerid")
                        players_elem = root.find("players")
                        if players_elem:
                            for player in players_elem.findall("player"):
                                if player.get("id") == playerid:
                                    winner_seat = int(player.get("seat"))
                                    break
            
            # 优先使用Rank="2"的结果
            if last_rank_2_seat is not None:
                return last_rank_2_seat
            elif winner_seat is not None:
                return winner_seat
                
    except Exception as e:
        print(f"识别获胜玩家失败: {e}")
    
    return None

def convert_rep_to_training_format(rep_path: str, target_player_id: int = None, prefer_winner: bool = False) -> Dict:
    """
    将.rep文件转换为训练数据格式
    
    Args:
        rep_path: .rep文件路径
        target_player_id: 目标玩家ID（seat），如果为None，则提取所有玩家的数据
        prefer_winner: 如果target_player_id为None且prefer_winner=True，则优先选择获胜玩家
    
    Returns:
        训练数据格式的字典
    """
    try:
        # 如果prefer_winner=True且target_player_id为None，尝试识别获胜玩家
        if prefer_winner and target_player_id is None:
            winner_seat = get_winner_from_rep(rep_path)
            if winner_seat is not None:
                target_player_id = winner_seat
                print(f"自动识别获胜玩家: seat={winner_seat}")
        # 解析XML文件
        tree = ET.parse(rep_path)
        root = tree.getroot()
        
        # 提取玩家信息
        players = {}
        players_elem = root.find("players")
        if players_elem:
            for player in players_elem.findall("player"):
                seat = int(player.get("seat"))
                players[seat] = {
                    "id": player.get("id"),
                    "name": player.get("name"),
                    "nickname": player.get("nickname"),
                    "seat": seat
                }
        
        # 提取初始手牌和动作
        initial_hands = {}
        actions = []
        actions_elem = root.find("actions")
        
        if actions_elem:
            for action in actions_elem.findall("action"):
                action_name = action.get("name")
                seat = action.get("seat")
                data = action.get("data", "")
                
                if action_name == "dispatch" and seat is not None:
                    # 发牌，记录初始手牌
                    seat_num = int(seat)
                    _, cards = parse_action_data(action_name, data)
                    initial_hands[seat_num] = cards
                elif action_name in ["Discard", "Pass"] and seat is not None:
                    # 出牌或PASS
                    seat_num = int(seat)
                    action_type, cards = parse_action_data(action_name, data)
                    
                    actions.append({
                        "cur_pos": seat_num,
                        "cur_action": [action_type] + ([cards] if cards else []),
                        "action_type": action_type,
                        "cards": cards
                    })
        
        # 转换为训练数据格式
        training_data = []
        
        # 确定要提取的玩家
        target_seats = [target_player_id] if target_player_id is not None else list(initial_hands.keys())
        
        for seat in target_seats:
            if seat not in initial_hands:
                continue
                
            # 初始化手牌
            hand = set(initial_hands[seat])
            history = []
            
            # 遍历动作，提取该玩家的训练样本
            for action in actions:
                actor_seat = action["cur_pos"]
                action_type = action["action_type"]
                cards = action["cards"]
                
                # 如果是目标玩家的动作，记录训练样本
                if actor_seat == seat:
                    # 构建状态
                    state = {
                        "hand": list(hand),
                        "history": history[-10:] if len(history) > 10 else history
                    }
                    
                    # 目标动作（卡牌列表）
                    target = cards if action_type == "Discard" else []
                    
                    if target:  # 只记录非PASS的动作
                        training_data.append({
                            "player_seat": seat,
                            "state": state,
                            "action": target
                        })
                    
                    # 更新手牌（移除打出的牌）
                    if action_type == "Discard":
                        for card in cards:
                            if card in hand:
                                hand.remove(card)
                
                # 更新历史
                history.append({
                    "player": actor_seat,
                    "action_type": action_type,
                    "cards": cards
                })
        
        return {
            "replay_file": os.path.basename(rep_path),
            "players": players,
            "training_samples": training_data
        }
        
    except Exception as e:
        print(f"Error converting {rep_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def convert_to_replay_parser_format(training_data: Dict) -> List[Dict]:
    """
    将转换后的训练数据格式转换为ReplayParser期望的格式
    
    Args:
        training_data: convert_rep_to_training_format返回的格式
        
    Returns:
        ReplayParser格式的replay列表
    """
    replays = []
    
    # 按玩家分组
    players_data = {}
    for sample in training_data.get("training_samples", []):
        seat = sample["player_seat"]
        if seat not in players_data:
            players_data[seat] = {
                "player_id": seat,
                "initial_hand": sample["state"]["hand"],
                "actions": []
            }
        
        # 构建动作字符串
        action_type = "PASS" if len(sample["action"]) == 0 else "Discard"
        if action_type == "PASS":
            action_str = "['PASS', 'PASS', 'PASS']"
        else:
            action_str = f"['{action_type}', '{action_type}', {sample['action']}]"
        
        players_data[seat]["actions"].append({
            "cur_pos": seat,
            "cur_action": action_str
        })
    
    # 转换为ReplayParser格式
    for seat, data in players_data.items():
        replays.append({
            "player_id": data["player_id"],
            "initial_hand": data["initial_hand"],
            "actions": data["actions"]
        })
    
    return replays

def convert_rep_directory(rep_dir: str, output_dir: str = "game_records", target_player_id: int = None, format: str = "training", prefer_winner: bool = False):
    """
    批量转换.rep文件目录
    
    Args:
        rep_dir: .rep文件所在目录
        output_dir: 输出JSON文件目录
        target_player_id: 目标玩家ID（seat），如果为None，则提取所有玩家
    """
    os.makedirs(output_dir, exist_ok=True)
    
    converted_count = 0
    total_samples = 0
    
    # 遍历目录
    for root, dirs, files in os.walk(rep_dir):
        for file in files:
            if file.endswith(".rep"):
                rep_path = os.path.join(root, file)
                print(f"Processing: {rep_path}")
                
                # 转换文件
                training_data = convert_rep_to_training_format(rep_path, target_player_id, prefer_winner)
                
                if training_data and len(training_data["training_samples"]) > 0:
                    # 根据格式选择保存方式
                    if format == "replay_parser":
                        # 转换为ReplayParser格式
                        replays = convert_to_replay_parser_format(training_data)
                        for replay in replays:
                            output_filename = f"{file.replace('.rep', '')}_player{replay['player_id']}.json"
                            output_path = os.path.join(output_dir, output_filename)
                            with open(output_path, 'w', encoding='utf-8') as f:
                                json.dump(replay, f, ensure_ascii=False, indent=2)
                            converted_count += 1
                            total_samples += len(replay.get("actions", []))
                    else:
                        # 保存为训练数据格式
                        output_filename = file.replace(".rep", ".json")
                        output_path = os.path.join(output_dir, output_filename)
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(training_data, f, ensure_ascii=False, indent=2)
                        sample_count = len(training_data["training_samples"])
                        total_samples += sample_count
                        converted_count += 1
                        print(f"  ✓ Converted: {sample_count} training samples -> {output_path}")
                else:
                    print(f"  ✗ No training samples extracted")
    
    print(f"\n转换完成:")
    print(f"  转换文件数: {converted_count}")
    print(f"  总训练样本数: {total_samples}")
    print(f"  输出目录: {output_dir}")

if __name__ == "__main__":
    # 测试转换单个文件
    test_file = r"C:\Program Files (x86)\gdgame\MobileGD\replay\szqjl_2024-02-04_12_20_23_\_2024-02-04_12_15_56.rep"
    
    if os.path.exists(test_file):
        print("测试转换单个文件...")
        result = convert_rep_to_training_format(test_file, target_player_id=2)  # seat=2是szqjl
        if result:
            print(f"提取到 {len(result['training_samples'])} 个训练样本")
            if len(result['training_samples']) > 0:
                print(f"示例样本:")
                print(json.dumps(result['training_samples'][0], ensure_ascii=False, indent=2))
    else:
        print(f"测试文件不存在: {test_file}")
        print("\n使用方法:")
        print("  python src/knowledge_processor/platform_replay_converter.py")
        print("  然后调用 convert_rep_directory() 函数")

