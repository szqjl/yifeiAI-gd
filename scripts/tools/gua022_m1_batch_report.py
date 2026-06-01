#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M1/M3 batch acceptance report (GUA-022)."""

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


def _cutoff():
    es = ROOT / "execution_state.json"
    if es.exists():
        return datetime.fromisoformat(
            json.loads(es.read_text(encoding="utf-8"))["start_time"]
        )
    return None


def _session_last_files(player_tag: str, cutoff):
    all_rows = []
    for fp in sorted((ROOT / "game_records").glob("*.json")):
        if cutoff and datetime.fromtimestamp(fp.stat().st_mtime) < cutoff:
            continue
        m = RECORD_RE.match(fp.name)
        if not m:
            continue
        all_rows.append((int(m.group(4)), m.group(2), fp))
    sessions, cur, prev = [], [], -1
    for rnd, player, fp in all_rows:
        if rnd == 1 and prev > 1 and cur:
            sessions.append(cur)
            cur = []
        cur.append((player, fp))
        prev = rnd
    if cur:
        sessions.append(cur)
    ends = []
    for sess in sessions:
        tagged = [fp for pl, fp in sess if player_tag in pl]
        if tagged:
            ends.append(tagged[-1])
    return ends


def _count_decisions(fp, player_tag):
    data = json.loads(fp.read_text(encoding="utf-8"))
    pos = data.get("player_id")
    out = dict(dec=0, pass_n=0, approx=0, bomb=0)
    for a in data.get("actions") or []:
        if a.get("cur_pos") != pos:
            continue
        cur = a.get("cur_action") or []
        at = cur[0] if cur else None
        out["dec"] += 1
        if at == "PASS":
            out["pass_n"] += 1
            al = a.get("action_list") or a.get("actionList") or []
            if any(isinstance(x, list) and x and x[0] != "PASS" for x in al[1:]):
                out["approx"] += 1
        elif at == "Bomb":
            out["bomb"] += 1
    return out


def main():
    player_tag = sys.argv[1] if len(sys.argv) > 1 else "yf1_m1"
    teammate = "yf2_m1" if "yf1" in player_tag else "yf1_m1"
    cutoff = _cutoff()

    ends = _session_last_files(player_tag, cutoff)
    batches = []
    for fp in ends:
        data = json.loads(fp.read_text(encoding="utf-8"))
        vn = tuple((data.get("result") or {}).get("victoryNum") or ())
        if len(vn) == 4:
            batches.append(vn)

    stats = {player_tag: dict(dec=0, pass_n=0, approx=0, bomb=0),
             teammate: dict(dec=0, pass_n=0, approx=0, bomb=0)}
    for tag in stats:
        for fp in _session_last_files(tag, cutoff):
            c = _count_decisions(fp, tag)
            for k in stats[tag]:
                stats[tag][k] += c[k]

    es = json.loads((ROOT / "execution_state.json").read_text(encoding="utf-8"))
    print(f"target={es['target_games']} completed={es['completed_games']} "
          f"restart_count={es.get('restart_count')}")
    if batches:
        m3_w = sum(vn[0] for vn in batches)
        opp_w = sum(vn[1] for vn in batches)
        total = m3_w + opp_w
        print(f"batch_sessions={len(batches)} team_a_wins={m3_w} team_b_wins={opp_w} "
              f"total={total} team_a_rate={m3_w/total*100:.1f}%")
        for i, vn in enumerate(batches, 1):
            print(f"  batch{i}: vn={list(vn)} team_a={vn[0]} team_b={vn[1]}")
    for tag, s in stats.items():
        d = s["dec"] or 1
        print(f"{tag}: dec={s['dec']} pass={s['pass_n']/d*100:.1f}% "
              f"approx_pass={s['approx']} bomb={s['bomb']}")


if __name__ == "__main__":
    main()
