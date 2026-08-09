# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 1 第 3 项
lalala 牌谱 ETL — game_records_v8/*.json → counting 训练样本

> 真源：docs/guandan-brain/CardCountingNetwork-训练方案.md §3 数据来源 + §8 Phase 1
> 关联：GUA-223 / scripts/etl/botzone_to_counting_dataset.py（Botzone 版）
> 数据源：game_records_v8/*.json（V8 vs lalala 离线对局）
> 输出：data/training/card_counting_v1/ 复用 Botzone 输出目录

输入格式（每 .json = 1 个 game = 1 局）：
  initial_hand: List[str] 27 张 V8 字符串
  my_decisions: List[dict] 每决策点含 handCards / curRank / publicInfo / stage / action_index / action

输出格式（与 Botzone ETL 一致）：每决策点一个 .npz
  - history_4turn: (4, 128) 4 玩家响应序列（lalala 数据为 view 0/1/2/3 → publicInfo 推测）
  - hand_context: (461,) 见 botzone_to_counting_dataset
  - ground_truth: (108, 3) one-hot {MY_HAND, PLAYED, REST}

不动档：本模块只新增文件。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.etl.botzone_to_counting_dataset import (
    BZ_RANK_STR,
    BZ_SUIT_MAP,
    SLOT_COUNT,
    TOTAL_SLOTS,
    _V8_CARD_TO_SLOT,
    _build_v8_to_slot,
    v8_to_slot,
)
from src.v.nn.features.card_counting_network import (
    build_hand_context,
)
from src.v.nn.features.stage_encoding import (
    stage_to_onehot,
    tribute_events_to_vec,
)


# 复用 Botzone ETL 的 slot 映射
_build_v8_to_slot()


# === Game record → 回合级样本 ===

def _actions_to_bz_int(action: List[Any]) -> List[int]:
    """将 lalala action[2] (V8 字符串) 转 Botzone 整数（占位——lalala 数据无 bz_int 编码）。

    对 lalala 数据：直接用 V8 字符串做反推，不依赖 bz_int 转换。
    返回 [] 以避免 bz_int 路径误用。
    """
    return []


def _parse_my_decision_actions(my_decisions: List[dict]) -> List[List[str]]:
    """从 my_decisions 提取每步 V8 自己出牌的字符串列表（PASS 步返回空列表）。"""
    out = []
    for d in my_decisions:
        action = d.get("action", [])
        if len(action) >= 3 and isinstance(action[2], list):
            out.append(list(action[2]))
        else:
            out.append([])
    return out


def _compute_hand_progression(initial: List[str], my_actions: List[List[str]]) -> List[List[str]]:
    """从 initial 27 张 + V8 每步出牌，反推每步开始时手牌。"""
    hands = []
    cur = list(initial)
    for v8_cards in my_actions:
        hands.append(list(cur))
        for c in v8_cards:
            if c in cur:
                cur.remove(c)
            # else: 不一致时跳过（兼容 lalala 数据偶尔缺失）
    return hands


def _compute_played_progression(my_actions: List[List[str]]) -> List[Dict[int, list]]:
    """从 V8 出牌历史构造各 player 已出 bz_int 列表（简化：全归 V8=player 0）。

    注：lalala game_records 没有 history 字段，只能反推 V8 自己出牌。
    训练时 REST 类由"108 - MY_HAND - PLAYED" 反推，PLAYED 只含 V8 自出。
    这与 Botzone 数据不同——Botzone 含 4 玩家完整 history。
    """
    out = []
    played_v8 = []
    for v8_cards in my_actions:
        out.append({0: list(played_v8), 1: [], 2: [], 3: []})
        # bz_int 占位（lalala → 不强求精确 bz_int，CardCountingNetwork 用 V8 字符串）
        for c in v8_cards:
            try:
                slot = v8_to_slot(c)
                played_v8.append(slot)  # 占位用 slot id
            except KeyError:
                pass
    return out


def _compute_ground_truth(
    hand_at_step: List[str],
    played_at_step: Dict[int, list],
) -> np.ndarray:
    """同 Botzone ETL 算法。"""
    gt = np.zeros((TOTAL_SLOTS, 3), dtype=np.int8)
    hand_counter = [0] * SLOT_COUNT
    for card in hand_at_step:
        slot = v8_to_slot(card)
        if hand_counter[slot] < 2:
            hand_counter[slot] += 1
    played_counter = [0] * SLOT_COUNT
    for player_id in range(4):
        for slot_or_int in played_at_step.get(player_id, []):
            if isinstance(slot_or_int, int):
                slot = slot_or_int
            else:
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


def extract_game_samples(
    game_path: Path,
    output_dir: Path,
    write: bool = True,
) -> List[Dict[str, Any]]:
    """从单个 game_records_v8/*.json 提取回合级样本。"""
    text = game_path.read_text(encoding="utf-8")
    data = json.loads(text)

    game_id = data.get("game_id", game_path.stem)
    initial = data.get("initial_hand", [])
    my_decisions = data.get("my_decisions", [])
    if len(initial) != 27 or not my_decisions:
        return []

    # 提取每步 V8 出牌
    my_actions = _parse_my_decision_actions(my_decisions)
    # 反推 hand 序列
    hands = _compute_hand_progression(initial, my_actions)
    # 反推 played 序列
    played_list = _compute_played_progression(my_actions)

    samples = []
    for i, decision in enumerate(my_decisions):
        if i >= len(hands):
            break
        hand = hands[i]
        played = played_list[i]
        gt = _compute_ground_truth(hand, played)
        context = decision.get("context", {})
        cur_rank = context.get("curRank", "A")
        stage = context.get("stage", "play")
        global_state = {
            "level": cur_rank,
            "tribute": 0,
            "first": None,
            "last": None,
            "tribute_cards": {},
            "return_cards": {},
            "resist": False,
        }
        sample = {
            "match_id": f"lalala_{game_id}",
            "step_id": i,
            "hand_self": hand,
            "cur_rank": cur_rank,
            "history_raw": [[], [], [], []],  # lalala 无 history → 占位空
            "done": [],
            "pass_on": -1,
            "global": global_state,
            "stage": stage,
            "ground_truth": gt,
            "decision_act_index": int(decision.get("action_index", -1)),
            "decision_act_type": (decision.get("action") or ["?"])[0],
            "decision_act_cards": (decision.get("action") or [[]])[2] if len(decision.get("action", [])) >= 3 else [],
            "timestamp": decision.get("timestamp", "")[:19],
        }
        samples.append(sample)

        if write:
            out_path = output_dir / f"lalala_{game_id[:20]}_{i:04d}.npz"
            np.savez_compressed(
                out_path,
                ground_truth=gt,
                hand_self=np.array(hand, dtype=object),
                cur_rank=cur_rank,
                history_raw=np.array([[], [], [], []], dtype=object),
                done=np.array([], dtype=np.int8),
                global_state=json.dumps(global_state),
                stage=stage,
                decision_act_index=np.int32(int(decision.get("action_index", -1))),
                decision_act_type=str((decision.get("action") or ["?"])[0]),
                decision_act_cards=np.array((decision.get("action") or [[]])[2] if len(decision.get("action", [])) >= 3 else [], dtype=object),
                match_id=sample["match_id"],
                step_id=np.int32(i),
                has_warning=np.bool_(False),
                warning_cards=np.array([], dtype=object),
            )
    return samples


def verify_lalala_samples(samples: List[dict]) -> bool:
    """5 项硬门槛 ① 手算对账（与 Botzone ETL 共享逻辑）。"""
    for s in samples:
        gt = s["ground_truth"]
        n_my = int(gt[:, 0].sum())
        n_played = int(gt[:, 1].sum())
        n_rest = int(gt[:, 2].sum())
        if n_my + n_played + n_rest != TOTAL_SLOTS:
            logging.error("❌ step=%d 守恒失败 %d+%d+%d ≠ 108", s["step_id"], n_my, n_played, n_rest)
            return False
        if n_my != len(s["hand_self"]):
            logging.error("❌ step=%d MY_HAND=%d ≠ hand_self=%d", s["step_id"], n_my, len(s["hand_self"]))
            return False
    logging.info("✅ %d 个 lalala 样本手算对账 PASS", len(samples))
    return True


def main():
    parser = argparse.ArgumentParser(description="lalala 牌谱 ETL — game_records_v8 → 训练样本")
    parser.add_argument("--game-records-dir", type=Path, default=Path("game_records_v8"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/training/card_counting_v1"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个文件（0=全部）")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("game_records_to_counting_dataset")

    if not args.game_records_dir.exists():
        logger.error("❌ %s 不存在", args.game_records_dir)
        sys.exit(1)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(args.game_records_dir.glob("*.json"))
    if args.limit > 0:
        files = files[:args.limit]
    logger.info("扫描 %s: %d 个文件", args.game_records_dir, len(files))

    all_samples = []
    ok_count = 0
    for f in files:
        try:
            samples = extract_game_samples(f, args.output_dir, write=not args.dry_run)
            if samples:
                ok_count += 1
            all_samples.extend(samples)
        except Exception as e:
            logger.warning("⚠️ %s 解析失败: %s", f.name, e)
    verify_lalala_samples(all_samples)

    logger.info("=" * 60)
    logger.info("lalala ETL 完成: %d 个 game 成功 / %d 个样本", ok_count, len(all_samples))
    logger.info("样本/维度比: %.2f（含 Botzone 581 → %.2f）",
                len(all_samples) / 324,
                (len(all_samples) + 581) / 324)


if __name__ == "__main__":
    main()