# -*- coding: utf-8 -*-
"""
V7 动态特征工程 — LSTM 历史编码 64 维（GUA-037b）

输出：
  - dynamic_hidden: 64 维 LSTM hidden state（出牌历史 + numof* 序列）
  - total_dim = STATIC_STATE_DIM (124) + DYNAMIC_HIDDEN_DIM (64) = 188 维

序列构造（每步 8 维）：
  [curAction_type_onehot(5), curAction_rank_norm(1), myPos_onehot(1), numofplayers_norm(1)]
  其中 curAction_type one-hot: [PASS, Single, Pair, ..., Bomb] 取前 5 类

约束：
  - 总维度 ≤ 200（实施方案阈值）
  - LSTM 序列长度 ≤ 20（超长截断）
  - 推理延迟 ≤ 50ms/step
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple

# ── 常量 ──────────────────────────────────────────────
DYNAMIC_HIDDEN_DIM = 64        # LSTM hidden 输出维度
MAX_SEQ_LEN = 20               # 最大序列长度（超长截断）
SEQ_STEP_DIM = 8               # 每步特征维度

# 动作类型 → one-hot 索引（前 5 类 + 兜底）
ACTION_TYPE_MAP: Dict[str, int] = {
    "PASS": 0,
    "Single": 1,
    "Pair": 2,
    "Trips": 3,
    "ThreeWithTwo": 3,  # 三带二归入 Trips 类
    "TwoTrips": 4,
    "Straight": 4,       # 顺子归入连对类（同为多张组合）
    "ThreePair": 4,
    "Bomb": 4,
}
ACTION_TYPE_VOCAB = 5  # 0=PASS, 1=Single, 2=Pair, 3=Trips/ThreeWithTwo, 4=Complex

# 最大 rank 值（用于归一化）
MAX_RANK_VALUE = 12  # A=12


# ── 序列构造 ──────────────────────────────────────────

def _action_type_to_onehot(action: Any) -> List[float]:
    """将 action 转换为 5 维 one-hot（前 5 类）。"""
    onehot = [0.0] * ACTION_TYPE_VOCAB
    if isinstance(action, list) and len(action) > 0:
        type_str = str(action[0])
    elif isinstance(action, str):
        type_str = action
    else:
        type_str = "PASS"

    idx = ACTION_TYPE_MAP.get(type_str, 4)  # 兜底归入 Complex
    onehot[idx] = 1.0
    return onehot


def _action_rank_norm(action: Any) -> float:
    """从 action 中提取 rank 并归一化到 [0, 1]。"""
    if not isinstance(action, list) or len(action) < 2:
        return 0.0
    rank_str = str(action[1])
    rank_map = {r: i for i, r in enumerate(["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"])}
    return rank_map.get(rank_str, 0) / MAX_RANK_VALUE


def _mypos_onehot(my_pos: int, cur_pos: int) -> float:
    """本方/队友=1，对手=0。"""
    partner_pos = (my_pos + 2) % 4
    return 1.0 if cur_pos == my_pos or cur_pos == partner_pos else 0.0


def _numofplayers_norm(numofplayers: Optional[List[int]]) -> float:
    """numofplayers[4] 最大值归一化。"""
    if not numofplayers or len(numofplayers) < 4:
        return 0.0
    return max(numofplayers) / 27.0  # 每人最多 27 张


def build_history_sequence(
    history: List[Dict[str, Any]],
    my_pos: int,
) -> np.ndarray:
    """
    构造出牌历史序列。

    Args:
        history: 每步 dict，包含 curAction / curPos / numofplayers 等
        my_pos: 本方座位号

    Returns:
        shape=(seq_len, SEQ_STEP_DIM) 的 float32 数组，seq_len ≤ MAX_SEQ_LEN
    """
    if not history:
        return np.zeros((0, SEQ_STEP_DIM), dtype=np.float32)

    steps = []
    for h in history[-MAX_SEQ_LEN:]:  # 只取最近 20 步
        action = h.get("curAction", "PASS")
        cur_pos = h.get("curPos", -1)
        numofplayers = h.get("numofplayers", None)

        step_features = []
        # 5 维 action type one-hot
        step_features.extend(_action_type_to_onehot(action))
        # 1 维 action rank 归一化
        step_features.append(_action_rank_norm(action))
        # 1 维 myPos 标志
        step_features.append(_mypos_onehot(my_pos, cur_pos))
        # 1 维 numofplayers 归一化
        step_features.append(_numofplayers_norm(numofplayers))
        steps.append(step_features)

    return np.array(steps, dtype=np.float32)


# ── LSTM Encoder ──────────────────────────────────────

def lstm_encode(
    seq: np.ndarray,
    hidden_dim: int = DYNAMIC_HIDDEN_DIM,
) -> np.ndarray:
    """
    纯 numpy 实现的简化 LSTM 编码器（无需 torch）。

    将变长序列编码为固定长度 hidden state。
    使用简化版 LSTM（单层，无 torch 依赖，保证推理延迟 ≤ 50ms）。

    Args:
        seq: shape=(seq_len, SEQ_STEP_DIM) 输入序列
        hidden_dim: hidden 维度

    Returns:
        shape=(hidden_dim,) 的 float32 数组
    """
    if seq.shape[0] == 0:
        return np.zeros(hidden_dim, dtype=np.float32)

    # 使用 numpy 矩阵乘法模拟单层 LSTM
    input_dim = seq.shape[1]

    # 用随机正交初始化（固定 seed 保证确定性）
    rng = np.random.RandomState(42)

    # LSTM 权重（input→hidden + hidden→hidden）
    W_i = rng.randn(input_dim, hidden_dim) * 0.1
    W_f = rng.randn(input_dim, hidden_dim) * 0.1
    W_o = rng.randn(input_dim, hidden_dim) * 0.1
    W_c = rng.randn(input_dim, hidden_dim) * 0.1
    U_i = rng.randn(hidden_dim, hidden_dim) * 0.1
    U_f = rng.randn(hidden_dim, hidden_dim) * 0.1
    U_o = rng.randn(hidden_dim, hidden_dim) * 0.1
    U_c = rng.randn(hidden_dim, hidden_dim) * 0.1

    def sigmoid(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -10, 10)))

    h = np.zeros(hidden_dim, dtype=np.float32)
    c = np.zeros(hidden_dim, dtype=np.float32)

    for t in range(seq.shape[0]):
        x_t = seq[t]
        i_t = sigmoid(x_t @ W_i + h @ U_i)
        f_t = sigmoid(x_t @ W_f + h @ U_f)
        o_t = sigmoid(x_t @ W_o + h @ U_o)
        c_tilde = np.tanh(x_t @ W_c + h @ U_c)
        c = f_t * c + i_t * c_tilde
        h = o_t * np.tanh(c)

    return h.astype(np.float32)


# ── 主入口 ────────────────────────────────────────────

def extract_dynamic_features(
    game_state: Dict[str, Any],
    static_features: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    提取 64 维动态特征（LSTM 历史编码）。

    Args:
        game_state: 游戏状态字典，需含 history（出牌历史列表）和 myPos
        static_features: 可选的静态特征（当前未使用，预留拼接层）

    Returns:
        shape=(DYNAMIC_HIDDEN_DIM,) 的 float32 数组
    """
    history = game_state.get("history", [])
    if not isinstance(history, list):
        history = []

    my_pos = game_state.get("myPos", 0)

    seq = build_history_sequence(history, my_pos)
    hidden = lstm_encode(seq, DYNAMIC_HIDDEN_DIM)
    return hidden


def extract_combined_features(
    game_state: Dict[str, Any],
    static_features: np.ndarray,
) -> np.ndarray:
    """
    拼接静态特征 + LSTM 动态编码，输出 188 维特征向量。

    Args:
        game_state: 游戏状态
        static_features: shape=(STATIC_STATE_DIM,) 的静态特征

    Returns:
        shape=(STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM,) = (188,) 的 float32 数组
    """
    dynamic = extract_dynamic_features(game_state, static_features)
    combined = np.concatenate([static_features, dynamic], axis=0)
    return combined.astype(np.float32)
