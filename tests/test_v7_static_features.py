# -*- coding: utf-8 -*-
"""
GUA-037a 静态特征工程测试

覆盖 8+ 测试用例：
  1. test_dimension_124        — 输出维度恒定 124
  2. test_empty_hand           — 空手牌（全 0）
  3. test_27_card_hand         — 满手 27 张（108 维正确编码）
  4. test_heart_wildcard       — 含红心配（H+curRank）
  5. test_tribute_round        — 贡牌阶段（tributeResult）
  6. test_active_passive       — 主动/被动标志（curPos = myPos）
  7. test_bomb_count           — curBombNum 计数
  8. test_rank_suit_dist       — 级牌花色分布
  9. test_joker_detection      — Joker 检测
  10. test_normalized_range    — 所有归一化值在 [0, 1] 内
"""

import numpy as np
import pytest

from src.v.nn.features.static_features import (
    extract_static_features,
    STATIC_STATE_DIM,
    encode_hand_cards_108,
    CARD_TYPES,
    SUITS,
    RANKS,
    JOKERS,
)


def _make_game_state(**overrides) -> dict:
    """构造最小 game_state 工厂。"""
    state = {
        "handCards": [],
        "myPos": 0,
        "curPos": 0,
        "curRank": "2",
        "selfRank": "2",
        "oppoRank": "2",
        "actionList": [["S3"]],
        "curBombNum": 0,
    }
    state.update(overrides)
    return state


# ── 1. 维度检验 ──

class TestStaticFeaturesDimension:
    def test_dimension_124(self):
        """提取结果维度必须为 124。"""
        feat = extract_static_features(_make_game_state())
        assert feat.shape == (STATIC_STATE_DIM,), f"期望 124 维，实际 {feat.shape}"

    def test_dimension_always_fixed(self):
        """不同输入均应输出 124 维。"""
        states = [
            _make_game_state(handCards=["S2", "H3"]),
            _make_game_state(handCards=list(CARD_TYPES[:27]), curBombNum=3),
            _make_game_state(handCards=[], curPos=-1, tributeResult=[["S2", "H3"]]),
        ]
        for s in states:
            feat = extract_static_features(s)
            assert feat.shape == (STATIC_STATE_DIM,)


# ── 2. 手牌 one-hot 编码 ──

class TestHandCards108:
    def test_empty_hand_all_zero(self):
        """空手牌时 108 维全为 0。"""
        feat = extract_static_features(_make_game_state(handCards=[]))
        assert np.allclose(feat[0:108], 0), "空手牌 108 维必须全 0"

    def test_single_card_encoding(self):
        """单张牌在其对应位置为 [1, 0]，其余为 0。"""
        feat = extract_static_features(_make_game_state(handCards=["S2"]))
        # S2 在 CARD_TYPES 中的索引: suits[0]=S, ranks[0]=2 → CARD_TYPES[0]="S2"
        # 对应 dim 0 (第一张) = 1, dim 1 (第二张) = 0
        assert feat[0] == 1.0, "S2 第一张应为 1"
        assert feat[1] == 0.0, "S2 第二张应为 0"
        # 其他位置应为 0
        assert np.allclose(feat[2:108], 0), "单张牌非对应位置应为 0"

    def test_double_card_encoding(self):
        """两张相同牌在对应位置为 [1, 1]。"""
        feat = extract_static_features(_make_game_state(handCards=["S2", "S2"]))
        assert feat[0] == 1.0, "S2 第一张应为 1"
        assert feat[1] == 1.0, "S2 两张时第二张应为 1"

    def test_27_card_hand(self):
        """27 张满手牌：所有持有牌对应位置标记为 1。"""
        # 取前 27 种牌型各 1 张
        cards_27 = CARD_TYPES[:27]
        feat = extract_static_features(_make_game_state(handCards=cards_27))
        for i in range(27):
            # 每种牌 2 维，第 1 维应为 1
            assert feat[i * 2] == 1.0, f"第 {i} 种牌 {CARD_TYPES[i]} 第1维应为 1"
            assert feat[i * 2 + 1] == 0.0, f"第 {i} 种牌 {CARD_TYPES[i]} 第2维应为 0（仅1张）"
        # 未持有的牌对应位置为 0
        for i in range(27, 54):
            assert feat[i * 2] == 0.0, f"第 {i} 种牌 {CARD_TYPES[i]} 第1维应为 0"
            assert feat[i * 2 + 1] == 0.0, f"第 {i} 种牌 {CARD_TYPES[i]} 第2维应为 0"

    def test_joker_encoding(self):
        """王（BJ/RJ）编码在最后 4 维。"""
        feat = extract_static_features(_make_game_state(handCards=["BJ", "RJ"]))
        # BJ 是 CARD_TYPES[52], RJ 是 CARD_TYPES[53]
        # dim[104,105] for BJ, dim[106,107] for RJ
        assert feat[104] == 1.0, "BJ 第1张应为 1"
        assert feat[106] == 1.0, "RJ 第1张应为 1"


