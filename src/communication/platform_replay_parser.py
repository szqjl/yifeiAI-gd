# -*- coding: utf-8 -*-
"""
平台比赛记录解析器 - 解析掼蛋游戏平台的比赛记录格式
用于将平台比赛记录转换为系统可识别的游戏回放格式
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any


class PlatformReplayParser:
    """平台比赛记录解析器"""
    
    def __init__(self):
        """初始化解析器"""
        # 设置日志
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # 添加控制台处理器
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def parse_platform_replay(self, rep_path: str) -> Dict[str, Any]:
        """
        解析平台比赛记录文件
        
        Args:
            rep_path: 比赛记录文件路径
            
        Returns:
            解析后的游戏数据
        """
        game_data = {
            "game_id": None,
            "start_time": None,
            "end_time": None,
            "duration": 0.0,
            "players": [],
            "initial_hands": {},
            "actions": []
        }
        
        try:
            # 解析XML文件
            tree = ET.parse(rep_path)
            root = tree.getroot()
            
            # 提取游戏基本信息
            game_data["game_id"] = root.get("time").replace(" ", "T").replace(":", "")[:17]
            game_data["start_time"] = root.get("time")
            
            # 提取玩家信息
            players = root.find("players")
            if players:
                for player in players.findall("player"):
                    game_data["players"].append({
                        "id": player.get("id"),
                        "name": player.get("name"),
                        "nickname": player.get("nickname"),
                        "seat": int(player.get("seat"))
                    })
            
            # 提取动作信息
            actions = root.find("actions")
            if actions:
                last_time = 0
                for action in actions.findall("action"):
                    action_name = action.get("name")
                    action_time = int(action.get("time")) / 1000.0  # 转换为秒
                    seat = action.get("seat")
                    data = action.get("data")
                    
                    # 更新最后时间，计算游戏时长
                    if action_time > last_time:
                        last_time = action_time
                    
                    # 转换为系统动作格式
                    system_action = {
                        "timestamp": datetime.now().isoformat(),  # 平台记录中没有实际时间戳，使用当前时间
                        "cur_pos": int(seat) if seat is not None else -1,
                        "cur_action": [action_name, data],
                        "timestamp_ms": action_time * 1000.0,
                        "action_type": action_name,
                        "action_data": data
                    }
                    
                    # 提取初始手牌
                    if action_name == "dispatch" and seat is not None:
                        game_data["initial_hands"][int(seat)] = data
                    
                    game_data["actions"].append(system_action)
                
                # 设置游戏时长
                game_data["duration"] = last_time
            
            self.logger.info(f"解析完成，共找到 {len(game_data['actions'])} 个动作")
            
        except Exception as e:
            self.logger.error(f"解析平台比赛记录失败: {e}")
        
        return game_data
    
    def convert_to_system_format(self, platform_data: Dict) -> Dict:
        """
        将平台比赛记录转换为系统可识别的格式
        
        Args:
            platform_data: 平台比赛记录数据
            
        Returns:
            系统格式的游戏数据
        """
        # 创建系统格式数据
        system_data = {
            "game_id": platform_data.get("game_id"),
            "start_time": platform_data.get("start_time"),
            "end_time": platform_data.get("end_time"),
            "duration": platform_data.get("duration"),
            "initial_hands": platform_data.get("initial_hands", {}),
            "server_actions": [],
            "client_decisions": {},
            "all_players_hands": platform_data.get("initial_hands", {}),
            "actions": platform_data.get("actions", [])
        }
        
        # 转换平台动作到服务器动作格式
        for action in platform_data.get("actions", []):
            server_action = {
                "timestamp": action["timestamp"],
                "player_name": f"player_{action['cur_pos']}",
                "player_pos": action["cur_pos"],
                "act_index": 0,  # 平台记录中没有actIndex
                "action": [action["action_type"], action["action_data"]]
            }
            system_data["server_actions"].append(server_action)
        
        return system_data
    
    def generate_replay_file(self, system_data: Dict, output_path: str):
        """
        生成系统格式的回放文件
        
        Args:
            system_data: 系统格式的游戏数据
            output_path: 输出文件路径
        """
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(system_data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"回放文件生成成功: {output_path}")


if __name__ == "__main__":
    # 示例用法
    parser = PlatformReplayParser()
    
    # 解析平台比赛记录
    # 注意：这里使用示例路径，实际使用时需要替换为真实路径
    rep_path = "c:\\Program Files (x86)\\gdgame\\MobileGD\\replay\\szqjl_2024-02-04_12_20_23_\\_2024-02-04_12_15_56.rep"
    platform_data = parser.parse_platform_replay(rep_path)
    
    # 转换为系统格式
    system_data = parser.convert_to_system_format(platform_data)
    
    # 生成回放文件
    output_path = "game_records\\platform_enhanced_" + platform_data.get("game_id", "unknown") + ".json"
    parser.generate_replay_file(system_data, output_path)
