#!/usr/bin/env python3
"""WF-12: align actions[step-1] -> my_decisions entry (internal test harness)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def action_key(action: Any) -> Optional[tuple]:
    """Normalize platform action for equality (type, rank, sorted cards)."""
    if not isinstance(action, list) or not action:
        return None
    typ = str(action[0]).upper()
    rank = str(action[1]).upper() if len(action) > 1 else ""
    cards_raw = action[2] if len(action) > 2 and isinstance(action[2], list) else []
    return (typ, rank, tuple(sorted(str(c).upper() for c in cards_raw)))


def is_play_decision(decision: Dict[str, Any]) -> bool:
    """Exclude tribute/back notify decisions from play-turn sequence."""
    ctx = decision.get("context") or {}
    stage = ctx.get("stage")
    if stage in ("tribute", "back"):
        return False
    if stage == "play":
        return True
    return stage is None and ctx.get("source") == "act"


def find_decision_at_step(
    game_data: Dict[str, Any], step_num: int
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Map 1-based step number in actions[] to the matching my_decisions entry.

    Raises ValueError when step is out of range, wrong seat, or alignment fails.
    """
    actions: List[Dict[str, Any]] = game_data.get("actions") or []
    player_id = game_data.get("player_id")
    if player_id is None:
        raise ValueError("game_data missing player_id")
    if step_num < 1 or step_num > len(actions):
        raise ValueError(f"step {step_num} out of range 1..{len(actions)}")

    play = actions[step_num - 1]
    cur_pos = play.get("cur_pos")
    if cur_pos != player_id:
        raise ValueError(
            f"step {step_num} cur_pos={cur_pos} != player_id={player_id}; "
            "choose a step where the analysis subject acted"
        )

    turn_idx = sum(1 for a in actions[:step_num] if a.get("cur_pos") == player_id) - 1
    play_decisions = [d for d in game_data.get("my_decisions") or [] if is_play_decision(d)]
    if turn_idx >= len(play_decisions):
        raise ValueError(
            f"no play my_decisions[{turn_idx}] "
            f"(have {len(play_decisions)} play entries, need turn #{turn_idx + 1})"
        )

    decision = play_decisions[turn_idx]
    expected_key = action_key(play.get("cur_action"))
    if action_key(decision.get("action")) != expected_key:
        matches = [
            i
            for i, d in enumerate(play_decisions)
            if action_key(d.get("action")) == expected_key
        ]
        if len(matches) == 1:
            decision = play_decisions[matches[0]]
        else:
            raise ValueError(
                f"ordinal/action mismatch at step {step_num}: "
                f"cur_action={play.get('cur_action')!r}, "
                f"ordinal_decision={decision.get('action')!r}, "
                f"action_key_matches={matches}"
            )

    return decision, play


def main() -> None:
    yf2_path = REPO / (
        "game_records_v7/20260701175356193021 "
        "[yf2_v7]-[opponent_1_3]-[36]-[2].json"
    )
    data = json.loads(yf2_path.read_text(encoding="utf-8"))
    dec, _ = find_decision_at_step(data, 37)
    ctx = dec["context"]
    assert ctx["curRank"] == "Q"
    assert ctx["handCards_size"] == 20
    assert dec["action"][:2] == ["ThreeWithTwo", "T"]
    print("yf2 step 37 OK", ctx["curRank"], ctx["handCards_size"])

    ok = fail = 0
    for fp in (REPO / "game_records_v7").glob("*yf1_v7*.json"):
        g = json.loads(fp.read_text(encoding="utf-8"))
        pid = g.get("player_id")
        for i, act in enumerate(g.get("actions") or []):
            if act.get("cur_pos") != pid:
                continue
            try:
                find_decision_at_step(g, i + 1)
                ok += 1
            except ValueError:
                fail += 1
    print(f"yf1_v7 batch: ok={ok} fail={fail}")


if __name__ == "__main__":
    main()
