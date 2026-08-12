#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动规则挖掘 discover_rule_candidates.py — b 路线（事后统计败招）v1 骨架

真源：docs/guandan-brain/自动规则挖掘-discover_rule_candidates-设计方案.md（v4.1）
路线：b（事后统计）+ A 定义（状态级「同情形」= 我方手牌规模 + greater 牌型 + 点数）

管线：
  ① 决策点切片（自对弈池 game_records_v8/*.json，默认 yf1_v8 视角，stage==play）
  ② A 状态键（handCards_size + greater 牌型 + 点数）分桶
  ③ 桶内动作聚类 → 名次/得分对比（victoryNum/order → 队名次）
  ④ 输出候选规则：同状态键下「动作 → 名次差异」显著的 bad_action

用法示例：
  python scripts/checks/discover_rule_candidates.py
  python scripts/checks/discover_rule_candidates.py --records game_records_v8 --player yf1_v8 --min-n 3
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# 队位映射：队 A = seat0+2（yf1/yf2_v8），队 B = seat1+3（yf3/yf4_v8）
_TEAM_OF_SEAT = {0: "A", 1: "B", 2: "A", 3: "B"}

_PLAY_ACT_NAMES = {"tribute", "back"}  # 非 play 阶段动作（须剔除）


def _is_pass(act) -> bool:
    if not act:
        return True
    return bool(act) and act[0] == "PASS"


def _cards_of_action(act) -> list:
    if not act:
        return []
    if isinstance(act, list) and len(act) >= 3 and isinstance(act[2], list):
        return [str(c) for c in act[2]]
    return [str(c) for c in act]


def _action_sig(act: list) -> tuple:
    """动作签名：牌型+点数（不含具体牌）。PASS 归一。"""
    if _is_pass(act):
        return ("PASS", None)
    return (act[0], act[1]) if len(act) >= 2 else (act[0], None)


def _team_rank(d: dict) -> int:
    """我方队名次（1=头游）。order = 出完顺序（index 0 先出完）。"""
    order = (d.get("result") or {}).get("order") or []
    if not order:
        return 0
    my_seat = int(d.get("player_id", 0))
    my_team = _TEAM_OF_SEAT[my_seat]
    team_seats = [i for i in range(4) if _TEAM_OF_SEAT[i] == my_team]
    # 名次 = 队内最先出完者的名次
    return min(order.index(s) for s in team_seats) + 1


def _team_score(d: dict) -> int:
    """我方队得分（victoryNum 两席之和；OpenGuanDan 记分口径）。"""
    vn = (d.get("result") or {}).get("victoryNum") or []
    if not vn:
        return 0
    my_seat = int(d.get("player_id", 0))
    my_team = _TEAM_OF_SEAT[my_seat]
    return sum(vn[i] for i in range(4) if _TEAM_OF_SEAT[i] == my_team)


def _split_tricks(actions: list[dict]) -> list[list[dict]]:
    """按领出点（greater_pos==-1 或 greater 为 PASS）切 trick，返回各 trick 的 action 子序列。"""
    tricks = []
    cur = None
    for a in actions:
        if a.get("cur_action") is None:
            continue
        ga = a.get("greater_action")
        if a.get("greater_pos") == -1 or (ga and ga[0] == "PASS"):
            if cur is not None:
                tricks.append(cur)
            cur = [a]
        else:
            if cur is None:
                cur = []
            cur.append(a)
    if cur:
        tricks.append(cur)
    return tricks


def _trick_control(trick: list[dict], my_team: str) -> tuple:
    """窗口结果：trick 最后一压（拿回牌权者）是否我方队。返回 (win_control, last_seat, lead_seat)。"""
    last_seat = None
    for a in trick:
        ca = a.get("cur_action")
        if ca and ca[0] != "PASS":
            last_seat = a["cur_pos"]
    lead_seat = trick[0]["cur_pos"] if trick else None
    win_control = (last_seat is not None and _TEAM_OF_SEAT[last_seat] == my_team)
    return win_control, last_seat, lead_seat


def slice_decision_points(d: dict, player: str | None = None):
    """① 决策点切片：以 actions 为真源（同 check_endgame_solver）。

    决策点 = actions 中 cur_pos==my_seat 且非 PASS 的条目（真实出牌），天然带 trick 归属。
    窗口结果 = 所在 trick 最后一压是否我方队（拿回牌权）。
    级牌 = my_decisions 首个非 None context.curRank（game_info.curRank 恒 "2" 不可信）。
    """
    if player and d.get("player_name") != player:
        return []
    my_seat = int(d.get("player_id", 0))
    my_team = _TEAM_OF_SEAT[my_seat]
    actions = d.get("actions") or []

    real_rank = (d.get("game_info") or {}).get("curRank", "2")
    for md in d.get("my_decisions") or []:
        cr = (md.get("context") or {}).get("curRank")
        if cr is not None:
            real_rank = str(cr)
            break

    out = []
    hand = Counter(str(c) for c in (d.get("initial_hand") or []))
    for trick in _split_tricks(actions):
        win_control, last_seat, lead_seat = _trick_control(trick, my_team)
        for a in trick:
            if a["cur_pos"] != my_seat:
                continue
            ca = a.get("cur_action")
            if not ca or ca[0] == "PASS":
                continue
            ga = a.get("greater_action")
            if ga and ga[0] != "PASS" and len(ga) >= 2:
                gt, gv = ga[0], ga[1]
            else:
                gt, gv = "LEAD", None
            hs = sum(hand.values())
            out.append({
                "ts": a.get("timestamp", ""),
                "action": ca,
                "action_sig": _action_sig(ca),
                "state_key": (hs, gt, gv),
                "hand_size": hs,
                "greater": ga,
                "trick_id": len(out),
                "win_control": win_control,
                "last_seat": last_seat,
                "lead_seat": lead_seat,
                "rank": _team_rank(d),
                "score": _team_score(d),
                "file": d.get("game_id", ""),
                "player": d.get("player_name", ""),
            })
            hand -= Counter(str(c) for c in _cards_of_action(ca))
    return out


def mine_bad_actions(points: list[dict], min_n: int = 3, ctrl_gap: float = 0.25,
                     include_lead: bool = False):
    """③④ 桶内动作 → 窗口结果（拿回牌权率）对比，产出 bad_action 候选。

    规则：同状态键桶内，某动作样本数>=min_n，且其拿回牌权率比桶内最优动作低 >= ctrl_gap。
    默认只挖跟压场景（greater != LEAD）——领出受手牌结构协变量影响，难以归因。
    """
    buckets = defaultdict(list)
    for p in points:
        key = p["state_key"]
        if not include_lead and key[1] == "LEAD":
            continue
        buckets[key].append(p)

    candidates = []
    for key, pts in buckets.items():
        by_act = defaultdict(list)
        for p in pts:
            by_act[p["action_sig"]].append(p["win_control"])
        # 只处理 >1 动作的桶（需对照）
        if len(by_act) < 2:
            continue
        # 统一门槛：候选动作与对照动作均须样本>=min_n
        eligible = {a: w for a, w in by_act.items() if len(w) >= min_n}
        if len(eligible) < 2:
            continue
        for act, wins in eligible.items():
            rate = sum(wins) / len(wins)
            best_act, best_wins = max(eligible.items(), key=lambda x: sum(x[1]) / len(x[1]))
            best_rate = sum(best_wins) / len(best_wins)
            if best_rate - rate >= ctrl_gap:
                candidates.append({
                    "state_key": key,
                    "bad_action": act,
                    "bad_n": len(wins),
                    "bad_control_rate": round(rate, 3),
                    "best_action": best_act,
                    "best_control_rate": round(best_rate, 3),
                    "bucket_n": len(pts),
                    "all_actions": {str(a): (len(w), round(sum(w) / len(w), 3))
                                    for a, w in by_act.items()},
                    "samples": [{"file": p["file"], "ts": p["ts"], "action": p["action"],
                                 "win_control": p["win_control"], "lead_seat": p["lead_seat"]}
                                for p in pts if p["action_sig"] == act][:5],
                })
    # 按拿回牌权率差距降序
    candidates.sort(key=lambda c: c["best_control_rate"] - c["bad_control_rate"], reverse=True)
    return candidates


def main() -> None:
    ap = argparse.ArgumentParser(description="自动规则挖掘（b 路线 v1）")
    ap.add_argument("--records", default="game_records_v8",
                    help="自对弈池牌谱目录（默认 game_records_v8）")
    ap.add_argument("--player", default="yf1_v8", help="视角（默认 yf1_v8；None=全视角）")
    ap.add_argument("--min-n", type=int, default=3, help="动作样本数下限（默认 3）")
    ap.add_argument("--ctrl-gap", type=float, default=0.25, help="拿回牌权率差距阈值（默认 0.25）")
    ap.add_argument("--lead", action="store_true",
                    help="也挖掘自由领出（LEAD）场景（默认只挖跟压场景）")
    ap.add_argument("--out", default="tmp/rule_candidates.json", help="输出路径")
    args = ap.parse_args()

    player = None if args.player.lower() == "none" else args.player
    files = sorted(glob.glob(str(ROOT / args.records / "*.json")))
    print(f"扫描 {len(files)} 个牌谱（{args.records}/*.json）")

    all_points = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        all_points.extend(slice_decision_points(d, player))

    print(f"决策点切片: {len(all_points)}（视角={player or 'all'}）")

    buckets = defaultdict(int)
    for p in all_points:
        buckets[p["state_key"]] += 1
    print(f"状态键数: {len(buckets)}")

    candidates = mine_bad_actions(all_points, min_n=args.min_n, ctrl_gap=args.ctrl_gap,
                                  include_lead=args.lead)
    print(f"\n候选 bad_action 规则: {len(candidates)} 个（min_n={args.min_n}"
          f" ctrl_gap={args.ctrl_gap} lead={'开' if args.lead else '关（只挖跟压）'}）")

    for i, c in enumerate(candidates[:15], 1):
        gap = c["best_control_rate"] - c["bad_control_rate"]
        print(f"\n[RC-{i:04d}] 状态键 hs={c['state_key'][0]} greater={c['state_key'][1]}[{c['state_key'][2]}]")
        print(f"  bad_action={c['bad_action']}  n={c['bad_n']}  拿回牌权率={c['bad_control_rate']}")
        print(f"  最佳对照={c['best_action']}  拿回牌权率={c['best_control_rate']}  差距={gap:.2f}")
        print(f"  桶内全部: {c['all_actions']}")

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        json.dump({
            "meta": {
                "source": args.records, "player": player, "min_n": args.min_n,
                "ctrl_gap": args.ctrl_gap, "decisions": len(all_points),
                "state_keys": len(buckets), "candidates": len(candidates),
            },
            "candidates": candidates,
        }, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n已写出 {out_path}")


if __name__ == "__main__":
    main()
