# -*- coding: utf-8 -*-
"""
婢х偛宸遍惃鍕鐖堕幋蹇曞Ц閹浣猴紕鎮婇崳 (Enhanced Game State Manager)
閸旂喕鍏橀敍
- 缂佸瓨濮㈢瑰本鏆ｉ惃鍕鐖堕幋蹇曞Ц閹浣蜂繆閹
- 闂嗗棙鍨氱拋鎵澧濆Ο鈥虫健
- 閹绘劒绶甸悩鑸典焦鐓＄拠銏″复閸
- 閺閹镐胶濮搁幀浣告彥閻撗冩嫲閹銏
"""

from typing import Dict, List, Optional, Tuple
from .card_tracking import CardTracker


class EnhancedGameStateManager:
    """婢х偛宸遍惃鍕鐖堕幋蹇曞Ц閹浣猴紕鎮婇崳"""
    
    def __init__(self):
        # 閸╄櫣閻樿埖浣蜂繆閹
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
        
        # 閸忛崗鍙樹繆閹
        self.public_info: List[Dict] = []
        self.play_cards: Dict[str, List[str]] = {
            '0': [],
            '1': [],
            '2': [],
            '3': [],
        }
        
        # 鐠佹壆澧濆Ο鈥虫健
        self.card_tracker = CardTracker()
        
        # 闂冪喎寮告担宥囩枂閿涘牊鐗撮幑缂佸嫰妲︾憴鍕鍨鐠侊紕鐣婚敍
        self.teammate_pos: Optional[int] = None
        self.opponent_positions: List[int] = []
    
    def update_from_message(self, message: Dict):
        """
        娴犲孩绉烽幁閺囧瓨鏌婇悩鑸
        
        Args:
            message: 楠炲啿褰撮崣鎴︿胶娈慗SON濞戝牊浼
        """
        # 閺囧瓨鏌婇崺铏圭涙
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
        
        # 婵″倹鐏夐弰鐥璷tify濞戝牊浼呴敍灞炬纯閺傛媽鎵澧濇穱鈩冧紖
        if message.get("type") == "notify" and message.get("stage") == "play":
            if self.cur_pos is not None and self.cur_action is not None:
                self.card_tracker.update_from_play(
                    self.cur_pos, self.cur_action, self.my_pos
                )
        
        # 婵″倹鐏夐弰鐥歱isodeOver閿涘矂鍣哥純鐠佹壆澧
        if message.get("stage") == "episodeOver":
            self.card_tracker.reset_episode()
    
    def _update_team_info(self):
        """閺囧瓨鏌婇梼鐔峰几閸滃苯瑙勫滄穱鈩冧紖"""
        if self.my_pos is not None:
            # 闂冪喎寮告担宥囩枂閿(myPos + 2) % 4
            self.teammate_pos = (self.my_pos + 2) % 4
            
            # 鐎佃勫滄担宥囩枂閿涙艾褰熸径鏍﹁⒈娑撴担宥囩枂
            self.opponent_positions = [
                (self.my_pos + 1) % 4,
                (self.my_pos + 3) % 4
            ]
    
    def _update_play_cards(self):
        """閺囧瓨鏌婇悳鈺佽泛缍嬮崜宥嗗ⅵ閸戣櫣娈戦悧"""
        for i, info in enumerate(self.public_info):
            pos = str(i)
            if info.get("playArea") is None:
                self.play_cards[pos] = []
            else:
                play_area = info["playArea"]
                if isinstance(play_area, list) and len(play_area) >= 3:
                    # 瀹夊叏璁块棶绗笁涓厓绱狅紙鍗＄墝鍒楄〃锛
                    cards = play_area[2]
                    self.play_cards[pos] = cards if isinstance(cards, list) else []
                else:
                    self.play_cards[pos] = []
    
    def is_passive_play(self) -> bool:
        """
        閸掋倖鏌囬弰閸氾附妲哥悮閸斻劌鍤閻楀矉绱欓棁鐟曚礁甯囬崚璁圭礆
        
        Returns:
            True: 鐞氶崝銊ュ毉閻楀矉绱滷alse: 娑撹插З閸戣櫣澧
        """
        return (
            self.stage == "play" and
            self.greater_pos is not None and
            self.greater_pos != self.my_pos and
            self.cur_pos != -1
        )
    
    def is_active_play(self) -> bool:
        """
        閸掋倖鏌囬弰閸氾附妲告稉璇插З閸戣櫣澧濋敍鍫㈠芳閸忓牆鍤閻楀本鍨ㄩ幒銉╁函绱
        
        Returns:
            True: 娑撹插З閸戣櫣澧濋敍瀛巃lse: 鐞氶崝銊ュ毉閻
        """
        return (
            self.stage == "play" and
            (self.greater_pos == -1 or self.cur_pos == -1)
        )
    
    def is_teammate_action(self) -> bool:
        """
        閸掋倖鏌囪ぐ鎾冲犻張婢堆冨З娴ｆ粍妲搁崥锔芥Ц闂冪喎寮搁崙铏规畱
        
        Returns:
            True: 閺勯梼鐔峰几閸戣櫣娈戦敍瀛巃lse: 娑撳秵妲
        """
        return (
            self.greater_pos is not None and
            self.greater_pos == self.teammate_pos
        )
    
    def get_player_remain_cards(self, pos: int) -> int:
        """閼惧嘲褰囬悳鈺佽泛澧挎担娆戝濋弫"""
        return self.card_tracker.get_player_remain(pos)
    
    def get_teammate_remain_cards(self) -> int:
        """閼惧嘲褰囬梼鐔峰几閸撯晙缍戦悧灞炬殶"""
        if self.teammate_pos is not None:
            return self.card_tracker.get_player_remain(self.teammate_pos)
        return 27
    
    def get_opponent_remain_cards(self) -> List[int]:
        """閼惧嘲褰囩佃勫滈崜鈺缍戦悧灞炬殶閸掓勩"""
        return [
            self.card_tracker.get_player_remain(pos)
            for pos in self.opponent_positions
        ]
    
    def get_pass_count(self) -> Tuple[int, int]:
        """閼惧嘲褰嘝ASS濞嗏剝鏆"""
        return self.card_tracker.get_pass_count()
    
    def get_remaining_cards(self) -> Dict:
        """閼惧嘲褰囬崜鈺缍戦悧灞界氨娣団剝浼"""
        return self.card_tracker.get_remaining_cards(self.cur_rank)
    
    def calculate_rest_cards(self) -> List[List[str]]:
        """鐠侊紕鐣婚崜鈺缍戦悧灞界氨閿涘牊甯撻梽銈嗗滈悧灞芥倵閿"""
        return self.card_tracker.calculate_rest_cards(self.hand_cards, self.cur_rank)
    
    def get_state_summary(self) -> Dict:
        """閼惧嘲褰囬悩鑸典焦鎲崇憰"""
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

