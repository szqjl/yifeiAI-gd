# -*- coding: utf-8 -*-
"""
记牌与推理模块 (Card Tracking & Inference Module)
功能：
- 维护每个玩家的出牌历史
- 跟踪剩余牌库（按花色和点数）
- 计算剩余牌概率分布
- 推理对手可能持有的牌型
- 记录连续PASS次数
"""

import copy
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class CardTracker:
    """记牌与推理模块"""
    
    def __init__(self):
        # 玩家历史记录：每个玩家打出的牌和剩余牌数
        self.history = {
            '0': {'send': [], 'remain': 27},
            '1': {'send': [], 'remain': 27},
            '2': {'send': [], 'remain': 27},
            '3': {'send': [], 'remain': 27},
        }
        
        # 剩余牌库：按花色和点数分类
        # 索引：A=0, 2=1, 3=2, ..., K=12, B=13(小王), R=13(大王)
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # 黑桃
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # 红桃
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # 梅花（无大王）
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # 方片（无小王）
        }
        
        # 按点数分类的剩余牌（用于快速查询）
        # 索引：A=0, 2=1, ..., K=12, B=13, R=13
        self.remain_cards_classbynum = [8] * 13 + [2, 2]  # 13种点数各8张，小王2张，大王2张
        
        # 连续PASS次数
        self.pass_num = 0  # 队友和自己连续PASS次数
        self.my_pass_num = 0  # 自己连续PASS次数
        
        # 卡牌索引映射
        self.card_index = {
            "A": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6,
            "8": 7, "9": 8, "T": 9, "J": 10, "Q": 11, "K": 12,
            "R": 13, "B": 13
        }
        
        # 卡牌值映射（用于比较大小）
        self.card_value = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
            "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
            "B": 16, "R": 17
        }
    
    def update_from_play(self, cur_pos: int, cur_action: List, my_pos: int):
        """
        更新出牌信息
        
        Args:
            cur_pos: 出牌玩家位置 (0-3)
            cur_action: 出牌动作 [type, rank, cards]
            my_pos: 自己的位置
        """
        # 如果不是PASS，更新出牌历史
        if cur_action[0] != "PASS" and cur_action[2] != "PASS":
            for card in cur_action[2]:
                # 记录出牌
                self.history[str(cur_pos)]["send"].append(card)
                self.history[str(cur_pos)]["remain"] -= 1
                
                # 更新剩余牌库
                card_type = str(card[0])  # 花色
                card_rank = card[1]  # 点数
                x = self.card_index[card_rank]
                
                if self.remain_cards[card_type][x] > 0:
                    self.remain_cards[card_type][x] -= 1
                
                # 更新按点数分类的剩余牌
                if card_rank in ["B", "R"]:
                    # 小王或大王
                    if self.remain_cards_classbynum[13] > 0:
                        self.remain_cards_classbynum[13] -= 1
                else:
                    # 普通牌
                    idx = self.card_index[card_rank]
                    if self.remain_cards_classbynum[idx] > 0:
                        self.remain_cards_classbynum[idx] -= 1
        
        # 更新连续PASS次数
        teammate_pos = (my_pos + 2) % 4
        if cur_pos == teammate_pos or cur_pos == my_pos:
            if cur_action[0] == "PASS":
                self.pass_num += 1
            else:
                self.pass_num = 0
        
        if cur_pos == my_pos:
            if cur_action[0] == "PASS":
                self.my_pass_num += 1
            else:
                self.my_pass_num = 0
    
    def get_player_remain(self, pos: int) -> int:
        """获取玩家剩余牌数"""
        return self.history[str(pos)]["remain"]
    
    def get_remaining_cards(self, rank: str = None) -> Dict:
        """
        获取剩余牌库
        
        Args:
            rank: 主牌级别，如果提供，会计算主牌数量
        
        Returns:
            剩余牌库字典
        """
        if rank:
            # 计算主牌数量
            rank_card = f"H{rank}"  # 主牌通常是红桃
            rank_count = 0
            for suit in ["S", "H", "C", "D"]:
                idx = self.card_index[rank]
                rank_count += self.remain_cards[suit][idx]
            
            return {
                "remain_cards": copy.deepcopy(self.remain_cards),
                "remain_cards_classbynum": copy.deepcopy(self.remain_cards_classbynum),
                "rank_count": rank_count
            }
        else:
            return {
                "remain_cards": copy.deepcopy(self.remain_cards),
                "remain_cards_classbynum": copy.deepcopy(self.remain_cards_classbynum)
            }
    
    def calculate_rest_cards(self, handcards: List[str], rank: str) -> List[List[str]]:
        """
        计算剩余牌库（排除手牌后）
        
        Args:
            handcards: 手牌列表
            rank: 当前主牌级别
        
        Returns:
            按点数分组的剩余牌列表
        """
        card_value_v2s = {
            0: "A", 1: "2", 2: "3", 3: "4", 4: "5", 5: "6", 6: "7",
            7: "8", 8: "9", 9: "T", 10: "J", 11: "Q", 12: "K"
        }
        
        # 复制剩余牌库
        new_remaincards = {}
        for key, val in self.remain_cards.items():
            new_remaincards[key] = copy.deepcopy(val)
        
        # 减去手牌
        for card in handcards:
            card_type = str(card[0])
            x = self.card_index[card[1]]
            if new_remaincards[card_type][x] > 0:
                new_remaincards[card_type][x] -= 1
        
        # 转换为列表格式
        rest_cards = []
        for key, value in new_remaincards.items():
            for i in range(len(value)):
                if value[i] == 0:
                    continue
                
                # 处理小王和大王
                if i == 13 and key == 'S':
                    val = 'B'
                elif i == 13 and key == 'H':
                    val = 'R'
                else:
                    val = card_value_v2s[i]
                
                # 添加剩余牌
                for _ in range(value[i]):
                    rest_cards.append(key + val)
        
        # 设置主牌值
        card_value_s2v = copy.deepcopy(self.card_value)
        card_value_s2v[str(rank)] = 15
        
        # 按大小排序
        rest_cards = sorted(rest_cards, key=lambda item: card_value_s2v[item[1]])
        
        # 按点数分组
        new_rest_cards = []
        if rest_cards:
            tmp = [rest_cards[0]]
            pre = rest_cards[0]
            for card in rest_cards[1:]:
                if card[1] != pre[1]:
                    new_rest_cards.append(tmp)
                    tmp = [card]
                    pre = card
                else:
                    tmp.append(card)
            new_rest_cards.append(tmp)
        
        return new_rest_cards
    
    def reset_episode(self):
        """重置小局数据"""
        self.history = {
            '0': {'send': [], 'remain': 27},
            '1': {'send': [], 'remain': 27},
            '2': {'send': [], 'remain': 27},
            '3': {'send': [], 'remain': 27},
        }
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],
        }
        self.remain_cards_classbynum = [8] * 13 + [2, 2]
        self.pass_num = 0
        self.my_pass_num = 0
    
    def get_pass_count(self) -> Tuple[int, int]:
        """获取PASS次数"""
        return self.pass_num, self.my_pass_num
    
    def get_history(self) -> Dict:
        """获取历史记录"""
        return copy.deepcopy(self.history)

