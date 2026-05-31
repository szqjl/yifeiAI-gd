#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit recorded greater_pos/greaterAction vs rule-recomputed trick winner."""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from communication.game_recorder import GameRecorder  # noqa: E402

RECORD_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)

# Single rank strength (higher wins); level card handled separately
RANK_VAL = {
    "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14, "2": 15, "B": 16, "R": 17,
}


def norm_level(s):
    s = str(s or "2").strip().upper()
    if s in ("10", "T"):
        return "T"
    if s == "1":
        return "A"
    return s


def action_type(action):
    if not action or not isinstance(action, list):
        return None
    return (action[0] or "").upper()


def single_strength(rank_char, level):
    """Approximate single strength for audit (level card > A, jokers on top)."""
    if rank_char in ("B", "R"):
        return RANK_VAL[rank_char]
    base = RANK_VAL.get(rank_char, 0)
    if rank_char == level:
        return 15.5  # between 2 and B
    return base


def beats_single(cur, prev, level):
    if action_type(cur) != "SINGLE" or action_type(prev) != "SINGLE":
        return None  # skip non-single compare
    cr = cur[1] if len(cur) > 1 else ""
    pr = prev[1] if len(prev) > 1 else ""
    return single_strength(cr, level) > single_strength(pr, level)


def resolve_cur_rank(data, filename):
    gi = data.get("game_info") or {}
    cur = gi.get("curRank")
    if not cur:
        for d in data.get("my_decisions") or []:
            cur = (d.get("context") or {}).get("curRank")
            if cur:
                break
    if not cur:
        for a in data.get("actions") or []:
            cur = (a.get("context") or {}).get("curRank")
            if cur:
                break
    m = RECORD_RE.match(filename)
    if (not cur or str(cur).lower() == "unknown") and m and m.group(5):
        cur = m.group(5)
    return norm_level(cur or "2")


def audit_file(path: Path):
    data = GameRecorder.load_game(path)
    level = resolve_cur_rank(data, path.name)
    actions = data.get("actions") or []

    stats = {
        "steps": len(actions),
        "non_pass": 0,
        "cur_eq_greater": 0,
        "pass_steps": 0,
        "single_compare": 0,
        "single_should_not_win": 0,  # played single but didn't beat prev greater
        "single_rec_greater_wrong": 0,  # above + recorded greater became cur
        "pos13_steps": 0,
        "pos13_single_wrong": 0,
        "examples": [],
    }

    comp_gpos = -1
    comp_gact = None
    pass_streak = 0

    for i, a in enumerate(actions):
        cpos = a.get("cur_pos", -1)
        cact = a.get("cur_action") or []
        gpos = a.get("greater_pos", -1)
        gact = a.get("greater_action") or []
        at = action_type(cact)

        if at == "PASS":
            stats["pass_steps"] += 1
            pass_streak += 1
            if pass_streak >= 3:
                comp_gpos, comp_gact = -1, None
                pass_streak = 0
            # recorded greater on PASS usually keeps trick winner
            continue

        pass_streak = 0
        stats["non_pass"] += 1
        if cpos == gpos:
            stats["cur_eq_greater"] += 1

        if cpos in (1, 3):
            stats["pos13_steps"] += 1

        prev_gact = comp_gact
        prev_gpos = comp_gpos

        if comp_gpos == -1 or comp_gact is None:
            # lead / new trick
            comp_gpos, comp_gact = cpos, cact
        else:
            won = beats_single(cact, comp_gact, level)
            if won is True:
                comp_gpos, comp_gact = cpos, cact
            elif won is False:
                # did not beat; computed greater unchanged
                if cpos in (1, 3):
                    stats["pos13_single_wrong"] += 1
                stats["single_should_not_win"] += 1
                if gpos == cpos and gact == cact:
                    stats["single_rec_greater_wrong"] += 1
                    if len(stats["examples"]) < 5:
                        stats["examples"].append({
                            "step": i + 1,
                            "cur_pos": cpos,
                            "cur": cact,
                            "prev_greater": prev_gact,
                            "rec_greater": gact,
                        })
            elif won is None:
                # non-single: assume server greater may be valid; adopt recorded if matches cur
                if gpos == cpos:
                    comp_gpos, comp_gact = cpos, cact

        if at == "SINGLE" and prev_gact and action_type(prev_gact) == "SINGLE":
            stats["single_compare"] += 1

    return stats


def main():
    files = sorted(
        [f for f in (REPO / "game_records").glob("*.json") if not f.name.startswith("enhanced_")],
        key=lambda p: p.name,
    )
    total = {
        "files": 0,
        "single_rec_greater_wrong": 0,
        "single_should_not_win": 0,
        "single_compare": 0,
        "non_pass": 0,
        "cur_eq_greater": 0,
        "pos13_single_wrong": 0,
    }
    per_file = []

    for f in files:
        st = audit_file(f)
        total["files"] += 1
        for k in total:
            if k != "files":
                total[k] += st[k]
        if st["single_rec_greater_wrong"]:
            m = RECORD_RE.match(f.name)
            per_file.append((st["single_rec_greater_wrong"], f.name, st["examples"][:2]))

    print("=== 仓库 game_records 审计（仅 yf1/yf2 客户端录制，无独立「玩家1/3 JSON」）===")
    print(f"文件数: {total['files']} (yf1×19 + yf2×19，同局各一份视角)")
    print()
    print("说明: JSON 里每一步的 greater 来自 notify 广播，四家共用同一条 greater；")
    print("      没有单独的「玩家1/玩家3 客户端 JSON」，只有 cur_pos=1/3 的出牌步。")
    print()
    np = total["non_pass"]
    ce = total["cur_eq_greater"]
    print(f"非 PASS 步数: {np}")
    print(f"  其中 cur_pos==greater_pos: {ce} ({100*ce/np:.1f}%)" if np else "")
    sc = total["single_compare"]
    sw = total["single_should_not_win"]
    wr = total["single_rec_greater_wrong"]
    print(f"单牌可比对步数: {sc}")
    print(f"  按规则压不过上一手 greater 的: {sw} ({100*sw/sc:.1f}%)" if sc else "")
    print(f"  且录制 greater 仍改成 cur 的(明确错发): {wr} ({100*wr/sc:.1f}%)" if sc else "")
    print(f"  其中 cur_pos 为 1 或 3 的: {total['pos13_single_wrong']}")
    print()
    print("=== 有错发示例的文件（单牌 greater 错改）===")
    per_file.sort(reverse=True)
    for n, name, ex in per_file[:8]:
        print(f"  {n}处  {name}")
        for e in ex:
            print(f"    step{e['step']} pos{e['cur_pos']} {e['cur']} 上一手{e['prev_greater']} -> 录成{e['rec_greater']}")
    if not per_file:
        print("  (无)")
    print()
    print("=== M3 实战是否读 JSON 里的 greater？===")
    print("  否。对战时 M3DecisionEngine 读 WebSocket act 的 greaterPos/greaterAction，")
    print("  并经 game_logic.trick_state.resolve_effective_greater 用 publicInfo.playArea 校正（GUA-027）。")
    print("  回放 yf_replay 对每步用 TrickSequenceTracker / playArea 重算「本圈最大(重算)」。")


if __name__ == "__main__":
    main()
