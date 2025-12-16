# -*- coding: utf-8 -*-
"""
1312掼蛋平台数据格式转换器
将1312格式的JSON数据转换为训练所需的格式
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET


class Replay1312Converter:
    """1312数据格式转换器"""
    
    def __init__(self):
        """初始化转换器"""
        self.card_mapping = {
            'R': 'R',  # 大王/红心配
            'B': 'B',  # 小王/黑心配
        }
    
    def parse_action_string(self, action_str: str) -> Tuple[str, List[str]]:
        """
        解析动作字符串
        
        Args:
            action_str: 动作字符串，格式如 "['Discard', 'Discard', ['C4', 'DA']]"
        
        Returns:
            (action_type, cards_list)
        """
        try:
            import ast
            parsed = ast.literal_eval(action_str)
            if len(parsed) < 3:
                return 'PASS', []
            
            action_type = parsed[0]
            cards = parsed[2] if isinstance(parsed[2], list) else []
            
            if action_type == 'PASS' or not cards:
                return 'PASS', []
            
            return 'Discard', cards
        except Exception as e:
            # 如果解析失败，尝试简单匹配
            if 'PASS' in action_str.upper():
                return 'PASS', []
            return 'UNKNOWN', []
    
    def extract_rank_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名中提取级牌等级
        
        1312文件名格式：replay_player0_szqjl_2023-12-26_13_08_42_.json
        如果文件名中包含级牌信息，提取它
        
        Returns:
            级牌等级（如"2", "4", "A"），如果无法提取则返回None
        """
        # 尝试从文件名中提取级牌信息
        # 这里可以根据实际文件名格式调整
        match = re.search(r'rank[_-]?([2-9AJQK])', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None
    
    def extract_result_from_rep_file(self, rep_file_path: str, player_id: int) -> Optional[Dict]:
        """
        从对应的.rep文件中提取比赛结果
        
        Args:
            rep_file_path: .rep文件路径
            player_id: 玩家ID（seat）
        
        Returns:
            包含比赛结果的字典，格式：
            {
                'result': 'win' or 'loss',
                'rank': 1-4,  # 排名（1=头游，2=二游，3=三游，4=四游）
                'ranks': {1: seat1, 2: seat2, ...},  # 所有玩家的排名
                'game_end_result': 'WON' or 'LOST'
            }
        """
        if not os.path.exists(rep_file_path):
            return None
        
        try:
            tree = ET.parse(rep_file_path)
            root = tree.getroot()
            
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
            
            # 提取GameEnd动作
            game_end_result = None
            record_player_id = root.get("playerid")
            record_seat = None
            
            # 找到记录者的seat
            players_elem = root.find("players")
            if players_elem:
                for player in players_elem.findall("player"):
                    if player.get("id") == record_player_id:
                        record_seat = int(player.get("seat"))
                        break
            
            if actions_elem:
                for action in actions_elem.findall("action"):
                    if action.get("name") == "GameEnd":
                        game_end_result = action.get("data", "")
                        break
            
            # 确定当前玩家的排名和结果
            player_rank = None
            for rank, seat in ranks.items():
                if seat == player_id:
                    player_rank = rank
                    break
            
            # 如果玩家没有明确的Rank记录，但游戏已结束，推断排名
            if player_rank is None and game_end_result:
                # 如果头游和二游已确定，且玩家不是其中之一，则推断为三游或四游
                if len(ranks) >= 2:  # 至少有头游和二游
                    if player_id not in ranks.values():
                        # 推断：如果游戏结束且玩家不是头游或二游，可能是三游或四游
                        # 根据GameEnd结果推断：如果记录者输了，且不是头游二游，可能是三游或四游
                        if record_seat == player_id:
                            # 记录者输了，且不是头游二游，推断为三游或四游
                            # 需要根据其他信息推断具体是三游还是四游
                            # 暂时标记为3（三游）
                            player_rank = 3
                        else:
                            # 非记录者，且不是头游二游，推断为三游或四游
                            player_rank = 3  # 默认三游，可能需要更复杂的推断逻辑
            
            # 确定胜负（头游和二游是获胜方）
            result = None
            if player_rank is not None:
                if player_rank <= 2:  # 头游或二游
                    result = 'win'
                else:  # 三游或四游
                    result = 'loss'
            elif game_end_result and record_seat == player_id:
                # 如果无法从Rank确定，使用GameEnd结果
                result = 'win' if game_end_result == 'WON' else 'loss'
            elif game_end_result == 'LOST' and record_seat == player_id:
                # 记录者输了，且不是头游二游，推断为失败
                result = 'loss'
            
            return {
                'result': result,
                'rank': player_rank,
                'ranks': ranks,
                'game_end_result': game_end_result,
                'record_seat': record_seat
            }
            
        except Exception as e:
            print(f"⚠️ 从.rep文件提取结果失败: {e}")
            return None
    
    def find_corresponding_rep_file(self, json_file_path: str) -> Optional[str]:
        """
        查找对应的.rep文件（改进版：支持szqjl记录）
        
        Args:
            json_file_path: JSON文件路径
        
        Returns:
            .rep文件路径，如果找不到则返回None
        """
        json_filename = os.path.basename(json_file_path)
        
        # 检查是否是szqjl的记录
        is_szqjl = 'szqjl' in json_filename.lower()
        
        # 尝试从文件名提取日期时间
        # 格式1: replay_player0_szqjl_2023-12-26_13_08_42_.json
        # 格式2: replay_player3__2024-02-04_12_15_56.json
        match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})_(\d{2})', json_filename)
        if not match:
            return None
        
        date_str = match.group(1)  # 2023-12-26
        hour = match.group(2)      # 13
        minute = match.group(3)     # 08
        second = match.group(4)     # 42
        
        # 构建时间戳字符串（用于匹配）
        time_str = f"{date_str}_{hour}_{minute}_{second}"
        date_str_underscore = date_str.replace("-", "_")  # 2023_12_26
        
        # 查找可能的.rep文件目录
        possible_dirs = [
            r"C:\Program Files (x86)\gdgame\MobileGD\replay",
            os.path.join(os.path.dirname(json_file_path), "..", "replay"),
        ]
        
        for base_dir in possible_dirs:
            if not os.path.exists(base_dir):
                continue
            
            # 策略1: 如果包含szqjl，优先查找szqjl相关的.rep文件
            if is_szqjl:
                # 1.1 优先查找szqjl子目录中的.rep文件（更精确）
                # 格式: szqjl_2024-02-04_12_20_23_/_2024-02-04_12_15_56.rep
                # 子目录名包含日期，文件名为_日期时间.rep
                best_match = None
                best_match_score = 0
                
                for item in os.listdir(base_dir):
                    if item.startswith('szqjl_') and os.path.isdir(os.path.join(base_dir, item)):
                        dir_path = os.path.join(base_dir, item)
                        if os.path.exists(dir_path):
                            # 在子目录中查找.rep文件
                            try:
                                for file in os.listdir(dir_path):
                                    if file.endswith('.rep'):
                                        file_path = os.path.join(dir_path, file)
                                        # 优先精确匹配时间戳
                                        if time_str in file:
                                            return file_path  # 精确匹配，直接返回
                                        # 支持以下划线开头的文件名：_2024-02-04_12_15_56.rep
                                        if f"_{time_str}" in file:
                                            return file_path  # 精确匹配，直接返回
                                        # 匹配日期和时间（允许时间差）
                                        if date_str in file:
                                            # 尝试从文件名提取时间
                                            file_time_match = re.search(rf"{date_str}_(\d{{2}})_(\d{{2}})_(\d{{2}})", file)
                                            if file_time_match:
                                                file_hour = file_time_match.group(1)
                                                file_minute = file_time_match.group(2)
                                                file_second = file_time_match.group(3)
                                                # 计算时间差（分钟）
                                                time_diff = abs((int(file_hour) * 60 + int(file_minute)) - (int(hour) * 60 + int(minute)))
                                                # 如果时间差在10分钟内，认为是匹配的
                                                if time_diff <= 10:
                                                    if best_match is None or time_diff < best_match_score:
                                                        best_match = file_path
                                                        best_match_score = time_diff
                            except (PermissionError, OSError):
                                continue  # 跳过无法访问的目录
                
                # 如果找到最佳匹配，返回它
                if best_match:
                    return best_match
                
                # 1.2 查找直接在replay目录下的szqjl文件（作为备选）
                # 格式: szqjl_2023-12-26_13_08_42_.rep
                for file in os.listdir(base_dir):
                    if file.startswith('szqjl_') and file.endswith('.rep'):
                        # 优先精确匹配时间戳
                        if time_str in file:
                            return os.path.join(base_dir, file)
                        # 匹配日期和时间（允许时间差）
                        if date_str in file:
                            file_time_match = re.search(rf"{date_str}_(\d{{2}})_(\d{{2}})_(\d{{2}})", file)
                            if file_time_match:
                                file_hour = file_time_match.group(1)
                                file_minute = file_time_match.group(2)
                                time_diff = abs((int(file_hour) * 60 + int(file_minute)) - (int(hour) * 60 + int(minute)))
                                # 如果时间差在10分钟内，认为是匹配的
                                if time_diff <= 10:
                                    if best_match is None or time_diff < best_match_score:
                                        best_match = os.path.join(base_dir, file)
                                        best_match_score = time_diff
                
                # 返回最佳匹配
                return best_match
            else:
                # 策略2: 非szqjl记录，查找包含日期时间的目录
                for item in os.listdir(base_dir):
                    if date_str_underscore in item or date_str in item:
                        dir_path = os.path.join(base_dir, item)
                        if os.path.isdir(dir_path):
                            # 在目录中查找.rep文件
                            for file in os.listdir(dir_path):
                                if file.endswith('.rep') and (time_str in file or date_str in file):
                                    return os.path.join(dir_path, file)
        
        return None
    
    def infer_game_result(self, replay_data: Dict, json_file_path: str = "") -> Optional[str]:
        """
        推断游戏结果（改进版：优先从.rep文件提取）
        
        Args:
            replay_data: 原始replay数据
            json_file_path: JSON文件路径（用于查找对应的.rep文件）
        
        Returns:
            "win", "loss", 或 None
        """
        player_id = replay_data.get('player_id', 0)
        
        # 1. 优先尝试从.rep文件提取
        if json_file_path:
            rep_file_path = self.find_corresponding_rep_file(json_file_path)
            if rep_file_path:
                rep_result = self.extract_result_from_rep_file(rep_file_path, player_id)
                if rep_result and rep_result.get('result'):
                    return rep_result['result']
        
        # 2. 检查是否有result字段
        if 'result' in replay_data:
            result = replay_data['result']
            if isinstance(result, str):
                if 'win' in result.lower() or '胜' in result:
                    return 'win'
                elif 'loss' in result.lower() or '负' in result or '败' in result:
                    return 'loss'
            elif isinstance(result, bool):
                return 'win' if result else 'loss'
        
        # 3. 检查是否有game_info字段
        game_info = replay_data.get('game_info', {})
        if 'result' in game_info:
            result = game_info['result']
            if isinstance(result, str):
                if 'win' in result.lower() or '胜' in result:
                    return 'win'
                elif 'loss' in result.lower() or '负' in result:
                    return 'loss'
        
        return None
    
    def infer_all_players_hands(self, replay_data: Dict, fixed_hand: List[str] = None) -> Dict[int, List[str]]:
        """
        推断所有玩家的手牌
        
        从initial_hand和actions序列推断所有玩家的手牌分布
        
        Args:
            replay_data: 原始replay数据
            fixed_hand: 修复后的手牌（如果提供）
        
        Returns:
            所有玩家的手牌字典 {player_id: [cards]}
        """
        hero_id = replay_data.get('player_id', 0)
        # 使用修复后的手牌（如果提供），否则使用原始手牌
        hero_initial_hand = set(fixed_hand if fixed_hand else replay_data.get('initial_hand', []))
        
        # 初始化所有玩家的手牌
        all_hands = {}
        for pos in range(4):
            if pos == hero_id:
                all_hands[pos] = list(hero_initial_hand)
            else:
                all_hands[pos] = []  # 初始化为空，后续通过动作更新
        
        # 通过动作序列更新手牌
        hero_hand = set(hero_initial_hand)
        for action_log in replay_data.get('actions', []):
            actor_pos = action_log.get('cur_pos')
            action_str = action_log.get('cur_action', '')
            _, cards_played = self.parse_action_string(action_str)
            
            # 过滤掉级牌标记（如'D0', 'DA'等）
            cards_played = [c for c in cards_played if c not in ['D0', 'DA', 'H0', 'HA', 'C0', 'CA', 'S0', 'SA']]
            
            # 更新对应玩家的手牌
            if actor_pos == hero_id:
                # Hero的手牌：从初始手牌中移除已出的牌
                for card in cards_played:
                    if card in hero_hand:
                        hero_hand.remove(card)
                all_hands[hero_id] = list(hero_hand)
            else:
                # 其他玩家的手牌：无法准确知道，保持为空或估算
                # 这里可以根据需要实现估算逻辑
                pass
        
        return all_hands
    
    def validate_and_fix_hand(self, initial_hand: List[str], actions: List[Dict], 
                             player_id: int, cur_rank: str = '2') -> Tuple[List[str], List[str]]:
        """
        验证并修复手牌数据
        
        Args:
            initial_hand: 初始手牌列表
            actions: 动作序列
            player_id: 玩家ID
            cur_rank: 当前级牌等级
        
        Returns:
            (修复后的手牌列表, 警告信息列表)
        """
        warnings = []
        fixed_hand = list(initial_hand)
        expected_count = 27  # 掼蛋游戏每个玩家27张牌（108张/4人）
        
        # 统计从actions中打出的所有牌
        played_cards = []
        for action_log in actions:
            if action_log.get('cur_pos') == player_id:
                action_str = action_log.get('cur_action', '')
                _, cards = self.parse_action_string(action_str)
                played_cards.extend(cards)
        
        # 检查手牌数量
        hand_count = len(fixed_hand)
        if hand_count != expected_count:
            warnings.append(f"初始手牌数量: {hand_count} (期望: {expected_count})")
            
            # 尝试从actions中推断缺失的牌
            if hand_count < expected_count:
                missing_count = expected_count - hand_count
                warnings.append(f"缺少 {missing_count} 张牌")
                
                # 检查是否有重复的牌（可能是数据记录问题）
                hand_set = set(fixed_hand)
                duplicates = []
                for card in fixed_hand:
                    if fixed_hand.count(card) > 1 and card not in duplicates:
                        duplicates.append(card)
                
                if duplicates:
                    warnings.append(f"发现重复牌: {duplicates}")
                
                # 检查actions中是否有未在手牌中的牌（可能是缺失的牌）
                missing_cards = []
                for card in played_cards:
                    if card not in fixed_hand and card not in missing_cards:
                        # 排除级牌标记（如'D0'）
                        if card not in ['D0', 'DA', 'H0', 'HA', 'C0', 'CA', 'S0', 'SA']:
                            missing_cards.append(card)
                
                if missing_cards:
                    warnings.append(f"在actions中发现但不在手牌中的牌: {missing_cards[:5]}...")
                    # 可以选择添加这些牌，但需要谨慎
                    # fixed_hand.extend(missing_cards[:min(len(missing_cards), missing_count)])
            
            elif hand_count > expected_count:
                warnings.append(f"手牌数量过多: {hand_count} (期望: {expected_count})")
                # 可以选择移除多余的牌，但需要谨慎
                # fixed_hand = fixed_hand[:expected_count]
        
        return fixed_hand, warnings
    
    def convert_to_training_format(self, replay_data: Dict, filename: str = "", json_file_path: str = "") -> Dict:
        """
        将1312格式转换为训练格式
        
        Args:
            replay_data: 1312格式的replay数据
            filename: 文件名（用于提取级牌等级）
        
        Returns:
            转换后的训练格式数据
        """
        # 提取基本信息
        player_id = replay_data.get('player_id', 0)
        initial_hand = replay_data.get('initial_hand', [])
        actions = replay_data.get('actions', [])
        
        # 提取级牌等级（先提取，用于验证）
        cur_rank = None
        game_info = replay_data.get('game_info', {})
        if 'curRank' in game_info:
            cur_rank = str(game_info['curRank'])
        if not cur_rank:
            cur_rank = self.extract_rank_from_filename(filename)
        if not cur_rank:
            cur_rank = '2'  # 默认级牌为2
        
        # 验证并修复手牌数据
        fixed_hand, warnings = self.validate_and_fix_hand(initial_hand, actions, player_id, cur_rank)
        
        # 输出警告信息
        if warnings:
            warning_msg = f"文件 {filename} (玩家 {player_id}): " + "; ".join(warnings)
            print(f"⚠️ 警告: {warning_msg}")
        
        # 推断所有玩家手牌（使用修复后的手牌）
        all_players_hands = self.infer_all_players_hands(replay_data, fixed_hand)
        
        # 推断游戏结果（优先从.rep文件提取）
        game_result = self.infer_game_result(replay_data, json_file_path if json_file_path else filename)
        
        # 如果从.rep文件提取了结果，也提取排名信息
        rep_result_info = None
        if json_file_path or filename:
            rep_file_path = self.find_corresponding_rep_file(json_file_path if json_file_path else filename)
            if rep_file_path:
                rep_result_info = self.extract_result_from_rep_file(rep_file_path, player_id)
        
        # 构建转换后的数据（使用修复后的手牌）
        game_info_dict = {
            'curRank': cur_rank,
            'game_result': game_result if game_result else 'unknown',
            'data_warnings': warnings if warnings else []
        }
        
        # 如果从.rep文件提取了结果，添加排名信息
        if rep_result_info:
            game_info_dict['rank'] = rep_result_info.get('rank')  # 玩家排名（1-4）
            game_info_dict['all_ranks'] = rep_result_info.get('ranks', {})  # 所有玩家排名
            if rep_result_info.get('rank'):
                rank_names = {1: "头游", 2: "二游", 3: "三游", 4: "四游"}
                game_info_dict['rank_name'] = rank_names.get(rep_result_info['rank'], f"第{rep_result_info['rank']}名")
        
        converted_data = {
            'player_id': player_id,
            'initial_hand': fixed_hand,  # 使用修复后的手牌
            'all_players_hands': {str(k): v for k, v in all_players_hands.items()},
            'game_info': game_info_dict,
            'actions': actions
        }
        
        # 保留所有原始字段（可能包含额外信息）
        for key, value in replay_data.items():
            if key not in converted_data:
                # 保留原始数据中的额外字段（可能包含策略信息或其他重要数据）
                converted_data[key] = value
        
        # 如果有result字段，也保留
        if 'result' in replay_data:
            converted_data['result'] = replay_data['result']
        
        # 添加转换元数据
        converted_data['_conversion_meta'] = {
            'converted_at': datetime.now().isoformat(),
            'source_format': '1312_json',
            'strategy_info_source': 'inferred',  # 策略信息来源：推断
            'data_completeness': {
                'has_strategy_labels': False,  # JSON中没有策略标签
                'has_game_result': game_result is not None,
                'has_all_players_hands': any(len(v) > 0 for v in all_players_hands.values()),
                'strategy_will_be_inferred': True  # ReplayParser会推断策略
            }
        }
        
        return converted_data
    
    def convert_file(self, input_path: str, output_path: Optional[str] = None) -> Dict:
        """
        转换单个文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径（如果为None，则覆盖原文件）
        
        Returns:
            转换后的数据字典
        """
        # 读取原始数据
        with open(input_path, 'r', encoding='utf-8') as f:
            replay_data = json.load(f)
        
        # 转换数据（传入文件路径以便查找对应的.rep文件）
        filename = os.path.basename(input_path)
        converted_data = self.convert_to_training_format(replay_data, filename, input_path)
        
        # 保存转换后的数据
        if output_path is None:
            output_path = input_path  # 覆盖原文件
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, ensure_ascii=False, indent=2)
        
        return converted_data
    
    def convert_directory(self, input_dir: str, output_dir: Optional[str] = None, 
                          pattern: str = "replay_player*_szqjl_*.json") -> List[Dict]:
        """
        批量转换目录中的1312格式文件
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录（如果为None，则覆盖原文件）
            pattern: 文件匹配模式
        
        Returns:
            转换后的数据列表
        """
        import glob
        
        if output_dir is None:
            output_dir = input_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 查找匹配的文件
        file_pattern = os.path.join(input_dir, pattern)
        files = glob.glob(file_pattern)
        
        converted_files = []
        for file_path in files:
            try:
                filename = os.path.basename(file_path)
                output_path = os.path.join(output_dir, filename)
                
                converted_data = self.convert_file(file_path, output_path)
                converted_files.append(converted_data)
                
                print(f"✓ 转换完成: {filename}")
            except Exception as e:
                print(f"✗ 转换失败: {file_path}, 错误: {e}")
        
        return converted_files


