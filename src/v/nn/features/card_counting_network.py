# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 1
CardCountingNetwork — LSTM 50K baseline

> 真源：docs/guandan-brain/CardCountingNetwork-训练方案.md §四 + §八 Phase 1
> 关联：GUA-223 / GUA-057 / 训练方案 §11.1（验收修订见 docs/analysis/param_data_ratio.md）

模型结构：
  - 输入编码：history 4 turn × 128 维 + hand_context 461 维 = 461 维
  - LSTM(1 层, hidden=32) 处理 history 序列（4 步）
  - 接 hand_context + LSTM hidden → head(Linear → 324 = 108×3)
  - 参数量 ~19K（在 LSTM 5K-50K 区间）

输入维度：
  - history_seq: (4, 128) 4 个 turn × (player_onehot(4) + action_slot(54) + claim_slot(54) + len_bucket(16))
  - hand_context: (461,) = hand_self(108) + cur_rank_emb(4) + stage_onehot(7) + tribute_vec(335) + rest_distribution(7)
  - 输出: (108, 3) one-hot-like logits {MY_HAND, PLAYED, REST}

训练：
  - loss: masked CE (3 类)
  - optimizer: Adam(lr=3e-4, wd=1e-4)
  - batch_size: 32
  - max_epochs: 30（Phase 1 修订：577 样本不期望收敛）

不动档：本模块只新增文件 + 提供 forward 接口；不在 _heuristic_select 接入。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.v.nn.features.stage_encoding import (
    STAGE_DIM,
    TRIBUTE_VEC_DIM,
    build_input_features,
)


logger = logging.getLogger("card_counting_network")


# === 维度常量 ===

HISTORY_TURN_DIM = 128  # 4 + 54 + 54 + 16
HISTORY_NUM_TURNS = 4
HISTORY_SEQ_DIM = HISTORY_NUM_TURNS * HISTORY_TURN_DIM  # 512

HAND_CONTEXT_DIM = 108 + 4 + STAGE_DIM + TRIBUTE_VEC_DIM + 7  # = 461
# 108 (hand_self) + 4 (cur_rank onehot) + 7 (stage) + 335 (tribute) + 7 (rest_dist)

HIDDEN_DIM = 32
OUTPUT_DIM = 108 * 3  # 324


# === History turn 编码器（无 torch 依赖） ===

def encode_history_turn(player_id: int, response: list) -> np.ndarray:
    """单 turn 编码：player_onehot(4) + action_slot(54) + claim_slot(54) + len_bucket(16) = 128 维。"""
    vec = np.zeros(HISTORY_TURN_DIM, dtype=np.float32)
    if 0 <= player_id < 4:
        vec[player_id] = 1.0
    action, claim = [], []
    if isinstance(response, list) and len(response) >= 1 and isinstance(response[0], list):
        action = response[0]
        if len(response) >= 2 and isinstance(response[1], list):
            claim = response[1]
    for ci in action:
        try:
            slot = int(ci) % 54
            if slot < 54:
                vec[4 + slot] = 1.0
        except (TypeError, ValueError):
            pass
    for ci in claim:
        try:
            slot = int(ci) % 54
            if slot < 54:
                vec[58 + slot] = 1.0
        except (TypeError, ValueError):
            pass
    # len bucket (上限 15)
    n = min(len(action), 15)
    vec[112 + n] = 1.0
    return vec


def encode_history_sequence(history_raw: list) -> np.ndarray:
    """4 turn history → (4, 128) sequence。"""
    seq = np.zeros((HISTORY_NUM_TURNS, HISTORY_TURN_DIM), dtype=np.float32)
    if not isinstance(history_raw, list):
        return seq
    for i, entry in enumerate(history_raw[:HISTORY_NUM_TURNS]):
        if isinstance(entry, dict):
            pid = entry.get("player", -1)
            resp = entry.get("response", [])
        elif isinstance(entry, list):
            pid = i
            resp = entry
        else:
            continue
        seq[i] = encode_history_turn(pid, resp)
    return seq


def encode_hand_self(hand_cards: List[str]) -> np.ndarray:
    """V8 字符串手牌列表 → 108 维。"""
    vec = np.zeros(108, dtype=np.float32)
    for c in hand_cards:
        try:
            from src.v.nn.features.stage_encoding import v8_to_slot
            slot = v8_to_slot(c)
            if vec[slot] < 2:
                vec[slot] += 1.0
            if slot + 54 < 108 and vec[slot + 54] < 1:
                vec[slot + 54] += 1.0
        except KeyError:
            pass
    return vec


def encode_cur_rank(cur_rank: str) -> np.ndarray:
    """cur_rank 字符串 → 4 维 one-hot (A/2-9/T/J/Q/K/H2/HR → 14 简化)。"""
    vec = np.zeros(4, dtype=np.float32)
    rank_to_idx = {"A": 0, "2": 1, "5": 2, "K": 3}
    if cur_rank in rank_to_idx:
        vec[rank_to_idx[cur_rank]] = 1.0
    else:
        vec[0] = 1.0  # default A
    return vec


