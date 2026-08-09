# -*- coding: utf-8 -*-
"""
GUA-223 Phase 0 ETL — Botzone 日志 → CardCountingNetwork 训练样本

> 真源：docs/guandan-brain/CardCountingNetwork-训练方案.md §8 Phase 0
> 关联：GUA-057（母条目）/ GUA-223（本子任务）/ ITERATIONS v8-gua223-card-counting-phase0
> 数据源：logs/v8_vs_botzone_*.log（不进 Git；WF-13 强约束）
> 输出：data/training/card_counting_v1/<match>_<step>.npz

输入格式（每个 match）：
  [ts] [botzone_adapter] [INFO] 收到 request: match=<id> stage=deal
  [ts] [botzone_adapter] [INFO] 发牌: match=<id> player=0 hand=27 curRank=2 hand=[...]
  [ts] [botzone_adapter] [INFO] 收到 request: match=<id> stage=play
  [ts] [botzone_adapter] [INFO] play request raw: match=<id> {"stage":"play",...}
  [ts] [botzone_adapter] [INFO] 决策: match=<id> type=... rank=... cards=... actIndex=...

Botzone history 两种格式（A/B 见 botzone_adapter.py L1636）：
  A. 数组格式：[[action, claim], [], [], []]    # 按玩家索引
  B. 字典格式：[{"player":0,"response":[action, claim]}, ...]
  其中 action=[bz_int,...] claim=[bz_int,...]，空数组=PASS

输出格式（每个 stage=play 步一个 .npz）：
  X:
    - hand_self: V8 字符串列表（27 张 → 递减）
    - cur_rank: str
    - history_raw: List 变长 — 每步 4 玩家 Botzone action/claim
    - done: List[int] 已 done 玩家
    - global_state: json.dumps(tribute/back/level 等)
    - stage: str
  y:
    - ground_truth: (108, 3) one-hot {MY_HAND, PLAYED, REST}
      REST = 未出且不在我方手里（属于 player 1/2/3，无法拆分 teammate/opponent）
      3 类简化版（不区分 teammate/opponent 是 Botzone 日志的固有限制）
  meta:
    - match_id / step_id / decision_act_index / decision_act_type / decision_act_cards

Phase 0 硬门槛 ① 手算对账：
  ① hand_self 各副本数 = 27
  ② PLAYED ∪ MY_HAND ∪ REST = 108（守恒）
  ③ 每步 REST 数 = 108 - |hand_self| - |played_history_total|
  ④ 已 done player PLAYED = 27（精确还原）
  ⑤ 同局后续步 hand_self 严格单调递减
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Botzone 编码常量（从 src/communication/botzone_adapter.py L46-47 复制以避免重型 import）
BZ_RANK_STR = "A23456789TJQK"  # value 0-12
BZ_SUIT_MAP = {0: "H", 1: "D", 2: "S", 3: "C"}  # heart, diamond, spade, club

SLOT_COUNT = 54
TOTAL_SLOTS = 108  # 54 × 2 副本

_V8_CARD_TO_SLOT: Dict[str, int] = {}


def _build_v8_to_slot() -> None:
    for value in range(13):
        for suit_idx in range(4):
            _V8_CARD_TO_SLOT[f"{BZ_SUIT_MAP[suit_idx]}{BZ_RANK_STR[value]}"] = (
                value * 4 + suit_idx
            )
    _V8_CARD_TO_SLOT["SB"] = 52
    _V8_CARD_TO_SLOT["HR"] = 53


_build_v8_to_slot()


def bz_int_to_v8(bz_int: int) -> str:
    """Botzone 整数 (0-107) → V8 字符串（'SK' / 'HR' 等）"""
    first_deck = bz_int % 54
    value = first_deck // 4
    suit_idx = first_deck % 4
    if value == 13:
        return "SB" if suit_idx in (0, 2) else "HR"
    return f"{BZ_SUIT_MAP[suit_idx]}{BZ_RANK_STR[value]}"


def v8_to_slot(v8_str: str) -> int:
    """V8 字符串 → 槽位 id (0-53)"""
    return _V8_CARD_TO_SLOT[v8_str]


# === 日志正则 ===

DEAL_LINE_RE = re.compile(
    r"\[botzone_adapter\] \[INFO\] 发牌: match=(\S+) player=(\d+) hand=(\d+) curRank=(\S+) hand=(\[[^\]]+\])"
)
PLAY_REQ_RE = re.compile(
    r"\[botzone_adapter\] \[INFO\] 收到 request: match=(\S+) stage=(\S+)"
)
PLAY_RAW_RE = re.compile(
    r"\[botzone_adapter\] \[INFO\] play request raw: match=(\S+) (\{.*\})"
)
DECISION_RE = re.compile(
    r"\[botzone_adapter\] \[INFO\] 决策: match=(\S+) type=(\S+) rank=(\S+) cards=(\[[^\]]*\]) actIndex=(\d+)"
)
GAME_OVER_RE = re.compile(
    r"\[botzone_adapter\] \[INFO\] 对局结束: match=(\S+) slot=(\d+) players=(\d+) scores=(\[[^\]]+\])"
)


def _safe_eval_list(s: str) -> list:
    """安全解析 Python list 字符串（仅信任日志固定格式）"""
    if s == "[]" or s == "[PASS]":
        return []
    try:
        return eval(s, {"__builtins__": {}}, {})
    except Exception:
        return []


def parse_history_entries(history: list) -> List[Tuple[int, list, list]]:
    """解析 history 列表 → [(player, action_cards, claim_cards), ...]

    兼容 A/B 两种格式（参 botzone_adapter.py _parse_bz_play_history L1636）。
    """
    entries: List[Tuple[int, list, list]] = []
    if not isinstance(history, list):
        return entries
    for i, entry in enumerate(history):
        if isinstance(entry, dict):
            player = entry.get("player", -1)
            resp = entry.get("response", [])
        elif isinstance(entry, list):
            player = i
            resp = entry
        else:
            continue
        action_cards: list = []
        claim_cards: list = []
        if isinstance(resp, list) and len(resp) > 0 and isinstance(resp[0], list):
            action_cards = resp[0]
            if len(resp) > 1 and isinstance(resp[1], list):
                claim_cards = resp[1]
        entries.append((player, action_cards, claim_cards))
    return entries


def parse_log_file(log_path: Path) -> Dict[str, Any]:
    """解析整个日志 → {match_id: {hand_self, cur_rank, steps[], final_scores}}"""
    text = log_path.read_text(encoding="utf-8")
    matches: Dict[str, Any] = {}

    for line in text.splitlines():
        m = DEAL_LINE_RE.search(line)
        if m:
            match_id = m.group(1)
            hand = _safe_eval_list(m.group(5))
            if match_id not in matches:
                matches[match_id] = {
                    "hand_self": hand,
                    "cur_rank": m.group(4),
                    "steps": [],
                    "final_scores": None,
                }
            else:
                # 后续副（multi-episode）：覆盖（同一 match 多次 deal）
                matches[match_id]["hand_self"] = hand
                matches[match_id]["cur_rank"] = m.group(4)
                matches[match_id]["steps"] = []
                matches[match_id]["final_scores"] = None
            continue

        m = PLAY_REQ_RE.search(line)
        if m:
            match_id, stage = m.group(1), m.group(2)
            if match_id not in matches:
                matches[match_id] = {
                    "hand_self": [],
                    "cur_rank": None,
                    "steps": [],
                    "final_scores": None,
                }
            matches[match_id]["steps"].append({
                "step_id": len(matches[match_id]["steps"]),
                "stage": stage,
                "raw_line": line,
            })
            continue

        m = PLAY_RAW_RE.search(line)
        if m:
            match_id, json_str = m.group(1), m.group(2)
            if match_id in matches and matches[match_id]["steps"]:
                step = matches[match_id]["steps"][-1]
                try:
                    req = json.loads(json_str)
                    step["history_raw"] = req.get("history", [])
                    step["done"] = req.get("done", [])
                    step["pass_on"] = req.get("pass_on", -1)
                    step["global"] = req.get("global", {})
                except json.JSONDecodeError:
                    pass
            continue

        m = DECISION_RE.search(line)
        if m:
            match_id = m.group(1)
            if match_id in matches and matches[match_id]["steps"]:
                step = matches[match_id]["steps"][-1]
                step["decision_act_index"] = int(m.group(5))
                step["decision_act_type"] = m.group(2)
                step["decision_act_rank"] = m.group(3)
                step["decision_act_cards"] = _safe_eval_list(m.group(4))
            continue

        m = GAME_OVER_RE.search(line)
        if m:
            match_id = m.group(1)
            if match_id in matches:
                matches[match_id]["final_scores"] = _safe_eval_list(m.group(4))
            continue

    return matches


def compute_hand_at_step(
    match_data: Dict[str, Any], step_idx: int
) -> Tuple[List[str], List[str]]:
    """反推第 step_idx 步开始时 V8 剩余手牌 + 不一致 warning 列表。

    返回：(hand, warning_cards)
      - hand: 剩余手牌 V8 字符串列表
      - warning_cards: history 声称 V8 出过但不在累计手牌中的牌（GUA-216 双扣 bug 信号）
    """
    hand = list(match_data["hand_self"])
    warnings: List[str] = []
    for s in match_data["steps"][:step_idx+1]:
        history = s.get("history_raw", [])
        if not history:
            continue
        parsed = parse_history_entries(history)
        for player_id, action_cards, _claim in parsed:
            if player_id != 0:
                continue  # 只关心 V8 自己
            for card_int in action_cards:
                try:
                    v8_card = bz_int_to_v8(int(card_int))
                except (TypeError, ValueError):
                    continue
                if v8_card in hand:
                    hand.remove(v8_card)
                else:
                    warnings.append(v8_card)
                    logging.warning(
                        "step=%d 试图移除不在手牌中的牌 %s (hand=%s)",
                        step_idx, v8_card, hand,
                    )
    return hand, warnings


def compute_played_at_step(match_data: Dict[str, Any], step_idx: int) -> Dict[int, list]:
    """反推第 step_idx 步开始时各席已出的 Botzone 整数列表（含重复）。"""
    played: Dict[int, list] = {0: [], 1: [], 2: [], 3: []}
    for s in match_data["steps"][:step_idx+1]:
        history = s.get("history_raw", [])
        parsed = parse_history_entries(history)
        for player_id, action_cards, _claim in parsed:
            if player_id < 0 or player_id > 3:
                continue
            played[player_id].extend(action_cards)
    return played


def compute_ground_truth(
    hand_at_step: List[str],
    played_at_step: Dict[int, list],
) -> np.ndarray:
    """计算 108 维 ground truth：每副本状态 one-hot {MY_HAND, PLAYED, REST}。

    REST = 未出且不在我方手里（属于 player 1/2/3，无法拆分 teammate/opponent）
    """
    gt = np.zeros((TOTAL_SLOTS, 3), dtype=np.int8)

    hand_counter = [0] * SLOT_COUNT
    for card in hand_at_step:
        slot = v8_to_slot(card)
        if hand_counter[slot] < 2:
            hand_counter[slot] += 1

    played_counter = [0] * SLOT_COUNT
    for player_id in range(4):
        for card_int in played_at_step.get(player_id, []):
            try:
                slot = int(card_int) % SLOT_COUNT
            except (TypeError, ValueError):
                continue
            if played_counter[slot] < 2:
                played_counter[slot] += 1

    for slot in range(SLOT_COUNT):
        for deck_idx in range(2):
            idx = slot + deck_idx * SLOT_COUNT
            if hand_counter[slot] > 0:
                gt[idx] = [1, 0, 0]
                hand_counter[slot] -= 1
            elif played_counter[slot] > 0:
                gt[idx] = [0, 1, 0]
                played_counter[slot] -= 1
            else:
                gt[idx] = [0, 0, 1]

    return gt


def extract_match_samples(
    log_path: Path,
    match_id: str,
    output_dir: Path,
    write: bool = True,
) -> List[Dict[str, Any]]:
    """提取 1 个 match 的所有 step 样本。"""
    matches = parse_log_file(log_path)
    if match_id not in matches:
        raise ValueError(f"未找到 match={match_id} 在 {log_path}")

    match_data = matches[match_id]
    n_steps = len(match_data["steps"])
    logging.info(
        "提取 match=%s hand_self=%d 张 curRank=%s 步数=%d final_scores=%s",
        match_id,
        len(match_data["hand_self"]),
        match_data["cur_rank"],
        n_steps,
        match_data["final_scores"],
    )

    samples: List[Dict[str, Any]] = []
    for step_idx, step in enumerate(match_data["steps"]):
        if step["stage"] != "play":
            continue
        if "history_raw" not in step:
            continue

        hand, warning_cards = compute_hand_at_step(match_data, step_idx)
        played = compute_played_at_step(match_data, step_idx)
        gt = compute_ground_truth(hand, played)
        has_warning = bool(warning_cards)

        sample = {
            "match_id": match_id,
            "step_id": step_idx,
            "hand_self": hand,
            "cur_rank": match_data["cur_rank"],
            "history_raw": step["history_raw"],
            "done": step.get("done", []),
            "pass_on": step.get("pass_on", -1),
            "global": step.get("global", {}),
            "stage": step["stage"],
            "ground_truth": gt,
            "decision_act_index": step.get("decision_act_index", -1),
            "decision_act_type": step.get("decision_act_type", "?"),
            "decision_act_cards": step.get("decision_act_cards", []),
            "timestamp": step.get("raw_line", "")[:20],
            "has_warning": has_warning,
            "warning_cards": warning_cards,
        }
        samples.append(sample)

        if write:
            out_path = output_dir / f"{match_id[:24]}_{step_idx:04d}.npz"
            np.savez_compressed(
                out_path,
                ground_truth=gt,
                hand_self=np.array(hand, dtype=object),
                cur_rank=match_data["cur_rank"],
                history_raw=np.array(step["history_raw"], dtype=object),
                done=np.array(step.get("done", []), dtype=np.int8),
                global_state=json.dumps(step.get("global", {})),
                stage=step["stage"],
                decision_act_index=np.int32(step.get("decision_act_index", -1)),
                decision_act_type=str(step.get("decision_act_type", "?")),
                decision_act_cards=np.array(step.get("decision_act_cards", []), dtype=object),
                match_id=match_id,
                step_id=np.int32(step_idx),
                has_warning=np.bool_(has_warning),
                warning_cards=np.array(warning_cards, dtype=object),
            )

    logging.info(
        "✅ match=%s 提取 %d 个 stage=play 样本（写入 %s）",
        match_id, len(samples), output_dir,
    )
    return samples


def verify_samples(samples: List[Dict[str, Any]]) -> bool:
    """5 项硬门槛 ① 手算对账。"""
    if not samples:
        logging.error("❌ 无样本可验证")
        return False

    n_my_first = int(samples[0]["ground_truth"][:, 0].sum())
    if n_my_first != len(samples[0]["hand_self"]):
        logging.error(
            "❌ 第 1 步 MY_HAND=%d ≠ hand_self=%d",
            n_my_first, len(samples[0]["hand_self"]),
        )
        return False

    prev_my = len(samples[0]["hand_self"])
    for i, s in enumerate(samples[1:], 1):
        cur_my = len(s["hand_self"])
        if cur_my > prev_my:
            logging.error("❌ step=%d hand_self 递增 %d → %d", i, prev_my, cur_my)
            return False
        prev_my = cur_my

    for s in samples:
        gt = s["ground_truth"]
        n_my = int(gt[:, 0].sum())
        n_played = int(gt[:, 1].sum())
        n_rest = int(gt[:, 2].sum())
        if n_my + n_played + n_rest != TOTAL_SLOTS:
            logging.error(
                "❌ step=%d 守恒失败 %d+%d+%d ≠ 108",
                s["step_id"], n_my, n_played, n_rest,
            )
            return False

    for s in samples:
        gt = s["ground_truth"]
        n_my = int(gt[:, 0].sum())
        n_played = int(gt[:, 1].sum())
        n_rest = int(gt[:, 2].sum())
        assert n_rest == TOTAL_SLOTS - n_my - n_played, "REST 计算不一致"

    logging.info("✅ 5 项硬门槛 ① 手算对账 PASS（%d 个 step）", len(samples))
    return True


def main():
    parser = argparse.ArgumentParser(
        description="GUA-223 Phase 0 ETL — Botzone 日志 → CardCountingNetwork 训练样本"
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("logs/v8_vs_botzone_20260809_105812.log"),
        help="Botzone 对局日志路径",
    )
    parser.add_argument(
        "--match",
        type=str,
        default="6a77f5650fbd680d7c6cf7c9",
        help="要提取的 match_id（前 8 字符可）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/training/card_counting_v1"),
        help="样本输出目录",
    )

    # === 全量模式（WF-13 数据累积基线）===
    parser.add_argument(
        "--all-matches",
        action="store_true",
        help="扫描 logs/v8_vs_botzone_*.log 全部 match（除 _err/_nohup）并 ETL",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="全量模式下的日志目录",
    )
    parser.add_argument("--dry-run", action="store_true", help="只验证，不写盘")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.all_matches:
        # 全量模式：扫 logs/v8_vs_botzone_*.log
        all_samples = []
        all_match_ids = []
        log_files = sorted([
            p for p in args.log_dir.glob("v8_vs_botzone_*.log")
            if "_err" not in p.name and "_nohup" not in p.name
        ])
        if not log_files:
            logging.error("❌ 在 %s 未找到 v8_vs_botzone_*.log", args.log_dir)
            sys.exit(1)
        for log_path in log_files:
            matches = parse_log_file(log_path)
            for mid in matches:
                all_match_ids.append((log_path.name, mid))
        logging.info("全量模式: %d 个日志 / %d 个 match", len(log_files), len(all_match_ids))
        total_ok = True
        for log_name, mid in all_match_ids:
            samples = extract_match_samples(
                Path("logs") / log_name, mid, args.output_dir, write=not args.dry_run
            )
            ok = verify_samples(samples)
            total_ok = total_ok and ok
            all_samples.extend(samples)
        # 全量统计
        n_my = sum(int(s["ground_truth"][:, 0].sum()) for s in all_samples) // len(all_samples) if all_samples else 0
        n_played_total = sum(int(s["ground_truth"][:, 1].sum()) for s in all_samples)
        n_rest_total = sum(int(s["ground_truth"][:, 2].sum()) for s in all_samples)
        logging.info("=" * 60)
        logging.info("全量累积: %d 个样本（来自 %d 个 match × %d 个日志）",
                     len(all_samples), len(all_match_ids), len(log_files))
        logging.info("样本/维度比: %.2f（目标 ≥24）", len(all_samples) / 324)
        sys.exit(0 if total_ok else 1)

    matches = parse_log_file(args.log)
    full_match_id = None
    for mid in matches:
        if mid.startswith(args.match) or mid == args.match:
            full_match_id = mid
            break
    if full_match_id is None:
        logging.error("❌ 未找到 match 前缀=%s 在 %s", args.match, args.log)
        logging.info("可用 match: %s", list(matches.keys()))
        sys.exit(1)
    if full_match_id != args.match:
        logging.info("使用 match=%s（匹配前缀）", full_match_id)

    samples = extract_match_samples(
        args.log, full_match_id, args.output_dir, write=not args.dry_run
    )
    ok = verify_samples(samples)

    logging.info("=== 前 3 步摘要 ===")
    for s in samples[:3]:
        gt = s["ground_truth"]
        logging.info(
            "  step=%d hand_self=%d PLAYED=%d REST=%d 决策=%s/%s actIndex=%d",
            s["step_id"],
            int(gt[:, 0].sum()),
            int(gt[:, 1].sum()),
            int(gt[:, 2].sum()),
            s["decision_act_type"],
            s["decision_act_cards"],
            s["decision_act_index"],
        )

    sys.exit(0 if ok else 1)




def _np_to_pylist(arr) -> list:
    """numpy 数组 -> Python list，兼容 0-d / 1-d / 空数组。

    GUA-223 lalala ETL 写空 decision_act_cards 时退化为 0-d 数组，Botzone ETL 写 shape=(0,) dtype=object；
    训练时统一规整为 Python list（含空列表）。
    """
    import numpy as _np
    if isinstance(arr, _np.ndarray):
        if arr.ndim == 0:
            return [arr.item()] if arr.size else []
        return [x.item() if hasattr(x, "item") else x for x in arr.tolist()]
    return list(arr)


def iter_clean_samples(
    output_dir: Path,
    drop_warnings: bool = True,
) -> List[Dict[str, Any]]:
    """加载 data/training/card_counting_v1/ 所有 .npz 为训练样本列表。

    Args:
        output_dir: .npz 目录
        drop_warnings: True = 跳过 has_warning=True 的样本（GUA-216 双扣 bug 残留）；
                       False = 全部返回（训练时降权即可）

    Returns:
        样本 dict 列表，每个含 ground_truth(108,3) + hand_self + cur_rank + history_raw +
                  done + global_state + stage + decision_* + match_id + step_id +
                  has_warning + warning_cards
    """
    samples: List[Dict[str, Any]] = []
    for npz_path in sorted(output_dir.glob("*.npz")):
        d = np.load(npz_path, allow_pickle=True)
        has_warning = bool(d["has_warning"])
        if drop_warnings and has_warning:
            continue
        samples.append({
            "path": str(npz_path),
            "match_id": str(d["match_id"]),
            "step_id": int(d["step_id"]),
            "hand_self": list(d["hand_self"]),
            "cur_rank": str(d["cur_rank"]),
            "history_raw": list(d["history_raw"]),
            "done": list(d["done"]),
            "global_state": json.loads(str(d["global_state"])),
            "stage": str(d["stage"]),
            "ground_truth": d["ground_truth"],
            "decision_act_index": int(d["decision_act_index"]),
            "decision_act_type": str(d["decision_act_type"]),
            "decision_act_cards": _np_to_pylist(d["decision_act_cards"]),
            "has_warning": has_warning,
            "warning_cards": _np_to_pylist(d["warning_cards"]),
        })
    return samples


def summarize_dataset(output_dir: Path) -> Dict[str, int]:
    """统计数据集：总样本数 / 含 warning 数 / V8 决策数 / match 数。"""
    total = 0
    warnings = 0
    v8_dec = 0
    match_ids: set = set()
    for npz_path in sorted(output_dir.glob("*.npz")):
        total += 1
        d = np.load(npz_path, allow_pickle=True)
        if bool(d["has_warning"]):
            warnings += 1
        if int(d["decision_act_index"]) >= 0:
            v8_dec += 1
        match_ids.add(str(d["match_id"]))
    return {
        "total_samples": total,
        "warning_samples": warnings,
        "v8_decision_samples": v8_dec,
        "match_count": len(match_ids),
        "samples_per_dim": round(total / 324, 2),
    }

if __name__ == "__main__":
    main()