def convert_1312_replay(input_path: str, output_path: Optional[str] = None) -> Dict:
    """
    便捷函数：转换1312格式的replay文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径（如果为None，则覆盖原文件）
    
    Returns:
        转换后的数据字典
    """
    converter = Replay1312Converter()
    return converter.convert_file(input_path, output_path)


def convert_1312_directory(input_dir: str, output_dir: Optional[str] = None) -> List[Dict]:
    """
    便捷函数：批量转换1312格式的replay文件目录
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录（如果为None，则覆盖原文件）
    
    Returns:
        转换后的数据列表
    """
    converter = Replay1312Converter()
    return converter.convert_directory(input_dir, output_dir)


if __name__ == "__main__":
    # 测试转换单个文件
    test_file = "game_records/replay_player0_szqjl_2023-12-26_13_08_42_.json"
    
    if os.path.exists(test_file):
        print("测试转换1312格式文件...")
        converter = Replay1312Converter()
        result = converter.convert_file(test_file, test_file.replace('.json', '_converted.json'))
        
        print(f"\n转换结果:")
        print(f"  玩家ID: {result['player_id']}")
        print(f"  初始手牌数: {len(result['initial_hand'])}")
        print(f"  动作数: {len(result['actions'])}")
        print(f"  级牌等级: {result['game_info']['curRank']}")
        print(f"  游戏结果: {result['game_info']['game_result']}")
        print(f"  所有玩家手牌: {list(result['all_players_hands'].keys())}")
    else:
        print(f"测试文件不存在: {test_file}")
        print("\n使用方法:")
        print("  python 1312_replay_converter.py")
        print("  或调用 convert_1312_replay(input_path, output_path)")

