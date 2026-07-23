# -*- coding: utf-8 -*-
"""GUA-166：主攻拆对扩 scope。

- 锚点：yf1_v8 在 `20260721160656059092` 步 18 有 ST-DT 对 + HA 百搭，但 role=主攻
  → GUA-157 拆对窗口不开 → 只能走 Single/HA 出百搭。
- 修复：把 `allow_assist_pair_borrow` 从 `role=="助攻"` 扩到 `role in {主攻,助攻,超强主攻}`；
  同时 `_heuristic_select` ⑩ 同步扩 scope。
- 主攻阈值严一档：对手 ≥T（rank value 8 = T）时主攻不借调，避免浪费 ST/T 同级压不过；
  助攻/超强主攻 5-T 全窗口。
"""

import pytest

from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

MAIN_ROLE = "主攻"
ASSIST_ROLE = "助攻"
SUPER_MAIN_ROLE = "超强主攻"


def _engine_with_tt(role=MAIN_ROLE, hand=None, include_wild=True, include_t=True):
    """构造 18 张手牌：有 TT 对 + 小散张。

    默认对手 Single/9（greater_val=7），TT 对拆 ST（T=8 > 7）可压。
    """
    if hand is None:
        hand = [
            ("ST" if include_t else "S3"), ("DT" if include_t else "D3"),
            "D3", "D4", "D5", "D6", "D7", "D8",
            "C3", "C4", "C5", "C6", "C7", "C8",
            "S3", "S4", "S5", "S6", "S7", "S8",
        ]
    hand = list(dict.fromkeys(hand))[:18]
    if include_wild and "HA" not in hand:
        hand.append("HA")
    hand = list(dict.fromkeys(hand))[:18]

    card_mask = {
        **{c: (-1, 0.0, 1) for c in hand if c not in ("ST", "DT")},
    }
    if include_t and "ST" in hand and "DT" in hand:
        card_mask["ST"] = (0, 0.0, 2)
        card_mask["DT"] = (0, 0.0, 2)
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {0: "pair"} if include_t else {}
    engine._group_members = {
        -1: [c for c in hand if c not in ("ST", "DT")],
    }
    if include_t and "ST" in hand and "DT" in hand:
        engine._group_members[0] = ["ST", "DT"]
    engine._current_role = role
    return engine, hand


def _state(engine, hand, greater_rank="9", greater_card="D9"):
    return {
        "myPos": 0,
        "greaterPos": 3,
        "greaterAction": ["Single", greater_rank, [greater_card]],
        "handCards": hand,
        "curRank": "A",
    }


def _min_press(engine, hand, **kw):
    state = _state(engine, hand, **kw)
    return engine._recommend_min_press_impl(
        state,
        engine._card_mask,
        state["greaterAction"],
        "Single",
        hand,
        "A",
    )


# ── 例 1：主攻 + 对手 9 + TT 对 + 无 natural 可压 → 拆 T 出 ST ──
def test_gua166_main_attack_borrows_t_pair_vs_9():
    """GUA-166 主攻拆对核心场景：对手 Single/9 + 主攻 + TT 对 + 无散张 natural 可压 → 出 ST。"""
    engine, hand = _engine_with_tt(role=MAIN_ROLE, include_wild=False)
    rec = _min_press(engine, hand)
    assert rec is not None, "GUA-166 主攻应能拆 TT 对出 ST 压 9"
    assert rec["cards"][0] in ("ST", "DT"), f"应出 ST/DT，实际 {rec}"
    assert rec["rank"] == "T", f"应出 rank=T，实际 {rec}"


# ── 例 2：主攻 + 对手 T + 无 wild + TT 对 → 主攻严一档不借调（PASS） ──
def test_gua166_main_attack_skips_pair_borrow_vs_t():
    """主攻严一档：对手 ≥T + 无 wild 可压 + TT 对 → 不借调 → return None（PASS 让道）。

    ST=T 同级压不过 T（同级不赢），严一档阻止拆对；散张都 ≤9 < T，
    无 natural 可压 → 走 GUA-165 让出 / 上游 PASS。
    """
    engine, hand = _engine_with_tt(role=MAIN_ROLE, include_wild=False, include_t=True)
    rec = _min_press(engine, hand, greater_rank="T", greater_card="DT")
    # 主攻 + 对手 T：borrow_window={"5-9"}，T 不在 → 不借调
    # 散张都 ≤9 < T(=8)，无 natural 可压 → return None
    assert rec is None, (
        f"GUA-166 主攻严一档：对手 T 时不借调且无 natural 可压 → 让出 return None；"
        f"实际 {rec}"
    )


