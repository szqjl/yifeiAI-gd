# -*- coding: utf-8 -*-
"""
GUA-038 BC 数据集 — 从 game_records/*.json 提取 (state_512d, action_index) 标签对。

数据来源：
  - game_records/*.json（M3 离线 game_records 或 V7 录牌）
  - 筛选策略：仅用 batch_game_result.victoryNum[0] >= 2 的局（评审 §7.4 约束 4）

状态重建策略：
  1. 优先从录牌的 record_step.full_state 重建（V7-internal 录牌格式）
  2. fallback：从 my_decisions + actions 列表重建（兼容 M3 旧格式）

与 M3 的耦合约束：
  - **只读** game_records/*.json
  - **禁止** `from src.m.m3 import *`
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.v.nn.features.static_features import extract_static_features, STATIC_STATE_DIM, extract_state_belief, BELIEF_DIM
from src.v.nn.features.dynamic_features import extract_dynamic_features, DYNAMIC_HIDDEN_DIM
from src.v.nn.features.memory_tracker import MemoryTracker, MEMORY_TRACKER_DIM, MEMORY_TRACKER_DIM_V061

logger = logging.getLogger("bc_dataset")

# GUA-054 升级（2026-06-17）：EFFECTIVE_FEATURE_DIM 220 → 229（24 → 33，含 grouping_score 9 维）
# 229 = 124(static) + 64(dynamic) + 8(belief) + 24(MT_GUA052) + 9(grouping_GUA054)
EFFECTIVE_FEATURE_DIM = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM + MEMORY_TRACKER_DIM  # 124 + 64 + 8 + 33 = 229
# GUA-061 升级（2026-06-18）：229 → 268（grouping_engine 替换 grouping_scanner，+15 维）
# 268 = 124(static) + 64(dynamic) + 8(belief) + 24(MT_GUA052) + 24(grouping_GUA061) + 24(extra pad)
EFFECTIVE_FEATURE_DIM_V061 = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM + MEMORY_TRACKER_DIM_V061  # 124+64+8+48=244
TARGET_FEATURE_DIM = 512
TARGET_ACTION_DIM = 512
RECORD_DIR = Path("game_records")

# ── 工具函数 ──────────────────────────────────────────


# GUA-061 牌格式标准化（历史数据 BJ/RJ → 平台原生 SB/HR）
_LEGACY_NORMALIZE = {"BJ": "SB", "RJ": "HR"}


def _normalize_cards(cards: List[str]) -> List[str]:
    """标准化牌面格式，将旧编码 BJ→SB, RJ→HR。"""
    return [_LEGACY_NORMALIZE.get(c, c) for c in cards]


def _get_victory_num(game_data: Dict[str, Any]) -> Optional[List[int]]:
    """从 game_data 中提取 victoryNum（兼容多种存储位置）。"""
    # result 字段
    result = game_data.get("result") or {}
    vn = result.get("victoryNum") or game_data.get("victoryNum")
    if vn and isinstance(vn, (list, tuple)) and len(vn) == 4:
        return list(vn)
    # game_info 中的胜利信息
    return None


def _filter_by_victory_num(game_data: Dict[str, Any]) -> bool:
    """检查是否满足 victoryNum[0] >= 2（M3 团队 A 胜率 ≥2/3）。"""
    vn = _get_victory_num(game_data)
    if vn is None:
        # 无 victoryNum → 默认保留（兼容非 batch 格式）
        return True
    # victoryNum[0] = 0号位赢的局数，victoryNum[2] = 2号位赢的局数
    # 同队 [0] == [2]
    team_a_wins = vn[0]
    return team_a_wins >= 2


def _build_memory_tracker_state(game_state: Dict[str, Any],
                                 use_grouping_engine: bool = False) -> List[float]:
    """
    从 game_state 构建 memory_tracker 并返回 state_vector。

    GUA-054 模式（默认）：33 维（GUA-052 24 + GUA-054 9）
    GUA-061 模式（use_grouping_engine=True）：48 维（GUA-052 24 + GUA-061 24）

    replay 逻辑：
      1. 初始化 tracker（手牌 + curRank）
      2. 从 history/recentPlays 回放每步出牌
      3. get_state_vector(game_state) 拼接组牌特征
    """
    try:
        my_pos = game_state.get("myPos", 0)
        hand_cards = game_state.get("handCards", [])
        cur_rank = str(game_state.get("curRank", "2"))

        tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0,
                                use_grouping_engine=use_grouping_engine)
        if hand_cards:
            tracker.init_from_hand(hand_cards)
        tracker.set_level_rank(cur_rank)

        # 回放 history
        history = game_state.get("history", [])
        for h in history:
            seat = h.get("pos", h.get("seat", -1))
            if seat < 0:
                continue
            action = h.get("action") or h.get("curAction") or []
            ctx = h.get("context") or {}
            if action:
                tracker.record_play(seat, action, context=ctx)

        tracker.sync_tribute_phase_from_state(
            tribute_result=game_state.get("tributeResult"),
            back_result=game_state.get("backResult"),
            anti_pos=game_state.get("antiPos"),
            cur_rank=cur_rank,
        )

        # 回放 recentPlays
        recent = game_state.get("recentPlays", [])
        for rp in recent:
            seat = rp.get("pos", -1)
            if seat < 0:
                continue
            cards = rp.get("cards", [])
            if cards:
                action_type = rp.get("type", "Unknown")
                tracker.record_play(seat, [action_type, "", cards])

        return tracker.get_state_vector(game_state=game_state)
    except Exception:
        default_dim = MEMORY_TRACKER_DIM_V061 if use_grouping_engine else MEMORY_TRACKER_DIM
        return [0.0] * default_dim


def _reconstruct_features_from_full_state(
    full_state: Dict[str, Any],
    use_grouping_engine: bool = False,
) -> Optional[np.ndarray]:
    """从 full_state 重建 512 维特征向量。

    GUA-054 模式（默认）：
      0-123:     extract_static_features (124)
      124-187:   extract_dynamic_features (64)
      188-195:   extract_state_belief (8)
      196-228:   _build_memory_tracker_state (33) — GUA-052 24 + GUA-054 9

    GUA-061 模式（use_grouping_engine=True）：
      0-123:     extract_static_features (124)
      124-187:   extract_dynamic_features (64)
      188-195:   extract_state_belief (8)
      196-243:   _build_memory_tracker_state (48) — GUA-052 24 + GUA-061 24
    """
    try:
        static_features = extract_static_features(full_state)
        features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
        features[:STATIC_STATE_DIM] = static_features

        # GUA-037b: 叠加 LSTM 动态编码
        try:
            dynamic_features = extract_dynamic_features(full_state, static_features)
            features[STATIC_STATE_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM] = dynamic_features
        except Exception:
            pass

        # GUA-050: 叠加局面信念向量（188-195 维）
        try:
            belief = extract_state_belief(full_state)
            belief_start = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM
            features[belief_start:belief_start + BELIEF_DIM] = belief
        except Exception:
            pass

        # GUA-052 + GUA-054/061: 叠加记忆追踪 + 组牌特征
        try:
            mt_state = _build_memory_tracker_state(full_state, use_grouping_engine=use_grouping_engine)
            mt_start = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM
            mt_dim = MEMORY_TRACKER_DIM_V061 if use_grouping_engine else MEMORY_TRACKER_DIM
            features[mt_start:mt_start + mt_dim] = mt_state
        except Exception:
            pass

        return features
    except Exception as e:
        logger.debug("full_state 特征重建失败: %s", e)
        return None


def _reconstruct_features_from_my_decision(
    my_decision: Dict[str, Any],
    game_info: Optional[Dict[str, Any]] = None,
    use_grouping_engine: bool = False,
    current_hand_cards: Optional[List[str]] = None,
) -> Optional[np.ndarray]:
    """从 my_decisions 条目 + game_info 尽力重建特征（GUA-037a 静态 + GUA-037b 动态 + GUA-050 信念）。

    这是 M3 旧格式的 fallback，缺少 handCards 和完整 actionList。
    构造一个最小可用状态用于 extract_static_features（大部分维为 0）。

    GUA-061 升级：current_hand_cards 从 initial_hand - 历史出牌重建，
    使 grouping_engine 24 维特征可计算。
    """
    ctx = my_decision.get("context") or {}
    action = my_decision.get("action") or []
    stage = ctx.get("stage", "play")

    # GUA-061: 用重建的 handCards 替换空列表
    hand_cards = current_hand_cards if current_hand_cards is not None else []

    # 伪造 state 字典，尽可能从 context 中提取信息
    fake_state: Dict[str, Any] = {
        "handCards": hand_cards,
        "actionList": [],
        "myPos": ctx.get("myPos", 0),
        "curPos": ctx.get("curPos", -1),
        "greaterPos": ctx.get("greaterPos", -1),
        "curRank": ctx.get("curRank", "2"),
        "stage": stage,
    }

    if game_info:
        fake_state.setdefault("selfRank", game_info.get("selfRank", "2"))
        fake_state.setdefault("oppoRank", game_info.get("oppoRank", "2"))
        fake_state.setdefault("curRank", game_info.get("curRank", "2"))
    else:
        fake_state["selfRank"] = ctx.get("selfRank", "2")
        fake_state["oppoRank"] = ctx.get("oppoRank", "2")

    try:
        static_features = extract_static_features(fake_state)
        features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
        features[:STATIC_STATE_DIM] = static_features

        # GUA-037b: 叠加 LSTM 动态编码（M3 旧格式通常无出牌历史，动态特征退化为零）
        try:
            dynamic_features = extract_dynamic_features(fake_state, static_features)
            features[STATIC_STATE_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM] = dynamic_features
        except Exception:
            pass

        # GUA-050: 叠加局面信念向量（188-195 维）
        try:
            belief = extract_state_belief(fake_state)
            belief_start = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM
            features[belief_start:belief_start + BELIEF_DIM] = belief
        except Exception:
            pass

        # GUA-052 + GUA-054/061: 叠加记忆追踪状态向量（M3 旧格式无出牌历史 → fallback 零向量）
        try:
            mt_state = _build_memory_tracker_state(fake_state, use_grouping_engine=use_grouping_engine)
            mt_start = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM
            mt_dim = MEMORY_TRACKER_DIM_V061 if use_grouping_engine else MEMORY_TRACKER_DIM
            features[mt_start:mt_start + mt_dim] = mt_state
        except Exception:
            pass

        return features
    except Exception as e:
        logger.debug("my_decision 特征重建失败: %s", e)
        return None


def _is_yf_player(player_name: str) -> bool:
    """检查是否为 yf 系列玩家（yf1_m3, yf2_m3, yf1_v7, yf2_v7 等）。"""
    name = (player_name or "").lower()
    return name.startswith("yf1") or name.startswith("yf2")


# ── 样本与数据集 ──────────────────────────────────────


class BCSample:
    """单条 BC 训练样本。"""

    def __init__(self, features: np.ndarray, action_index: int,
                 action_list_size: int, source_file: str):
        assert features.shape == (TARGET_FEATURE_DIM,), \
            f"特征维度异常: {features.shape}"
        self.features = features  # (512,) float32
        self.action_index = action_index  # 选中的动作在 actionList 中的下标
        self.action_list_size = action_list_size  # 有效动作数
        self.source_file = source_file

    def __repr__(self) -> str:
        return (f"BCSample(idx={self.action_index}, "
                f"act_size={self.action_list_size}, "
                f"src={Path(self.source_file).name})")


def load_samples(
    record_dir: str = "game_records",
    max_records: Optional[int] = None,
    require_victory_filter: bool = True,
    player_filter: Optional[str] = None,
    use_grouping_engine: bool = False,
) -> List[BCSample]:
    """从 game_records 加载 BC 训练样本。

    Args:
        record_dir: game_records 目录
        max_records: 最多读取的记录数（用于快速测试）
        require_victory_filter: 是否要求 victoryNum[0] >= 2
        player_filter: 玩家名过滤（如 "yf1_m3"），None 表示所有 yf 玩家
        use_grouping_engine: 是否使用 GUA-061 grouping_engine 24 维特征（默认 False=GUA-054 9 维）

    Returns:
        BCSample 列表
    """
    samples: List[BCSample] = []
    record_path = Path(record_dir)
    if not record_path.exists():
        logger.warning("录牌目录不存在: %s", record_dir)
        return samples

    json_files = sorted(record_path.glob("*.json"))
    if max_records:
        json_files = json_files[:max_records]

    loaded = 0
    skipped_vn = 0
    skipped_player = 0
    skipped_feature = 0

    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                game_data = json.load(f)
        except Exception as e:
            logger.debug("跳过文件 %s: %s", fp.name, e)
            continue

        # 玩家名过滤
        player_name = game_data.get("player_name", "")
        if player_filter:
            if player_name != player_filter:
                skipped_player += 1
                continue
        elif not _is_yf_player(player_name):
            skipped_player += 1
            continue

        # victoryNum 过滤（仅 M3 批次数据可用）
        if require_victory_filter and not _filter_by_victory_num(game_data):
            skipped_vn += 1
            continue

        game_info = game_data.get("game_info") or {}

        # 策略 1：从 steps[].full_state 重建（V7-internal 录牌格式）
        steps = game_data.get("steps")
        if steps and isinstance(steps, list):
            for step in steps:
                full_state = step.get("full_state")
                if not full_state:
                    continue
                features = _reconstruct_features_from_full_state(full_state, use_grouping_engine=use_grouping_engine)
                if features is None:
                    skipped_feature += 1
                    continue
                action_index = step.get("action_index", 0)
                if action_index >= TARGET_ACTION_DIM:
                    continue  # 超出模型输出维度，跳过（M3 硬编码枚举上限 1085 < 2048）
                action_list_size = full_state.get("actionList_size", 0)
                if action_list_size <= 1:
                    continue  # 单动作决策无学习意义
                samples.append(BCSample(
                    features=features,
                    action_index=action_index,
                    action_list_size=action_list_size,
                    source_file=str(fp),
                ))
            loaded += 1
            continue

        # 策略 2：从 my_decisions 重建（M3 旧格式 / V7 录牌格式）
        my_decisions = game_data.get("my_decisions")
        if my_decisions and isinstance(my_decisions, list):
            # GUA-061: 从 initial_hand 重建每步手牌（旧编码 BJ→SB, RJ→HR）
            initial_hand = _normalize_cards(game_data.get("initial_hand", []) or [])
            # GUA-076 fix: 用 Counter 替代 set 追踪已出牌，正确处理重复牌
            # （set 无法区分两张相同的牌，导致 current_hand 少算）
            from collections import Counter
            played_cards: Counter = Counter()
            for dec in my_decisions:
                ctx = dec.get("context") or {}

                # 优先用 ctx.handCards（平台每步记录的准确手牌）
                ctx_hand = ctx.get("handCards")
                if ctx_hand and isinstance(ctx_hand, list) and len(ctx_hand) > 0:
                    current_hand = _normalize_cards(ctx_hand)
                else:
                    # Fallback: 从 initial_hand 减去已出牌（Counter 正确处理重复）
                    current_hand = []
                    for c in initial_hand:
                        if played_cards.get(c, 0) > 0:
                            played_cards[c] -= 1
                        else:
                            current_hand.append(c)

                # 只保留 play 阶段
                if ctx.get("stage") not in (None, "", "play"):
                    # 非 play 阶段也要更新 played_cards（如 gang）
                    action = dec.get("action") or []
                    if len(action) >= 3 and isinstance(action[2], list):
                        for c in _normalize_cards(action[2]):
                            played_cards[c] += 1
                    continue
                action_index = dec.get("action_index")
                if action_index is None or action_index >= TARGET_ACTION_DIM:
                    continue  # 超出模型输出维度，跳过（M3 硬编码枚举上限 1085 < 2048）
                action_list_size = ctx.get("actionList_size", 0)
                if action_list_size <= 1:
                    continue

                # 优先从 context 中找完整 state
                full_state = ctx.get("full_state")
                if full_state:
                    features = _reconstruct_features_from_full_state(full_state, use_grouping_engine=use_grouping_engine)
                else:
                    features = _reconstruct_features_from_my_decision(
                        dec, game_info,
                        use_grouping_engine=use_grouping_engine,
                        current_hand_cards=current_hand,
                    )

                if features is None:
                    skipped_feature += 1
                    # 仍然更新 played_cards
                    action = dec.get("action") or []
                    if len(action) >= 3 and isinstance(action[2], list):
                        for c in _normalize_cards(action[2]):
                            played_cards[c] += 1
                    continue

                samples.append(BCSample(
                    features=features,
                    action_index=action_index,
                    action_list_size=action_list_size,
                    source_file=str(fp),
                ))

                # 更新 played_cards
                action = dec.get("action") or []
                if len(action) >= 3 and isinstance(action[2], list):
                    for c in _normalize_cards(action[2]):
                        played_cards[c] += 1
            loaded += 1
            continue

    logger.info(
        "BC 数据集加载: %d 样本 (来自 %d 记录, "
        "跳过: VN=%d 玩家=%d 特征=%d)",
        len(samples), loaded,
        skipped_vn, skipped_player, skipped_feature,
    )
    return samples


def train_val_split(
    samples: List[BCSample],
    val_ratio: float = 0.2,
    shuffle: bool = True,
    seed: int = 42,
) -> Tuple[List[BCSample], List[BCSample]]:
    """8:2 训练/验证集切分。

    Args:
        samples: 样本列表
        val_ratio: 验证集比例
        shuffle: 是否打乱
        seed: 随机种子

    Returns:
        (train_samples, val_samples)
    """
    indices = list(range(len(samples)))
    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(indices)

    split = max(1, int(len(samples) * val_ratio))
    val_idx = set(indices[:split])
    train_samples = [s for i, s in enumerate(samples) if i not in val_idx]
    val_samples = [s for i, s in enumerate(samples) if i in val_idx]

    logger.info(
        "数据集切分: 训练 %d / 验证 %d (%.1f:%.1f)",
        len(train_samples), len(val_samples),
        (1 - val_ratio) * 100, val_ratio * 100,
    )
    return train_samples, val_samples


# ── PyTorch Dataset 封装 ─────────────────────────────


def _collate_samples(samples: List[BCSample]) -> Dict[str, Any]:
    """将 BCSample 列表转为训练 batch。

    Returns:
        {
            "features": np.ndarray (batch, 512),
            "action_indices": np.ndarray (batch,),
            "action_list_sizes": np.ndarray (batch,),
        }
    """
    batch_size = len(samples)
    features = np.zeros((batch_size, TARGET_FEATURE_DIM), dtype=np.float32)
    action_indices = np.zeros(batch_size, dtype=np.int64)
    action_list_sizes = np.zeros(batch_size, dtype=np.int64)

    for i, s in enumerate(samples):
        features[i] = s.features
        action_indices[i] = s.action_index
        action_list_sizes[i] = s.action_list_size

    return {
        "features": features,
        "action_indices": action_indices,
        "action_list_sizes": action_list_sizes,
    }


def create_batches(
    samples: List[BCSample],
    batch_size: int = 64,
    shuffle: bool = True,
    seed: int = 42,
):
    """创建 mini-batch 生成器。

    Args:
        samples: 样本列表
        batch_size: 批大小
        shuffle: 是否打乱 epoch
        seed: 随机种子

    Yields:
        batch_dict: 包含 features, action_indices, action_list_sizes
    """
    indices = list(range(len(samples)))
    rng = random.Random(seed)

    while True:
        if shuffle:
            rng.shuffle(indices)
        for start in range(0, len(indices), batch_size):
            batch_idx = indices[start:start + batch_size]
            batch_samples = [samples[i] for i in batch_idx]
            yield _collate_samples(batch_samples)
        if not shuffle:
            break