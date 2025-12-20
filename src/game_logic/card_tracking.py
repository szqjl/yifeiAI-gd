# -*- coding: utf-8 -*-
"""
鐠佹壆澧濇稉搴㈠腹閻炲棙膩閸 (Card Tracking & Inference Module)
閸旂喕鍏橀敍
- 缂佸瓨濮㈠В蹇庨嚋閻溾晛鍓佹畱閸戣櫣澧濋崢鍡楀蕉
- 鐠虹喕閲滈崜鈺缍戦悧灞界氨閿涘牊瀵滈懞杈澹婇崪宀鍋ｉ弫甯绱
- 鐠侊紕鐣婚崜鈺缍戦悧灞惧倻宸奸崚鍡楃
- 閹恒劎鎮婄佃勫滈崣閼宠姤瀵旈張澶屾畱閻楀苯鐎
- 鐠佹澘缍嶆潻鐐电敾PASS濞嗏剝鏆
"""

import copy
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class CardTracker:
    """鐠佹壆澧濇稉搴㈠腹閻炲棙膩閸"""
    
    def __init__(self):
        # 閻溾晛璺哄坊閸欒尪鏉跨秿閿涙碍鐦℃稉閻溾晛鑸靛ⅵ閸戣櫣娈戦悧灞芥嫲閸撯晙缍戦悧灞炬殶
        self.history = {
            '0': {'send': [], 'remain': 27},
            '1': {'send': [], 'remain': 27},
            '2': {'send': [], 'remain': 27},
            '3': {'send': [], 'remain': 27},
        }
        
        # 閸撯晙缍戦悧灞界氨閿涙碍瀵滈懞杈澹婇崪宀鍋ｉ弫鏉垮瀻缁
        # 缁便垹绱╅敍娆=0, 2=1, 3=2, ..., K=12, B=13(鐏忓繒甯), R=13(婢堆呭竾)
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # 姒涙垶
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],  # 缁俱垺
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # 濮婂懓濮抽敍鍫熸￥婢堆呭竾閿
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # 閺傚湱澧栭敍鍫熸￥鐏忓繒甯囬敍
        }
        
        # 閹稿屽仯閺佹澘鍨庣猾鑽ゆ畱閸撯晙缍戦悧宀嬬礄閻銊ょ艾韫囬柅鐔哥叀鐠囬敍
        # 缁便垹绱╅敍娆=0, 2=1, ..., K=12, B=13, R=13
        self.remain_cards_classbynum = [8] * 13 + [2, 2]  # 13缁夊秶鍋ｉ弫鏉挎倗8瀵鐙呯礉鐏忓繒甯2瀵鐙呯礉婢堆呭竾2瀵
        
        # 鏉╃偟鐢籔ASS濞嗏剝鏆
        self.pass_num = 0  # 闂冪喎寮搁崪宀冨殰瀹歌精绻涚紒鐠揂SS濞嗏剝鏆
        self.my_pass_num = 0  # 閼峰歌精绻涚紒鐠揂SS濞嗏剝鏆
        
        # 閸楋紕澧濈槐銏犵穿閺勭姴鐨
        self.card_index = {
            "A": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6,
            "8": 7, "9": 8, "T": 9, "J": 10, "Q": 11, "K": 12,
            "R": 13, "B": 13
        }
        
        # 閸楋紕澧濋崐鍏兼Ё鐏忓嫸绱欓悽銊ょ艾濮ｆ棁绶濇径褍鐨閿
        self.card_value = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
            "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
            "B": 16, "R": 17
        }
    
    def update_from_play(self, cur_pos: int, cur_action: List, my_pos: int):
        """
        閺囧瓨鏌婇崙铏瑰濇穱鈩冧紖
        
        Args:
            cur_pos: 閸戣櫣澧濋悳鈺佹湹缍呯純 (0-3)
            cur_action: 閸戣櫣澧濋崝銊ょ稊 [type, rank, cards]
            my_pos: 閼峰歌京娈戞担宥囩枂
        """
        # 婵″倹鐏夋稉宥嗘ЦPASS閿涘本娲块弬鏉垮毉閻楀苯宸婚崣
        if cur_action[0] != "PASS" and cur_action[2] != "PASS":
            for card in cur_action[2]:
                # 瀹夋俺鐦℃稉閻溾晛鑸靛ⅵ閸戣櫣娈戦悧灞芥嫲閸撯晙缍戦悧灞炬殶
                if not card or not isinstance(card, str) or len(card) < 2:
                    continue
                
                # 鐠佹澘缍嶉崙铏瑰
                self.history[str(cur_pos)]["send"].append(card)
                self.history[str(cur_pos)]["remain"] -= 1
                
                # 閺囧瓨鏌婇崜鈺缍戦悧灞界氨
                card_type = str(card[0])  # 閼鸿精澹
                card_rank = card[1]  # 閻愯勬殶
                
                # 瀹夋俺鐦℃稉閻溾晛鑸靛ⅵ閸戣櫣娈戦悧灞芥嫲閸撯晙缍戦悧灞炬殶
                if card_rank not in self.card_index:
                    continue
                
                # 瀹夋俺鐦℃稉閻溾晛鑸靛ⅵ閸戣櫣娈戦悧灞芥嫲閸撯晙缍戦悧灞炬殶
                if card_type not in self.remain_cards:
                    continue
                    
                x = self.card_index[card_rank]
                
                if x < len(self.remain_cards[card_type]) and self.remain_cards[card_type][x] > 0:
                    self.remain_cards[card_type][x] -= 1
                
                # 閺囧瓨鏌婇幐澶屽仯閺佹澘鍨庣猾鑽ゆ畱閸撯晙缍戦悧
                if card_rank in ["B", "R"]:
                    # 鐏忓繒甯囬幋鏍с亣閻
                    if self.remain_cards_classbynum[13] > 0:
                        self.remain_cards_classbynum[13] -= 1
                else:
                    # 閺呴柅姘卞
                    idx = self.card_index[card_rank]
                    if self.remain_cards_classbynum[idx] > 0:
                        self.remain_cards_classbynum[idx] -= 1
        
        # 閺囧瓨鏌婃潻鐐电敾PASS濞嗏剝鏆
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
        """閼惧嘲褰囬悳鈺佽泛澧挎担娆戝濋弫"""
        return self.history[str(pos)]["remain"]
    
    def get_remaining_cards(self, rank: str = None) -> Dict:
        """
        閼惧嘲褰囬崜鈺缍戦悧灞界氨
        
        Args:
            rank: 娑撹崵澧濈痪褍鍩嗛敍灞藉倹鐏夐幓鎰绶甸敍灞肩窗鐠侊紕鐣绘稉鑽ゅ濋弫浼村櫤
        
        Returns:
            閸撯晙缍戦悧灞界氨鐎涙鍚
        """
        if rank:
            # 鐠侊紕鐣绘稉鑽ゅ濋弫浼村櫤
            rank_card = f"H{rank}"  # 娑撹崵澧濋柅姘鐖堕弰缁俱垺
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
        鐠侊紕鐣婚崜鈺缍戦悧灞界氨閿涘牊甯撻梽銈嗗滈悧灞芥倵閿
        
        Args:
            handcards: 閹靛澧濋崚妤勩
            rank: 瑜版挸澧犳稉鑽ゅ濈痪褍鍩
        
        Returns:
            閹稿屽仯閺佹澘鍨庣紒鍕娈戦崜鈺缍戦悧灞藉灙鐞
        """
        card_value_v2s = {
            0: "A", 1: "2", 2: "3", 3: "4", 4: "5", 5: "6", 6: "7",
            7: "8", 8: "9", 9: "T", 10: "J", 11: "Q", 12: "K"
        }
        
        # 婢跺秴鍩楅崜鈺缍戦悧灞界氨
        new_remaincards = {}
        for key, val in self.remain_cards.items():
            new_remaincards[key] = copy.deepcopy(val)
        
        # 閸戝繐骞撻幍瀣澧
        for card in handcards:
            card_type = str(card[0])
            x = self.card_index[card[1]]
            if new_remaincards[card_type][x] > 0:
                new_remaincards[card_type][x] -= 1
        
        # 鏉為幑娑撳搫鍨鐞涖劍鐗稿
        rest_cards = []
        for key, value in new_remaincards.items():
            for i in range(len(value)):
                if value[i] == 0:
                    continue
                
                # 婢跺嫮鎮婄亸蹇曞竾閸滃苯銇囬悳
                if i == 13 and key == 'S':
                    val = 'B'
                elif i == 13 and key == 'H':
                    val = 'R'
                else:
                    val = card_value_v2s[i]
                
                # 濞ｈ插為崜鈺缍戦悧
                for _ in range(value[i]):
                    rest_cards.append(key + val)
        
        # 鐠佸墽鐤嗘稉鑽ゅ濋崐
        card_value_s2v = copy.deepcopy(self.card_value)
        card_value_s2v[str(rank)] = 15
        
        # 閹稿娿亣鐏忓繑甯撴惔
        rest_cards = sorted(rest_cards, key=lambda item: card_value_s2v[item[1]])
        
        # 閹稿屽仯閺佹澘鍨庣紒
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
        """闁插秶鐤嗙亸蹇撶湰閺佺増宓"""
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
        """閼惧嘲褰嘝ASS濞嗏剝鏆"""
        return self.pass_num, self.my_pass_num
    
    def get_history(self) -> Dict:
        """閼惧嘲褰囬崢鍡楀蕉鐠佹澘缍"""
        return copy.deepcopy(self.history)

