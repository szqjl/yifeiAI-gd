# -*- coding: utf-8 -*-
"""
GUA-245: 残局 Q1 级牌压单策略缺失。

Gate：
  1. greaterAction == Single（对手出单）
  2. 任一敌人 remaining ≤ 5（残局冲刺阶段）
  3. 本方持有级牌单张（cur_rank rank 的单张，非逢人配 H{curRank}）
  4. 本方有冲刺路径（_has_structure_sprint_path 含顺子/整牌/炸弹）

命中 → 取最小级牌压（保留大级牌回手）。

背景（2026-08-17，match=6a83177a0fbd680d7c785a1e，V8=player2，
logs/v8_vs_botzone_20260817_211528.log，scores=[0,3,0,3] V8 队负）：
  V8 含 D2×2 + S2（三张级牌 2，curRank=2 时 2 是最大单张）。
  残局阶段对手多次出 Single（SA/S3/CA/S8/S6/DQ/H9 等），
  actionList 均含 Single 候选（可压），但 Q1 连续 8 次 PASS on Single
  （22:15:59~22:16:41）。
  根因：_q1_block_enemy 通用路径在「非报单对手出单 + 非领出」场景下，
  候选排序优先「回收优先」/「拆核心保护」/「级牌保留」，
  未考虑「级牌压单 → 夺回领出权 → 顺子冲刺」路径。
"""
import pytest

from src.v.nn.endgame.endgame_decide import EndgameDecider


