# -*- coding: utf-8 -*-
"""
游戏记录器 - 保存每局游戏并支持回放
格式参考：2021122022131000098 [szqjl]-[新城老王].fp
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, Any, List, Any, Optional


def _format_cards(action_cards: Any) -> str:
    """
    格式化牌面显示，支持多种数据格式
    
    Args:
        action_cards: 牌面数据，可能是各种格式
        
    Returns:
        格式化后的牌面字符串
    """
    if not action_cards:
        return ""
    
    try:
        # 如果是列表
        if isinstance(action_cards, list):
            if len(action_cards) == 0:
                return ""
            
            # 如果列表元素是列表（如 [["H", "4"], ["S", "5"]]）
            if isinstance(action_cards[0], list):
                cards = []
                for c in action_cards:
                    if isinstance(c, list) and len(c) >= 2:
                        # 处理 ["H", "4"] 格式
                        suit = str(c[0]) if len(c) > 0 else ""
                        rank = str(c[1]) if len(c) > 1 else ""
                        cards.append(f"{suit}{rank}")
                    elif isinstance(c, list) and len(c) == 1:
                        # 处理只有一个元素的列表
                        cards.append(str(c[0]))
                    elif isinstance(c, str):
                        cards.append(c)
                    else:
                        cards.append(str(c))
                return ' '.join(cards)
            
            # 如果列表元素是字符串（如 ["H4", "S5"]）
            elif isinstance(action_cards[0], str):
                return ' '.join(action_cards)
            
            # 如果列表元素是其他类型（如数字、元组等）
            else:
                return ' '.join([str(c) for c in action_cards])
        
        # 如果是字符串
        elif isinstance(action_cards, str):
            # 如果字符串看起来像是列表的字符串表示（如 "['H', '4']" 或 "['H', '4', 'S', '5']"）
            if action_cards.strip().startswith('['):
                # 尝试解析字符串形式的列表
                try:
                    import ast
                    parsed = ast.literal_eval(action_cards)
                    return _format_cards(parsed)  # 递归处理
                except:
                    # 如果解析失败，尝试手动解析简单的格式
                    # 处理类似 "['H', '4', 'S', '5']" 的格式
                    if "'" in action_cards or '"' in action_cards:
                        # 提取所有引号内的内容
                        import re
                        matches = re.findall(r"['\"]([^'\"]+)['\"]", action_cards)
                        if matches:
                            # 假设是成对的 [suit, rank, suit, rank, ...]
                            cards = []
                            for i in range(0, len(matches), 2):
                                if i + 1 < len(matches):
                                    cards.append(f"{matches[i]}{matches[i+1]}")
                            if cards:
                                return ' '.join(cards)
            return action_cards
        
        # 如果是元组
        elif isinstance(action_cards, tuple):
            return ' '.join([str(c) for c in action_cards])
        
        # 其他类型，直接转换
        else:
            result = str(action_cards)
            # 如果结果看起来像是列表的字符串表示，尝试解析
            if result.strip().startswith('[') and "'" in result:
                try:
                    import ast
                    parsed = ast.literal_eval(result)
                    return _format_cards(parsed)  # 递归处理
                except:
                    pass
            return result
    
    except Exception as e:
        # 如果格式化失败，返回原始数据的字符串表示（截断过长的内容）
        result = str(action_cards)
        if len(result) > 100:
            result = result[:100] + "..."
        return f"[格式化错误: {e}] {result}"


class GameRecorder:
    """游戏记录器 - 记录完整的游戏过程"""
    
    def __init__(self, player_id: int, player_name: str = ""):
        """
        初始化游戏记录器
        
        Args:
            player_id: 玩家位置 (0-3)
            player_name: 玩家名称
        """
        self.player_id = player_id
        self.player_name = player_name or f"player_{player_id}"
        
        # 创建记录目录
        self.record_dir = Path(__file__).parent.parent.parent / "game_records"
        self.record_dir.mkdir(exist_ok=True)
        
        # 当前游戏记录
        self.current_game: Optional[Dict[str, Any]] = None
        self.game_start_time: Optional[datetime] = None
        
        # 游戏计数，用于生成唯一文件名
        self.game_counter = 0
        
        # 确保记录目录存在
        if not self.record_dir.exists():
            self.record_dir.mkdir(parents=True, exist_ok=True)
        
    def record_game_start(self, message: dict):
        """
        记录游戏开始（V7协议兼容方法）
        
        Args:
            message: 游戏开始消息，包含playerPosition、handCards等信息
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        try:
            # 从V7协议的gameStart消息中提取信息
            player_pos = message.get("playerPosition", self.player_id)
            hand_cards = message.get("handCards", [])
            
            # 提取游戏信息
            game_info = {
                "curRank": message.get("curRank", "2"),
                "selfRank": message.get("selfRank", "2"),
                "oppoRank": message.get("oppoRank", "2"),
            }
            
            # 提取所有玩家手牌（如果消息中包含）
            all_players_hands = {}
            if "allPlayersHands" in message:
                all_players_hands = message["allPlayersHands"]
            elif "all_players_hands" in message:
                all_players_hands = message["all_players_hands"]
            
            # 调用start_game方法
            self.start_game(
                hand_cards=hand_cards,
                my_pos=player_pos,
                game_info=game_info,
                all_players_hands=all_players_hands
            )
            
            logger.info(f"✓ 游戏记录已初始化: 位置={player_pos}, 手牌数={len(hand_cards)}")
            
        except Exception as e:
            logger.error(f"✗ 记录游戏开始失败: {e}", exc_info=True)
    
    def start_game(self, hand_cards: List, my_pos: int, game_info: Dict = None, all_players_hands: Dict[int, List] = None):
        """
        开始记录一局游戏
        
        Args:
            hand_cards: 初始手牌（自己的）
            my_pos: 玩家位置
            game_info: 游戏信息（等级、对手等）
            all_players_hands: 所有玩家的手牌 {pos: hand_cards}
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        # ⚠️ 重要：如果已经有游戏记录在进行，先保存它（防止多局游戏时丢失记录）
        if self.current_game:
            logger.warning(f"⚠ 新游戏开始，但当前游戏记录未结束，先保存当前游戏记录")
            # 使用临时结果保存当前游戏
            temp_result = {
                "reason": "new_game_started_before_end",
                "saved_at": datetime.now().isoformat(),
                "game_counter": self.game_counter
            }
            self.end_game(temp_result)
        
        self.game_start_time = datetime.now()
        
        # 递增游戏计数器
        self.game_counter += 1
        
        # 生成游戏ID（时间戳格式：YYYYMMDDHHMMSSffffff）
        game_id = self.game_start_time.strftime('%Y%m%d%H%M%S%f')
        
        # 构建所有玩家的手牌信息
        # ⚠️ 重要：统一使用字符串键，确保与验证逻辑一致
        all_hands = {}
        if all_players_hands:
            # 深拷贝所有玩家的手牌，确保数据独立性
            for pos, cards in all_players_hands.items():
                pos_str = str(pos)  # 统一转换为字符串
                if isinstance(cards, list):
                    all_hands[pos_str] = cards.copy()
                else:
                    all_hands[pos_str] = []
        # 确保自己的手牌被记录（如果还没有）
        my_pos_str = str(my_pos)
        if my_pos_str not in all_hands:
            all_hands[my_pos_str] = hand_cards.copy() if isinstance(hand_cards, list) else []
        
        # 验证手牌格式
        for pos, cards in all_hands.items():
            if not isinstance(cards, list):
                logger.warning(f"⚠ 玩家{pos}的手牌格式不正确: {type(cards)}，已转换为空列表")
                all_hands[pos] = []
            # 验证卡牌格式（应该是字符串列表，如["C8", "D4"]）
            valid_cards = []
            for card in cards:
                if isinstance(card, str) and len(card) >= 2:
                    valid_cards.append(card)
                else:
                    logger.warning(f"⚠ 玩家{pos}的手牌中包含无效卡牌: {card}，已忽略")
            all_hands[pos] = valid_cards
        
        self.current_game = {
            "game_id": game_id,
            "start_time": self.game_start_time.isoformat(),
            "player_id": my_pos,
            "player_name": self.player_name,
            "initial_hand": hand_cards,  # 保留原有字段以兼容
            "all_players_hands": all_hands,  # 新增：所有玩家的手牌
            "game_info": game_info or {},
            "actions": [],  # 所有玩家的出牌动作
            "my_decisions": [],  # 我方的决策记录
            "result": None,
            "game_round": self.game_counter  # 新增：游戏轮次计数
        }
        
        logger.info(f"✓ 开始记录游戏 #{self.game_counter}: game_id={game_id}, my_pos={my_pos}, hand_cards={len(hand_cards)}, all_players_hands={len(all_hands)}个玩家")
        
    def record_action(self, cur_pos: int, cur_action: List, 
                     greater_pos: int = -1, greater_action: List = None,
                     context: Dict = None):
        """
        记录一个出牌动作
        
        Args:
            cur_pos: 出牌玩家位置
            cur_action: 当前动作
            greater_pos: 最大动作玩家位置
            greater_action: 最大动作
            context: 上下文信息（剩余牌数、等级等）
        """
        if not self.current_game:
            return
        
        # 注意：rest_cards包含的是剩余牌数，不是手牌列表，不要用它更新all_players_hands
        # 只保留原始的all_players_hands，确保它只包含手牌列表，不包含剩余牌数
        pass
        
        # ⚠️ 重要：规范化cur_action格式，确保卡牌信息正确
        normalized_action = self._normalize_action(cur_action)
        if normalized_action != cur_action:
            logger = logging.getLogger(f"GameRecorder.{self.player_name}")
            logger.debug(f"规范化动作: {cur_action} -> {normalized_action}")
            cur_action = normalized_action
        
        # 验证卡牌合法性（检测服务器发牌错误）
        self._validate_action_cards(cur_pos, cur_action)
        
        action_record = {
            "timestamp": datetime.now().isoformat(),
            "cur_pos": cur_pos,
            "cur_action": cur_action,
            "greater_pos": greater_pos,
            "greater_action": greater_action or [],
            "context": context or {}
        }
        
        self.current_game["actions"].append(action_record)
    
    def _normalize_action(self, cur_action: List) -> List:
        """
        规范化动作格式，确保卡牌信息正确
        
        Args:
            cur_action: 原始动作
            
        Returns:
            规范化后的动作
        """
        if not isinstance(cur_action, list):
            return cur_action
        
        # 如果是PASS，直接返回
        if len(cur_action) > 0 and cur_action[0] == "PASS":
            return cur_action
        
        # 标准格式：[action_type, rank, cards]
        if len(cur_action) >= 3 and isinstance(cur_action[2], list):
            # 规范化卡牌列表
            normalized_cards = []
            for card in cur_action[2]:
                if isinstance(card, str) and len(card) >= 2:
                    # 确保卡牌格式正确（如"C8"而不是其他格式）
                    normalized_cards.append(card)
                elif isinstance(card, list) and len(card) >= 2:
                    # 处理["C", "8"]格式，转换为"C8"
                    suit = str(card[0])
                    rank = str(card[1])
                    normalized_cards.append(f"{suit}{rank}")
                else:
                    # 无效卡牌，记录警告但保留
                    import logging
                    logger = logging.getLogger(f"GameRecorder.{self.player_name}")
                    logger.warning(f"⚠ 发现无效卡牌格式: {card}，已忽略")
            
            # 返回规范化后的动作
            return [cur_action[0], cur_action[1], normalized_cards]
        
        return cur_action
    
    def _validate_action_cards(self, cur_pos: int, cur_action: List):
        """
        验证动作中的卡牌是否合法（检测服务器发牌错误）
        
        Args:
            cur_pos: 出牌玩家位置
            cur_action: 当前动作
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        try:
            # ⚠️ 重要：PASS不是卡牌，只是动作，不需要验证
            if isinstance(cur_action, list) and len(cur_action) > 0:
                if cur_action[0] == "PASS":
                    return  # PASS动作不需要验证卡牌
            elif isinstance(cur_action, str) and cur_action.upper() == "PASS":
                return  # PASS字符串不需要验证卡牌
            
            # 提取动作中的卡牌
            action_cards = []
            if isinstance(cur_action, list):
                if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                    action_cards = cur_action[2]
                elif all(isinstance(card, str) for card in cur_action):
                    # 检查是否是PASS格式（如["PASS", "PASS", "PASS"]）
                    if len(cur_action) >= 1 and cur_action[0] == "PASS":
                        return  # PASS格式不需要验证
                    action_cards = cur_action
            
            if not action_cards:
                return
            
            # 检查初始手牌（如果可用）
            all_hands = self.current_game.get("all_players_hands", {})
            # ⚠️ 重要：统一使用字符串键
            cur_pos_str = str(cur_pos)
            initial_hand = all_hands.get(cur_pos_str, [])
            
            if not initial_hand:
                # 如果没有初始手牌信息，无法验证
                return
            
            # ⚠️ 重要：过滤掉PASS字符串（PASS不是卡牌，只是动作）
            valid_action_cards = [card for card in action_cards 
                                 if card != "PASS" and card.upper() != "PASS" 
                                 and isinstance(card, str) and len(card) >= 2]
            
            if not valid_action_cards:
                # 如果过滤后没有有效卡牌，可能是PASS动作，不需要验证
                return
            
            # 统计卡牌出现次数
            from collections import Counter
            action_card_counts = Counter(valid_action_cards)
            initial_card_counts = Counter(initial_hand)
            
            # 检查是否有卡牌在动作中出现次数超过初始手牌
            for card, count in action_card_counts.items():
                initial_count = initial_card_counts.get(card, 0)
                if count > initial_count:
                    logger.warning(
                        f"⚠ 卡牌验证失败：位置{cur_pos}的动作中，卡牌{card}出现{count}次，"
                        f"但初始手牌中只有{initial_count}次！这可能是服务器发牌错误。"
                    )
                    print(
                        f"[GameRecorder] ⚠ 警告：位置{cur_pos}的动作中，卡牌{card}出现{count}次，"
                        f"但初始手牌中只有{initial_count}次！"
                    )
            
            # 检查特殊卡牌（大王、小王）的数量
            joker_cards = [card for card in action_cards if card.endswith('R') or card.endswith('B')]
            if len(joker_cards) > 2:
                logger.warning(
                    f"⚠ 检测到异常：位置{cur_pos}的动作中包含{len(joker_cards)}张王牌（R或B），"
                    f"这超过了正常数量（最多2张）！"
                )
                print(
                    f"[GameRecorder] ⚠ 警告：位置{cur_pos}的动作中包含{len(joker_cards)}张王牌，"
                    f"这可能是服务器发牌错误！"
                )
                
        except Exception as e:
            logger.debug(f"卡牌验证时出错（非关键）：{e}")
    
    def record_my_action(self, message: dict, selected_action: Any, decision_time: float = None):
        """
        记录我方的动作（V7协议兼容方法）
        
        Args:
            message: 游戏状态消息，包含当前状态信息
            selected_action: 选择的动作（可能是字符串如"PASS"或列表）
            decision_time: 决策耗时（秒）
        """
        if not self.current_game:
            import logging
            logger = logging.getLogger(f"GameRecorder.{self.player_name}")
            logger.warning("⚠ record_my_action() called but current_game is None")
            return
        
        try:
            # 提取当前状态信息
            cur_pos = message.get("curPlayer", self.player_id)
            hand_cards = message.get("handCards", [])
            valid_actions = message.get("actions", [])
            
            # 构建决策记录
            decision_record = {
                "timestamp": datetime.now().isoformat(),
                "cur_pos": cur_pos,
                "hand_cards_count": len(hand_cards),
                "selected_action": selected_action,
                "decision_time": decision_time,
                "valid_actions_count": len(valid_actions) if valid_actions else 0,
                "context": {
                    "curRank": message.get("curRank", "2"),
                    "selfRank": message.get("selfRank", "2"),
                    "oppoRank": message.get("oppoRank", "2"),
                }
            }
            
            self.current_game["my_decisions"].append(decision_record)
            
            # 同时记录为动作（如果动作不是PASS）
            if selected_action and selected_action != "PASS":
                # 尝试将动作转换为列表格式
                if isinstance(selected_action, str):
                    # 如果是字符串，可能需要解析（这里简化处理）
                    cur_action = [selected_action]
                elif isinstance(selected_action, list):
                    cur_action = selected_action
                else:
                    cur_action = [str(selected_action)]
                
                # 记录动作
                self.record_action(
                    cur_pos=cur_pos,
                    cur_action=cur_action,
                    greater_pos=-1,
                    greater_action=None,
                    context=decision_record["context"]
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(f"GameRecorder.{self.player_name}")
            logger.error(f"✗ 记录我方动作失败: {e}", exc_info=True)
    
    def record_decision(self, action_index: int, action: List, 
                       score: float = None, layer: str = None,
                       candidates: List = None, context: Dict = None):
        """
        记录我方的决策
        
        Args:
            action_index: 选择的动作索引
            action: 选择的动作
            score: 动作评分
            layer: 使用的决策层
            candidates: 候选动作列表
            context: 决策上下文
        """
        if not self.current_game:
            return
        
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "action_index": action_index,
            "action": action,
            "score": score,
            "layer": layer,
            "candidates_count": len(candidates) if candidates else 0,
            "context": context or {}
        }
        
        self.current_game["my_decisions"].append(decision_record)
    
    def end_game(self, result: Dict):
        """
        结束游戏并保存记录
        
        Args:
            result: 游戏结果（victoryNum, draws等）
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        if not self.current_game:
            logger.warning(f"⚠ end_game() called but current_game is None! Player: {self.player_name}, Result: {result}")
            logger.warning("可能的原因：start_game()没有被调用，或者current_game被意外重置")
            return None
        
        try:
            end_time = datetime.now()
            self.current_game["end_time"] = end_time.isoformat()
            self.current_game["duration"] = (end_time - self.game_start_time).total_seconds()
            self.current_game["result"] = result
            
            # 生成文件名
            # 格式：YYYYMMDDHHMMSSffffff [player_name]-[opponent_name].json
            filename = self._generate_filename(result)
            filepath = self.record_dir / filename
            
            # 确保目录存在
            self.record_dir.mkdir(exist_ok=True)
            
            # 保存为JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_game, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ 游戏记录已保存: {filepath}")
            print(f"游戏记录已保存: {filepath}")
            
            # 重置
            self.current_game = None
            self.game_start_time = None
            
            return filepath
            
        except Exception as e:
            logger.error(f"✗ 保存游戏记录失败: {e}", exc_info=True)
            print(f"✗ 保存游戏记录失败: {e}")
            return None
            return None
    
    def _generate_filename(self, result: Dict) -> str:
        """
        生成文件名
        格式：YYYYMMDDHHMMSSffffff [player_name]-[opponent_name]-[game_round]-[start_level].json
        参考格式：2021122022131000098 [szqjl]-[新城老王]-[1]-[2].json
        """
        game_id = self.current_game["game_id"]
        game_round = self.current_game["game_round"]
        
        # 从结果中推断对手信息
        victory_num = result.get("victoryNum", [0, 0, 0, 0])
        
        # 判断对手位置（队友是(player_id+2)%4）
        teammate_pos = (int(self.player_id) + 2) % 4
        opponent_positions = [i for i in range(4) if i != int(self.player_id) and i != teammate_pos]
        
        # 根据胜利次数判断对手名称
        if len(opponent_positions) >= 2:
            oppo1_wins = victory_num[opponent_positions[0]]
            oppo2_wins = victory_num[opponent_positions[1]]
            if oppo1_wins > oppo2_wins:
                opponent_name = f"opponent_{opponent_positions[0]}"
            elif oppo2_wins > oppo1_wins:
                opponent_name = f"opponent_{opponent_positions[1]}"
            else:
                opponent_name = f"opponent_{opponent_positions[0]}_{opponent_positions[1]}"
        else:
            opponent_name = "opponent"
        
        # 获取当前游戏的等级信息（从game_info或result中获取）
        game_info = self.current_game.get("game_info", {})
        current_level = game_info.get("curRank", "unknown")
        
        # 从actions中获取游戏的起始等级（如果game_info中没有）
        if current_level == "unknown" and self.current_game.get("actions"):
            for action in self.current_game["actions"]:
                context = action.get("context", {})
                if "curRank" in context:
                    current_level = context["curRank"]
                    break
        
        # 生成唯一的文件名，包含游戏轮次和起始等级信息，避免覆盖
        # 格式：YYYYMMDDHHMMSSffffff [player_name]-[opponent_name]-[game_round]-[start_level].json
        filename = f"{game_id} [{self.player_name}]-[{opponent_name}]-[{game_round}]-[{current_level}].json"
        return filename
    
    @staticmethod
    def load_game(filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        加载游戏记录文件，并自动合并同一局游戏的其他客户端记录
        支持 JSON 和 Pickle (.data) 格式
        
        Args:
            filepath: 游戏记录文件路径
            
        Returns:
            游戏数据字典（已合并所有玩家的手牌）
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"游戏记录文件不存在: {filepath}")
        
        # 根据文件扩展名选择加载方式
        if filepath.suffix.lower() == '.data':
            # Pickle 格式
            game_data = GameRecorder._load_pickle_game(filepath)
        else:
            # JSON 格式（默认）
            with open(filepath, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
        
        # 尝试合并同一局游戏的其他客户端记录
        game_data = GameRecorder._merge_same_game_records(game_data, filepath)
        
        return game_data
    
    @staticmethod
    def _load_pickle_game(filepath: Path) -> Dict[str, Any]:
        """
        加载 Pickle 格式的游戏记录文件（.data 格式）
        将 Pickle 数据转换为与 JSON 格式兼容的字典结构
        
        Args:
            filepath: .data 文件路径
            
        Returns:
            转换后的游戏数据字典
        """
        import pickle
        from datetime import datetime
        
        game_data = {
            "game_id": filepath.stem,  # 使用文件名作为游戏ID
            "start_time": datetime.now().isoformat(),  # 如果没有时间信息，使用当前时间
            "player_id": 0,
            "player_name": "unknown",
            "initial_hand": [],
            "all_players_hands": {},
            "game_info": {},
            "actions": [],
            "my_decisions": [],
            "result": None,
            "game_round": 0
        }
        
        actions = []
        all_pickle_data = []
        
        try:
            # 读取 Pickle 文件中的所有数据（可能包含多个数据块）
            with open(filepath, 'rb') as f:
                while True:
                    try:
                        data = pickle.load(f)
                        all_pickle_data.append(data)
                    except EOFError:
                        break
                    except Exception as e:
                        # 如果某个数据块解析失败，记录但继续处理
                        continue
            
            # 如果只有一个数据块，可能是完整的游戏数据
            if len(all_pickle_data) == 1:
                data = all_pickle_data[0]
                # 尝试直接解析为游戏数据字典
                if isinstance(data, dict):
                    # 如果数据已经是字典格式，尝试直接使用
                    if "actions" in data or "cur_action" in data:
                        game_data.update(data)
                        if "actions" in data:
                            actions = data["actions"]
                    else:
                        # 可能是单个动作
                        action = GameRecorder._convert_pickle_data_to_action(data)
                        if action:
                            actions.append(action)
                else:
                    # 尝试转换为动作
                    action = GameRecorder._convert_pickle_data_to_action(data)
                    if action:
                        actions.append(action)
            else:
                # 多个数据块，每个可能是一个动作
                for data in all_pickle_data:
                    action = GameRecorder._convert_pickle_data_to_action(data)
                    if action:
                        actions.append(action)
            
            # 如果从字典中获取了actions，使用它；否则使用转换后的actions
            if not game_data.get("actions") and actions:
                game_data["actions"] = actions
            
            # 确保actions是列表
            if not isinstance(game_data.get("actions"), list):
                game_data["actions"] = actions if actions else []
            
            game_data["total_steps"] = len(game_data["actions"])
            
            # 尝试从动作中提取初始手牌信息
            # Pickle 格式可能不包含初始手牌，需要从动作中推断
            if game_data["actions"]:
                GameRecorder._infer_initial_hands_from_pickle(game_data, game_data["actions"])
            
        except Exception as e:
            raise ValueError(f"无法解析 Pickle 文件 {filepath}: {e}")
        
        return game_data
    
    @staticmethod
    def _convert_pickle_data_to_action(data: Any) -> Optional[Dict[str, Any]]:
        """
        将 Pickle 数据转换为标准动作格式
        
        Args:
            data: Pickle 加载的数据
            
        Returns:
            标准化的动作字典，如果无法转换则返回 None
        """
        from datetime import datetime
        
        # Pickle 数据可能是各种格式，需要灵活处理
        action = {
            "timestamp": datetime.now().isoformat(),
            "cur_pos": -1,
            "cur_action": [],
            "greater_pos": -1,
            "greater_action": [],
            "context": {}
        }
        
        # 尝试从数据中提取信息
        if isinstance(data, dict):
            # 如果数据已经是字典格式，直接使用
            # 检查是否包含标准字段
            if "cur_pos" in data or "cur_action" in data:
                action.update(data)
            elif "action" in data:
                # 可能是简化的格式
                action["cur_action"] = data.get("action", [])
                action["cur_pos"] = data.get("pos", data.get("player_id", -1))
        elif isinstance(data, (list, tuple)):
            # 如果数据是列表或元组，尝试解析为动作
            if len(data) >= 2:
                # 格式可能是 [pos, action] 或 [action_type, rank, cards]
                if isinstance(data[0], int):
                    # [pos, action] 格式
                    action["cur_pos"] = data[0]
                    action["cur_action"] = data[1] if isinstance(data[1], (list, str)) else []
                elif isinstance(data[0], str):
                    # [action_type, rank, cards] 格式
                    action["cur_action"] = list(data)
                    # 尝试从上下文推断位置（如果无法推断，使用-1）
                    action["cur_pos"] = -1
        elif isinstance(data, str):
            # 如果是字符串，尝试解析
            try:
                import ast
                parsed = ast.literal_eval(data)
                if isinstance(parsed, dict):
                    action.update(parsed)
                elif isinstance(parsed, (list, tuple)):
                    # 递归处理
                    return GameRecorder._convert_pickle_data_to_action(parsed)
            except:
                # 如果解析失败，将字符串作为动作内容
                action["cur_action"] = data
        
        # 确保 cur_action 是列表格式
        if isinstance(action["cur_action"], str):
            try:
                import ast
                action["cur_action"] = ast.literal_eval(action["cur_action"])
            except:
                # 如果解析失败，尝试简单的字符串分割
                if action["cur_action"].startswith('[') and action["cur_action"].endswith(']'):
                    # 可能是字符串形式的列表
                    try:
                        action["cur_action"] = eval(action["cur_action"])
                    except:
                        action["cur_action"] = [action["cur_action"]]
                else:
                    action["cur_action"] = [action["cur_action"]]
        
        # 如果无法提取有效信息，返回 None
        if action["cur_pos"] == -1 and not action["cur_action"]:
            return None
        
        return action
    
    @staticmethod
    def _infer_initial_hands_from_pickle(game_data: Dict[str, Any], actions: List[Dict[str, Any]]):
        """
        从 Pickle 格式的动作中推断初始手牌
        由于 Pickle 格式可能不包含初始手牌信息，需要从动作中反向推断
        
        Args:
            game_data: 游戏数据字典（会被修改）
            actions: 动作列表
        """
        # 统计每个玩家打出的牌
        played_cards_by_player = {str(i): [] for i in range(4)}
        
        for action in actions:
            cur_pos = action.get("cur_pos", -1)
            if cur_pos < 0 or cur_pos > 3:
                continue
            
            cur_action = action.get("cur_action", [])
            if not cur_action:
                continue
            
            # 解析动作，提取打出的牌
            if isinstance(cur_action, (list, tuple)) and len(cur_action) >= 3:
                cards = cur_action[2] if isinstance(cur_action[2], list) else []
                if cards:
                    played_cards_by_player[str(cur_pos)].extend(cards)
            elif isinstance(cur_action, str):
                # 尝试从字符串中提取卡牌信息
                try:
                    import ast
                    parsed = ast.literal_eval(cur_action)
                    if isinstance(parsed, (list, tuple)) and len(parsed) >= 3:
                        cards = parsed[2] if isinstance(parsed[2], list) else []
                        if played_cards_by_player[str(cur_pos)]:
                            played_cards_by_player[str(cur_pos)].extend(cards)
                except:
                    pass
        
        # 由于无法准确推断初始手牌（不知道哪些牌没被打出），
        # 这里只设置已打出的牌作为参考
        # 实际使用时，初始手牌可能不完整
        game_data["all_players_hands"] = played_cards_by_player
    
    @staticmethod
    def _merge_same_game_records(game_data: Dict[str, Any], current_filepath: Path) -> Dict[str, Any]:
        """
        合并同一局游戏的其他客户端记录，获取所有玩家的手牌
        
        Args:
            game_data: 当前游戏记录
            current_filepath: 当前文件路径
            
        Returns:
            合并后的游戏数据
        """
        # 获取当前记录的start_time
        start_time_str = game_data.get('start_time')
        if not start_time_str:
            return game_data
        
        try:
            from datetime import datetime
            current_start_time = datetime.fromisoformat(start_time_str)
        except:
            return game_data
        
        # 在同一个目录下查找其他记录文件
        record_dir = current_filepath.parent
        all_hands = game_data.get('all_players_hands', {}).copy()
        if not all_hands:
            # 如果没有all_players_hands，从initial_hand创建
            my_pos = game_data.get('player_id')
            if my_pos is not None:
                # 规范化my_pos为整数
                if isinstance(my_pos, str):
                    try:
                        my_pos = int(my_pos)
                    except:
                        pass
                all_hands[my_pos] = game_data.get('initial_hand', [])
        
        # 查找时间接近的其他记录文件（时间差在5秒内）
        for record_file in record_dir.glob('*.json'):
            if record_file == current_filepath:
                continue
            
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    other_data = json.load(f)
                
                other_start_time_str = other_data.get('start_time')
                if not other_start_time_str:
                    continue
                
                other_start_time = datetime.fromisoformat(other_start_time_str)
                time_diff = abs((current_start_time - other_start_time).total_seconds())
                
                # 如果时间差在5秒内，认为是同一局游戏
                if time_diff < 5:
                    other_hands = other_data.get('all_players_hands', {})
                    if not other_hands:
                        # 从initial_hand创建
                        other_pos = other_data.get('player_id')
                        if other_pos is not None:
                            # 规范化other_pos为整数
                            if isinstance(other_pos, str):
                                try:
                                    other_pos = int(other_pos)
                                except:
                                    continue
                            other_hands = {other_pos: other_data.get('initial_hand', [])}
                    
                    # 合并手牌信息
                    for pos, hand_cards in other_hands.items():
                        # 规范化pos为整数
                        if isinstance(pos, str):
                            try:
                                pos = int(pos)
                            except:
                                continue
                        # 如果该位置的手牌还没有记录，或者当前记录为空，则使用其他记录
                        if pos not in all_hands or not all_hands.get(pos):
                            all_hands[pos] = hand_cards
            except Exception as e:
                # 忽略读取失败的文件
                continue
        
        # 更新game_data
        game_data['all_players_hands'] = all_hands
        return game_data
    
    @staticmethod
    def replay_game(game_data: Dict, verbose: bool = True, analyze_rules: bool = True):
        """
        回放游戏并分析规则使用情况
        
        Args:
            game_data: 游戏记录数据
            verbose: 是否详细输出
            analyze_rules: 是否分析规则使用情况
        """
        print("=" * 80)
        print(f"游戏回放: {game_data['game_id']}")
        print(f"玩家: {game_data['player_name']} (位置{game_data['player_id']})")
        print(f"开始时间: {game_data['start_time']}")
        if game_data.get('end_time'):
            print(f"结束时间: {game_data['end_time']}")
            print(f"游戏时长: {game_data.get('duration', 0):.1f}秒")
        print("=" * 80)
        
        # 显示所有玩家的初始手牌
        my_pos = game_data['player_id']
        all_hands = game_data.get('all_players_hands', {})
        
        # 如果没有all_players_hands，使用旧的initial_hand字段
        if not all_hands:
            all_hands = {my_pos: game_data.get('initial_hand', [])}
        
        # 规范化键为整数
        normalized_hands = {}
        for pos, hand_cards in all_hands.items():
            if isinstance(pos, str):
                try:
                    pos = int(pos)
                except:
                    continue
            normalized_hands[pos] = hand_cards
        all_hands = normalized_hands
        
        print(f"\n【所有玩家初始手牌】:")
        print("-" * 80)
        # 显示每个玩家的手牌
        from collections import Counter
        
        # 牌点大小顺序
        rank_order = {'3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 
                     'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12, '2': 13, 
                     'B': 14, 'R': 15}
        
        # 花色顺序（同牌点时按此顺序）
        suit_order = {'C': 1, 'D': 2, 'H': 3, 'S': 4, 'B': 5, 'R': 6}
        
        suits = {'H': '红桃', 'S': '黑桃', 'C': '梅花', 'D': '方块', 'B': '小王', 'R': '大王'}
        
        # 按牌点大小排序，同牌点按花色排序
        def card_sort_key(card):
            if len(card) < 2:
                return (999, 999)
            suit = card[0]
            rank = card[1]
            rank_val = rank_order.get(rank, 999)
            suit_val = suit_order.get(suit, 999)
            return (rank_val, suit_val)
        
        def format_hand(hand_cards):
            """格式化手牌显示"""
            if not hand_cards:
                return "未知"
            
            # 处理不同格式的手牌
            normalized_cards = []
            for c in hand_cards:
                if isinstance(c, str):
                    normalized_cards.append(c)
                elif isinstance(c, list) and len(c) >= 2:
                    normalized_cards.append(f"{c[0]}{c[1]}")
                else:
                    normalized_cards.append(str(c))
            
            card_counts = Counter(normalized_cards)
            hand_display = []
            for card in sorted(card_counts.keys(), key=card_sort_key):
                count = card_counts[card]
                suit = card[0] if len(card) > 0 else ''
                rank = card[1] if len(card) > 1 else ''
                suit_name = suits.get(suit, suit)
                if count > 1:
                    hand_display.append(f"{suit_name}{rank}({count})")
                else:
                    hand_display.append(f"{suit_name}{rank}")
            return ' '.join(hand_display)
        
        teammate_pos = (my_pos + 2) % 4
        for pos in range(4):
            if pos == my_pos:
                label = "我"
            elif pos == teammate_pos:
                label = "队友"
            else:
                label = "对手"
            
            hand_cards = all_hands.get(pos, [])
            total_count = len(hand_cards) if hand_cards else 0
            hand_display = format_hand(hand_cards)
            print(f"  {pos}号位({label}): {total_count}张 - {hand_display}")
        
        # 回放出牌过程（易读格式）
        print(f"\n【出牌过程】({len(game_data['actions'])}步):")
        print("-" * 80)
        
        # my_pos 和 teammate_pos 已在上面定义，这里不需要重复定义
        
        # 初始化玩家剩余牌数和牌型统计
        player_cards = {0: 27, 1: 27, 2: 27, 3: 27}
        # 使用所有玩家的手牌信息初始化剩余牌数
        for pos, hand_cards in all_hands.items():
            if hand_cards:
                player_cards[pos] = len(hand_cards)
        
        # 构建所有玩家的初始手牌集合（用于一致性检查）
        all_hands = game_data.get('all_players_hands', {})
        if not all_hands:
            # 兼容旧格式
            my_pos = game_data['player_id']
            all_hands = {my_pos: game_data.get('initial_hand', [])}
        
        # 规范化键为整数
        normalized_hands = {}
        for pos, hand_cards in all_hands.items():
            if isinstance(pos, str):
                try:
                    pos = int(pos)
                except:
                    continue
            normalized_hands[pos] = hand_cards
        
        all_players_hands_sets = {}
        for pos, hand_cards in normalized_hands.items():
            hand_set = set()
            for c in hand_cards:
                if isinstance(c, str):
                    hand_set.add(c)
                elif isinstance(c, list) and len(c) >= 2:
                    hand_set.add(f"{c[0]}{c[1]}")
            all_players_hands_sets[pos] = hand_set
        
        # 保留旧的initial_hand_set以兼容
        my_pos = game_data['player_id']
        initial_hand_set = all_players_hands_sets.get(my_pos, set())
        
        action_type_stats = {}
        consistency_warnings = []  # 记录数据不一致的警告
        
        for i, action in enumerate(game_data['actions'], 1):
            cur_pos = action['cur_pos']
            cur_action = action['cur_action']
            greater_pos = action['greater_pos']
            greater_action = action['greater_action']
            
            # 如果cur_action是字符串，尝试解析为列表
            if isinstance(cur_action, str):
                try:
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                except:
                    pass
            
            if not cur_action or (isinstance(cur_action, list) and len(cur_action) == 0) or (isinstance(cur_action, list) and cur_action[0] == "PASS"):
                continue
            
            # 格式化动作显示
            if isinstance(cur_action, list):
                action_type = cur_action[0] if len(cur_action) > 0 else "PASS"
                action_rank = cur_action[1] if len(cur_action) > 1 else ""
                action_cards = cur_action[2] if len(cur_action) > 2 else []
            else:
                action_type = str(cur_action)
                action_rank = ""
                action_cards = []
            
            # 判断玩家关系
            if cur_pos == my_pos:
                player_label = "我"
            elif cur_pos == teammate_pos:
                player_label = "队友"
            else:
                player_label = "对手"
            
            # 格式化牌面显示
            cards_str = _format_cards(action_cards)
            
            # 如果action_rank有值，也显示出来
            rank_str = f" {action_rank}" if action_rank else ""
            
            # 如果格式化结果为空或不完整，尝试显示更多信息
            if not cards_str or (action_cards and len(str(action_cards)) > 20 and len(cards_str) < 5):
                # 显示原始数据的简化版本
                raw_str = str(action_cards)
                if len(raw_str) > 100:
                    raw_str = raw_str[:100] + "..."
                cards_str = f"[数据: {raw_str}]"
            
            # 计算出的牌数并更新剩余牌数
            if action_cards:
                if isinstance(action_cards, list):
                    card_count = len(action_cards)
                elif isinstance(action_cards, str):
                    try:
                        import ast
                        parsed = ast.literal_eval(action_cards)
                        card_count = len(parsed) if isinstance(parsed, list) else 1
                    except:
                        card_count = 1
                else:
                    card_count = 1
                player_cards[cur_pos] = max(0, player_cards[cur_pos] - card_count)
            
            # 统计牌型
            if action_type != "PASS":
                action_type_stats[action_type] = action_type_stats.get(action_type, 0) + 1
            
            # 检查数据一致性（检查所有有手牌记录的玩家）
            consistency_warning = None
            player_hand_set = all_players_hands_sets.get(cur_pos, set())
            if action_cards and player_hand_set:
                # 解析出牌
                played_cards = []
                if isinstance(action_cards, list) and len(action_cards) > 2:
                    # action_cards 是 cur_action[2]，即出牌列表
                    cards_data = action_cards
                    for c in cards_data:
                        if isinstance(c, str):
                            played_cards.append(c)
                        elif isinstance(c, list) and len(c) >= 2:
                            played_cards.append(f"{c[0]}{c[1]}")
                elif isinstance(cur_action, str):
                    # cur_action 是字符串格式，需要解析
                    try:
                        import ast
                        parsed = ast.literal_eval(cur_action)
                        if isinstance(parsed, list) and len(parsed) > 2:
                            cards_data = parsed[2]
                            if isinstance(cards_data, list):
                                for c in cards_data:
                                    if isinstance(c, str):
                                        played_cards.append(c)
                                    elif isinstance(c, list) and len(c) >= 2:
                                        played_cards.append(f"{c[0]}{c[1]}")
                    except:
                        pass
                
                # 检查是否有牌不在初始手牌中
                missing_cards = [card for card in played_cards if card not in player_hand_set]
                if missing_cards:
                    consistency_warning = f"⚠ 数据不一致：{', '.join(missing_cards)} 不在{cur_pos}号位初始手牌中（可能记录不完整）"
                    consistency_warnings.append((i, consistency_warning))
            
            # 显示剩余牌数
            remaining = player_cards[cur_pos]
            warning_str = f" {consistency_warning}" if consistency_warning else ""
            print(f"  {i:3d}. [{player_label:2s}] {cur_pos}号位: {action_type}{rank_str} {cards_str} (剩余:{remaining}张){warning_str}")
            
            # 如果是我的决策，显示决策信息
            if cur_pos == my_pos and analyze_rules:
                # 查找对应的决策记录
                decision = None
                for dec in game_data.get('my_decisions', []):
                    if dec.get('action') == cur_action:
                        decision = dec
                        break
                
                if decision:
                    layer = decision.get('layer', 'Unknown')
                    score = decision.get('score')
                    if score is not None:
                        print(f"       → 决策: {layer}层, 评分={score:.1f}")
        
        # 显示数据一致性警告
        if consistency_warnings:
            print("\n" + "=" * 80)
            print("【数据一致性警告】")
            print("-" * 80)
            print(f"发现 {len(consistency_warnings)} 处数据不一致：")
            for step, warning in consistency_warnings:
                print(f"  步骤{step}: {warning}")
            print("\n提示：这可能是因为初始手牌记录不完整，或出牌记录格式不一致。")
        
        # 显示牌型统计
        if action_type_stats:
            print("\n" + "=" * 80)
            print("【牌型使用统计】")
            print("-" * 80)
            for action_type, count in sorted(action_type_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"  {action_type}: {count}次")
        
        # 显示最终剩余牌数
        print("\n" + "=" * 80)
        print("【最终剩余牌数】")
        print("-" * 80)
        for pos in range(4):
            if pos == my_pos:
                label = "我"
            elif pos == teammate_pos:
                label = "队友"
            else:
                label = "对手"
            print(f"  {pos}号位({label}): {player_cards[pos]}张")
        
        # 显示游戏结果
        if game_data['result']:
            print("\n" + "=" * 80)
            print("【游戏结果】")
            print("-" * 80)
            result = game_data['result']
            victory_num = result.get('victoryNum', [0, 0, 0, 0])
            print(f"胜利次数: 0号位={victory_num[0]}, 1号位={victory_num[1]}, "
                  f"2号位={victory_num[2]}, 3号位={victory_num[3]}")
            
            if result.get('layer_stats'):
                print(f"\n【决策层使用统计】")
                for layer, stats in result['layer_stats'].items():
                    success = stats.get('success', 0)
                    failure = stats.get('failure', 0)
                    total = success + failure
                    if total > 0:
                        rate = success / total * 100
                        print(f"  {layer}: {success}/{total} ({rate:.1f}%)")
        
        print("=" * 80)

    def record_game_end(self, message: dict):
        """
        记录游戏结束（V7协议兼容方法）
        
        Args:
            message: 游戏结束消息，包含result等信息
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        # 提取结果信息
        result = {}
        if isinstance(message, dict):
            # V7协议格式
            game_result = message.get("result", {})
            if game_result:
                result = {
                    "winner": game_result.get("winner", -1),
                    "scores": game_result.get("scores", []),
                    "victoryNum": game_result.get("victoryNum", [])
                }
            else:
                # 可能是V5协议格式
                result = {
                    "victoryNum": message.get("victoryNum", []),
                    "draws": message.get("draws", 0)
                }
        
        # 调用end_game保存记录
        return self.end_game(result)
    
    def save_records(self):
        """保存游戏记录（兼容V7客户端）"""
        if self.current_game:
            self.end_game({})  # 结束当前游戏并保存
        
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        logger.info(f"游戏记录已保存到 {self.record_dir}")