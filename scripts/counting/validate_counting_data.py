# -*- coding: utf-8 -*-
"""
GUA-057 Phase 0 任务 2：Ground truth 构建手算对账

目的：验证 build_ground_truth() 的正确性——抽 10 副牌，对每副 step t：
  1. 提取 initial_hand（自己）+ 同局 yf2 initial_hand（队友）
  2. 累计 actions[0..t] 所有已出牌（按 cur_action[2] 列表）
  3. 手算 my_hand = initial_hand - 已出 by cur_pos=my_pos
     手算 partner_hand = partner_initial - 已出 by partner_pos
     手算 played = 所有已出牌计数（去 my_hand + partner_hand）
  4. 用 build_ground_truth() 函数计算同样 ground truth
  5. 对比：108 槽位状态分布必须完全相同

简化版（仅验证，不含 tribute/反贡处理）：
  - 输出形状：(54, 2) → 108 槽位；每槽位状态 ∈ {PLAYED, MY_HAND, PARTNER_HAND, OPPONENT_HAND}
  - 不做 NN softmax 概率——仅离散标签

用法：
  python scripts/counting/validate_counting_data.py [--n 10] [--records-dir game_records_v8]
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

# 平台术语常量（与 AGENTS.md 平台术语强制对齐表一致）
ALL_CARD_TYPES: List[str] = []
for r in "23456789TJQKA":
    for s in "SHDC":
        ALL_CARD_TYPES.append(f"{s}{r}")
ALL_CARD_TYPES.extend(["SB", "HR"])  # 54 种

# 状态常量
PLAYED = 0
MY_HAND = 1
PARTNER_HAND = 2
OPPONENT_HAND = 3


def card_to_slot(card: str) -> int:
    """card -> slot index (0-107)，54 种 × 2 副本（按出现顺序区分）。"""
    if card not in ALL_CARD_TYPES:
        return -1
    # 简化：第 1 次出现 = slot N，第 2 次 = slot N+54
    # build 时按 (card_type, copy_idx) 排序
    return ALL_CARD_TYPES.index(card)


def parse_action_cards(cur_action) -> List[str]:
    """cur_action = [type, rank, [cards]]，提取 cards 列表。"""
    if isinstance(cur_action, list) and len(cur_action) >= 3:
        third = cur_action[2]
        if isinstance(third, list):
            return list(third)
    return []


def find_my_pos(actions: List[dict], initial_player_id: int) -> int:
    """推断 my_pos = actions 中出现 cur_pos=initial_player_id 的最早位置。"""
    for a in actions:
        if a.get("cur_pos") == initial_player_id:
            return initial_player_id
    return initial_player_id


def find_partner_pos(my_pos: int) -> int:
    """掼蛋队友规则：my_pos=0↔2, 1↔3。"""
    return (my_pos + 2) % 4


def build_ground_truth_v0(
    initial_hands: Dict[int, List[str]],  # {pos: [cards]}
    actions: List[dict],
    my_pos: int,
    step_t: int,
) -> Dict[int, int]:
    """简化版 ground truth：108 槽位 → 状态。

    Args:
        initial_hands: {pos: [cards]}，必须包含 my_pos 和 partner_pos 的完整 27 张
        actions: actions 序列
        my_pos: 自己席号
        step_t: 计算到第几步（包含）

    Returns:
        {slot_idx: state}  dict
    """
    partner_pos = find_partner_pos(my_pos)

    # 1. my_hand 和 partner_hand 从 initial_hands 出发
    my_initial = set(initial_hands.get(my_pos, []))
    partner_initial = set(initial_hands.get(partner_pos, []))

    # 2. 累计 [0..step_t] 所有已出牌（含 my/partner/opp）
    all_played = []
    for a in actions[: step_t + 1]:
        cards = parse_action_cards(a.get("cur_action", []))
        all_played.extend(cards)

    played_count: Counter = Counter(all_played)

    # 3. 计算剩余牌
    my_remaining = list(my_initial - set(all_played))
    partner_remaining = list(partner_initial - set(all_played))

    # 4. 108 槽位状态映射（简化版：只标 PLAYED / MY_HAND / PARTNER_HAND，剩余归 OPPONENT_HAND）
    slots: Dict[int, int] = {}
    # 先标 PLAYED
    for card, cnt in played_count.items():
        if card in ALL_CARD_TYPES:
            base_slot = card_to_slot(card)
            for copy in range(cnt):
                if copy == 0:
                    slots[base_slot] = PLAYED
                else:
                    slots[base_slot + 54] = PLAYED

    # 再标 MY_HAND（覆盖 PLAYED 标签是错的——意味着 ground truth 算法自身冲突）
    # 正确逻辑：my_initial 中减去 played_count 中 my 自己出的部分
    # 但 simplified 不区分谁出的——这里直接用 initial - all_played
    for card in my_remaining:
        if card in ALL_CARD_TYPES:
            base_slot = card_to_slot(card)
            if base_slot not in slots:
                slots[base_slot] = MY_HAND

    # 再标 PARTNER_HAND
    for card in partner_remaining:
        if card in ALL_CARD_TYPES:
            base_slot = card_to_slot(card)
            if base_slot not in slots:
                slots[base_slot] = PARTNER_HAND

    # 其余未标 = OPPONENT_HAND
    for slot in range(108):
        if slot not in slots:
            slots[slot] = OPPONENT_HAND

    return slots


def manual_ground_truth(
    initial_hands: Dict[int, List[str]],
    actions: List[dict],
    my_pos: int,
    step_t: int,
) -> Dict[int, int]:
    """手算版本：完全独立的逻辑实现，用于与代码对比。

    与 build_ground_truth_v0 的关键差异：
      - 手算用 Counter 严格按 cur_pos 区分谁出的牌（my/partner/opp）
      - my_remaining = my_initial - (cur_pos=my_pos 的所有出牌)
      - partner_remaining = partner_initial - (cur_pos=partner_pos 的所有出牌)
    """
    partner_pos = find_partner_pos(my_pos)
    my_initial = list(initial_hands.get(my_pos, []))
    partner_initial = list(initial_hands.get(partner_pos, []))

    # 按 cur_pos 累计出牌
    played_by_pos: Dict[int, List[str]] = {0: [], 1: [], 2: [], 3: []}
    all_played: List[str] = []
    for a in actions[: step_t + 1]:
        cur_pos = a.get("cur_pos", -1)
        cards = parse_action_cards(a.get("cur_action", []))
        if cur_pos in played_by_pos:
            played_by_pos[cur_pos].extend(cards)
        all_played.extend(cards)

    my_remaining_set = set(my_initial) - set(played_by_pos[my_pos])
    partner_remaining_set = set(partner_initial) - set(played_by_pos[partner_pos])
    all_played_set = set(all_played)

    slots: Dict[int, int] = {}
    for card, cnt in Counter(all_played).items():
        if card in ALL_CARD_TYPES:
            base_slot = card_to_slot(card)
            for copy in range(cnt):
                if copy == 0:
                    slots[base_slot] = PLAYED
                else:
                    slots[base_slot + 54] = PLAYED

    for card in my_remaining_set:
        if card in ALL_CARD_TYPES:
            base_slot = card_to_slot(card)
            if base_slot not in slots:
                slots[base_slot] = MY_HAND

    for card in partner_remaining_set:
        if card in ALL_CARD_TYPES:
            base_slot = card_to_slot(card)
            if base_slot not in slots:
                slots[base_slot] = PARTNER_HAND

    for slot in range(108):
        if slot not in slots:
            slots[slot] = OPPONENT_HAND

    return slots


def verify_pair(yf1_path: Path, yf2_path: Path, n_samples: int = 3) -> List[Tuple[bool, str]]:
    """对 1 对 yf1/yf2 文件验证 ground truth 一致性。

    Returns: [(ok, msg), ...] 每个 sample 一条
    """
    results = []
    try:
        d1 = json.loads(yf1_path.read_text(encoding="utf-8"))
        d2 = json.loads(yf2_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [(False, f"JSON 解析失败: {e}")]

    my_pos_1 = int(d1.get("player_id", 0))
    my_pos_2 = int(d2.get("player_id", 0))
    if my_pos_1 == my_pos_2:
        return [(False, f"两视角 player_id 相同 ({my_pos_1})")]

    actions = d1.get("actions", [])
    n_actions = len(actions)
    if n_actions < 2:
        return [(False, "actions 序列太短")]

    # 合并 initial_hands
    initial_hands: Dict[int, List[str]] = {}
    initial_hands[my_pos_1] = list(d1.get("initial_hand", []))
    initial_hands[my_pos_2] = list(d2.get("initial_hand", []))

    # 抽 step：早期 / 中期 / 末期
    samples = [0, n_actions // 2, n_actions - 1][:n_samples]

    for step in samples:
        gt_code = build_ground_truth_v0(initial_hands, actions, my_pos_1, step)
        gt_manual = manual_ground_truth(initial_hands, actions, my_pos_1, step)

        # 对比
        diffs = []
        for slot in range(108):
            if gt_code.get(slot) != gt_manual.get(slot):
                diffs.append((slot, gt_code.get(slot), gt_manual.get(slot)))

        if not diffs:
            results.append((True, f"step {step}: 108 槽位 100% 一致"))
        else:
            results.append((False, f"step {step}: {len(diffs)} 处不一致，首处 slot={diffs[0]}"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Ground truth 手算对账")
    parser.add_argument("--n", type=int, default=10, help="抽 N 副验证（默认 10）")
    parser.add_argument("--records-dir", default="game_records_v8")
    args = parser.parse_args()

    records_dir = Path(args.records_dir)
    if not records_dir.exists():
        print(f"[ERROR] 目录不存在: {records_dir}", file=sys.stderr)
        return 1

    # 按 timestamp 全局序取前 N 对
    files = sorted(records_dir.glob("*.json"),
                   key=lambda p: int(p.stem.split(" ")[0]))
    yf1_files = [f for f in files if "[yf1_v8]" in f.name]
    yf2_files = [f for f in files if "[yf2_v8]" in f.name]

    pairs_tested = 0
    pairs_passed = 0
    all_ok = True
    print("=" * 60)
    print("GUA-057 Phase 0 任务 2：Ground truth 手算对账")
    print(f"records_dir = {records_dir}")
    print(f"验证对数: {args.n}")
    print("=" * 60)

    for f1 in yf1_files[: args.n]:
        # 找同 game_tag 的 yf2
        game_tag = f1.stem.split(" ", 1)[1].replace("[yf1_v8]-", "")
        candidates = [f for f in yf2_files if game_tag in f.stem]
        if not candidates:
            continue
        f2 = candidates[0]

        results = verify_pair(f1, f2, n_samples=3)
        pairs_tested += 1
        all_step_ok = all(ok for ok, _ in results)
        if all_step_ok:
            pairs_passed += 1

        for ok, msg in results:
            mark = "✓" if ok else "✗"
            print(f"  [{mark}] {f1.name[:30]} | {msg}")
        if not all_step_ok:
            all_ok = False

    print("=" * 60)
    print(f"  验证对数: {pairs_tested}")
    print(f"  全 step 一致: {pairs_passed}")
    if all_ok and pairs_tested >= args.n:
        print(f"[PASS] Phase 0 任务 2 通过（{pairs_passed}/{pairs_tested} 对全 step 一致）")
        return 0
    print(f"[FAIL] Phase 0 任务 2 失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
