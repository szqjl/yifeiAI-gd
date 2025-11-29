# -*- coding: utf-8 -*-
"""
YFAdapter V4 - Enhanced Data Conversion for Hybrid Decision Engine
增强版YF适配器 - 用于V4混合决策引擎

核心功能：
1. 数据格式转换（字符串 -> 列表）
2. 幂等性转换（避免重复转换）
3. 玩家位置映射
4. 完整的错误处理
"""

import logging
import sys
import os
from typing import Union, List, Dict, Optional
import copy

# 添加lalala目录到路径（使用原版lalala的底层模块）
LALALA_PATH = r"D:\NYGD\lalala"
if LALALA_PATH not in sys.path:
    sys.path.insert(0, LALALA_PATH)

# 导入lalala核心模块（底层实现）
try:
    from state import State
    from action import Action
except ImportError as e:
    print(f"✗ 导入底层模块失败: {e}")
    print(f"请确保 {LALALA_PATH} 存在且包含state.py和action.py")
    # 在V4中，我们不立即退出，而是抛出异常让上层处理
    raise ImportError(f"Failed to import base modules from {LALALA_PATH}: {e}")


class YFAdapter:
    """
    Adapter for YF strategy with robust data conversion.
    
    This adapter handles all data format conversions between the game server
    format and YF's expected format, with comprehensive error handling.
    """
    
    def __init__(self, player_id: int):
        """
        Initialize YFAdapter.
        
        Args:
            player_id: Player position (0-3)
        """
        self.player_id = player_id
        self.yf_state = None
        self.yf_action = None
        self.logger = logging.getLogger(f"YFAdapter-P{player_id}")
        
        # 初始化YF的State和Action
        self._initialize_yf_state()
        
        self.logger.info(f"YFAdapter initialized for player {player_id}")
    
    def decide(self, message: dict) -> List[tuple]:
        """
        Generate candidate actions using YF strategy.
        
        Task 2.1: 修改为返回候选动作列表而非单一动作
        
        Args:
            message: Game state message from server
            
        Returns:
            List of (action_idx, score) tuples, sorted by score descending
            Returns empty list if YF fails or should trigger Layer 2/3
            
        Raises:
            ValueError: If data conversion fails
            RuntimeError: If YF decision fails
        """
        candidates = []
        
        try:
            # 深拷贝消息，避免修改原始数据
            message_copy = copy.deepcopy(message)
            
            # 转换消息格式
            converted_message = self._convert_message(message_copy)
            
            # 使用YF的状态解析
            self.yf_state.parse(converted_message)
            
            # 使用YF的决策逻辑
            action_index = self._make_yf_decision(converted_message)
            
            # Task 2.1: 移除返回None的逻辑，改为返回空列表
            # 如果action_index为None，表示应该触发Layer 2/3，返回空列表
            if action_index is None:
                self.logger.debug("YF returned None, returning empty candidates list")
                return []  # 返回空列表，触发Layer 2/3
            
            # 验证动作有效性
            if not self._is_valid_action(action_index, message):
                self.logger.warning(f"YF returned invalid action: {action_index}, returning empty list")
                return []
            
            # Task 2.1: 返回候选列表格式
            # YF的主要选择，给予最高基础评分（100.0）
            candidates.append((action_index, 100.0))
            
            self.logger.debug(f"YF generated 1 candidate: action={action_index}, score=100.0")
            return candidates
            
        except Exception as e:
            self.logger.error(f"YF decision failed: {e}", exc_info=True)
            # Task 2.1: 失败时返回空列表而非抛出异常
            return []
    
    def _convert_message(self, message: dict) -> dict:
        """
        Convert message format for YF compatibility.
        
        Critical conversions:
        - Card format: string -> list (e.g., "H4" -> ["H", "4"])
        - Player positions: system -> YF mapping
        - publicInfo.playArea: handle all card types
        
        Args:
            message: Original message from server
            
        Returns:
            Converted message compatible with YF
            
        Raises:
            ValueError: If conversion fails
        """
        try:
            # 转换手牌格式
            if "handCards" in message:
                message["handCards"] = self._convert_cards(message["handCards"])
                self.logger.debug(f"Converted handCards: {len(message['handCards'])} cards")
            
            # 转换当前动作
            if "curAction" in message and isinstance(message["curAction"], list):
                message["curAction"] = self._convert_action(message["curAction"])
            
            # 转换最大动作
            if "greaterAction" in message and isinstance(message["greaterAction"], list):
                message["greaterAction"] = self._convert_action(message["greaterAction"])
            
            # 转换动作列表
            if "actionList" in message:
                message["actionList"] = self._convert_action_list(message["actionList"])
            
            # 转换publicInfo中的playArea
            if "publicInfo" in message:
                message["publicInfo"] = self._convert_public_info(message["publicInfo"])
            
            # 转换玩家位置映射
            message = self._convert_player_positions(message)
            
            return message
            
        except Exception as e:
            self.logger.error(f"Message conversion failed: {e}", exc_info=True)
            raise ValueError(f"Failed to convert message format: {e}")
    
    def _convert_cards(self, cards: Union[str, List]) -> List:
        """
        Convert card format from string to list.
        
        Supports:
        - String format: "H4,S5,D6" -> [["H", "4"], ["S", "5"], ["D", "6"]]
        - List of strings: ["H4", "S5"] -> [["H", "4"], ["S", "5"]]
        - Already converted: [["H", "4"]] -> [["H", "4"]] (idempotent)
        
        Args:
            cards: Cards in various formats
            
        Returns:
            List of cards in YF format [["suit", "rank"], ...]
            
        Raises:
            ValueError: If card format is invalid
        """
        # 空值处理
        if cards is None or cards == "":
            return []
        
        # 如果是字符串，先分割
        if isinstance(cards, str):
            if cards.strip() == "":
                return []
            # 分割逗号分隔的字符串
            cards = [c.strip() for c in cards.split(',') if c.strip()]
        
        # 如果不是列表，抛出错误
        if not isinstance(cards, list):
            raise ValueError(f"Invalid card format: expected str or list, got {type(cards)}")
        
        # 转换每张牌
        result = []
        for card in cards:
            converted_card = self._convert_single_card(card)
            # 过滤掉None值（空字符串）
            if converted_card is not None:
                result.append(converted_card)
        
        return result
    
    def _convert_single_card(self, card: Union[str, List]) -> List:
        """
        Convert a single card to YF format.
        
        Args:
            card: Single card (string or list)
            
        Returns:
            Card in format ["suit", "rank"]
            
        Raises:
            ValueError: If card format is invalid
        """
        # 如果已经是列表格式，检查并返回（幂等性）
        if isinstance(card, list):
            if len(card) == 2:
                # 确保rank是字符串，并转换10为T
                suit = str(card[0])
                rank = str(card[1]).replace('10', 'T')
                return [suit, rank]
            else:
                raise ValueError(f"Invalid card list format: {card}, expected length 2")
        
        # 如果是字符串，解析
        if isinstance(card, str):
            # 空字符串返回None，由上层过滤
            if len(card) == 0:
                return None
            
            # 大小王特殊处理: 'R' -> ['R', 'R'], 'B' -> ['B', 'B']
            if len(card) == 1:
                if card in ['R', 'B']:
                    return [card, card]
                else:
                    raise ValueError(f"Invalid single character card: {card}")
            
            # 普通牌: "H4" -> ["H", "4"], "H10" -> ["H", "T"]
            if len(card) >= 2:
                suit = card[0]
                rank = card[1:].replace('10', 'T')
                return [suit, rank]
        
        raise ValueError(f"Invalid card type: {type(card)}, value: {card}")
    
    def _convert_action(self, action: List) -> List:
        """
        Convert action format (e.g., curAction, greaterAction).
        
        Action format: [type, rank, cards]
        - type: "Single", "Pair", "PASS", etc.
        - rank: card rank
        - cards: list of cards or "PASS"
        
        Args:
            action: Action in original format
            
        Returns:
            Action with converted card format
        """
        if not isinstance(action, list) or len(action) < 3:
            return action
        
        action_type = action[0]
        rank = action[1]
        cards = action[2]
        
        # 如果是PASS，不转换
        if cards == "PASS" or action_type == "PASS":
            return [action_type, rank, "PASS"]
        
        # 转换牌列表
        if isinstance(cards, (str, list)):
            converted_cards = self._convert_cards(cards)
            return [action_type, rank, converted_cards]
        
        return action
    
    def _convert_action_list(self, action_list: List) -> List:
        """
        Convert all actions in actionList.
        
        Args:
            action_list: List of actions
            
        Returns:
            List of converted actions
        """
        result = []
        for action in action_list:
            if isinstance(action, list):
                converted_action = self._convert_action(action)
                result.append(converted_action)
            else:
                result.append(action)
        
        return result

    
    def _convert_public_info(self, public_info: List) -> List:
        """
        Convert publicInfo including playArea for all players.
        
        publicInfo format: [
            {'rest': 27, 'playArea': [type, rank, cards]},
            ...
        ]
        
        Args:
            public_info: List of player public information
            
        Returns:
            Converted public info with proper card formats
        """
        result = []
        
        for i, player_info in enumerate(public_info):
            if not isinstance(player_info, dict):
                result.append(player_info)
                continue
            
            converted_info = player_info.copy()
            
            # 转换playArea
            if "playArea" in converted_info:
                play_area = converted_info["playArea"]
                
                # None或空值处理
                if play_area is None:
                    converted_info["playArea"] = None
                # 如果是字典格式（某些服务器版本）
                elif isinstance(play_area, dict):
                    converted_info["playArea"] = self._convert_play_area_dict(play_area)
                # 如果是列表格式
                elif isinstance(play_area, list):
                    converted_info["playArea"] = self._convert_action(play_area)
            
            result.append(converted_info)
        
        return result
    
    def _convert_play_area_dict(self, play_area: dict) -> List:
        """
        Convert playArea from dict format to list format.
        
        Dict format: {"type": "Single", "rank": "4", "actions": ["H4"]}
        List format: ["Single", "4", [["H", "4"]]]
        
        Args:
            play_area: playArea in dict format
            
        Returns:
            playArea in list format
        """
        # 如果只有actIndex，说明还没有出牌
        if "actIndex" in play_area and "type" not in play_area:
            return ["PASS", "", "PASS"]
        
        # 提取字段
        card_type = play_area.get("type", "PASS")
        rank = play_area.get("rank", "")
        actions = play_area.get("actions", [])
        
        # 转换牌
        if actions and actions != "PASS":
            converted_actions = self._convert_cards(actions)
            return [card_type, rank, converted_actions]
        else:
            return [card_type, rank, "PASS"]
    
    def _convert_player_positions(self, message: dict) -> dict:
        """
        Convert player position mapping if needed.
        
        This ensures that teammate and opponent relationships are preserved
        correctly when converting between system and YF formats.
        
        Args:
            message: Message with player position information
            
        Returns:
            Message with converted player positions
        """
        # YF使用myPos来标识玩家位置
        # 我们的系统使用player_id (0-3)
        # 确保myPos字段存在且正确
        if "myPos" not in message:
            message["myPos"] = self.player_id
        
        # 验证队友/对手关系
        # 在掼蛋中：0和2是队友，1和3是队友
        # 这个映射在YF中也是一样的，所以不需要额外转换
        
        return message
    
    def _make_yf_decision(self, message: dict) -> Optional[int]:
        """
        Use YF's decision logic to select an action.
        
        Task 2.1: 保持返回单一动作或None，由decide()方法转换为列表格式
        
        Args:
            message: Converted message in YF format
            
        Returns:
            Action index (or None to trigger Layer 2/3)
            
        Raises:
            RuntimeError: If YF decision fails
        """
        try:
            # 提取YF需要的参数
            action_list = message.get("actionList", [])
            
            if not action_list:
                self.logger.warning("Empty actionList, returning 0 (PASS)")
                return 0
            
            # 调用YF的rule_parse方法
            # 添加详细日志用于诊断
            cur_pos = message.get("curPos", -1)
            greater_pos = message.get("greaterPos", -1)
            my_pos = self.yf_state._myPos
            cur_action = message.get("curAction", [])
            action_list_len = len(action_list)
            public_info = message.get("publicInfo", [])
            
            # 使用INFO级别确保日志可见
            self.logger.info(
                f"[YF-P{self.player_id}] Decision context: "
                f"myPos={my_pos}, curPos={cur_pos}, greaterPos={greater_pos}, "
                f"teammate={(my_pos+2)%4 if my_pos is not None else None}, "
                f"curAction={cur_action[0] if cur_action else 'None'}, "
                f"actionList_size={action_list_len}"
            )
            
            act_index = self.yf_action.rule_parse(
                message,
                self.yf_state._myPos,
                self.yf_state.remain_cards,
                self.yf_state.history,
                self.yf_state.remain_cards_classbynum,
                self.yf_state.pass_num,
                self.yf_state.my_pass_num,
                self.yf_state.tribute_result
            )
            
            self.logger.info(
                f"[YF-P{self.player_id}] Decided: action_index={act_index}, "
                f"action={action_list[act_index] if 0 <= act_index < action_list_len else 'INVALID'}"
            )
            
            # 检测过于保守的决策，触发Layer 2/3
            if act_index == 0 and len(action_list) > 1:  # 选择了PASS且有其他选择
                # 获取剩余牌数
                cards_left = {}
                for i, info in enumerate(public_info):
                    if isinstance(info, dict):
                        cards_left[i] = info.get('rest', 27)
                
                teammate_pos = (my_pos + 2) % 4
                next_pos = (my_pos + 1) % 4
                prev_pos = (my_pos - 1) % 4
                
                # 检测关键场景
                should_use_layer3 = False
                reason = ""
                
                # 场景1：对手快走完了
                opponent_min = min(
                    cards_left.get(next_pos, 27),
                    cards_left.get(prev_pos, 27)
                )
                if opponent_min <= 5:
                    should_use_layer3 = True
                    reason = f"对手快走完(剩{opponent_min}张)"
                
                # 场景2：对手连续控场
                if greater_pos not in [my_pos, teammate_pos, -1]:
                    if self.yf_state.pass_num >= 2:  # 我方连续PASS 2次
                        should_use_layer3 = True
                        reason = f"对手连续控场(我方已PASS {self.yf_state.pass_num}次)"
                
                # 场景3：队友已PASS且对手控场
                if cur_pos == teammate_pos and cur_action and cur_action[0] == "PASS":
                    if greater_pos not in [my_pos, teammate_pos, -1]:
                        should_use_layer3 = True
                        reason = "队友PASS且对手控场"
                
                if should_use_layer3:
                    self.logger.warning(
                        f"[YF-P{self.player_id}] 检测到过于保守: {reason}, "
                        f"触发Layer 2/3进行更积极的决策"
                    )
                    return None  # 返回None触发Layer 2/3
            
            return act_index
            
        except Exception as e:
            self.logger.error(f"YF rule_parse failed: {e}", exc_info=True)
            raise RuntimeError(f"YF decision failed: {e}")
    
    def _is_valid_action(self, action: int, message: dict) -> bool:
        """
        Validate that action is in the legal range.
        
        Args:
            action: Action index
            message: Original message with actionList
            
        Returns:
            True if action is valid, False otherwise
        """
        action_list = message.get("actionList", [])
        
        if not action_list:
            # 如果没有动作列表，只有0（PASS）是有效的
            return action == 0
        
        # 检查action是否在有效范围内
        is_valid = 0 <= action < len(action_list)
        
        if not is_valid:
            self.logger.error(
                f"Invalid action {action}: out of range [0, {len(action_list)})"
            )
        
        return is_valid
    
    # ========== 状态管理方法 ==========
    
    def _initialize_yf_state(self):
        """
        Initialize YF State and Action objects.
        
        This method creates new instances of State and Action for this adapter,
        ensuring proper isolation between different adapter instances.
        """
        try:
            # YF的State和Action需要传入name参数（字符串标识）
            # myPos会在parse(message)时从message中获取
            
            # 创建State实例 - 传入字符串名称作为标识
            client_name = f"yf_v4_p{self.player_id}"
            self.yf_state = State(client_name)
            
            # 创建Action实例 - 传入字符串名称作为标识
            self.yf_action = Action(client_name)
            
            # 验证状态初始化
            if not self._validate_state():
                raise RuntimeError("State validation failed after initialization")
            
            self.logger.info(
                f"YF state initialized: player_id={self.player_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize YF state: {e}", exc_info=True)
            raise RuntimeError(f"State initialization failed: {e}")
    
    def _update_yf_state(self, message: dict):
        """
        Update YF state with new message.
        
        This method calls YF's state.parse() to update internal state
        based on the game message.
        
        Args:
            message: Converted message in YF format
            
        Raises:
            RuntimeError: If state update fails
        """
        try:
            # 调用YF的parse方法更新状态
            self.yf_state.parse(message)
            
            # 验证状态更新后的完整性
            if not self._validate_state():
                self.logger.warning("State validation failed after update")
            
            self.logger.debug(
                f"State updated: stage={message.get('stage')}, "
                f"type={message.get('type')}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update YF state: {e}", exc_info=True)
            raise RuntimeError(f"State update failed: {e}")
    
    def _validate_state(self) -> bool:
        """
        Validate that YF state has all required fields.
        
        Returns:
            True if state is valid, False otherwise
        """
        try:
            # 检查State对象存在
            if self.yf_state is None:
                self.logger.error("yf_state is None")
                return False
            
            # 检查关键字段存在
            required_fields = [
                'history', 'remain_cards', 'play_cards',
                'remain_cards_classbynum', 'pass_num', 'my_pass_num'
            ]
            
            for field in required_fields:
                if not hasattr(self.yf_state, field):
                    self.logger.error(f"Missing required field: {field}")
                    return False
            
            # 检查history结构
            if not isinstance(self.yf_state.history, dict):
                self.logger.error("history is not a dict")
                return False
            
            # 检查所有玩家的history都存在
            for player_id in ['0', '1', '2', '3']:
                if player_id not in self.yf_state.history:
                    self.logger.error(f"Missing history for player {player_id}")
                    return False
            
            # 检查remain_cards结构
            if not isinstance(self.yf_state.remain_cards, dict):
                self.logger.error("remain_cards is not a dict")
                return False
            
            required_suits = ['S', 'H', 'C', 'D']
            for suit in required_suits:
                if suit not in self.yf_state.remain_cards:
                    self.logger.error(f"Missing suit in remain_cards: {suit}")
                    return False
            
            self.logger.debug("State validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"State validation error: {e}", exc_info=True)
            return False
    
    def reset(self):
        """
        Reset YF state for a new game.
        
        This method reinitializes the State and Action objects,
        clearing all game history and preparing for a new game.
        """
        try:
            self.logger.info("Resetting YF state")
            
            # 重新初始化状态
            self._initialize_yf_state()
            
            self.logger.info("YF state reset complete")
            
        except Exception as e:
            self.logger.error(f"Failed to reset state: {e}", exc_info=True)
            raise RuntimeError(f"State reset failed: {e}")


# 测试和调试函数
def test_card_conversion():
    """测试牌格式转换功能"""
    adapter = YFAdapter(0)
    
    test_cases = [
        # (输入, 期望输出, 描述)
        ("H4,S5,D6", [["H", "4"], ["S", "5"], ["D", "6"]], "逗号分隔字符串"),
        (["H4", "S5"], [["H", "4"], ["S", "5"]], "字符串列表"),
        ([["H", "4"]], [["H", "4"]], "已转换格式（幂等性）"),
        ("", [], "空字符串"),
        ([], [], "空列表"),
        ("R", [["R", "R"]], "大王"),
        ("B", [["B", "B"]], "小王"),
        ("H10", [["H", "T"]], "10转换为T"),
    ]
    
    print("=" * 60)
    print("牌格式转换测试")
    print("=" * 60)
    
    all_passed = True
    for i, (input_data, expected, description) in enumerate(test_cases, 1):
        try:
            result = adapter._convert_cards(input_data)
            passed = result == expected
            all_passed = all_passed and passed
            
            status = "✓" if passed else "✗"
            print(f"{status} 测试 {i} ({description})")
            print(f"  输入: {input_data}")
            print(f"  输出: {result}")
            if not passed:
                print(f"  期望: {expected}")
        except Exception as e:
            print(f"✗ 测试 {i} ({description}) - 异常: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过!")
    else:
        print("✗ 有测试失败")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    # 运行测试
    test_card_conversion()
