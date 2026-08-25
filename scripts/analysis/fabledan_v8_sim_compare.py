# -*- coding: utf-8 -*-
"""FableDan engine vs V8 botzone_adapter 规则对照实验（step-b）。

从 FableDan 自对弈中采样真实决策点，对比：
  1) 合法着法数量与牌型直方图
  2) 抽象签名集合差集（平台牌型名 + 张数 + 比较键）
  3) beats() 语义一致性（同手牌转换后的 V8 action 对）

用法（仓库根目录）：
    python scripts/analysis/fabledan_v8_sim_compare.py
    python scripts/analysis/fabledan_v8_sim_compare.py --episodes 20 --seed 7 --json-out tmp/fd_v8_compare.json

真源记录：docs/reasearch/fabledan-train-demo-样本观测.md §6
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_REPO = Path(__file__).resolve().parents[2]
_FABLE = _REPO / "external" / "FableDan"
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_FABLE) not in sys.path:
    sys.path.insert(0, str(_FABLE))

from fabledan.combos import (  # noqa: E402
    PASS,
    ROCKET,
    STRAIGHT,
    SFLUSH,
    TYPE_NAMES,
    beats as fd_beats,
    gen_moves,
)
from fabledan.engine import play_round  # noqa: E402
from fabledan.agents import RandomAgent  # noqa: E402
from fabledan.cards import RANK_NAMES as FD_RANK_NAMES  # noqa: E402

from src.communication.botzone_adapter import (  # noqa: E402
    ActionListGenerator,
    bz_to_v8_card,
    _rank_to_order,
)

# FableDan level index 0..12 -> V8 cur_rank
FD_LEVEL_TO_V8 = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K"]

FD_TYPE_TO_V8 = {
    "PASS": "PASS",
    "SINGLE": "Single",
    "PAIR": "Pair",
    "TRIPLE": "Trips",
    "FULL": "ThreeWithTwo",
    "STRAIGHT": "Straight",
    "PLATE": "ThreePair",
    "TUBE": "TwoTrips",
    "BOMB": "Bomb",
    "SFLUSH": "StraightFlush",
    "ROCKET": "Rocket",
}


def fd_rank_to_v8(rank_idx: int) -> str:
    if rank_idx == 13:
        return "B"
    if rank_idx == 14:
        return "R"
    return FD_LEVEL_TO_V8[rank_idx]


def level_v8(lv: int) -> str:
    return FD_LEVEL_TO_V8[lv]


def hand_bz_to_v8(hand: List[int]) -> List[str]:
    return [bz_to_v8_card(c) for c in hand]


def fd_move_sig(move, lv: int) -> Tuple[str, int, int]:
    """粗签名：(平台牌型, 张数, 比较键 int)。"""
    tname = TYPE_NAMES[move.type]
    if move.type == PASS:
        return ("PASS", 0, 0)
    v8t = FD_TYPE_TO_V8[tname]
    size = move.size
    key = int(move.key)
    if tname == "ROCKET":
        return ("Rocket", size, 99)
    return (v8t, size, key)


def v8_action_sig(action: list, cur_rank: str, gen: ActionListGenerator) -> Tuple[str, int, int]:
    t = action[0] if action else ""
    if t == "PASS":
        return ("PASS", 0, 0)
    cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else []
    size = len(cards)
    rank = action[1] if len(action) >= 2 else ""
    if t in ("Straight", "StraightFlush") and cards:
        key = gen._straight_top_order(cards, cur_rank)
    else:
        key = _rank_to_order(rank, cur_rank)
    if t == "Bomb" and size == 4 and _is_four_jokers(cards):
        return ("Rocket", size, 99)
    return (t, size, key)


def _is_four_jokers(cards: List[str]) -> bool:
    if len(cards) != 4:
        return False
    ranks = {c[1:] if len(c) > 2 else c[1] for c in cards}
    return ranks <= {"B", "R"} and len(ranks) == 2


def v8_beats(action: list, greater: list, cur_rank: str) -> bool:
    """与 botzone_adapter.BotzoneAdapter._beats 同语义（裁判 checkBigger）。"""
    t1, r1 = action[0], action[1] if len(action) >= 2 else ""
    t2, r2 = greater[0], greater[1] if len(greater) >= 2 else ""

    def _bomb_count(a: list) -> int:
        cards = a[2] if len(a) >= 3 and isinstance(a[2], list) else []
        return len(cards)

    if t1 not in ("Bomb", "StraightFlush"):
        if t2 in ("Bomb", "StraightFlush"):
            return False
    else:
        if t2 not in ("Bomb", "StraightFlush"):
            return True
        if t1 == "Bomb" and t2 == "Bomb":
            a_cnt, g_cnt = _bomb_count(action), _bomb_count(greater)
            if a_cnt != g_cnt:
                return a_cnt > g_cnt
            return _rank_to_order(r1, cur_rank) > _rank_to_order(r2, cur_rank)
        if t1 == "StraightFlush" and t2 == "Bomb":
            return _bomb_count(greater) < 6
        if t1 == "Bomb" and t2 == "StraightFlush":
            return _bomb_count(action) >= 6
    if t1 == t2:
        if t1 in ("Straight", "StraightFlush"):
            a_cards = (action[2]
                       if len(action) >= 3 and isinstance(action[2], list) else [])
            g_cards = (greater[2]
                       if len(greater) >= 3 and isinstance(greater[2], list) else [])
            if a_cards and g_cards:
                return (ActionListGenerator._straight_top_order(a_cards, cur_rank)
                        > ActionListGenerator._straight_top_order(g_cards, cur_rank))
        return _rank_to_order(r1, cur_rank) > _rank_to_order(r2, cur_rank)
    return False


def fd_move_to_v8_action(move, cur_rank: str) -> list:
    """尽力将 FableDan Move 转为 V8/OpenGuanDan action 三元组。"""
    if move.type == PASS:
        return ["PASS", "PASS", "PASS"]
    v8_type = FD_TYPE_TO_V8[TYPE_NAMES[move.type]]
    cards = hand_bz_to_v8(move.cards)
    if move.type == ROCKET:
        return ["Bomb", "R", cards]
    if move.type in (STRAIGHT, SFLUSH):
        low_rank = fd_rank_to_v8(move.claim_ranks[0]) if move.claim_ranks else "2"
        return [v8_type, low_rank, cards]
    if move.type == PASS:
        return ["PASS", "PASS", "PASS"]
    pr = move.claim_ranks[0] if move.claim_ranks else 0
    rank = fd_rank_to_v8(pr)
    return [v8_type, rank, cards]


@dataclass
class ScenarioDiff:
    episode: int
    step: int
    player: int
    level: int
    leading: bool
    hand_size: int
    n_fd: int
    n_v8: int
    type_hist_fd: Dict[str, int]
    type_hist_v8: Dict[str, int]
    fd_only: List[str] = field(default_factory=list)
    v8_only: List[str] = field(default_factory=list)
    beats_checked: int = 0
    beats_mismatch: int = 0


@dataclass
class CompareReport:
    episodes: int
    decision_points: int
    skipped_singleton: int
    count_match: int
    count_mismatch: int
    sig_exact_match: int
    beats_checked: int
    beats_mismatch: int
    mismatch_examples: List[Dict[str, Any]] = field(default_factory=list)
    scenario_diffs: List[ScenarioDiff] = field(default_factory=list)


def _type_hist(sigs: Set[Tuple[str, int, int]]) -> Dict[str, int]:
    c: Counter[str] = Counter()
    for t, _, _ in sigs:
        c[t] += 1
    return dict(c)


def compare_obs(episode: int, step: int, obs: dict) -> Optional[ScenarioDiff]:
    lv = obs["level"]
    cur = level_v8(lv)
    gen = ActionListGenerator(cur_rank=cur)
    hand_v8 = hand_bz_to_v8(obs["hand"])
    lead = obs.get("lead")
    leading = lead is None or lead.type == PASS

    fd_moves = obs["legal"]
    if leading:
        v8_moves = gen.generate_lead_actions(hand_v8)
    else:
        lead_v8 = fd_move_to_v8_action(lead, cur)
        v8_moves = gen.generate_follow_actions(hand_v8, lead_v8)

    fd_sigs = {fd_move_sig(m, lv) for m in fd_moves}
    v8_sigs = {v8_action_sig(a, cur, gen) for a in v8_moves}

    fd_only = sorted(f"{a}|{b}|{c}" for a, b, c in sorted(fd_sigs - v8_sigs))[:8]
    v8_only = sorted(f"{a}|{b}|{c}" for a, b, c in sorted(v8_sigs - fd_sigs))[:8]

    beats_checked = 0
    beats_mismatch = 0
    if not leading and lead is not None:
        for m in fd_moves:
            if m.type == PASS:
                continue
            beats_checked += 1
            fd_ok = fd_beats(m, lead, lv)
            mv_v8 = fd_move_to_v8_action(m, cur)
            lead_v8 = fd_move_to_v8_action(lead, cur)
            v8_ok = v8_beats(mv_v8, lead_v8, cur)
            if fd_ok != v8_ok:
                beats_mismatch += 1

    return ScenarioDiff(
        episode=episode,
        step=step,
        player=obs["player"],
        level=lv,
        leading=leading,
        hand_size=len(obs["hand"]),
        n_fd=len(fd_moves),
        n_v8=len(v8_moves),
        type_hist_fd=_type_hist(fd_sigs),
        type_hist_v8=_type_hist(v8_sigs),
        fd_only=fd_only,
        v8_only=v8_only,
        beats_checked=beats_checked,
        beats_mismatch=beats_mismatch,
    )


class _CollectAgent:
    """包装 RandomAgent，在 act 时记录 obs。"""

    def __init__(self, inner, buf: list):
        self.inner = inner
        self.buf = buf

    def act(self, obs):
        if len(obs["legal"]) >= 2:
            self.buf.append(obs)
        return self.inner.act(obs)


def collect_decision_points(episodes: int, seed: int) -> List[dict]:
    rng = random.Random(seed)
    out: List[dict] = []
    for ep in range(episodes):
        buf: List[dict] = []
        agents = [
            _CollectAgent(RandomAgent(rng.getrandbits(48)), buf)
            for _ in range(4)
        ]
        play_round(agents, rng=random.Random(rng.getrandbits(48)))
        out.extend(buf)
    return out


def run_compare(episodes: int, seed: int, max_examples: int) -> CompareReport:
    points = collect_decision_points(episodes, seed)
    diffs: List[ScenarioDiff] = []
    count_match = 0
    sig_exact = 0
    beats_checked = 0
    beats_mismatch = 0
    examples: List[Dict[str, Any]] = []

    for i, obs in enumerate(points):
        ep = i // max(1, len(points) // max(episodes, 1))
        d = compare_obs(ep, i + 1, obs)
        if d is None:
            continue
        diffs.append(d)
        if d.n_fd == d.n_v8:
            count_match += 1
        if not d.fd_only and not d.v8_only:
            sig_exact += 1
        beats_checked += d.beats_checked
        beats_mismatch += d.beats_mismatch
        if (d.fd_only or d.v8_only or d.beats_mismatch) and len(examples) < max_examples:
            examples.append(asdict(d))

    return CompareReport(
        episodes=episodes,
        decision_points=len(diffs),
        skipped_singleton=0,
        count_match=count_match,
        count_mismatch=len(diffs) - count_match,
        sig_exact_match=sig_exact,
        beats_checked=beats_checked,
        beats_mismatch=beats_mismatch,
        mismatch_examples=examples,
        scenario_diffs=diffs,
    )


def _print_summary(r: CompareReport) -> None:
    print("=== FableDan vs V8 ActionListGenerator 对照 ===")
    print(f"episodes={r.episodes}  decision_points={r.decision_points}")
    print(f"count 一致: {r.count_match}/{r.decision_points}  "
          f"({100 * r.count_match / max(r.decision_points, 1):.1f}%)")
    print(f"签名集合完全一致: {r.sig_exact_match}/{r.decision_points}  "
          f"({100 * r.sig_exact_match / max(r.decision_points, 1):.1f}%)")
    print(f"beats 抽检: {r.beats_checked}  不一致: {r.beats_mismatch}")
    if r.mismatch_examples:
        print("\n--- 差异样例（最多 %d 条）---" % len(r.mismatch_examples))
        for ex in r.mismatch_examples[:5]:
            print(
                f"  ep~{ex['episode']} step={ex['step']} p={ex['player']} "
                f"lv={FD_LEVEL_TO_V8[ex['level']]} lead={ex['leading']} "
                f"n_fd={ex['n_fd']} n_v8={ex['n_v8']} "
                f"beats_mm={ex['beats_mismatch']}"
            )
            if ex["fd_only"]:
                print(f"    fd_only: {ex['fd_only'][:4]}")
            if ex["v8_only"]:
                print(f"    v8_only: {ex['v8_only'][:4]}")


def main() -> None:
    ap = argparse.ArgumentParser(description="FableDan vs V8 规则枚举对照")
    ap.add_argument("--episodes", type=int, default=15,
                    help="FableDan 自对弈副数（采样决策点）")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-examples", type=int, default=12,
                    help="JSON 中保留的差异样例数")
    ap.add_argument("--json-out", default="",
                    help="可选：写出完整报告 JSON")
    args = ap.parse_args()

    report = run_compare(args.episodes, args.seed, args.max_examples)
    _print_summary(report)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "episodes": report.episodes,
            "decision_points": report.decision_points,
            "count_match": report.count_match,
            "count_mismatch": report.count_mismatch,
            "sig_exact_match": report.sig_exact_match,
            "beats_checked": report.beats_checked,
            "beats_mismatch": report.beats_mismatch,
            "mismatch_examples": report.mismatch_examples,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"\nJSON -> {out_path}")


if __name__ == "__main__":
    main()