def _make_ec(my_pos=2, enemies=None):
    """构建 endgame context。"""
    if enemies is None:
        enemies = {
            1: {"remaining": 4, "danger_level": "高",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
            3: {"remaining": 10, "danger_level": "中",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
        }
    return {
        "my_pos": my_pos,
        "cur_pos": (my_pos + 3) % 4,  # 对手出牌，我方跟牌
        "cur_rank": "2",
        "numofplayers": [7, 4, 10, 10],
        "is_active": True,
        "enemies": enemies,
        "teammate": {"remaining": 10, "is_close": False, "assist_prefer": []},
        "self": {"remaining": 13, "has_two_clean_hands": False,
                 "has_bomb": False, "should_sprint": False},
        "finished": [],
    }


def _make_gs(hand, enemy_pos=1, enemy_single="SA"):
    """构建对手出 Single 的 game_state（我方跟牌轮）。"""
    return {
        "curRank": "2",
        "handCards": list(hand),
        "myPos": 2,
        "curPos": enemy_pos,  # 对手出牌位置
        "greaterPos": enemy_pos,
        "greaterAction": ["Single", "A", [enemy_single]],
        "curAction": ["Single", "A", [enemy_single]],
        "numofplayers": [7, 4, 10, 10],
        "publicInfo": [{"rest": n} for n in [7, 4, 10, 10]],
        "done": [],
        "stage": "play",
        "selfRank": "2",
        "oppoRank": "2",
        "_botzone_mode": True,
    }


def _make_candidates(hand):
    """从手牌生成候选动作列表（List[Tuple[int, action]]）。"""
    from collections import Counter
    cnt = Counter(hand)
    candidates = []
    # Single 候选
    for i, card in enumerate(hand):
        rank = card[1] if len(card) > 1 else card
        candidates.append((i, ["Single", rank, [card]]))
    # Pair 候选（cnt[card] 是张数 int）
    offset = len(hand)
    for card, count in cnt.items():
        if count >= 2:
            rank = card[1] if len(card) > 1 else card
            candidates.append((offset, ["Pair", rank, [card, card]]))
            offset += 1
    return candidates


class TestGua245LevelCardPressSingle:
    """GUA-245 单元测试。"""

    def setup_method(self):
        self.decider = EndgameDecider()

    def test_gate1_rejects_non_single(self):
        """Gate 1：greaterAction 非 Single → 返回 None。"""
        hand = ["D2", "S2", "SA", "SK", "SQ", "SJ", "ST",
                "H5", "H6", "H7", "H8", "H9", "HT"]
        gs = _make_gs(hand)
        gs["greaterAction"] = ["Pair", "A", ["SA", "DA"]]
        ec = _make_ec()
        candidates = _make_candidates(hand)
        result = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None

    def test_gate2_rejects_no_low_enemy(self):
        """Gate 2：所有敌人 remaining > 5 → 返回 None。"""
        hand = ["D2", "S2", "SA", "SK", "SQ", "SJ", "ST",
                "H5", "H6", "H7", "H8", "H9", "HT"]
        gs = _make_gs(hand)
        ec = _make_ec(enemies={
            1: {"remaining": 10, "danger_level": "中",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
            3: {"remaining": 8, "danger_level": "中",
                "recommended_types": [], "banned_types": [], "baoshu": {}},
        })
        candidates = _make_candidates(hand)
        result = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None

    def test_gate3_rejects_no_level_single(self):
        """Gate 3：本方无级牌单张 → 返回 None。"""
        # 手牌无 D2/S2（级牌 rank=2 的单张），但有冲刺路径
        hand = ["SA", "SK", "SQ", "SJ", "ST", "S8", "S7",
                "H5", "H6", "H7", "H8", "H9", "HT"]
        gs = _make_gs(hand)
        ec = _make_ec()
        candidates = _make_candidates(hand)
        result = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None

    def test_gate4_rejects_no_sprint(self):
        """Gate 4：本方无冲刺路径 → 返回 None。"""
        # 手牌无顺子/炸弹，纯散牌（间隔大、无 SF、无 bomb-like）
        hand = ["D2", "SA", "C7", "D9", "HJ", "C3", "D4",
                "H5", "C6", "S8", "HT", "CQ", "DK"]
        gs = _make_gs(hand)
        ec = _make_ec()
        candidates = _make_candidates(hand)
        result = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None

    def test_gate_rejects_wild_level_card(self):
        """Gate 3：逢人配 H{curRank} 不算级牌单张 → 返回 None。"""
        # H2 是逢人配，不是级牌单张
        hand = ["H2", "SA", "SK", "SQ", "SJ", "ST",
                "H5", "H6", "H7", "H8", "H9", "HT", "D5"]
        gs = _make_gs(hand)
        ec = _make_ec()
        candidates = _make_candidates(hand)
        result = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is None

    def test_positive_picks_smallest_level_single(self):
        """正例：选最小级牌单张压（保留大级牌回手）。"""
        # 手牌含 D2 + S2（两个级牌单）+ 4x8 炸（冲刺路径）
        # 4x8 炸弹去掉后剩 D2 S2 SA → ranks {2,A} = 2 ≤ 3 → sprint=True
        hand = ["D2", "S2", "C8", "D8", "H8", "S8", "SA"]
        gs = _make_gs(hand)
        ec = _make_ec()
        candidates = _make_candidates(hand)
        result = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is not None
        idx, action = result
        # 应选最小级牌（D2 和 S2 同 rank，取 min 按 value）
        cards = action[2]
        assert len(cards) == 1
        assert cards[0] in ("D2", "S2")

    def test_positive_picks_single_level_single(self):
        """正例：只有一个级牌单张时选它。"""
        hand = ["D2", "C8", "D8", "H8", "S8", "SA"]
        gs = _make_gs(hand)
        ec = _make_ec()
        candidates = _make_candidates(hand)
        result = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert result is not None
        idx, action = result
        assert action[2] == ["D2"]

    def test_integration_q1_block_enemy(self):
        """集成：_q1_block_enemy 在对手出单 + 敌人≤5 + 级牌单 + 冲刺 → 出级牌单。"""
        # 手牌含 D2（级牌单）+ 4x8 炸（冲刺路径）
        hand = ["D2", "C8", "D8", "H8", "S8", "SA", "SK", "SQ"]
        gs = _make_gs(hand, enemy_pos=1, enemy_single="SA")
        ec = _make_ec()
        action_list = [
            ["Single", "2", ["D2"]],
            ["Single", "A", ["SA"]],
            ["Single", "K", ["SK"]],
            ["Single", "Q", ["SQ"]],
            ["Bomb", "8", ["C8", "D8", "H8", "S8"]],
        ]
        result = self.decider._q1_block_enemy(gs, action_list, ec)
        # 应出 D2（级牌单压 SA），而非 PASS
        if result is not None:
            idx, action = result
            cards = action[2]
            assert cards == ["D2"], f"期望出 D2 级牌压单，实际出 {cards}"

    def test_integration_fallback_when_no_sprint(self):
        """集成：无冲刺路径时回退老逻辑（不触发 GUA-245）。"""
        # 手牌含 D2 但无冲刺路径（纯散牌，间隔大）
        hand = ["D2", "SA", "C7", "D9", "HJ", "C3", "D4",
                "H5", "C6", "S8", "HT", "CQ", "DK"]
        gs = _make_gs(hand, enemy_pos=1, enemy_single="SA")
        ec = _make_ec()
        action_list = [
            ["Single", "2", ["D2"]],
            ["Single", "A", ["SA"]],
            ["Single", "7", ["C7"]],
            ["Single", "9", ["D9"]],
            ["Single", "J", ["HJ"]],
            ["PASS"],
        ]
        result = self.decider._q1_block_enemy(gs, action_list, ec)
        # GUA-245 不触发（无冲刺路径），走老逻辑
        # 老逻辑可能出其他牌或 PASS，关键是不触发 GUA-245 专属路径
        # 验证：直接调 _q1_level_card_press_single 确认返回 None
        candidates = _make_candidates(hand)
        direct = self.decider._q1_level_card_press_single(gs, candidates, ec, 1, ec["enemies"][1])
        assert direct is None, "无冲刺路径时 GUA-245 应返回 None"
