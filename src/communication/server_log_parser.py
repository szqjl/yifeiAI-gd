# -*- coding: utf-8 -*-
"""
服务器日志解析器 - 从服务器日志中提取游戏数据
用于整合服务器日志和客户端决策记录，实现更准确的游戏回放
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional


class ServerLogParser:
    """服务器日志解析器"""
    
    def __init__(self):
        # 正则表达式：匹配服务器日志行
        self.log_pattern = re.compile(r'\[I (\d{6} \d{6}) server:\d+\] (\w+) send \{\'actIndex\': (\d+)\} (\[.*?\])')
        # 正则表达式：匹配游戏开始信息
        self.game_start_pattern = re.compile(r'游戏开始')
        # 正则表达式：匹配玩家初始手牌
        self.initial_hand_pattern = re.compile(r'(\w+)初始手牌: (\[.*?\])')
        
        # 设置日志，添加控制台输出
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # 设置为DEBUG级别
        
        # 添加控制台处理器
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
    def parse_log_file(self, log_path: str) -> Dict[str, Any]:
        """
        解析服务器日志文件
        
        Args:
            log_path: 日志文件路径
            
        Returns:
            解析后的游戏数据
        """
        game_data = {
            "server_actions": [],  # 从服务器提取的动作
            "initial_hands": {},  # 从服务器提取的初始手牌
            "game_id": None,  # 游戏ID
            "start_time": None,  # 开始时间
            "end_time": None,  # 结束时间
            "duration": 0.0  # 游戏时长
        }
        
        # 尝试使用多种编码打开文件，增强编码处理能力
        encodings = ['utf-8', 'gbk', 'cp936', 'gb18030', 'latin-1', 'utf-16', 'utf-32']
        lines = []
        
        # 首先尝试使用常规方式打开文件
        for encoding in encodings:
            try:
                with open(log_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                self.logger.info(f"使用编码 {encoding} 成功打开文件: {log_path}")
                break
            except UnicodeDecodeError:
                self.logger.warning(f"编码 {encoding} 无法解码文件: {log_path}")
                continue
            except Exception as e:
                self.logger.error(f"打开文件失败: {log_path}，错误: {e}")
                continue
        
        # 如果常规方式失败，尝试使用二进制模式读取并解码
        if not lines:
            self.logger.warning(f"常规编码方式失败，尝试使用二进制模式读取: {log_path}")
            try:
                with open(log_path, 'rb') as f:
                    binary_data = f.read()
                
                # 尝试多种编码解码
                for encoding in encodings:
                    try:
                        text = binary_data.decode(encoding)
                        lines = text.splitlines()
                        self.logger.info(f"使用二进制模式+{encoding} 成功解码文件: {log_path}")
                        break
                    except UnicodeDecodeError:
                        continue
                
                # 最后尝试使用errors='replace'，忽略无法解码的字符
                if not lines:
                    text = binary_data.decode('utf-8', errors='replace')
                    lines = text.splitlines()
                    self.logger.info(f"使用二进制模式+utf-8(replace) 成功解码文件: {log_path}")
            except Exception as e:
                self.logger.error(f"二进制模式读取失败: {log_path}，错误: {e}")
        
        if not lines:
            self.logger.error(f"无法打开文件: {log_path}，已尝试所有编码方式")
            return game_data
        
        # 调试：打印前几行
        self.logger.info(f"共读取到 {len(lines)} 行")
        for i, line in enumerate(lines[:5]):
            self.logger.info(f"第 {i+1} 行: {line.strip()[:100]}... (长度: {len(line.strip())})")
        
        # 逐行解析，使用字符串操作替代正则表达式
        matched_count = 0
        unmatched_count = 0
        import ast
        
        for i, line in enumerate(lines):
            try:
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否是有效的日志行
                if not line.startswith('[I'):
                    unmatched_count += 1
                    if i < 5:
                        self.logger.info(f"不是有效的日志行: {line}")
                    continue
                
                # 直接使用字符串操作提取时间戳
                i_pos = line.find('[I') + 2
                server_pos = line.find('server:', i_pos)
                if server_pos == -1:
                    unmatched_count += 1
                    if i < 5:
                        self.logger.info(f"找不到server:位置: {line}")
                    continue
                timestamp_str = line[i_pos:server_pos].strip()
                # 调试：打印提取到的时间戳
                if i < 5:
                    self.logger.info(f"提取到的时间戳: '{timestamp_str}'，长度: {len(timestamp_str)}")
                
                # 提取玩家名称
                server_end_pos = line.find(']', server_pos) + 1
                send_pos = line.find(' send ', server_end_pos)
                if send_pos == -1:
                    unmatched_count += 1
                    if i < 5:
                        self.logger.info(f"找不到send位置: {line}")
                    continue
                player_name = line[server_end_pos:send_pos].strip()
                
                # 提取actIndex
                act_index_start = line.find("'actIndex':") + 11
                act_index_end = line.find("}", act_index_start)
                if act_index_start == -1 or act_index_end == -1:
                    unmatched_count += 1
                    if i < 5:
                        self.logger.info(f"找不到actIndex: {line}")
                    continue
                act_index_str = line[act_index_start:act_index_end].strip()
                act_index = int(act_index_str)
                
                # 提取动作部分
                action_start = line.find('[', act_index_end)
                action_end = line.rfind(']') + 1
                if action_start == -1 or action_end == -1:
                    unmatched_count += 1
                    if i < 5:
                        self.logger.info(f"找不到动作部分: {line}")
                    continue
                action_str = line[action_start:action_end]
                
                # 调试：打印匹配结果
                if i < 5:
                    self.logger.info(f"匹配成功！时间戳: {timestamp_str}, 玩家: {player_name}, actIndex: {act_index}, 动作: {action_str[:50]}...")
                
                # 解析动作
                action = ast.literal_eval(action_str)
                
                # 解析时间戳，使用更直接的方法，跳过不可见字符问题
                # 手动解析时间戳，不依赖datetime.strptime
                try:
                    # 先提取年、月、日
                    year = int(timestamp_str[0:2])
                    month = int(timestamp_str[2:4])
                    day = int(timestamp_str[4:6])
                    
                    # 提取时、分、秒
                    hour = int(timestamp_str[7:9])
                    minute = int(timestamp_str[10:12])
                    second = int(timestamp_str[13:15])
                    
                    # 创建datetime对象
                    timestamp = datetime(year=2000+year, month=month, day=day, 
                                       hour=hour, minute=minute, second=second)
                except Exception as e:
                    # 如果解析失败，使用当前时间作为备选
                    self.logger.warning(f"时间戳解析失败，使用当前时间: {e}")
                    timestamp = datetime.now()
                    
                # 调试：打印解析后的时间戳
                if i < 5:
                    self.logger.info(f"解析后的时间戳: {timestamp}")
                
                # 确定玩家位置
                player_pos = self._get_player_position(player_name)
                
                # 记录服务器动作
                server_action = {
                    "timestamp": timestamp.isoformat(),
                    "player_name": player_name,
                    "player_pos": player_pos,
                    "act_index": act_index,
                    "action": action
                }
                game_data["server_actions"].append(server_action)
                
                matched_count += 1
                
                # 更新开始和结束时间
                if not game_data["start_time"] or timestamp < datetime.fromisoformat(game_data["start_time"]):
                    game_data["start_time"] = timestamp.isoformat()
                if not game_data["end_time"] or timestamp > datetime.fromisoformat(game_data["end_time"]):
                    game_data["end_time"] = timestamp.isoformat()
            except Exception as e:
                unmatched_count += 1
                if unmatched_count < 5:
                    self.logger.error(f"解析行失败: {line[:50]}...，错误: {e}")
                continue
        
        self.logger.info(f"解析完成，匹配到 {matched_count} 行，未匹配到 {unmatched_count} 行")
        
        # 计算游戏时长
        if game_data["start_time"] and game_data["end_time"]:
            try:
                start = datetime.fromisoformat(game_data["start_time"])
                end = datetime.fromisoformat(game_data["end_time"])
                game_data["duration"] = (end - start).total_seconds()
            except Exception as e:
                self.logger.error(f"计算游戏时长失败: {e}")
        
        # 生成游戏ID
        if game_data["start_time"]:
            game_data["game_id"] = game_data["start_time"].replace('-', '').replace(':', '').replace('.', '')[:17]
        
        # 从动作中提取初始手牌
        game_data["initial_hands"] = self._extract_initial_hands(game_data["server_actions"])
        
        self.logger.info(f"解析完成，共找到 {len(game_data['server_actions'])} 个动作")
        return game_data
    
    def _get_player_position(self, player_name: str) -> int:
        """
        根据玩家名称获取位置
        
        Args:
            player_name: 玩家名称
            
        Returns:
            玩家位置 (0-3)
        """
        player_map = {
            # 主要玩家名称映射
            "yf1_v5": 0,
            "client3": 1,
            "yf2_v5": 2,
            "client4": 3,
            # 基本玩家名称映射
            "yf1": 0,
            "yf2": 2,
            # 扩展映射，支持更多可能的玩家名称
            "player0": 0,
            "player1": 1,
            "player2": 2,
            "player3": 3,
            "client1": 0,
            "client2": 1,
            "client0": 0,
            "client4": 3,
            # 支持Test玩家名称
            "Test1": 0,
            "Test2": 1,
            "Test3": 2,
            "Test4": 3,
            # 支持数字形式的玩家名称
            "0": 0,
            "1": 1,
            "2": 2,
            "3": 3
        }
        
        # 首先尝试直接映射
        if player_name in player_map:
            return player_map[player_name]
        
        # 尝试从玩家名称中提取数字
        import re
        match = re.search(r'\d', player_name)
        if match:
            pos = int(match.group())
            return pos if 0 <= pos < 4 else -1
        
        # 最后兜底，根据玩家名称长度映射
        return len(player_name) % 4
    
    def _extract_initial_hands(self, server_actions: List[Dict]) -> Dict[int, List]:
        """
        从服务器动作中提取初始手牌
        
        Args:
            server_actions: 服务器动作列表
            
        Returns:
            所有玩家的初始手牌
        """
        initial_hands = {}
        player_first_action = {}
        
        # 遍历所有动作，提取初始手牌信息
        for action in server_actions:
            try:
                if isinstance(action, dict) and "action" in action:
                    player_pos = action["player_pos"]
                    action_data = action["action"]
                    
                    if isinstance(action_data, list) and len(action_data) > 0:
                        action_type = action_data[0]
                        
                        # 1. 处理初始发牌动作（如果有的话）
                        if action_type == "dispatch":
                            if len(action_data) >= 3 and isinstance(action_data[2], list):
                                # 直接设置初始手牌，确保只设置一次
                                initial_hands[player_pos] = action_data[2].copy()
                                self.logger.info(f"从dispatch动作获取玩家{player_pos}初始手牌: {len(action_data[2])}张")
                        
                        # 2. 处理进贡还贡阶段的信息
                        elif action_type in ["tribute", "back"]:
                            # 只在玩家没有初始手牌时才处理进贡还贡
                            if player_pos not in initial_hands:
                                if len(action_data) >= 3 and isinstance(action_data[2], list):
                                    # 设置初始手牌，而不是extend，避免重复添加
                                    initial_hands[player_pos] = action_data[2].copy()
                                    self.logger.info(f"从{action_type}动作获取玩家{player_pos}初始手牌: {len(action_data[2])}张")
                        
                        # 3. 记录玩家第一次出牌动作，用于后续推断
                        elif action_type != "Pass" and len(action_data) >= 3 and isinstance(action_data[2], list):
                            if player_pos not in player_first_action:
                                player_first_action[player_pos] = action_data[2]
                                self.logger.info(f"记录玩家{player_pos}第一次出牌: {action_type}, {len(action_data[2])}张")
            except Exception as e:
                self.logger.error(f"解析动作失败: {action}, 错误: {e}")
        
        # 调试：打印初始手牌提取结果
        for pos, cards in initial_hands.items():
            self.logger.info(f"玩家{pos}初始手牌: {len(cards)}张")
        self.logger.info(f"玩家第一次出牌记录: {player_first_action}")
        
        return initial_hands
    
    def merge_with_client_records(self, server_data: Dict, client_records: List[Dict]) -> Dict:
        """
        合并服务器数据和客户端记录
        
        Args:
            server_data: 服务器解析的数据
            client_records: 客户端记录列表
            
        Returns:
            合并后的游戏数据
        """
        merged_data = {
            "game_id": server_data["game_id"],
            "start_time": server_data["start_time"],
            "end_time": server_data["end_time"],
            "duration": server_data["duration"],
            "initial_hands": server_data["initial_hands"],
            "server_actions": server_data["server_actions"],
            "client_decisions": {},  # 按玩家位置存储客户端决策
            "all_players_hands": {},
            "actions": []  # 合并后的动作列表
        }
        
        # 合并客户端记录
        for client_record in client_records:
            player_pos = client_record.get("player_id")
            if player_pos is not None:
                # 合并初始手牌
                if "initial_hand" in client_record and player_pos not in merged_data["all_players_hands"]:
                    merged_data["all_players_hands"][player_pos] = client_record["initial_hand"]
                
                # 合并all_players_hands
                if "all_players_hands" in client_record:
                    for pos, hand in client_record["all_players_hands"].items():
                        if isinstance(pos, str):
                            try:
                                pos = int(pos)
                            except:
                                continue
                        if pos not in merged_data["all_players_hands"]:
                            merged_data["all_players_hands"][pos] = hand
                
                # 合并客户端决策
                if "my_decisions" in client_record:
                    merged_data["client_decisions"][player_pos] = client_record["my_decisions"]
        
        # 合并服务器动作到主动作列表
        for server_action in server_data["server_actions"]:
            # 转换为客户端记录格式
            action_record = {
                "timestamp": server_action["timestamp"],
                "cur_pos": server_action["player_pos"],
                "cur_action": server_action["action"],
                "greater_pos": -1,  # 从服务器日志中无法直接获取，需要推断
                "greater_action": [],
                "context": {
                    "player_name": server_action["player_name"]
                }
            }
            merged_data["actions"].append(action_record)
        
        # 按时间排序动作列表
        merged_data["actions"].sort(key=lambda x: x["timestamp"])
        
        return merged_data
    
    @staticmethod
    def generate_replay_file(merged_data: Dict, output_path: str):
        """
        生成回放文件
        
        Args:
            merged_data: 合并后的游戏数据
            output_path: 输出路径
        """
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 示例用法
    parser = ServerLogParser()
    # 解析服务器日志
    server_data = parser.parse_log_file("../../src/communication/Testscore/服务端")
    print(f"解析到 {len(server_data['server_actions'])} 个动作")
    print(f"游戏ID: {server_data['game_id']}")
    print(f"初始手牌: {server_data['initial_hands']}")
    print(f"开始时间: {server_data['start_time']}")
    print(f"结束时间: {server_data['end_time']}")
    print(f"游戏时长: {server_data['duration']:.1f}秒")
    
    # 打印前5个动作
    print("\n前5个动作:")
    for i, action in enumerate(server_data['server_actions'][:5]):
        print(f"  {i+1}. [{action['player_name']}] {action['action']}")
