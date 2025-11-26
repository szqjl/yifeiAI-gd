# -*- coding: utf-8 -*-
"""
增强的游戏状态管理器 (Enhanced Game State Manager)
功能：
- 维护完整的游戏状态信息
- 集成记牌模块
- 提供状态查询接口
- 支持状态快照和恢复
"""

from typing import Dict, List, Optional, Tuple
from .card_tracking import CardTracker


class EnhancedGameStateManager:
    """增强的游戏状态管理器"""
    
    def __init__(self):
        # 基础状态信息
        self.my_pos: Optional[int] = None
        self.hand_cards: List[str] = []
        self.cur_pos: Optional[int] = None
        self.cur_action: Optional[List] = None
        self.greater_pos: Optional[int] = None
        self.greater_action: Optional[List] = None
        self.stage: Optional[str] = None
        self.cur_rank: str = "2"
        self.self_rank: Optional[str] = None
        self.oppo_rank: Optional[str] = None
        
        # 公共信息
        self.public_info: List[Dict] = []
        self.play_cards: Dict[str, List[str]] = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        }
        
        # 记牌模块
        self.card_tracker = CardTracker()
        
        # 队友位置（根据组队规则计算）
        self.teammate_pos: Optional[int] = None
        self.opponent_positions: List[int] = []
    
    def update_from_message(self, message: Dict):
        """
        从消息更新状态
        
        Args:
            message: 平台发送的JSON消息
        """
        # 更新基础字段
        if "myPos" in message:
            self.my_pos = message["myPos"]
            self._update_team_info()
        
        if "handCards" in message:
            self.hand_cards = message["handCards"]
        
        if "curPos" in message:
            self.cur_pos = message["curPos"]
        
        if "curAction" in message:
            self.cur_action = message["curAction"]
        
        if "greaterPos" in message:
            self.greater_pos = message["greaterPos"]
        
        if "greaterAction" in message:
            self.greater_action = message["greaterAction"]
        
        if "stage" in message:
            self.stage = message["stage"]
        
        if "curRank" in message:
            self.cur_rank = message["curRank"]
        
        if "selfRank" in message:
            self.self_rank = message["selfRank"]
        
        if "oppoRank" in message:
            self.oppo_rank = message["oppoRank"]
        
        if "publicInfo" in message:
            self.public_info = message["publicInfo"]
            self._update_play_cards()
        
        # 如果是notify消息，更新记牌信息
        if message.get("type") == "notify" and message.get("stage") == "play":
            if self.cur_pos is not None and self.cur_action is not None:
                self.card_tracker.update_from_play(
                    self.cur_pos, self.cur_action, self.my_pos
                )
        
        # 如果是episodeOver，重置记牌
        if message.get("stage") == "episodeOver":
            self.card_tracker.reset_episode()
    
    def _update_team_info(self):
        """更新队友和对手信息"""
        if self.my_pos is not None:
            # 队友位置：(myPos + 2) % 4
            self.teammate_pos = (self.my_pos + 2) % 4
            
            # 对手位置：另外两个位置
            self.opponent_positions = [
                (self.my_pos + 1) % 4,
                (self.my_pos + 3) % 4
            ]
    
    def _update_play_cards(self):
        """更新玩家当前打出的牌"""
        for i, info in enumerate(self.public_info):
            pos = str(i)
            if info.get("playArea") is None:
                self.play_cards[pos] = []
            else:
                play_area = info["playArea"]
                if isinstance(play_area, list) and len(play_area) > 2:
                    self.play_cards[pos] = play_area[2]  # 卡牌列表
                else:
                    self.play_cards[pos] = []
    
    def is_passive_play(self) -> bool:
        """
        判断是否是被动出牌（需要压制）
        
        Returns:
            True: 被动出牌，False: 主动出牌
        """
        return (
            self.stage == "play" and
            self.greater_pos is not None and
            self.greater_pos != self.my_pos and
            self.cur_pos != -1
        )
    
    def is_active_play(self) -> bool:
        """
        判断是否是主动出牌（率先出牌或接风）
        
        Returns:
            True: 主动出牌，False: 被动出牌
        """
        return (
            self.stage == "play" and
            (self.greater_pos == -1 or self.cur_pos == -1)
        )
    
    def is_teammate_action(self) -> bool:
        """
        判断当前最大动作是否是队友出的
        
        Returns:
            True: 是队友出的，False: 不是
        """
        return (
            self.greater_pos is not None and
            self.greater_pos == self.teammate_pos
        )
    
    def get_player_remain_cards(self, pos: int) -> int:
        """获取玩家剩余牌数"""
        return self.card_tracker.get_player_remain(pos)
    
    def get_teammate_remain_cards(self) -> int:
        """获取队友剩余牌数"""
        if self.teammate_pos is not None:
            return self.card_tracker.get_player_remain(self.teammate_pos)
        return 27
    
    def get_opponent_remain_cards(self) -> List[int]:
        """获取对手剩余牌数列表"""
        return [
            self.card_tracker.get_player_remain(pos)
            for pos in self.opponent_positions
        ]
    
    def get_pass_count(self) -> Tuple[int, int]:
        """获取PASS次数"""
        return self.card_tracker.get_pass_count()
    
    def get_remaining_cards(self) -> Dict:
        """获取剩余牌库信息"""
        return self.card_tracker.get_remaining_cards(self.cur_rank)
    
    def calculate_rest_cards(self) -> List[List[str]]:
        """计算剩余牌库（排除手牌后）"""
        return self.card_tracker.calculate_rest_cards(self.hand_cards, self.cur_rank)
    
    def get_state_summary(self) -> Dict:
        """获取状态摘要"""
        return {
            "my_pos": self.my_pos,
            "teammate_pos": self.teammate_pos,
            "opponent_positions": self.opponent_positions,
            "hand_cards_count": len(self.hand_cards),
            "stage": self.stage,
            "cur_rank": self.cur_rank,
            "self_rank": self.self_rank,
            "oppo_rank": self.oppo_rank,
            "is_passive": self.is_passive_play(),
            "is_active": self.is_active_play(),
            "is_teammate_action": self.is_teammate_action(),
            "teammate_remain": self.get_teammate_remain_cards(),
            "opponent_remain": self.get_opponent_remain_cards(),
            "pass_num": self.card_tracker.pass_num,
            "my_pass_num": self.card_tracker.my_pass_num,
        }