# ── 3. 级牌/红心配 ──

class TestRankAndWildcard:
    def test_rank_normalization(self):
        """等级归一化值在 [0, 1] 范围内。"""
        for rank_str, expected_val in [("2", 0.0), ("A", 1.0), ("7", 5 / 12)]:
            feat = extract_static_features(_make_game_state(curRank=rank_str))
            assert abs(feat[108] - expected_val) < 1e-6, f"curRank={rank_str} 期望 {expected_val}"

    def test_heart_wildcard_detected(self):
        """持有 H+curRank 时红心配标志为 1。"""
        feat = extract_static_features(_make_game_state(curRank="5", handCards=["H5", "S3"]))
        assert feat[111] == 1.0, "持有 H5 时红心配标志应为 1"

    def test_heart_wildcard_absent(self):
        """未持有 H+curRank 时红心配标志为 0。"""
        feat = extract_static_features(_make_game_state(curRank="5", handCards=["S5", "H3"]))
        assert feat[111] == 0.0, "未持有 H5 时红心配标志应为 0"

    def test_joker_flag_detected(self):
        """持有王时 Joker 标志为 1。"""
        feat = extract_static_features(_make_game_state(handCards=["BJ"]))
        assert feat[112] == 1.0, "持有 BJ 时 Joker 标志应为 1"

    def test_joker_flag_absent(self):
        """无王时 Joker 标志为 0。"""
        feat = extract_static_features(_make_game_state(handCards=["S2", "H3"]))
        assert feat[112] == 0.0, "无王时 Joker 标志应为 0"


# ── 4. 级牌花色分布 ──

class TestRankSuitDistribution:
    def test_rank_suit_four_ways(self):
        """curRank 牌在各花色计数 4 维。"""
        # 持有 4 种花色的 curRank 各 1 张
        cards = [f"{s}5" for s in SUITS]  # S5, H5, D5, C5
        feat = extract_static_features(_make_game_state(curRank="5", handCards=cards))
        for i in range(4):
            assert feat[113 + i] == 0.5, f"花色 {SUITS[i]} 计数应为 0.5（1/2）"

    def test_rank_suit_double_heart(self):
        """红心 curRank 有 2 张时值为 1.0。"""
        feat = extract_static_features(_make_game_state(curRank="5", handCards=["H5", "H5"]))
        assert feat[114] == 1.0, "红心 2 张时应为 1.0"


# ── 5. 主动/被动标志 ──

class TestActivePassive:
    def test_active_when_my_turn(self):
        """curPos = myPos 时为主动 (1)。"""
        feat = extract_static_features(_make_game_state(myPos=0, curPos=0))
        assert feat[117] == 1.0

    def test_active_when_partner_turn(self):
        """curPos = partner (myPos+2) 时为主动 (1)。"""
        feat = extract_static_features(_make_game_state(myPos=0, curPos=2))
        assert feat[117] == 1.0

    def test_passive_when_opponent_turn(self):
        """curPos 为对手时为被动 (0)。"""
        feat = extract_static_features(_make_game_state(myPos=0, curPos=1))
        assert feat[117] == 0.0


# ── 6. 游戏阶段 ──

class TestGamePhase:
    def test_tribute_phase(self):
        """贡牌阶段 one-hot = [1, 0, 0]。"""
        feat = extract_static_features(_make_game_state(
            tributeResult=[["S2", "H3"]],
            handCards=["S2"],
            curPos=0,
            actionList=[["PASS"]]
        ))
        assert feat[118] == 1.0, "贡牌阶段 dim 118 应为 1"
        assert feat[119] == 0.0
        assert feat[120] == 0.0

    def test_play_phase(self):
        """出牌阶段 one-hot = [0, 1, 0]。"""
        feat = extract_static_features(_make_game_state(
            handCards=["S2", "H3"],
            curPos=0,
            actionList=[["S2"]]
        ))
        assert feat[118] == 0.0
        assert feat[119] == 1.0, "出牌阶段 dim 119 应为 1"
        assert feat[120] == 0.0


# ── 7. Bomb 计数 ──

