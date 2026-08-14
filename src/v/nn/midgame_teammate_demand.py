# -*- coding: utf-8 -*-
"""GUA-234 中期队友需求感知（观测层，§3.5.4）

设计真源：docs/guandan-brain/V8-中期压顺灵活性-组牌-动态重组方案.md
本模块只产出 demand / feed_P / 强信号标志，不改组牌、不强改出牌。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Sequence, Set, Tuple

FEED_TYPES = ("Single", "Pair", "Trips", "Straight", "ThreeWithTwo")
PHASE_TYPES = ("Straight", "ThreeWithTwo", "Pair")

RANK_ORDER = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14, "B": 16, "R": 17,
}

# 牌力档位门禁（方案 §二）
TIER_SUPER = "超强牌"
TIER_STRONG_PLUS = "强牌+"
TIER_STRONG = "强牌"
TIER_STRONG_MINUS = "强牌-"
TIER_WEAK = "超弱牌"


def resolve_power_gate_tier(
    score_tier: Optional[str],
    role: Optional[str],
) -> str:
    """将 score_tier + role 映射为动态组牌门禁档；冲突取更保守（偏不启用）。"""
    by_score = {
        "天胡": TIER_SUPER,
        "好牌": TIER_STRONG_PLUS,
        "尚可": TIER_STRONG,
        "偏弱": TIER_STRONG_MINUS,
        "烂牌": TIER_WEAK,
    }.get(score_tier or "", None)
    by_role = {
        "超强主攻": TIER_SUPER,
        "主攻": TIER_STRONG,  # 上沿/下沿粗分：默认「强牌」；强牌+靠 score
        "助攻": TIER_STRONG_MINUS,
        "超弱": TIER_WEAK,
    }.get(role or "", None)

    order = [TIER_SUPER, TIER_STRONG_PLUS, TIER_STRONG, TIER_STRONG_MINUS, TIER_WEAK]
    candidates = [t for t in (by_score, by_role) if t is not None]
    if not candidates:
        return TIER_STRONG  # 未知时允许动态组牌（中性）
    # 更保守 = 更靠前（超强最保守：不启用）
    return min(candidates, key=lambda t: order.index(t))


def dynamic_regroup_enabled(tier: str) -> bool:
    """超强牌关闭动态重组；其余档开启（观测/后续重组）。"""
    return tier != TIER_SUPER


def _norm_type(action: Any) -> Optional[str]:
    if not action:
        return None
    if isinstance(action, str):
        t = action
    elif isinstance(action, (list, tuple)) and action:
        t = str(action[0])
    else:
        return None
    if t in ("PASS", "pass", "tribute", "back"):
        return "PASS" if t.lower() == "pass" or t == "PASS" else None
    if t == "ThreeWithTwo":
        return "ThreeWithTwo"
    if t in FEED_TYPES or t in ("Bomb", "StraightFlush", "TwoTrips", "ThreePair", "FourKings"):
        return t
    return t


def _action_rank(action: Any) -> Optional[str]:
    if isinstance(action, (list, tuple)) and len(action) >= 2:
        r = action[1]
        if r and str(r) != "PASS":
            return str(r)
    return None


def _rank_val(rank: Optional[str]) -> int:
    if not rank:
        return 0
    return RANK_ORDER.get(str(rank), 0)


def _is_top_twt(action: Any) -> bool:
    """顶档 TWT：三头为 A，或带牌点为 A（经典到顶）。"""
    t = _norm_type(action)
    if t != "ThreeWithTwo":
        return False
    rank = _action_rank(action)
    if rank == "A":
        return True
    cards = []
    if isinstance(action, (list, tuple)) and len(action) >= 3 and isinstance(action[2], list):
        cards = action[2]
    # 带对：后两张同点且为 A
    if len(cards) >= 5:
        k1, k2 = str(cards[-2])[1:], str(cards[-1])[1:]
        if k1 == "A" and k2 == "A":
            return True
    return False


@dataclass
class PlayEvent:
    seat: int
    role: str  # self / teammate / enemy
    pattern: str
    rank: Optional[str] = None
    raw: Any = None
    is_pass: bool = False


@dataclass
class MidgameTeammateDemandTracker:
    """本副累计的队友需求观测器。"""

    recent: Deque[PlayEvent] = field(default_factory=lambda: deque(maxlen=64))
    play_count: Dict[str, int] = field(default_factory=dict)
    opponent_consecutive: Dict[str, int] = field(default_factory=dict)
    teammate_pass_on_sequence: Dict[str, int] = field(default_factory=dict)
    _active_opp_type: Optional[str] = None
    _opp_streak: int = 0
    _history_synced: int = 0

    twt_topped_out: bool = False
    twt_pressed_unreclaimed: bool = False
    straight_pressed_unreclaimed: bool = False

    def reset(self) -> None:
        self.recent.clear()
        self.play_count.clear()
        self.opponent_consecutive.clear()
        self.teammate_pass_on_sequence.clear()
        self._active_opp_type = None
        self._opp_streak = 0
        self._history_synced = 0
        self.twt_topped_out = False
        self.twt_pressed_unreclaimed = False
        self.straight_pressed_unreclaimed = False

    def _role_of(self, seat: int, my_pos: int) -> str:
        if seat == my_pos:
            return "self"
        if seat == (my_pos + 2) % 4:
            return "teammate"
        return "enemy"

    def observe(
        self,
        seat: int,
        action: Any,
        my_pos: int,
        *,
        is_pass: bool = False,
    ) -> None:
        pattern = "PASS" if is_pass else (_norm_type(action) or "PASS")
        if pattern is None:
            return
        role = self._role_of(int(seat), int(my_pos))
        ev = PlayEvent(
            seat=int(seat),
            role=role,
            pattern=pattern if pattern != "PASS" else "PASS",
            rank=_action_rank(action) if not is_pass else None,
            raw=action,
            is_pass=(is_pass or pattern == "PASS"),
        )
        self.recent.append(ev)

        if role == "teammate" and not ev.is_pass and ev.pattern in FEED_TYPES:
            self.play_count[ev.pattern] = self.play_count.get(ev.pattern, 0) + 1

        if role == "enemy" and not ev.is_pass and ev.pattern in FEED_TYPES:
            if self._active_opp_type == ev.pattern:
                self._opp_streak += 1
            else:
                self._active_opp_type = ev.pattern
                self._opp_streak = 1
                self.teammate_pass_on_sequence[ev.pattern] = 0
            self.opponent_consecutive[ev.pattern] = self._opp_streak
        elif role == "enemy" and (ev.is_pass or ev.pattern not in FEED_TYPES):
            # 敌方换型/PASS：连续同型重置
            self._active_opp_type = None
            self._opp_streak = 0
        elif role == "teammate" and ev.is_pass and self._active_opp_type and self._opp_streak >= 2:
            t = self._active_opp_type
            self.teammate_pass_on_sequence[t] = self.teammate_pass_on_sequence.get(t, 0) + 1
        elif role in ("self", "teammate") and not ev.is_pass:
            # 我方或队友接管 → 连续同型序列中断
            self._active_opp_type = None
            self._opp_streak = 0

        self._refresh_strong_signals()

    def sync_from_play_history(
        self,
        play_history: Sequence[Dict[str, Any]],
        my_pos: int,
    ) -> None:
        """增量同步 MemoryTracker.play_history（仅追加未消费条目）。"""
        if not play_history:
            return
        n = len(play_history)
        if self._history_synced > n:
            self._history_synced = 0
        for entry in play_history[self._history_synced :]:
            seat = entry.get("seat")
            if seat is None:
                continue
            action = entry.get("action") or entry.get("cards")
            atype = entry.get("action_type") or entry.get("type")
            if action is None and atype:
                action = [atype, entry.get("rank") or "PASS", entry.get("cards") or []]
            if atype and str(atype).lower() == "pass":
                self.observe(int(seat), ["PASS", "PASS", "PASS"], my_pos, is_pass=True)
            elif action:
                self.observe(int(seat), action, my_pos)
        self._history_synced = n

    def _refresh_strong_signals(self) -> None:
        events = list(self.recent)
        self.twt_topped_out = self._detect_twt_top_reclaim(events)
        self.twt_pressed_unreclaimed = (
            False if self.twt_topped_out else self._detect_twt_unreclaimed(events)
        )
        self.straight_pressed_unreclaimed = self._detect_straight_unreclaimed(events)

    def _detect_twt_top_reclaim(self, events: List[PlayEvent]) -> bool:
        # teammate small TWT → enemy bigger TWT → teammate top TWT
        for i, ev in enumerate(events):
            if ev.role != "teammate" or ev.pattern != "ThreeWithTwo" or ev.is_pass:
                continue
            if _is_top_twt(ev.raw):
                continue
            low_rank = _rank_val(ev.rank)
            for j in range(i + 1, len(events)):
                mid = events[j]
                if mid.role != "enemy" or mid.pattern != "ThreeWithTwo" or mid.is_pass:
                    continue
                if _rank_val(mid.rank) <= low_rank:
                    continue
                for k in range(j + 1, len(events)):
                    top = events[k]
                    if top.role != "teammate" or top.pattern != "ThreeWithTwo" or top.is_pass:
                        continue
                    if _is_top_twt(top.raw) or _rank_val(top.rank) >= _rank_val("A"):
                        return True
                    break
                break
        return False

    def _detect_twt_unreclaimed(self, events: List[PlayEvent]) -> bool:
        for i, ev in enumerate(events):
            if ev.role != "teammate" or ev.pattern != "ThreeWithTwo" or ev.is_pass:
                continue
            if _is_top_twt(ev.raw):
                continue
            low_rank = _rank_val(ev.rank)
            for j in range(i + 1, len(events)):
                mid = events[j]
                if mid.role != "enemy" or mid.pattern != "ThreeWithTwo" or mid.is_pass:
                    continue
                if _rank_val(mid.rank) <= low_rank:
                    continue
                # 之后队友未用更大 TWT 接回，而是 PASS（或再也没有更大 TWT）
                saw_bigger = False
                saw_pass = False
                for k in range(j + 1, len(events)):
                    later = events[k]
                    if later.role == "teammate" and later.pattern == "ThreeWithTwo" and not later.is_pass:
                        if _rank_val(later.rank) > _rank_val(mid.rank) or _is_top_twt(later.raw):
                            saw_bigger = True
                            break
                    if later.role == "teammate" and later.is_pass:
                        saw_pass = True
                        break
                if saw_pass and not saw_bigger:
                    return True
                break
        return False

    def _detect_straight_unreclaimed(self, events: List[PlayEvent]) -> bool:
        for i, ev in enumerate(events):
            if ev.role != "teammate" or ev.pattern != "Straight" or ev.is_pass:
                continue
            low_rank = _rank_val(ev.rank)
            for j in range(i + 1, len(events)):
                mid = events[j]
                if mid.role != "enemy" or mid.pattern != "Straight" or mid.is_pass:
                    continue
                if _rank_val(mid.rank) <= low_rank:
                    continue
                saw_bigger = False
                saw_pass = False
                for k in range(j + 1, len(events)):
                    later = events[k]
                    if later.role == "teammate" and later.pattern == "Straight" and not later.is_pass:
                        if _rank_val(later.rank) > _rank_val(mid.rank):
                            saw_bigger = True
                            break
                    if later.role == "teammate" and later.is_pass:
                        saw_pass = True
                        break
                if saw_pass and not saw_bigger:
                    return True
                break
        return False

    def demand(self, pattern: str) -> float:
        """草案 demand(T)；强信号在 compute_feed_P 覆盖。"""
        total_lead = sum(self.play_count.get(t, 0) for t in FEED_TYPES) or 1
        lead_freq = self.play_count.get(pattern, 0) / total_lead
        pass_pen = 1.0 if self.teammate_pass_on_sequence.get(pattern, 0) >= 2 else 0.0
        score = 0.5 * lead_freq - 0.4 * pass_pen
        if pattern == "ThreeWithTwo" and self.twt_topped_out:
            score -= 0.5
        if pattern == "Straight" and self.twt_topped_out:
            score += 0.3
        if pattern == "Straight" and self.twt_pressed_unreclaimed:
            score += 0.4
        if pattern == "ThreeWithTwo" and self.twt_pressed_unreclaimed:
            score -= 0.2
        if pattern in ("ThreeWithTwo", "Trips") and self.straight_pressed_unreclaimed:
            score += 0.3
        return score

    def raw_main(self) -> Optional[str]:
        scores = {t: self.demand(t) for t in FEED_TYPES}
        best = max(scores, key=lambda t: scores[t])
        if scores[best] < 0.05 and self.play_count.get(best, 0) == 0:
            return None
        return best

    def apply_phase_gate(self, raw_main: Optional[str]) -> Set[str]:
        """§3.5.4.1 相位门 → 喂牌集合 P。"""
        if not raw_main:
            return set()
        if raw_main == "Straight":
            cnt = self.play_count.get("Straight", 0)
            return {"Straight"} if cnt <= 3 else {"Single", "Pair"}
        if raw_main == "ThreeWithTwo":
            cnt = self.play_count.get("ThreeWithTwo", 0)
            return {"ThreeWithTwo"} if cnt <= 3 else {"Trips", "Single", "Pair"}
        if raw_main == "Pair":
            cnt = self.play_count.get("Pair", 0)
            return {"Pair"} if cnt <= 3 else {"Single"}
        return {raw_main}

    def apply_strong_signal_overrides(self, p: Set[str]) -> Set[str]:
        """§3.5.4.2–4.4 覆盖相位门结果。"""
        out = set(p)
        if self.twt_topped_out:
            out.discard("ThreeWithTwo")
            out |= {"Straight", "Single", "Pair"}
        if self.twt_pressed_unreclaimed and not self.twt_topped_out:
            out.discard("ThreeWithTwo")
            out |= {"Straight", "Single", "Pair"}
        if self.straight_pressed_unreclaimed:
            # 勿因出过顺忌夯
            out |= {"ThreeWithTwo", "Trips"}
        return out

    def compute_feed_P(self, teammate_remaining: Optional[int] = None) -> Optional[List[str]]:
        """返回中期喂牌优先列表；残局 1–5 返回 None（交 assist_prefer_for）。"""
        if teammate_remaining is not None and 1 <= int(teammate_remaining) <= 5:
            return None
        main = self.raw_main()
        p = self.apply_phase_gate(main)
        p = self.apply_strong_signal_overrides(p)
        # 稳定优先序
        order = ["Straight", "ThreeWithTwo", "Trips", "Pair", "Single"]
        return [t for t in order if t in p]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "play_count": dict(self.play_count),
            "demand": {t: round(self.demand(t), 4) for t in FEED_TYPES},
            "raw_main": self.raw_main(),
            "twt_topped_out": self.twt_topped_out,
            "twt_pressed_unreclaimed": self.twt_pressed_unreclaimed,
            "straight_pressed_unreclaimed": self.straight_pressed_unreclaimed,
            "teammate_pass_on_sequence": dict(self.teammate_pass_on_sequence),
            "opponent_consecutive": dict(self.opponent_consecutive),
        }
