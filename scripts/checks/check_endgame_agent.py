# -*- coding: utf-8 -*-
"""
残局智能体独立调试脚本（Endgame Agent Debug Tool）
===================================================

用途：在不启动完整对战的情况下，独立调试 EndgamePreprocessor + EndgameDecider。

用法：
    # ① 独立模式：给定手牌+剩余张数，展示完整 Q0→Q3 决策 trace
    python scripts/checks/check_endgame_agent.py --hand H2,H2,S2,D2,CA,HA,SA,CK --rank 2 --players 8,3,12,10 --pos 0

    # ② 扫描模式：扫描 game_records_v7，统计残局覆盖率
    python scripts/checks/check_endgame_agent.py --scan

    # ③ 单记录模式：从 game_record JSON 中抽取残局快照
    python scripts/checks/check_endgame_agent.py --record game_records_v7/xxx.json [--step 5]

输出：
    - 独立模式：残局上下文 + Q0→Q3 决策 trace + 命中的 action
    - 扫描模式：激活率 / Q0-Q3 各命中率 / 各 Q 级样本数
    - 记录模式：指定步的残局上下文 + 决策结果
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# 确保 src/ 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from v.nn.endgame.endgame_preprocessor import (
    EndgamePreprocessor, endgame_rule, BAOSHU_RULE,
)
from v.nn.endgame.endgame_decide import EndgameDecider

# ── Guard 工具 ──
try:
    from src.v.nn.guards.v7_guards import (
        get_action_type, get_card_value,
        CARD_RANK_ORDER,
    )
    GUARD_TOOLS_OK = True
except ImportError:
    GUARD_TOOLS_OK = False

# ═══════════════════════════════════════════════════════
#  常量
# ═══════════════════════════════════════════════════════

_SEP = "=" * 72
_SEP2 = "-" * 72


def _rank_key(r: str) -> int:
    """rank → 数值（便于排序）。"""
    return CARD_RANK_ORDER.get(r, 0) if GUARD_TOOLS_OK else {
        "2":0,"3":1,"4":2,"5":3,"6":4,"7":5,"8":6,"9":7,"T":8,"J":9,"Q":10,"K":11,"A":12
    }.get(r, 0)


# ═══════════════════════════════════════════════════════
#  Mock actionList 生成器
# ═══════════════════════════════════════════════════════

def _rank_cards(hand_cards: List[str]) -> Dict[str, List[str]]:
    """hand_cards → {rank: [cards]}。"""
    groups: Dict[str, List[str]] = {}
    for c in hand_cards:
        r = c[1] if len(c) >= 2 and c[0] in "SHDC" else c
        groups.setdefault(r, []).append(c)
    return groups


def _generate_mock_actions(hand_cards: List[str], cur_rank: str) -> List[List]:
    """从手牌生成简化 actionList（覆盖核心牌型）。"""
    rank_groups = _rank_cards(hand_cards)
    actions: List[List] = []
    all_cards = list(hand_cards)

    # ① 单张
    for c in all_cards:
        r = c[1] if len(c) >= 2 and c[0] in "SHDC" else c
        actions.append(["Single", r, [c]])

    # ② 对子（≥2 张）
    for r, cards in rank_groups.items():
        if len(cards) >= 2:
            actions.append(["Pair", r, cards[:2]])

    # ③ 三张 / 炸弹
    for r, cards in rank_groups.items():
        if len(cards) >= 3:
            actions.append(["Trips", r, cards[:3]])
        if len(cards) >= 4:
            actions.append(["Bomb", r, cards[:4]])

    # ④ 顺子（5 张连续）
    sorted_ranks = sorted(rank_groups.keys(), key=_rank_key)
    for i in range(len(sorted_ranks) - 4):
        window = sorted_ranks[i:i+5]
        vals = [_rank_key(r) for r in window]
        if vals[-1] - vals[0] == 4 and vals == list(range(vals[0], vals[0]+5)):
            cards = [rank_groups[r][0] for r in window]
            if len(cards) == 5:
                actions.append(["Straight", window[0], cards])

    # ⑤ 三带二
    trips_ranks = [r for r, cs in rank_groups.items() if len(cs) >= 3]
    pair_ranks = [r for r, cs in rank_groups.items() if len(cs) >= 2 and r not in trips_ranks]
    if trips_ranks and pair_ranks:
        t, p = trips_ranks[0], pair_ranks[0]
        actions.append(["ThreeWithTwo", t, rank_groups[t][:3] + rank_groups[p][:2]])

    return actions


# ═══════════════════════════════════════════════════════
#  输出格式化
# ═══════════════════════════════════════════════════════

def _fmt_env(enemies: Dict, teammate: Dict, self_ctx: Dict) -> None:
    """打印残局环境摘要。"""
    print(f"\n  {'残局环境':─^66s}")
    print(f"  {'位置':<6s} {'剩余':>4s} {'危险等级':<8s} {'推荐牌型':<24s} {'禁止牌型'}")
    for pos, e in sorted(enemies.items()):
        rec = ", ".join(e.get("recommended_types", [])) or "—"
        ban = ", ".join(e.get("banned_types", [])) or "—"
        bs = e.get("baoshu", {})
        if bs:
            ban += f"  [BAOSHU never_play: {', '.join(bs.get('never_play', []))}]"
            rec += f"  [block_with: {', '.join(bs.get('block_with', []))}]"
        print(f"  敌{pos:<5} {e.get('remaining',27):4d}  {e.get('danger_level','—'):<8s} {rec:<24s} {ban}")
    if teammate:
        prefer = ", ".join(teammate.get("assist_prefer", [])) or "—"
        print(f"  队友    {teammate.get('remaining',27):4d}  —        assist_prefer: {prefer}")
    s = self_ctx
    print(f"  自己    {s.get('remaining',27):4d}  两手整牌={s.get('has_two_clean_hands',False)} "
          f"有炸={s.get('has_bomb',False)} 冲刺={s.get('should_sprint',False)}")


def _fmt_actions(actions: List, max_show: int = 30) -> None:
    """打印 actionList 摘要。"""
    print(f"\n  {'actionList 候选 (共 %d)' % len(actions):─^66s}")
    for i, a in enumerate(actions[:max_show]):
        atype = get_action_type(a) if GUARD_TOOLS_OK else (a[0] if a else "?")
        cards = a[2] if len(a) >= 3 and isinstance(a[2], list) else (a if isinstance(a, list) else [])
        print(f"  [{i:3d}] {atype:<14s} {' '.join(str(c) for c in cards)[:40]}")
    if len(actions) > max_show:
        print(f"  ... 还有 {len(actions)-max_show} 个")


def _fmt_decision_trace(result: Tuple, action_list: List) -> None:
    """打印决策 trace。"""
    idx, act = result
    if idx is None:
        print(f"\n  {'决策结果':─^66s}")
        print("  ✗ 残局未命中 → 回退上游管线")
        return
    atype = get_action_type(act) if GUARD_TOOLS_OK else (act[0] if act else "?")
    cards = act[2] if len(act) >= 3 and isinstance(act[2], list) else act
    print(f"\n  {'决策结果':─^66s}")
    print(f"  ✓ 命中  idx={idx}  type={atype}")
    print(f"    cards: {' '.join(str(c) for c in cards)}")


# ═══════════════════════════════════════════════════════
#  Mode 1: 独立模式
# ═══════════════════════════════════════════════════════

def run_standalone(args) -> None:
    """独立模式：给定手牌+四家张数，展示 Q0→Q3 决策 trace。"""
    hand = [h.strip() for h in args.hand.split(",") if h.strip()]
    rank = args.rank
    players = [int(p.strip()) for p in args.players.split(",") if p.strip()]
    my_pos = args.pos
    cur_pos = args.curpos if args.curpos is not None else my_pos

    if len(players) != 4:
        print(f"错误: --players 需要 4 个数（如 8,3,12,10），得到 {len(players)} 个")
        sys.exit(1)

    print(f"\n{_SEP}")
    print(f"  残局智能体独立调试")
    print(f"{_SEP}")
    print(f"  手牌 ({len(hand)} 张): {' '.join(hand)}")
    print(f"  级牌: {rank}    我的位置: {my_pos}    当前出牌权: {cur_pos}")
    print(f"  四家剩余: {players}")

    # ── 构建 game_state ──
    game_state: Dict[str, Any] = {
        "myPos": my_pos,
        "curPos": cur_pos,
        "curRank": rank,
        "numofplayers": players,
        "handCards": hand,
        "actionList": _generate_mock_actions(hand, rank),
    }

    # ── ① 预处理器 ──
    ep = EndgamePreprocessor()
    game_state = ep.preprocess(game_state)
    ec = game_state.get("_endgame_context", {})

    print(f"\n  is_active: {ec.get('is_active', False)}")

    if not ec.get("is_active"):
        print("  ✗ 没有玩家进入残局区（≤10 张），智能体不激活")
        _fmt_actions(game_state["actionList"])
        return

    _fmt_env(ec.get("enemies", {}), ec.get("teammate", {}), ec.get("self", {}))

    # ── ② Decider ──
    action_list = game_state["actionList"]
    _fmt_actions(action_list)

    print(f"\n{_SEP2}")
    print(f"  Q0→Q3 决策流程")
    print(f"{_SEP2}")

    decider = EndgameDecider()
    filtered, is_empty = decider.apply_banned_filter(action_list, game_state)
    if is_empty:
        print("  ⚠ banned 硬排后 actionList 为空 → L3 降级")
    elif len(filtered) < len(action_list):
        print(f"  banned 过滤: {len(action_list)} → {len(filtered)} (移除 {len(action_list)-len(filtered)} 个)")
    else:
        print(f"  banned 过滤: 无 banned 类型需要排除")

    result = decider.decide(game_state, filtered if not is_empty else action_list)
    _fmt_decision_trace(result, action_list)

    # ── ③ 对手规则一览 ──
    print(f"\n{_SEP2}")
    print(f"  对手规则参考")
    print(f"{_SEP2}")
    for pos in range(4):
        if pos == my_pos:
            continue
        rem = players[pos]
        if rem <= 10:
            rule = endgame_rule.get(rem, ("低", [], []))
            bs = BAOSHU_RULE.get(rem)
            role = "敌" if pos in ((my_pos+1)%4, (my_pos+3)%4) else "队友"
            print(f"  {role}{pos} 剩 {rem} 张: danger={rule[0]} rec={rule[1]} banned={rule[2]}")
            if bs:
                print(f"         BAOSHU: {bs[0]}, block={bs[1]}, never={bs[2]}")

    print(f"\n{_SEP}")
    print("  调试完成")
    print(f"{_SEP}\n")


# ═══════════════════════════════════════════════════════
#  状态重建（扫描 + 记录模式共用）
# ═══════════════════════════════════════════════════════

def _find_decision_global_state(
    actions: List[Dict], decision: Dict, my_pos: int, start_si: int
) -> Tuple[List[int], int]:
    """
    通过匹配 decision["action"] 与 actions[*]["cur_action"] 找到 my_decision
    对应的全局 actions 列表位置，返回 (决策前的四家剩余张数, 匹配到的下标)。
    """
    dec_action = decision.get("action", [])
    dec_cards: set = set()
    if isinstance(dec_action, list) and len(dec_action) >= 3 and isinstance(dec_action[2], list):
        dec_cards = set(dec_action[2])

    # 先回放 start_si 之前的所有 action
    remaining = [27, 27, 27, 27]
    for i in range(start_si):
        act = actions[i]
        pos = act.get("cur_pos", -1)
        cur_action = act.get("cur_action", [])
        played = len(cur_action[2]) if isinstance(cur_action, list) and len(cur_action) >= 3 and isinstance(cur_action[2], list) else 0
        if 0 <= pos < 4:
            remaining[pos] = max(0, remaining[pos] - played)

    # 从 start_si 开始搜索匹配
    for i in range(start_si, len(actions)):
        act = actions[i]
        cur_action = act.get("cur_action", [])
        act_cards: set = set()
        if isinstance(cur_action, list) and len(cur_action) >= 3 and isinstance(cur_action[2], list):
            act_cards = set(cur_action[2])

        if dec_cards and act_cards and act_cards == dec_cards:
            if act.get("cur_pos", -1) == my_pos:
                return (list(remaining), i)

        # 未匹配 → 扣减
        pos = act.get("cur_pos", -1)
        played = len(cur_action[2]) if isinstance(cur_action, list) and len(cur_action) >= 3 and isinstance(cur_action[2], list) else 0
        if 0 <= pos < 4:
            remaining[pos] = max(0, remaining[pos] - played)

    return (list(remaining), len(actions))


# ═══════════════════════════════════════════════════════
#  Mode 2: 扫描模式
# ═══════════════════════════════════════════════════════

def _classify_q_level(ec: Dict) -> str:
    """根据 _endgame_context 判断命中的 Q 级别。"""
    self_ctx = ec.get("self", {})
    enemies = ec.get("enemies", {})
    teammate = ec.get("teammate", {})
    if self_ctx.get("should_sprint"):
        return "Q0"
    if enemies:
        return "Q1"
    if teammate.get("is_close"):
        return "Q2"
    return "Q3"


def run_scan(args) -> None:
    """扫描模式：统计 game_records_v7 中的残局覆盖率。"""
    records_dir = Path(args.scan_dir or "game_records_v7")
    if not records_dir.exists():
        print(f"错误: 目录不存在 — {records_dir}")
        sys.exit(1)

    json_files = sorted(records_dir.glob("*.json"))
    if not json_files:
        print(f"错误: {records_dir} 中没有 JSON 文件")
        sys.exit(1)

    print(f"\n{_SEP}")
    print(f"  残局智能体覆盖扫描")
    print(f"{_SEP}")
    print(f"  目录: {records_dir}")
    print(f"  文件: {len(json_files)} 个")

    # 统计变量
    total_decisions = 0
    endgame_activated = 0
    total_endgame_decisions = 0
    q_hits: Dict[str, int] = {"Q0": 0, "Q1": 0, "Q2": 0, "Q3": 0}
    banned_filtered = 0
    files_with_endgame = 0
    sample_details: List[Dict] = []

    ep = EndgamePreprocessor()
    decider = EndgameDecider()
    batch_size = max(1, args.batch_games or 10)

    for fi, fpath in enumerate(json_files):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ⚠ 跳过 {fpath.name}: {e}")
            continue

        my_decisions = data.get("my_decisions", [])
        pname = str(data.get("player_name", ""))
        pid = str(data.get("player_id", ""))
        my_pos = 2 if ("yf2" in pname.lower() or pid == "2") else 0
        game_info = data.get("game_info", {})
        cur_rank = str(game_info.get("curRank", "2"))
        initial_hand = data.get("initial_hand", [])
        if isinstance(initial_hand, str):
            initial_hand = initial_hand.split(",")
        actions = data.get("actions", [])

        file_has_endgame = False
        prev_si = 0

        for di, dec in enumerate(my_decisions):
            total_decisions += 1
            ctx = dec.get("context", {})

            # 通过 action 匹配找到全局位置
            players_rem, matched_si = _find_decision_global_state(
                actions, dec, my_pos, prev_si
            )
            prev_si = matched_si

            hand = list(ctx.get("handCards", initial_hand))
            total_hand = len(hand) if hand else 27
            players_rem[my_pos] = total_hand

            # 检查残局激活
            if not any(1 <= p <= 10 for p in players_rem):
                continue

            endgame_activated += 1
            file_has_endgame = True

            action_list = _generate_mock_actions(hand, cur_rank)
            gs = {
                "myPos": my_pos, "curPos": ctx.get("curPos", my_pos),
                "curRank": cur_rank, "numofplayers": players_rem,
                "handCards": hand, "actionList": action_list,
            }

            try:
                gs = ep.preprocess(gs)
                ec = gs.get("_endgame_context", {})
                if not ec.get("is_active"):
                    continue

                total_endgame_decisions += 1
                filtered, is_empty = decider.apply_banned_filter(action_list, gs)
                if len(filtered) < len(action_list):
                    banned_filtered += len(action_list) - len(filtered)

                result = decider.decide(gs, filtered if not is_empty else action_list)
                idx, act = result

                if idx is not None:
                    ql = _classify_q_level(ec)
                    q_hits[ql] = q_hits.get(ql, 0) + 1

                    if len(sample_details) < 20:
                        atype = get_action_type(act) if GUARD_TOOLS_OK else (act[0] if act else "?")
                        sample_details.append({
                            "file": fpath.name, "step": di,
                            "players": list(players_rem),
                            "my_remaining": total_hand,
                            "q_level": ql, "action_type": atype,
                        })
            except Exception:
                continue

        if file_has_endgame:
            files_with_endgame += 1

        if (fi + 1) % batch_size == 0:
            print(f"  已处理: {fi+1}/{len(json_files)}  残局激活点: {endgame_activated}")

    # ── 统计报告 ──
    print(f"\n{_SEP}")
    print(f"  覆盖率报告")
    print(f"{_SEP}")
    print(f"  总决策点:          {total_decisions}")
    print(f"  残局激活点:         {endgame_activated} ({endgame_activated/max(1,total_decisions)*100:.1f}%)")
    print(f"  残局管线决策:       {total_endgame_decisions}")
    print(f"  含残局文件:         {files_with_endgame}/{len(json_files)}")
    print(f"  banned 过滤移除:    {banned_filtered} 个 action")
    print(f"")
    print(f"  Q 级命中分布:")
    for ql in ["Q0", "Q1", "Q2", "Q3"]:
        print(f"    {ql}: {q_hits.get(ql, 0)}")
    hit_total = sum(q_hits.values())
    print(f"    命中合计:         {hit_total} / {total_endgame_decisions} ({hit_total/max(1,total_endgame_decisions)*100:.1f}%)")

    if sample_details:
        print(f"\n  命中样本 (前 20):")
        print(f"  {'文件':<50s} {'步':>3s} {'剩':>4s} {'四家剩余':<20s} {'Q级'}")
        for s in sample_details:
            ps = "/".join(str(p) for p in s["players"])
            print(f"  {s['file']:<50s} {s['step']:3d}  {s['my_remaining']:4d}  {ps:<20s} {s['q_level']}")

    print(f"\n{_SEP}")
    print("  扫描完成")
    print(f"{_SEP}\n")


# ═══════════════════════════════════════════════════════
#  Mode 3: 单记录模式
# ═══════════════════════════════════════════════════════

def run_single_record(args) -> None:
    """单记录模式：从 game_record JSON 中抽取残局快照。"""
    fpath = Path(args.record)
    if not fpath.exists():
        print(f"错误: 文件不存在 — {fpath}")
        sys.exit(1)

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    pname = str(data.get("player_name", ""))
    pid = str(data.get("player_id", ""))
    my_pos = 2 if ("yf2" in pname.lower() or pid == "2") else 0
    game_info = data.get("game_info", {})
    cur_rank = str(game_info.get("curRank", "2"))
    initial_hand = data.get("initial_hand", [])
    if isinstance(initial_hand, str):
        initial_hand = initial_hand.split(",")

    my_decisions = data.get("my_decisions", [])
    actions = data.get("actions", [])

    # 选步：自动找第一个残局点 或 手动指定
    target_step = args.step
    if target_step is None:
        prev_si = 0
        for di, dec in enumerate(my_decisions):
            ctx = dec.get("context", {})
            players_rem, matched_si = _find_decision_global_state(actions, dec, my_pos, prev_si)
            prev_si = matched_si
            hand = list(ctx.get("handCards", initial_hand))
            players_rem[my_pos] = len(hand) if hand else 27
            if any(1 <= p <= 10 for p in players_rem):
                target_step = di
                break
        if target_step is None:
            print("✗ 该记录中没有残局点（所有玩家均 >10 张）")
            return

    if target_step >= len(my_decisions):
        print(f"错误: --step={target_step} 超出范围 (共 {len(my_decisions)} 步)")
        sys.exit(1)

    # 重放到目标步
    prev_si = 0
    for di in range(target_step):
        _, prev_si = _find_decision_global_state(actions, my_decisions[di], my_pos, prev_si)

    dec = my_decisions[target_step]
    ctx = dec.get("context", {})
    hand = list(ctx.get("handCards", initial_hand))
    players_rem, matched_si = _find_decision_global_state(actions, dec, my_pos, prev_si)
    if hand:
        players_rem[my_pos] = len(hand)
    cur_pos = ctx.get("curPos", my_pos)

    print(f"\n{_SEP}")
    print(f"  单记录残局调试")
    print(f"{_SEP}")
    print(f"  文件: {fpath.name}")
    print(f"  步:   {target_step} (全局 actions 下标 ≈ {matched_si})")
    print(f"  手牌 ({len(hand)} 张): {' '.join(hand[:15])}{'...' if len(hand)>15 else ''}")
    print(f"  级牌: {cur_rank}    我的位置: {my_pos}    出牌权: {cur_pos}")
    print(f"  四家剩余: {players_rem}")

    action_list = _generate_mock_actions(hand, cur_rank)
    game_state = {
        "myPos": my_pos, "curPos": cur_pos,
        "curRank": cur_rank, "numofplayers": players_rem,
        "handCards": hand, "actionList": action_list,
    }

    ep = EndgamePreprocessor()
    game_state = ep.preprocess(game_state)
    ec = game_state.get("_endgame_context", {})

    print(f"\n  is_active: {ec.get('is_active', False)}")
    if ec.get("is_active"):
        _fmt_env(ec.get("enemies", {}), ec.get("teammate", {}), ec.get("self", {}))
        _fmt_actions(action_list)

        print(f"\n{_SEP2}")
        print(f"  Q0→Q3 决策流程")
        print(f"{_SEP2}")

        decider = EndgameDecider()
        filtered, is_empty = decider.apply_banned_filter(action_list, game_state)
        if is_empty:
            print("  ⚠ banned 硬排后 actionList 为空 → L3 降级")
        elif len(filtered) < len(action_list):
            print(f"  banned 过滤: {len(action_list)} → {len(filtered)}")

        result = decider.decide(game_state, filtered if not is_empty else action_list)
        _fmt_decision_trace(result, action_list)
    else:
        print("  ✗ 该步未进入残局区")

    actual_action = dec.get("action", [])
    actual_layer = dec.get("layer", "?")
    actual_cards = actual_action[2] if len(actual_action) >= 3 else actual_action
    print(f"\n  实际出牌: {actual_layer} layer, cards={actual_cards}")

    print(f"\n{_SEP}\n")


# ═══════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="残局智能体独立调试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 独立模式
  python scripts/checks/check_endgame_agent.py --hand H2,H2,S2,D2,CA,HA,SA,CK --rank 2 --players 8,3,12,10 --pos 0

  # 扫描模式
  python scripts/checks/check_endgame_agent.py --scan

  # 单记录模式
  python scripts/checks/check_endgame_agent.py --record game_records_v7/xxx.json --step 5
        """,
    )
    parser.add_argument("--hand", default=None, help="手牌，逗号分隔")
    parser.add_argument("--rank", default="2", help="级牌 rank（默认 2）")
    parser.add_argument("--players", default=None, help="四家剩余张数，逗号分隔")
    parser.add_argument("--pos", type=int, default=0, help="我的位置（0-3）")
    parser.add_argument("--curpos", type=int, default=None, help="当前出牌权位置")
    parser.add_argument("--scan", action="store_true", help="扫描 game_records_v7")
    parser.add_argument("--scan-dir", default=None, help="扫描目录（默认 game_records_v7）")
    parser.add_argument("--batch-games", type=int, default=10, help="进度汇报间隔")
    parser.add_argument("--record", default=None, help="单记录 JSON 路径")
    parser.add_argument("--step", type=int, default=None, help="指定步（默认自动找残局点）")

    args = parser.parse_args()

    if args.scan:
        run_scan(args)
    elif args.record:
        run_single_record(args)
    elif args.hand and args.players:
        run_standalone(args)
    else:
        print("请指定运行模式：")
        print("  独立模式:   --hand + --players")
        print("  扫描模式:   --scan")
        print("  单记录:     --record")
        print()
        print("示例:")
        print("  python scripts/checks/check_endgame_agent.py --hand H2,H2,S2,D2,CA,HA,SA,CK --rank 2 --players 8,3,12,10 --pos 0")
        print("  python scripts/checks/check_endgame_agent.py --scan")
        print("  python scripts/checks/check_endgame_agent.py --record game_records_v7/xxx.json --step 5")
        sys.exit(1)


if __name__ == "__main__":
    main()
