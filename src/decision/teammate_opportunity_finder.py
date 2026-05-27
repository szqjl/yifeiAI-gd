# -*- coding: utf-8 -*-
"""
队友传牌识别器 - 分析队友可能的需求，主动为队友创造机会
根本原因分析显示：M1缺乏"主动为队友传牌"的意识，导致无法协作赢
本模块实现队伙协作的核心逻辑
"""

from typing import Dict, List, Optional, Tuple


class TeammateOpportunityFinder:
    """
    识别队友的传牌机会和需求

    核心思路：
    1. 基于历史信息推测队友手中可能有什么牌
    2. 识别"队友能接"且"对我方有利"的牌型
    3. 主动出这样的牌，为队友创造控场机会
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def analyze_teammate_needs(
        self,
        my_pos: int,
        handcards: List[str],
        history_info: Dict,
        team_coordination_info: Dict,
        current_greater_action: List = None,
    ) -> Dict:
        """
        分析队友的需求

        Args:
            my_pos: 我的座位号
            handcards: 我的手牌
            history_info: 历史信息
            team_coordination_info: 队伙协作信息
            current_greater_action: 当前最大的动作

        Returns:
            {
                'teammate_likely_has': [队友可能拥有的高牌],
                'teammate_lacking': [队友可能缺少的牌],
                'good_pass_types': [适合传给队友的牌型],
            }
        """
        teammate_pos = (my_pos + 2) % 4

        analysis = {
            'teammate_likely_has': [],
            'teammate_lacking': [],
            'good_pass_types': [],
            'pass_opportunity': False,
        }

        if not team_coordination_info:
            return analysis

        # ① 推测队友可能拥有的高牌（从未出过或出过很少）
        teammate_sent = team_coordination_info.get('teammate_sent', [])
        teammate_remain = team_coordination_info.get('teammate_remain', 27)

        # 统计队友已出过的牌
        sent_count = {}
        for card in teammate_sent:
            sent_count[card] = sent_count.get(card, 0) + 1

        # 推测队友可能拥有的高牌
        high_ranks = ['A', 'K', 'Q', 'J', 'T']
        for rank in high_ranks:
            count_sent = sum(1 for card in teammate_sent if card[1:] == rank)
            # 掼蛋每个点数4张牌（两种花色各2张）
            if count_sent < 3:  # 如果队友未出过该点数的3张或以上，很可能还在手中
                analysis['teammate_likely_has'].append(rank)

        # ② 推测队友可能缺少的牌型
        # 这取决于对方的进攻模式——如果对方在出某种牌型，队友可能缺这种
        opponent_1_sent = team_coordination_info.get('opponent_1_sent', [])
        opponent_2_sent = team_coordination_info.get('opponent_2_sent', [])

        # 如果对方频繁出某个牌型，推测队友可能缺这个点数
        for sent_list in [opponent_1_sent, opponent_2_sent]:
            for card in sent_list[-5:]:  # 检查最近出过的5张牌
                rank = card[1:] if len(card) > 1 else card
                if rank not in analysis['teammate_lacking']:
                    analysis['teammate_lacking'].append(rank)

        # ③ 识别适合传给队友的牌型
        # 我手中有，但对方没有出过很多的牌 → 队友可能也没出过 → 传给队友
        my_ranks = {}
        for card in handcards:
            rank = card[1:] if len(card) > 1 else card
            my_ranks[rank] = my_ranks.get(rank, 0) + 1

        for rank, count in my_ranks.items():
            if rank in analysis['teammate_likely_has']:
                # 这是队友可能还有的高牌，传给队友能帮助他控场
                analysis['good_pass_types'].append({
                    'rank': rank,
                    'reason': 'teammate_likely_has',
                })

        # ④ 判断是否有传牌的好机会
        # 条件：队友是下一个玩家 且 当前没有更大的动作（或轮到我们时）
        if current_greater_action and current_greater_action[0] != 'Pass':
            # 对方有进攻，我应该被动应对，可能没有传牌的机会
            analysis['pass_opportunity'] = False
        else:
            # 当前没有需要压制的动作，可以主动传牌给队友
            analysis['pass_opportunity'] = True

        return analysis

    def find_passing_actions(
        self,
        my_pos: int,
        action_list: List[List],
        analysis: Dict,
    ) -> List[Tuple[int, str]]:
        """
        从action_list中找出可以用来传牌的动作

        Args:
            my_pos: 我的座位号
            action_list: 合法动作列表
            analysis: 队友分析结果

        Returns:
            列表 [(action_idx, reason), ...] 表示适合传牌的动作
        """
        passing_actions = []

        good_pass_types = analysis.get('good_pass_types', [])
        if not good_pass_types:
            return passing_actions

        # 遍历action_list，找出那些包含"好传牌"牌型的动作
        for i, action in enumerate(action_list):
            if len(action) < 3:
                continue

            action_type = action[0]
            action_rank = action[1] if len(action) > 1 else None
            cards = action[2] if isinstance(action[2], list) else []

            # 跳过PASS
            if action_type == 'Pass':
                continue

            # 检查这个动作是否包含"好传牌"的牌型
            for good_type in good_pass_types:
                if action_rank == good_type['rank']:
                    passing_actions.append((i, good_type['reason']))
                    break

        return passing_actions

    def should_prioritize_passing(
        self,
        analysis: Dict,
        context: Dict,
    ) -> bool:
        """
        判断是否应该优先传牌给队友

        Args:
            analysis: 队友分析结果
            context: 游戏上下文

        Returns:
            True 表示应该优先传牌
        """
        # 条件1：有传牌的机会
        if not analysis.get('pass_opportunity', False):
            return False

        # 条件2：队友还在认真出牌（剩余牌数较多）
        teammate_remain = context.get('teammate_rest_cards', 27)
        if teammate_remain > 12:  # P0改进：从15降到12，更积极地传牌
            # 队友还有足够的牌，不需要急着传
            return False

        # 条件3：我的牌力足够支撑传牌
        card_power = context.get('card_power', 5.0)
        if card_power < 3:  # P0改进：从4降到3，降低牌力要求
            # 我的牌太弱，传牌反而容易被对方压制
            return False

        return True

    def debug_info(self, analysis: Dict) -> str:
        """返回调试信息"""
        info = "【队友传牌分析】\n"
        info += f"  队友可能拥有: {analysis.get('teammate_likely_has', [])}\n"
        info += f"  适合传牌的牌型: {[t['rank'] for t in analysis.get('good_pass_types', [])]}\n"
        info += f"  传牌机会: {'有' if analysis.get('pass_opportunity', False) else '无'}\n"
        return info
