#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off batch report for GUA-022 / GUA-026 acceptance."""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)


def main():
    cutoff = None
    if len(sys.argv) > 1:
        cutoff = datetime.fromisoformat(sys.argv[1])
    else:
        es = ROOT / "execution_state.json"
        if es.exists():
            cutoff = datetime.fromisoformat(
                json.loads(es.read_text(encoding="utf-8"))["start_time"]
            )

    rows = []
    for fp in sorted((ROOT / "game_records").glob("*.json")):
        if cutoff and datetime.fromtimestamp(fp.stat().st_mtime) < cutoff:
            continue
        m = RECORD_RE.match(fp.name)
        if not m:
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        rows.append((fp, m, data))

    print(f"new_records={len(rows)}")
    match_keys = {(m.group(3), int(m.group(4)), m.group(5)) for _, m, _ in rows}
    print(f"unique_match_keys={len(match_keys)}")

    vn_vals = []
    for _, m, data in rows:
        vn = (data.get("result") or {}).get("victoryNum")
        if vn:
            vn_vals.append(tuple(vn))
    print(f"victoryNum_nonempty={len(vn_vals)}")
    if vn_vals:
        print("vn_distribution:", dict(Counter(vn_vals)))

    stats = defaultdict(
        lambda: {
            "decisions": 0,
            "pass": 0,
            "bomb": 0,
            "tw2": 0,
            "tw2_level": 0,
            "approx_pass": 0,
        }
    )
    for _, m, data in rows:
        player = m.group(2)
        pos = data.get("player_id")
        lvl = m.group(5) or "2"
        rank_card = "H" + str(lvl)
        for a in data.get("actions") or []:
            if a.get("cur_pos") != pos:
                continue
            cur = a.get("cur_action") or []
            at = cur[0] if cur else None
            s = stats[player]
            s["decisions"] += 1
            if at == "PASS":
                s["pass"] += 1
                al = a.get("action_list") or a.get("actionList") or []
                if any(isinstance(x, list) and x and x[0] != "PASS" for x in al[1:]):
                    s["approx_pass"] += 1
            elif at == "Bomb":
                s["bomb"] += 1
            elif at in ("ThreeWithTwo", "TripsPair"):
                s["tw2"] += 1
                cards = cur[2] if len(cur) > 2 else []
                if rank_card in cards or any(str(c).endswith(lvl) for c in cards):
                    s["tw2_level"] += 1

    for p in sorted(stats):
        s = stats[p]
        d = s["decisions"] or 1
        print(
            f"{p}: decisions={s['decisions']} pass={s['pass']} "
            f"({s['pass']/d*100:.1f}%) approx_pass={s['approx_pass']} "
            f"bomb={s['bomb']} tw2={s['tw2']} tw2_level={s['tw2_level']}"
        )

    # Per-batch session wins: round number drops back to 1 after a prior round > 1
    yf1_rows = []
    for fp in sorted((ROOT / "game_records").glob("*[yf1_m3]*.json")):
        if cutoff and datetime.fromtimestamp(fp.stat().st_mtime) < cutoff:
            continue
        m = RECORD_RE.match(fp.name)
        if not m:
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        vn = tuple((data.get("result") or {}).get("victoryNum") or ())
        yf1_rows.append((fp.stat().st_mtime, int(m.group(4)), vn))
    yf1_rows.sort()
    sessions = []
    cur = []
    prev_rnd = -1
    for ts, rnd, vn in yf1_rows:
        if rnd == 1 and prev_rnd > 1 and cur:
            sessions.append(cur)
            cur = []
        cur.append((rnd, vn))
        prev_rnd = rnd
    if cur:
        sessions.append(cur)
    batches = [s[-1][1] for s in sessions if s and len(s[-1][1]) == 4]
    if batches:
        m3_w = sum(vn[0] for vn in batches)
        opp_w = sum(vn[1] for vn in batches)
        total = m3_w + opp_w
        rate = (m3_w / total * 100) if total else 0.0
        print(
            f"batch_sessions={len(batches)} m3_wins={m3_w} opp_wins={opp_w} "
            f"total={total} m3_rate={rate:.1f}%"
        )
        for i, vn in enumerate(batches, 1):
            print(f"  batch{i}: vn={list(vn)} m3={vn[0]} opp={vn[1]}")

    es = ROOT / "execution_state.json"
    if es.exists():
        print("execution_state:", json.loads(es.read_text(encoding="utf-8")))
    lvn = ROOT / "batch_executor" / "latest_victory_num.json"
    if lvn.exists():
        print("latest_vn:", json.loads(lvn.read_text(encoding="utf-8")))
    cb = ROOT / "batch_executor" / "current_batch.json"
    if cb.exists():
        print("current_batch:", json.loads(cb.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
