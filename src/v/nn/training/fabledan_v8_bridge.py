# -*- coding: utf-8 -*-
"""FableDan 仿真引擎 ↔ V8 botzone_adapter 桥接层（V8 自学习 step-c）。

FableDan `engine` 负责整副仿真与 MC 回报；本模块把决策点 `obs` 转为 V8 可用的
手牌字符串 + OpenGuanDan `actionList`，并支持将 V8 所选着法映射回 FableDan legal index。

平台牌型名使用 PascalCase（Single / ThreeWithTwo / StraightFlush …）。
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from fabledan.combos import PASS, ROCKET, STRAIGHT, SFLUSH, TYPE_NAMES

from src.communication.botzone_adapter import (
    ActionListGenerator,
    bz_to_v8_card,
)
from src.v.nn.training.fd_env import ensure_fabledan_importable

ensure_fabledan_importable()
from fabledan.encode import encode_flat  # noqa: E402

# FableDan level index 0..12 (A=0) -> V8 cur_rank
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


def level_index_to_v8(lv: int) -> str:
    return FD_LEVEL_TO_V8[lv]


def hand_bz_to_v8(hand: List[int]) -> List[str]:
    return [bz_to_v8_card(c) for c in hand]


def fd_move_to_v8_action(move, cur_rank: str) -> list:
    """FableDan Move -> OpenGuanDan action [Type, Rank, cards_str]."""
    if move.type == PASS:
        return ["PASS", "PASS", "PASS"]
    v8_type = FD_TYPE_TO_V8[TYPE_NAMES[move.type]]
    cards = hand_bz_to_v8(move.cards)
    if move.type == ROCKET:
        return ["Bomb", "R", cards]
    if move.type in (STRAIGHT, SFLUSH):
        low_rank = fd_rank_to_v8(move.claim_ranks[0]) if move.claim_ranks else "2"
        return [v8_type, low_rank, cards]
    pr = move.claim_ranks[0] if move.claim_ranks else 0
    rank = fd_rank_to_v8(pr)
    return [v8_type, rank, cards]


@dataclass
class V8DecisionContext:
    """单决策点的 V8 侧视图（由 FableDan obs 导出）。"""

    player: int
    cur_rank: str
    level_index: int
    hand_v8: List[str]
    hand_bz: List[int]
    left: List[int]
    done: List[bool]
    leading: bool
    lead_v8: Optional[list]
    n_fd_legal: int


def obs_to_v8_context(obs: dict) -> V8DecisionContext:
    lv = obs["level"]
    cur = level_index_to_v8(lv)
    lead = obs.get("lead")
    leading = lead is None or lead.type == PASS
    lead_v8 = None if leading else fd_move_to_v8_action(lead, cur)
    return V8DecisionContext(
        player=obs["player"],
        cur_rank=cur,
        level_index=lv,
        hand_v8=hand_bz_to_v8(obs["hand"]),
        hand_bz=list(obs["hand"]),
        left=list(obs["left"]),
        done=list(obs["done"]),
        leading=leading,
        lead_v8=lead_v8,
        n_fd_legal=len(obs["legal"]),
    )


def generate_v8_action_list(ctx: V8DecisionContext) -> List[list]:
    gen = ActionListGenerator(cur_rank=ctx.cur_rank)
    if ctx.leading:
        return gen.generate_lead_actions(ctx.hand_v8)
    assert ctx.lead_v8 is not None
    return gen.generate_follow_actions(ctx.hand_v8, ctx.lead_v8)


def v8_action_to_fd_index(legal: list, v8_action: list) -> Optional[int]:
    """将 V8 action 匹配到 FableDan legal 列表下标；无法匹配时返回 None。"""
    if v8_action[0] == "PASS":
        for i, m in enumerate(legal):
            if m.type == PASS:
                return i
        return None
    target = Counter(v8_action[2]) if len(v8_action) >= 3 else Counter()
    for i, m in enumerate(legal):
        if m.type == PASS:
            continue
        got = Counter(hand_bz_to_v8(m.cards))
        if got == target:
            return i
    return None


def list_mappable_v8_actions(
    obs: dict,
    action_list: List[list],
) -> List[Tuple[int, int, np.ndarray]]:
    """可映射的 (v8_index, fd_index, mc_feature) 三元组。"""
    legal = obs["legal"]
    out: List[Tuple[int, int, np.ndarray]] = []
    for v8_idx, action in enumerate(action_list):
        fd_idx = v8_action_to_fd_index(legal, action)
        if fd_idx is None:
            continue
        feat = np.asarray(encode_flat(obs, legal[fd_idx]), dtype=np.float32)
        out.append((v8_idx, fd_idx, feat))
    return out


def encode_mc_feature(obs: dict, v8_action: list) -> np.ndarray:
    """V8 着法 → DMC 训练特征（与 fd_native 同维 encode_flat）。"""
    fd_idx = v8_action_to_fd_index(obs["legal"], v8_action)
    if fd_idx is None:
        raise ValueError("v8 action not mappable to FableDan legal")
    return np.asarray(encode_flat(obs, obs["legal"][fd_idx]), dtype=np.float32)


@dataclass
class V8TrainingSample:
    """V8 自学习样本（单步）；z_mc 在副末回填。"""

    player: int
    cur_rank: str
    hand_v8: List[str]
    action_list: List[list]
    chosen_action: list
    chosen_v8_index: int
    chosen_fd_index: int
    n_v8_legal: int
    n_fd_legal: int
    feature: Optional[np.ndarray] = None
    z_mc: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player": self.player,
            "cur_rank": self.cur_rank,
            "hand_size": len(self.hand_v8),
            "n_v8_legal": self.n_v8_legal,
            "n_fd_legal": self.n_fd_legal,
            "chosen_type": self.chosen_action[0],
            "chosen_v8_index": self.chosen_v8_index,
            "chosen_fd_index": self.chosen_fd_index,
            "has_feature": self.feature is not None,
            "z_mc": self.z_mc,
        }


def build_v8_sample(obs: dict, v8_index: int, action_list: List[list]) -> V8TrainingSample:
    ctx = obs_to_v8_context(obs)
    chosen = action_list[v8_index]
    fd_idx = v8_action_to_fd_index(obs["legal"], chosen)
    if fd_idx is None:
        fd_idx = -1
    return V8TrainingSample(
        player=ctx.player,
        cur_rank=ctx.cur_rank,
        hand_v8=ctx.hand_v8,
        action_list=action_list,
        chosen_action=chosen,
        chosen_v8_index=v8_index,
        chosen_fd_index=fd_idx,
        n_v8_legal=len(action_list),
        n_fd_legal=ctx.n_fd_legal,
        feature=encode_mc_feature(obs, chosen) if fd_idx >= 0 else None,
    )


def v8_sample_to_export_record(sample: V8TrainingSample) -> Dict[str, Any]:
    """Botzone 对照用 JSON 记录（单步一条）。"""
    return {
        "player": sample.player,
        "cur_rank": sample.cur_rank,
        "hand_v8": sorted(sample.hand_v8),
        "action_list": sample.action_list,
        "chosen_action": sample.chosen_action,
        "chosen_v8_index": sample.chosen_v8_index,
        "chosen_fd_index": sample.chosen_fd_index,
        "n_v8_legal": sample.n_v8_legal,
        "n_fd_legal": sample.n_fd_legal,
        "z_mc": sample.z_mc,
    }


def export_v8_samples(
    samples: Sequence[V8TrainingSample],
    path: Union[str, Path],
    *,
    append: bool = False,
) -> int:
    """将 V8TrainingSample 列表落盘为 JSONL（每行一步决策）。

    Returns:
        写入条数。
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    written = 0
    with out.open(mode, encoding="utf-8") as fh:
        for sample in samples:
            fh.write(json.dumps(v8_sample_to_export_record(sample), ensure_ascii=False))
            fh.write("\n")
            written += 1
    return written
