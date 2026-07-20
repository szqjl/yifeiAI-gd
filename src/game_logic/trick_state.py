# -*- coding: utf-8 -*-
"""本圈最大动作（greater）解析：playArea 重算 + 与消息字段交叉校验。

GUA-027：M3 被动决策与回放共用，避免盲信 notify/act 中错误的 greaterPos/greaterAction。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

RANK_VAL = {
    "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14, "2": 2, "B": 16, "R": 17,
}


def norm_level(cur_rank: Any) -> str:
    s = str(cur_rank or "2").strip().upper()
    if s in ("10", "T"):
        return "T"
    if s == "1":
        return "A"
    return s


def normalize_action(action: Any) -> List:
    if isinstance(action, (list, tuple)):
        return list(action)
    if isinstance(action, str):
        try:
            import ast
            parsed = ast.literal_eval(action)
            if isinstance(parsed, (list, tuple)):
                return list(parsed)
        except Exception:
            pass
    return []


def action_type(action: Any) -> Optional[str]:
    act = normalize_action(action)
    if not act:
        return None
    return str(act[0] or "").upper() or None


def rank_value(rank_char: Any, cur_rank: str) -> float:
    r = str(rank_char or "").upper()
    if r in ("B", "R"):
        return float(RANK_VAL[r])
    level = norm_level(cur_rank)
    if r == level:
        return 15.5
    return float(RANK_VAL.get(r, 0))


def actions_equal(a: Any, b: Any) -> bool:
    aa = normalize_action(a)
    bb = normalize_action(b)
    if len(aa) != len(bb):
        return False
    if not aa and not bb:
        return True
    if aa and bb and aa[0] != bb[0]:
        return False
    if len(aa) > 1 and aa[1] != bb[1]:
        return False
    if len(aa) > 2:
        ca = aa[2] if isinstance(aa[2], list) else []
        cb = bb[2] if isinstance(bb[2], list) else []
        return sorted(ca) == sorted(cb)
    return True


def action_beats(challenger: Any, defender: Any, cur_rank: Any) -> Optional[bool]:
    """challenger 是否压过 defender；None 表示无法比较（不同类型且无炸弹压制）。"""
    ct = action_type(challenger)
    dt = action_type(defender)
    if not ct or not dt or ct == "PASS" or dt == "PASS":
        return None

    bomb_types = {"BOMB", "STRAIGHTFLUSH"}
    if ct in bomb_types and dt not in bomb_types:
        return True
    if dt in bomb_types and ct not in bomb_types:
        return False

    if ct != dt:
        return None

    ca = normalize_action(challenger)
    da = normalize_action(defender)
    if len(ca) < 2 or len(da) < 2:
        return None

    if ct == "BOMB":
        cc = ca[2] if len(ca) > 2 and isinstance(ca[2], list) else []
        dc = da[2] if len(da) > 2 and isinstance(da[2], list) else []
        if len(cc) != len(dc):
            return len(cc) > len(dc)

    return rank_value(ca[1], cur_rank) > rank_value(da[1], cur_rank)


def leader_from_play_areas(
    public_info: Any,
    cur_rank: Any,
) -> Tuple[int, Optional[List]]:
    """从 act/notify 的 publicInfo 中取本圈 playArea 最大一手。"""
    level = norm_level(cur_rank)
    best_pos = -1
    best_act = None
    if not isinstance(public_info, list):
        return best_pos, best_act

    for i, info in enumerate(public_info):
        if not isinstance(info, dict):
            continue
        pa = info.get("playArea")
        if pa is None:
            continue
        act = normalize_action(pa)
        at = action_type(act)
        if not at or at == "PASS":
            continue
        if best_act is None or action_beats(act, best_act, level) is True:
            best_pos, best_act = i, act
    return best_pos, best_act


def resolve_effective_greater(
    cur_pos: Any = -1,
    cur_action: Any = None,
    greater_pos: Any = -1,
    greater_action: Any = None,
    public_info: Any = None,
    cur_rank: Any = "2",
) -> Dict[str, Any]:
    """解析本圈有效 greater；返回 beat_action 供被动 dispatch 比牌。"""
    level = norm_level(cur_rank)
    cur_action_n = normalize_action(cur_action)
    greater_action_n = normalize_action(greater_action)

    try:
        msg_gpos = int(greater_pos)
    except (TypeError, ValueError):
        msg_gpos = -1

    msg_gact = greater_action_n if action_type(greater_action_n) not in (None, "PASS") else None
    pa_pos, pa_act = leader_from_play_areas(public_info, level)

    eff_pos = msg_gpos
    eff_act = msg_gact
    source = "msg"
    corrected = False

    if pa_act is not None:
        if msg_gact is None:
            eff_pos, eff_act, source = pa_pos, pa_act, "playArea"
            corrected = msg_gpos != pa_pos
        elif action_beats(pa_act, msg_gact, level) is True:
            eff_pos, eff_act, source = pa_pos, pa_act, "playArea"
            corrected = not (msg_gpos == pa_pos and actions_equal(msg_gact, pa_act))
        elif actions_equal(pa_act, msg_gact):
            eff_pos, eff_act, source = pa_pos, pa_act, "playArea"
            corrected = msg_gpos != pa_pos
        else:
            # playArea 与 msg 不一致且 msg 更强：仍优先桌面 playArea（v1006 act 真源）
            eff_pos, eff_act, source = pa_pos, pa_act, "playArea"
            corrected = not (msg_gpos == pa_pos and actions_equal(msg_gact, pa_act))

    if eff_act is None and action_type(cur_action_n) not in (None, "PASS"):
        eff_act = cur_action_n
        if eff_pos < 0 and cur_pos is not None:
            try:
                eff_pos = int(cur_pos)
            except (TypeError, ValueError):
                pass

    beat_action = eff_act
    if beat_action is None or action_type(beat_action) in (None, "PASS"):
        if action_type(greater_action_n) not in (None, "PASS"):
            beat_action = greater_action_n
        elif action_type(cur_action_n) not in (None, "PASS"):
            beat_action = cur_action_n
        else:
            beat_action = greater_action_n or cur_action_n or ["PASS", "", "PASS"]

    return {
        "greater_pos": eff_pos,
        "greater_action": eff_act or greater_action_n,
        "beat_action": beat_action,
        "source": source,
        "corrected": corrected,
    }


class TrickSequenceTracker:
    """按出牌流水重算本圈最大（用于无 playArea 的录制回放）。"""

    def __init__(self, cur_rank: Any = "2"):
        self.cur_rank = norm_level(cur_rank)
        self.leader_pos = -1
        self.leader_action = None
        self.pass_streak = 0

    def reset_trick(self):
        self.leader_pos = -1
        self.leader_action = None
        self.pass_streak = 0

    def apply(self, cur_pos: Any, cur_action: Any):
        act = normalize_action(cur_action)
        at = action_type(act)
        if at == "PASS":
            self.pass_streak += 1
            if self.pass_streak >= 3:
                self.reset_trick()
            return

        self.pass_streak = 0
        try:
            pos = int(cur_pos)
        except (TypeError, ValueError):
            return

        if self.leader_action is None:
            self.leader_pos, self.leader_action = pos, act
            return

        if action_beats(act, self.leader_action, self.cur_rank) is True:
            self.leader_pos, self.leader_action = pos, act

    def snapshot(self) -> Dict[str, Any]:
        return {
            "greater_pos": self.leader_pos,
            "greater_action": self.leader_action or [],
        }


def resolve_for_recorded_action(action: Dict[str, Any], tracker: TrickSequenceTracker) -> Dict[str, Any]:
    """对录制的一步：先按 tracker 模拟本步出牌后的本圈最大，再与录制 greater 比对。"""
    ctx = action.get("context") or {}
    level = norm_level(ctx.get("curRank") or tracker.cur_rank)
    public_info = ctx.get("publicInfo")

    pa_pos, pa_act = leader_from_play_areas(public_info, level)
    if pa_act is not None:
        post_pos, post_act = pa_pos, pa_act
        source = "playArea"
    else:
        sim = TrickSequenceTracker(level)
        sim.leader_pos = tracker.leader_pos
        sim.leader_action = tracker.leader_action
        sim.pass_streak = tracker.pass_streak
        sim.apply(action.get("cur_pos"), action.get("cur_action"))
        post = sim.snapshot()
        post_pos = post["greater_pos"]
        post_act = post["greater_action"] or None
        source = "tracker"

    rec_gpos = action.get("greater_pos", -1)
    rec_gact = action.get("greater_action")
    corrected = not (
        rec_gpos == post_pos and actions_equal(rec_gact, post_act)
    )
    return {
        "greater_pos": post_pos,
        "greater_action": post_act or [],
        "beat_action": post_act or rec_gact or [],
        "source": source,
        "corrected": corrected,
    }
