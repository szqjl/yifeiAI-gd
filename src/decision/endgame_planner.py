# -*- coding: utf-8 -*-
"""
残局两手规划器 - 当手牌≤12张时，枚举"两手恰好出完"的所有组合
根本原因分析显示：M1缺乏残局规划，导致残局逐张输
本模块实现lalala的绝招：两手规划
"""

from typing import Dict, List, Tuple, Optional


class EndgamePlanner:
    """
    残局决策引擎：当手牌≤12张时，规划两手如何恰好出完

    核心逻辑来自lalala：
    - 枚举actionList中所有"两个动作合并后等于手牌总数"的配对
    - 从这些配对中选出最优组合
    - 优先这些"恰好出完"的配对，避免被对手压制
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.endgame_threshold = 12  # 手牌≤12张时启用两手规划

    def is_endgame(self, handcards: List[str]) -> bool:
        """
        判断是否进入残局阶段

        Args:
            handcards: 手牌列表

        Returns:
            True 表示已进入残局（≤12张）
        """
        return len(handcards) <= self.endgame_threshold

    def find_two_hand_combinations(
        self, handcards: List[str], action_list: List[List]
    ) -> List[Tuple[int, int]]:
        """
        找出所有"两手恰好出完"的配对

        核心逻辑（来自lalala）：
        - 枚举action_list中的所有两个不同动作
        - 如果它们的牌张数之和等于手牌总数，则记录这个配对

        Args:
            handcards: 当前手牌列表
            action_list: 合法动作列表，每个动作格式：[type, rank, [cards...]]

        Returns:
            列表 [(i, j), ...] 表示第i和第j个动作配对可以恰好出完
        """
        if not self.is_endgame(handcards) or not action_list:
            return []

        hand_count = len(handcards)
        combinations = []

        for i in range(len(action_list)):
            action_i = action_list[i]
            # 提取action中的牌列表（格式：[type, rank, [cards...]]）
            if len(action_i) < 3:
                continue
            cards_i = action_i[2]
            if not isinstance(cards_i, list):
                continue
            count_i = len(cards_i)

            for j in range(i + 1, len(action_list)):
                action_j = action_list[j]
                if len(action_j) < 3:
                    continue
                cards_j = action_j[2]
                if not isinstance(cards_j, list):
                    continue
                count_j = len(cards_j)

                # 检查两个动作是否恰好出完所有牌
                if count_i + count_j == hand_count:
                    combinations.append((i, j))

        return combinations

    def evaluate_combination_pair(
        self,
        action_i: List,
        action_j: List,
        history_info: Dict = None,
        context: Dict = None,
    ) -> float:
        """
        评估一个两手配对的质量

        评分因素：
        1. 牌力：优先出大牌组合（第二手留小牌是死局）
        2. 对手压制能力：是否能压制对方最后的进攻
        3. 队伙协作：是否能配合队伙

        Args:
            action_i: 第一手动作
            action_j: 第二手动作
            history_info: 历史信息（对手出过什么牌）
            context: 游戏上下文

        Returns:
            评分（0-100）
        """
        score = 50.0  # 基础分

        if len(action_i) < 3 or len(action_j) < 3:
            return score

        cards_i = action_i[2] if isinstance(action_i[2], list) else []
        cards_j = action_j[2] if isinstance(action_j[2], list) else []

        # ① 优先让第一手强，第二手保守
        # （第二手是最后防线，需要灵活应对）
        if len(cards_i) > len(cards_j):
            score += 10  # 第一手更强

        # ② 优先出炸弹作为第一手（如果有的话）
        if action_i[0] == 'Bomb':
            score += 20
        if action_j[0] == 'Bomb':
            score -= 10  # 不希望炸弹作为最后的防线

        # ③ 避免出 PASS 作为配对的一部分
        if action_i[0] == 'Pass':
            score -= 30
        if action_j[0] == 'Pass':
            score -= 20

        return max(0, min(100, score))

    def select_best_combination(
        self,
        combinations: List[Tuple[int, int]],
        action_list: List[List],
        context: Dict = None,
    ) -> Optional[Tuple[int, int]]:
        """
        从多个两手配对中选出最优的

        Args:
            combinations: 所有可行的两手配对
            action_list: 完整的动作列表
            context: 游戏上下文

        Returns:
            最优配对 (i, j) 或 None
        """
        if not combinations or not action_list:
            return None

        best_pair = None
        best_score = -1

        for i, j in combinations:
            if i >= len(action_list) or j >= len(action_list):
                continue

            action_i = action_list[i]
            action_j = action_list[j]

            score = self.evaluate_combination_pair(action_i, action_j, context=context)

            if score > best_score:
                best_score = score
                best_pair = (i, j)

        return best_pair

    def is_pair_viable(self, pair: Tuple[int, int], greater_action: List) -> bool:
        """
        检查一个两手配对是否在当前轮次中可行

        两手配对中的第一手必须能压制greater_action（或greater_action为空/PASS）

        Args:
            pair: (i, j) 配对
            greater_action: 当前最大的动作

        Returns:
            True 表示这个配对可行
        """
        if not pair or len(pair) != 2:
            return False

        i, j = pair

        # 如果没有需要压制的动作，任何配对都可行
        if not greater_action or greater_action[0] == 'Pass':
            return True

        # 否则需要检查第一手是否能压制
        # （这里简化处理，实际应该调用卡型比较逻辑）
        return True

    def recommend_first_action(
        self, combinations: List[Tuple[int, int]], action_list: List[List], context: Dict = None
    ) -> Optional[int]:
        """
        从两手配对中推荐第一手的动作索引

        Args:
            combinations: 所有可行的两手配对
            action_list: 完整的动作列表
            context: 游戏上下文

        Returns:
            推荐的第一手动作索引 或 None
        """
        best_pair = self.select_best_combination(combinations, action_list, context)

        if best_pair:
            return best_pair[0]  # 返回第一手的索引

        return None

    def debug_info(self, combinations: List[Tuple[int, int]], action_list: List[List]) -> str:
        """返回调试信息"""
        info = f"【残局两手规划】\n  找到 {len(combinations)} 个两手配对\n"
        for i, (idx_i, idx_j) in enumerate(combinations[:5]):  # 只显示前5个
            if idx_i < len(action_list) and idx_j < len(action_list):
                ai = action_list[idx_i]
                aj = action_list[idx_j]
                info += f"  配对{i}: [{ai[0]}({len(ai[2])}张)] + [{aj[0]}({len(aj[2])}张)]\n"
        return info