def encode_rest_distribution(rest_cards: List[str]) -> np.ndarray:
    """未出牌 V8 列表 → 7 维分布桶（None/1-3/4-6/7-9/10-13/14-20/21+）。"""
    vec = np.zeros(7, dtype=np.float32)
    n = len(rest_cards) if rest_cards else 0
    if n == 0:
        vec[0] = 1.0
    elif n <= 3:
        vec[1] = 1.0
    elif n <= 6:
        vec[2] = 1.0
    elif n <= 9:
        vec[3] = 1.0
    elif n <= 13:
        vec[4] = 1.0
    elif n <= 20:
        vec[5] = 1.0
    else:
        vec[6] = 1.0
    return vec


def build_hand_context(
    hand_cards: List[str],
    cur_rank: str,
    stage: str,
    global_state: dict,
    tribute_events: Optional[List[dict]] = None,
    rest_cards: Optional[List[str]] = None,
) -> np.ndarray:
    """拼装 hand_context = hand_self(108) + cur_rank(4) + stage(7) + tribute(335) + rest_dist(7) = 461 维。"""
    vec_hand = encode_hand_self(hand_cards)
    vec_rank = encode_cur_rank(cur_rank)
    vec_stage_tribute = build_input_features(stage, global_state, tribute_events)
    vec_rest = encode_rest_distribution(rest_cards or [])
    return np.concatenate([vec_hand, vec_rank, vec_stage_tribute, vec_rest])


def build_sample_input(sample: dict) -> tuple:
    """从 ETL sample dict → (history_seq (4,128), hand_context (461,))。"""
    history_seq = encode_history_sequence(sample["history_raw"])
    # 反推 rest_cards（粗略）：从 history 累计 + hand_self 推 108-MY-PLAYED
    # 简化：rest 数量（不取具体牌）
    n_my = len(sample["hand_self"])
    n_played = sum(
        len(action)
        for _pid, action, _claim in _safe_parse_history(sample["history_raw"])
        if action
    )
    rest_n = max(0, 108 - n_my - n_played)
    rest_cards = ["?"] * rest_n
    hand_ctx = build_hand_context(
        hand_cards=sample["hand_self"],
        cur_rank=sample.get("cur_rank", "A"),
        stage=sample.get("stage", "play"),
        global_state=sample.get("global_state", {}),
        tribute_events=None,
        rest_cards=rest_cards,
    )
    return history_seq, hand_ctx


def _safe_parse_history(history):
    """安全解析 history 列表，返回 [(player, action, claim), ...]。"""
    out = []
    if not isinstance(history, list):
        return out
    for i, entry in enumerate(history):
        if isinstance(entry, dict):
            pid = entry.get("player", -1)
            resp = entry.get("response", [])
        elif isinstance(entry, list):
            pid = i
            resp = entry
        else:
            continue
        action, claim = [], []
        if isinstance(resp, list) and len(resp) >= 1 and isinstance(resp[0], list):
            action = resp[0]
            if len(resp) >= 2 and isinstance(resp[1], list):
                claim = resp[1]
        out.append((pid, action, claim))
    return out


# === PyTorch 模型 ===

class CardCountingNet(nn.Module):
    """CardCountingNetwork LSTM baseline 模型。"""

    def __init__(
        self,
        hidden_dim: int = HIDDEN_DIM,
        num_layers: int = 1,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        # history encoder: 4 turn × 128 → LSTM
        self.turn_proj = nn.Linear(HISTORY_TURN_DIM, hidden_dim)
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        # hand context encoder: 461 → hidden_dim
        self.hand_proj = nn.Linear(HAND_CONTEXT_DIM, hidden_dim)
        # fusion: hidden (lstm) + hidden (hand) → 324
        self.fusion = nn.Linear(hidden_dim * 2, hidden_dim)
        self.head = nn.Linear(hidden_dim, OUTPUT_DIM)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        history_seq: torch.Tensor,  # (B, 4, 128)
        hand_context: torch.Tensor,  # (B, 461)
    ) -> torch.Tensor:
        B = history_seq.shape[0]
        # history LSTM
        h = self.turn_proj(history_seq)  # (B, 4, hidden)
        h, (hn, _cn) = self.lstm(h)  # hn: (1, B, hidden)
        lstm_feat = hn[-1]  # (B, hidden)
        # hand context
        hand_feat = self.hand_proj(hand_context)  # (B, hidden)
        # fusion
        fused = torch.cat([lstm_feat, hand_feat], dim=-1)  # (B, 2*hidden)
        fused = self.dropout(F.relu(self.fusion(fused)))  # (B, hidden)
        out = self.head(fused)  # (B, 324)
        # reshape to (B, 108, 3)
        return out.view(B, 108, 3)


def count_parameters(model: nn.Module) -> int:
    """返回可训练参数总数。"""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# === 便捷 load / save ===

def save_checkpoint(model: CardCountingNet, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": {
            "hidden_dim": model.hidden_dim,
            "num_layers": 1,  # 默认
        },
    }, path)


def load_checkpoint(path: Path, device: str = "cpu") -> CardCountingNet:
    ckpt = torch.load(path, map_location=device, weights_only=False)
    cfg = ckpt.get("config", {})
    model = CardCountingNet(
        hidden_dim=cfg.get("hidden_dim", HIDDEN_DIM),
        num_layers=cfg.get("num_layers", 1),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model