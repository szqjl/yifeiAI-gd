# -*- coding: utf-8 -*-
"""
手牌组合优化模块 (Hand Combination Optimizer)
功能：
- 识别所有可能的牌型组合
- 优化组牌策略（优先保留同花顺、炸弹等）
- 考虑主牌对组合的影响
- 避免破坏有价值的牌型
参考获奖代码的完整实现
"""

from typing import Dict, List, Tuple
import copy


class HandCombiner:
    """手牌组合优化器"""
    
    def __init__(self):
        # 卡牌值映射
        self.card_value = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
            "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14,
            "B": 16, "R": 17
        }
        
        # 卡牌索引映射
        self.card_index = {
            "A": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6,
            "8": 7, "9": 8, "T": 9, "J": 10, "Q": 11, "K": 12,
            "R": 13, "B": 13
        }
    
    def combine_handcards(self, handcards: List[str], rank: str) -> Tuple[Dict, Dict]:
        """
        组合手牌，识别所有可能的牌型（完整实现）
        
        Args:
            handcards: 手牌列表
            rank: 当前主牌级别
        
        Returns:
            (sorted_cards, bomb_info)
            sorted_cards: 按牌型分类的手牌
            bomb_info: 炸弹信息字典
        """
        # 初始化结果
        cards = {
            "Single": [],
            "Pair": [],
            "Trips": [],
            "Bomb": [],
        }
        bomb_info = {}
        
        # 按点数排序
        handcards = sorted(handcards, key=lambda item: self.card_value.get(item[1], 0))
        
        # 识别单张、对子、三张、炸弹
        start = 0
        for i in range(1, len(handcards) + 1):
            if i == len(handcards) or handcards[i][1] != handcards[i - 1][1]:
                count = i - start
                if count == 1:
                    cards["Single"].append(handcards[i - 1])
                elif count == 2:
                    cards["Pair"].append(handcards[start:i])
                elif count == 3:
                    cards["Trips"].append(handcards[start:i])
                else:
                    cards["Bomb"].append(handcards[start:i])
                    bomb_info[handcards[start][1]] = count
                start = i
        
        # 准备识别顺子的牌（排除主牌、小王、大王和炸弹）
        temp = []
        for card in handcards:
            if card[1] != rank and card[1] != 'B' and card[1] != 'R':
                temp.append(card)
        
        # 排除炸弹中的牌
        for bomb in cards['Bomb']:
            if bomb[0][1] != rank and bomb[0][1] != 'B' and bomb[0][1] != 'R':
                for card in bomb:
                    if card in temp:
                        temp.remove(card)
        
        # 统计点数（用于识别顺子）
        cardre = [0] * 14
        for card in temp:
            rank_char = card[1]
            if rank_char == 'A':
                cardre[0] += 1
            elif rank_char in ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']:
                idx = self.card_index[rank_char]
                cardre[idx] += 1
        
        # 查找最优顺子（参考获奖代码算法）
        st = []
        minnum = 10
        mintwonum = 10
        
        # 查找普通顺子（2-K）
        for i in range(1, len(cardre) - 4):
            if 0 not in cardre[i:i + 5]:
                onenum = 0
                zeronum = 0
                twonum = 0
                for j in cardre[i:i + 5]:
                    if j - 1 == 0:
                        zeronum += 1
                    if j - 1 == 1:
                        onenum += 1
                    if j - 1 == 2:
                        twonum += 1
                
                if zeronum > onenum and minnum >= onenum:
                    if len(st) == 0:
                        if zeronum >= onenum + twonum:
                            st.append(i)
                            minnum = onenum
                            mintwonum = twonum
                    else:
                        if minnum == onenum:
                            if i == 1:
                                if mintwonum > twonum:
                                    if zeronum >= onenum + twonum:
                                        st = []
                                        st.append(i)
                                        minnum = onenum
                                        mintwonum = twonum
                            else:
                                if mintwonum >= twonum:
                                    if zeronum >= onenum + twonum:
                                        st = []
                                        st.append(i)
                                        minnum = onenum
                                        mintwonum = twonum
                        else:
                            if zeronum >= onenum + twonum:
                                st = []
                                st.append(i)
                                minnum = onenum
                                mintwonum = twonum
        
        # 查找A-5特殊顺子
        if 0 not in cardre[10:] and cardre[0] != 0:
            onenum = 0
            zeronum = 0
            twonum = 0
            for j in cardre[10:]:
                if j - 1 == 0:
                    zeronum += 1
                if j - 1 == 1:
                    onenum += 1
                if j - 1 == 2:
                    twonum += 1
            if cardre[0] - 1 == 0:
                zeronum += 1
            if cardre[0] - 1 == 1:
                onenum += 1
            if cardre[0] - 1 == 2:
                twonum += 1
            
            if zeronum > onenum and minnum >= onenum:
                if len(st) == 0:
                    if zeronum >= onenum + twonum:
                        st.append(10)
                        minnum = onenum
                        mintwonum = twonum
                else:
                    if minnum == onenum:
                        if mintwonum >= twonum:
                            if zeronum >= onenum + twonum:
                                st = []
                                st.append(10)
                                minnum = onenum
                                mintwonum = twonum
                    else:
                        if zeronum >= onenum + twonum:
                            st = []
                            st.append(10)
                            minnum = onenum
                            mintwonum = twonum
        
        # 构建顺子牌列表
        tmp = []
        Flushtmp = []
        nowhandcards = []
        Straight = []
        
        if len(st) > 0:
            for i in range(st[0], st[0] + 5):
                if 1 < i < 10:
                    Straight.append(str(i))
                if i % 13 == 1:
                    Straight.append('A')
                if i == 10:
                    Straight.append('T')
                if i == 11:
                    Straight.append('J')
                if i == 12:
                    Straight.append('Q')
                if i == 13:
                    Straight.append('K')
        
        # 检查同花顺
        sttemp = []
        for i in range(4):
            sttemp.append([0] * 5)
        counttemp = 0
        
        colortemp = {"S": 0, "H": 1, "C": 2, "D": 3}
        rev_colortemp = {0: 'S', 1: 'H', 2: 'C', 3: 'D'}
        
        for i in range(0, len(handcards) - 1):
            if handcards[i][1] in Straight:
                sttemp[colortemp[handcards[i][0]]][counttemp] += 1
                if handcards[i][1] != handcards[i + 1][1]:
                    counttemp += 1
        
        StraightFlushflag = -1
        for i in range(4):
            if sttemp[i][0] > 0 and sttemp[i][1] > 0 and sttemp[i][2] > 0 and sttemp[i][3] > 0 and sttemp[i][4] > 0:
                StraightFlushflag = i
        
        if StraightFlushflag >= 0:
            # 找到同花顺
            for i in Straight:
                Flushtmp.append(rev_colortemp[StraightFlushflag] + i)
            for i in range(0, len(handcards)):
                if handcards[i] not in Flushtmp:
                    nowhandcards.append(handcards[i])
        else:
            # 只有顺子，没有同花顺
            for i in range(0, len(handcards)):
                if handcards[i][1] in Straight:
                    tmp.append(handcards[i])
                    if handcards[i][1] in Straight:
                        Straight.remove(handcards[i][1])
                else:
                    nowhandcards.append(handcards[i])
        
        # 重新分类剩余牌
        newcards = {
            "Single": [],
            "Pair": [],
            "Trips": [],
            "Bomb": [],
            "Straight": [],
            "StraightFlush": []
        }
        
        if len(tmp) == 5:
            # 处理A-5特殊顺子
            if tmp[-1][1] == 'A' and tmp[-2][1] == '5':
                tmpptmp = [tmp[-1]]
                for kkk in tmp[:-1]:
                    tmpptmp.append(kkk)
                newcards['Straight'].append(tmpptmp)
            else:
                newcards['Straight'].append(tmp)
        
        if len(Flushtmp) == 5:
            newcards['StraightFlush'].append(Flushtmp)
        
        # 重新分类剩余牌
        start = 0
        for i in range(1, len(nowhandcards) + 1):
            if i == len(nowhandcards) or nowhandcards[i][1] != nowhandcards[i - 1][1]:
                count = i - start
                if count == 1:
                    newcards["Single"].append(nowhandcards[i - 1])
                elif count == 2:
                    newcards["Pair"].append(nowhandcards[start:i])
                elif count == 3:
                    newcards["Trips"].append(nowhandcards[start:i])
                else:
                    newcards["Bomb"].append(nowhandcards[start:i])
                start = i
        
        return newcards, bomb_info
    
    def get_grouping_priority(self) -> Dict[str, int]:
        """
        获取组牌优先级
        
        Returns:
            优先级字典（数值越大优先级越高）
        """
        return {
            "StraightFlush": 100,  # 同花顺优先级最高
            "Bomb": 80,            # 炸弹
            "Straight": 60,        # 顺子
            "ThreeWithTwo": 50,    # 三带二
            "TwoTrips": 45,        # 钢板
            "ThreePair": 40,       # 三连对
            "Trips": 30,           # 三张
            "Pair": 20,            # 对子
            "Single": 10           # 单张
        }
    
    def is_in_straight(self, action: List, straight_member: List[str]) -> bool:
        """
        判断动作中的牌是否在顺子中
        
        Args:
            action: 动作 [type, rank, cards]
            straight_member: 顺子中的牌列表
        
        Returns:
            True: 在顺子中，False: 不在
        """
        if len(straight_member) == 0:
            return False
        
        for card in action[2]:
            if card in straight_member:
                return True
        
        return False

