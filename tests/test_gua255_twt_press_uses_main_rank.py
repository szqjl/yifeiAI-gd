# -*- coding: utf-8 -*-
"""GUA-255: _recommend_min_press_impl 对 ThreeWithTwo 取 greater_cards[0]（带牌）算牌力，
导致用 666+KK 压 777+55 的推荐被 actionList 拒（PASS），真正可压的 JJJ+KK 从未考虑。

背景（2026-08-20，match=6a86911a0fbd680d7c7c284b L370-377）：
  上家 player3 打 TWT/7 (C5 H7 D5 S7 C7)，V8=player0 手牌含 666+44、JJJ+KK 与双炸。
  日志 L374：GUA-075 推荐 rec={type=ThreeWithTwo rank=6 cards=['C6','D6','H6','HK','SK']}
  → actionList 无匹配（666 压不过 777）→ 回退 PASS，且 L376 前置过滤移除 3/5 拆核心动作。
  根因：greater_val 用 greater_cards[0]=C5（带牌，value=3）而非主牌 7（value=5），
  _build_three_with_two_press 找 rank>3 的三张 → 666（rank>3 满足），本应找 rank>5 的 JJJ。
"""
import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7


def _engine(hand_cards, card_mask=None, group_type_map=None, group_members=None):
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask or {c: (-1, 0.0, 1) for c in hand_cards}
    engine._group_type_map = group_type_map or {}
    engine._group_members = group_members or {}
    engine._current_role = "超强主攻"
    return engine


def test_twt_press_uses_main_rank_not_scatter_card():
    """TWT/7 (C5 H7 D5 S7 C7) 跟压：greater_val 应为主牌 7 而非带牌 C5，
    推荐结果必须为 rank>7 的三带二（JJJ 而非 666）。"""
    hand = ["C6", "D6", "H6", "HK", "SK", "CJ", "DJ", "HJ", "C4", "S4"]
    greater = ["ThreeWithTwo", "7", ["C5", "H7", "D5", "S7", "C7"]]
    engine = _engine(hand)
    rec = engine._recommend_min_press_impl(
        {"handCards": hand, "curRank": "2"},
        engine._card_mask,
        greater,
        "ThreeWithTwo",
        hand,
        "2",
    )
    assert rec is not None, "手牌 JJJ+KK/666+KK 应能推荐三带二压 TWT/7"
    assert rec["type"] == "ThreeWithTwo"
    # 主牌必须 > 7（不能用 666 去压 777）→ 应为 J（JJJ+44，min 策略中 JJJ 是
    # 手牌里唯一主牌>7 的三张；666 被正确排除）
    assert rec["rank"] in ("T", "J", "Q", "K", "A"), \
        f"推荐主牌 {rec['rank']} 应大于 7；实际 rec={rec}"


def test_twt_press_min_strategy_picks_smallest_pressable():
    """能压 TWT/7 的最小三带二是 888（若手牌有 888+xx），保持 min 策略。"""
    hand = ["C8", "D8", "H8", "C4", "S4", "CJ", "DJ", "HJ", "HK", "SK"]
    greater = ["ThreeWithTwo", "7", ["C5", "H7", "D5", "S7", "C7"]]
    engine = _engine(hand)
    rec = engine._recommend_min_press_impl(
        {"handCards": hand, "curRank": "2"},
        engine._card_mask,
        greater,
        "ThreeWithTwo",
        hand,
        "2",
    )
    assert rec is not None
    assert rec["type"] == "ThreeWithTwo"
    assert rec["rank"] == "8", f"min 策略应选 888；实际 rec={rec}"


def test_twt_press_no_bigger_trip_returns_none():
    """手牌无主牌>7 的三张 → 无同型可压 → 返回 None（回退，勿推荐更小 TWT）。"""
    hand = ["C6", "D6", "H6", "C4", "S4", "HK", "SK"]
    greater = ["ThreeWithTwo", "7", ["C5", "H7", "D5", "S7", "C7"]]
    engine = _engine(hand)
    rec = engine._recommend_min_press_impl(
        {"handCards": hand, "curRank": "2"},
        engine._card_mask,
        greater,
        "ThreeWithTwo",
        hand,
        "2",
    )
    assert rec is None, "666 压不过 777，不应推荐"