class TestBombCount:
    def test_bomb_zero(self):
        """无炸弹时值为 0。"""
        feat = extract_static_features(_make_game_state(curBombNum=0))
        assert feat[121] == 0.0

    def test_bomb_five_overseven(self):
        """5 个炸弹归一化为 0.5。"""
        feat = extract_static_features(_make_game_state(curBombNum=5))
        assert abs(feat[121] - 0.5) < 1e-6

    def test_bomb_capped_at_ten(self):
        """炸弹数超过 10 时截断至 1.0。"""
        feat = extract_static_features(_make_game_state(curBombNum=15))
        assert feat[121] == 1.0


# ── 8. 贡局标志 ──

class TestTributeFlag:
    def test_tribute_flag_on(self):
        """有 tributeResult 时贡局标志为 1。"""
        feat = extract_static_features(_make_game_state(tributeResult=[["S2"]]))
        assert feat[122] == 1.0

    def test_tribute_flag_off(self):
        """无 tributeResult 时贡局标志为 0。"""
        feat = extract_static_features(_make_game_state())
        assert feat[122] == 0.0


# ── 9. Hand count ──

class TestHandCount:
    def test_hand_count_normalized(self):
        """手牌数归一化至 [0, 1]。"""
        feat = extract_static_features(_make_game_state(handCards=["S2", "H3"]))
        expected = 2.0 / 27.0
        assert abs(feat[123] - expected) < 1e-6

    def test_hand_count_empty(self):
        """空手牌计数为 0。"""
        feat = extract_static_features(_make_game_state(handCards=[]))
        assert feat[123] == 0.0


# ── 10. 全局归一化范围 ──

class TestNormalizedRange:
    def test_all_features_in_01(self):
        """所有特征值应在 [0, 1] 内。"""
        states = [
            _make_game_state(handCards=[]),
            _make_game_state(handCards=CARD_TYPES[:20], curBombNum=7, curRank="K"),
            _make_game_state(
                handCards=["BJ", "RJ", "H5", "S5", "S5"],
                curRank="5",
                tributeResult=[["S2"]],
                curBombNum=3,
            ),
            _make_game_state(
                handCards=CARD_TYPES[:27] + CARD_TYPES[:27],
                curBombNum=10,
            ),
        ]
        for i, s in enumerate(states):
            feat = extract_static_features(s)
            assert np.all(feat >= 0) and np.all(feat <= 1), f"状态 {i} 存在超出 [0,1] 的特征"


# ── 11. encode_hand_cards_108 单元测试 ──

class TestEncodeHandCards108:
    def test_zero_cards(self):
        """空列表全零。"""
        enc = encode_hand_cards_108([])
        assert len(enc) == 108
        assert all(v == 0.0 for v in enc)

    def test_one_each_type(self):
        """54 种牌各 1 张，每种前 1 维为 1。"""
        enc = encode_hand_cards_108(CARD_TYPES)
        assert len(enc) == 108
        for i in range(54):
            assert enc[i * 2] == 1.0, f"第 {i} 种牌 {CARD_TYPES[i]} 第一维"
            assert enc[i * 2 + 1] == 0.0, f"第 {i} 种牌 {CARD_TYPES[i]} 第二维"

    def test_two_each_of_first_10(self):
        """前 10 种牌各 2 张，对应 [1,1]。"""
        hand = CARD_TYPES[:10] * 2
        enc = encode_hand_cards_108(hand)
        for i in range(10):
            assert enc[i * 2] == 1.0 and enc[i * 2 + 1] == 1.0, f"第 {i} 种应为 [1,1]"
        for i in range(10, 54):
            assert enc[i * 2] == 0.0 and enc[i * 2 + 1] == 0.0, f"第 {i} 种应为 [0,0]"


# ── 12. Engine 集成测试（需 torch） ──

torch_available = False
try:
    import torch
    torch_available = True
except ImportError:
    pass


@pytest.mark.skipif(not torch_available, reason="需要 torch")
class TestEngineFeatureExtraction:
    def test_engine_output_512(self):
        """engine._extract_features 输出仍为 512 维（兼容旧模型）。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(handCards=["S2", "H3", "D5"], curPos=0)
        feat = engine._extract_features(gs, [["S2"]])
        assert feat is not None
        assert feat.shape == (512,), f"期望 512 维，实际 {feat.shape}"

    def test_engine_first_124_matches_static(self):
        """engine 输出的前 124 维应与静态特征一致。"""
        from src.decision.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
        engine = UltimateWinRateEngineV7(player_id=0)
        gs = _make_game_state(handCards=["S2", "BJ", "H5", "H5"], curRank="5", curBombNum=2)
        feat = engine._extract_features(gs, [["S2"]])
        static = extract_static_features(gs)
        assert np.allclose(feat[:124], static), "前 124 维应与静态特征一致"