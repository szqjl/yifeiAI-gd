# -*- coding: utf-8 -*-
"""
历史信息追踪器 - 维护每个玩家的出牌历史和剩余牌库分布
根本原因分析显示：M1缺乏对对手和队友的历史信息，无法做对手建模
本模块解决这一根本缺陷
"""

from typing import Dict, List, Optional, Set
from collections import defaultdict


class HistoryTracker:
    """
    维护完整的游戏历史信息，支持对手建模和队友分析

    数据结构：
    - history: 记录每个玩家出过的牌
    - remain_cards: 按花色点数统计剩余牌库
    """

    def __init__(self):
        """初始化跟踪器，假设每人初始27张牌"""
        self.CARDS_PER_PLAYER = 27
        self.TOTAL_CARDS_PER_SUIT = 4  # 掼蛋每种点数4张（2种花色）

        # 初始化历史记录：每个位置记录其出过的牌
        self.history = {
            '0': {'send': [], 'remain': self.CARDS_PER_PLAYER},
            '1': {'send': [], 'remain': self.CARDS_PER_PLAYER},
            '2': {'send': [], 'remain': self.CARDS_PER_PLAYER},
            '3': {'send': [], 'remain': self.CARDS_PER_PLAYER},
        }

        # 初始化剩余牌库（掼蛋标准牌库）
        # 花色: S(黑桃), H(红心), D(方块), C(梅花)
        # 点数: 3-A, B(小王), R(大王)
        self.remain_cards = self._init_remain_cards()

    def _init_remain_cards(self) -> Dict[str, List[int]]:
        """初始化剩余牌库分布"""
        remain = {}

        # 标准牌 (3-A, 每种4张)
        for suit in ['S', 'H', 'D', 'C']:
            for rank in ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']:
                remain[f"{suit}{rank}"] = 4

        # 王牌 (各2张)
        remain['B'] = 2  # 小王
        remain['R'] = 2  # 大王

        return remain

    def record_play(self, player_pos: int, cards: List[str]) -> None:
        """
        记录一次出牌

        Args:
            player_pos: 玩家座位号 (0-3)
            cards: 出牌列表 (如 ['S3', 'S4'])
        """
        if not cards or player_pos not in [0, 1, 2, 3]:
            return

        pos_str = str(player_pos)

        # 更新出牌历史
        self.history[pos_str]['send'].extend(cards)
        self.history[pos_str]['remain'] = max(0, self.history[pos_str]['remain'] - len(cards))

        # 更新剩余牌库
        for card in cards:
            if card in self.remain_cards:
                self.remain_cards[card] = max(0, self.remain_cards[card] - 1)

    def get_player_history(self, player_pos: int) -> Dict:
        """
        获取某玩家的出牌历史

        Args:
            player_pos: 玩家座位号

        Returns:
            {'send': [出过的牌列表], 'remain': 剩余张数}
        """
        if player_pos not in [0, 1, 2, 3]:
            return {'send': [], 'remain': 0}
        return self.history[str(player_pos)]

    def get_remain_cards(self) -> Dict[str, int]:
        """
        获取剩余牌库分布

        Returns:
            每张牌还剩几张
        """
        return self.remain_cards.copy()

    def get_remain_count_for_player(self, player_pos: int) -> int:
        """
        获取某玩家的剩余牌数

        Args:
            player_pos: 玩家座位号

        Returns:
            剩余张数
        """
        if player_pos not in [0, 1, 2, 3]:
            return 0
        return self.history[str(player_pos)]['remain']

    def infer_player_hand_possibility(self, player_pos: int, known_cards: Set[str] = None) -> Dict[str, int]:
        """
        推测某玩家手中可能的牌（已出过的牌肯定没有）

        Args:
            player_pos: 玩家座位号
            known_cards: 已经确认的该玩家手牌 (可选)

        Returns:
            该玩家可能拥有的牌及其可能性
        """
        sent_cards = set(self.history[str(player_pos)]['send'])

        # 统计该玩家已出过的每种牌
        sent_count = {}
        for card in self.history[str(player_pos)]['send']:
            sent_count[card] = sent_count.get(card, 0) + 1

        possibility = {}
        for card, total in self.remain_cards.items():
            if card not in sent_cards or sent_count.get(card, 0) < total:
                # 这张牌总共有total张，玩家出过sent_count[card]张
                # 所以玩家可能还有 total - sent_count[card] 张
                max_possible = total - sent_count.get(card, 0)
                if max_possible > 0:
                    possibility[card] = max_possible

        return possibility

    def get_team_coordination_info(self, my_pos: int) -> Dict:
        """
        获取队伙配合信息

        Args:
            my_pos: 我的座位号

        Returns:
            队伙相关信息，便于做配合决策
        """
        teammate_pos = (my_pos + 2) % 4
        opponent_poses = [(my_pos + 1) % 4, (my_pos + 3) % 4]

        return {
            'teammate_sent': self.history[str(teammate_pos)]['send'],
            'teammate_remain': self.history[str(teammate_pos)]['remain'],
            'opponent_1_sent': self.history[str(opponent_poses[0])]['send'],
            'opponent_1_remain': self.history[str(opponent_poses[0])]['remain'],
            'opponent_2_sent': self.history[str(opponent_poses[1])]['send'],
            'opponent_2_remain': self.history[str(opponent_poses[1])]['remain'],
        }

    def get_dominant_ranks(self, player_pos: int) -> List[str]:
        """
        推测某玩家擅长的牌型（出过该牌多次或从未出过）

        Args:
            player_pos: 玩家座位号

        Returns:
            [可能拥有的高牌列表]
        """
        sent_count = defaultdict(int)
        for card in self.history[str(player_pos)]['send']:
            # 提取点数
            rank = card[1:] if len(card) > 1 else card
            sent_count[rank] += 1

        # 未出过的高牌最可能在手中
        dominant_ranks = []
        high_ranks = ['A', 'K', 'Q', 'J', 'T', '9']
        for rank in high_ranks:
            if sent_count[rank] == 0:
                # 这个点数从未出过，很可能手中还有
                dominant_ranks.append(rank)

        return dominant_ranks

    def reset(self) -> None:
        """重置跟踪器（副级或局级切换时）"""
        self.history = {
            '0': {'send': [], 'remain': self.CARDS_PER_PLAYER},
            '1': {'send': [], 'remain': self.CARDS_PER_PLAYER},
            '2': {'send': [], 'remain': self.CARDS_PER_PLAYER},
            '3': {'send': [], 'remain': self.CARDS_PER_PLAYER},
        }
        self.remain_cards = self._init_remain_cards()

    def debug_info(self) -> str:
        """返回调试信息"""
        info = "【历史追踪器状态】\n"
        for pos in range(4):
            h = self.history[str(pos)]
            info += f"  P{pos}: 出过 {len(h['send'])} 张, 剩余 {h['remain']} 张, 出牌: {h['send'][-5:]}\n"
        return info