# ── 例 3：主攻 + 对手 9 + 无 99/TT/JJ 对（只有 KK/AA）→ GUA-165 让出 ──
def test_gua166_main_attack_no_borrowable_pair_yields():
    """主攻 + 对手 9 + 无 9/TT/JJ 可拆对（只有 KK/AA）→ GUA-165 让出 return None。

    KK/AA 不在 9/TT/JJ 借调窗口，且 AA is_core=1 不拆。
    """
    hand = [
        "SK", "DK",           # KK 对（不在 9/TT/JJ 窗口）
        "S4", "D4",           # 4 散张（4 < 9 不能压）
        "D3", "D5", "D6", "D7", "D8",
        "C3", "C4", "C5", "C6", "C7", "C8",
        "S3", "S5", "S6", "S7", "S8",
    ]
    hand = list(dict.fromkeys(hand))[:18]
    card_mask = {
        **{c: (-1, 0.0, 1) for c in hand if c not in ("SK", "DK")},
        "SK": (0, 0.0, 2),
        "DK": (0, 0.0, 2),
    }
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {0: "pair"}
    engine._group_members = {
        -1: [c for c in hand if c not in ("SK", "DK")],
        0: ["SK", "DK"],
    }
    engine._current_role = MAIN_ROLE
    rec = _min_press(engine, hand)
    # KK 不在 9/TT/JJ 借调窗口 → has_borrowable_pair=False → GUA-165 让出 return None
    assert rec is None, f"无可借调对时 GUA-165 应让出，实际 {rec}"


# ── 例 4：GUA-157 兼容 —— 助攻 + 对手 9 + TT 对 → 拆 T（GUA-157 5-T 窗口） ──
def test_gua166_assist_keeps_gua157_5_to_t_window():
    """助攻 + 对手 9 + TT 对 → 拆 T（GUA-157 5-T 窗口仍生效）。

    主攻也用 5-T 窗口（GUA-157 助攻窗口），与 GUA-166 主攻 5-9 严一档区分。
    """
    engine, hand = _engine_with_tt(role=ASSIST_ROLE, include_wild=False)
    rec = _min_press(engine, hand, greater_rank="9", greater_card="D9")
    # 助攻 + 对手 9：borrow_window={5-T}，9 在 → 借调
    assert rec is not None, "助攻 5-T 窗口 GUA-157 应能拆对"
    assert rec["cards"][0] in ("ST", "DT"), f"应出 ST/DT，实际 {rec}"
    assert rec["rank"] == "T"


# ── 例 5：残局放行 —— 主攻 8 张 + 仅有 TT 对 + 对手 9 → 仍拆对 ──
def test_gua166_endgame_main_attack_still_borrows_pair():
    """残局 last=8 → GUA-165 wild-guard 放行（≤10 张）；主攻也能拆对。"""
    hand = [
        "ST", "DT",
        "D3", "D4", "D5", "D6", "D7",
    ]
    hand = list(dict.fromkeys(hand))[:8]
    card_mask = {
        **{c: (-1, 0.0, 1) for c in hand if c not in ("ST", "DT")},
        "ST": (0, 0.0, 2),
        "DT": (0, 0.0, 2),
    }
    engine = UltimateWinRateEngineV7(player_id=0)
    engine._card_mask = card_mask
    engine._group_type_map = {0: "pair"}
    engine._group_members = {
        -1: [c for c in hand if c not in ("ST", "DT")],
        0: ["ST", "DT"],
    }
    engine._current_role = MAIN_ROLE
    rec = _min_press(engine, hand)
    # 8 张残局：GUA-165 不触发（≤10），主攻 + TT 对 + 对手 9 → GUA-166 拆 T 出 ST
    assert rec is not None, "残局主攻仍可拆对"
    assert rec["cards"][0] in ("ST", "DT")
    assert rec["rank"] == "T"
