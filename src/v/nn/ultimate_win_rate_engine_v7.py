# -*- coding: utf-8 -*-
"""
Ultimate Win Rate Decision Engine V7
终极胜率导向决策引擎 V7版本
基于终极胜率导向训练模型的决策引擎
"""

import torch
import torch.nn as nn
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27

# 特征工程（与 bc_dataset.py 训练管线对齐）
try:
    from src.v.nn.features.static_features import (
        extract_static_features, STATIC_STATE_DIM,
        extract_state_belief, BELIEF_DIM,
    )
    from src.v.nn.features.dynamic_features import extract_dynamic_features, DYNAMIC_HIDDEN_DIM
    from src.v.nn.features.memory_tracker import MemoryTracker, MEMORY_TRACKER_DIM
    FEATURE_IMPORT_OK = True
except ImportError as e:
    FEATURE_IMPORT_OK = False
    print(f"[Warning] 特征工程导入失败: {e}, 使用简化特征")

TARGET_FEATURE_DIM = 512  # 与 bc_dataset.py 一致

class UltimateWinRateEngineV7:
    """
    终极胜率导向决策引擎 V7
    使用训练好的终极胜率导向模型进行决策

    特征管线（与 bc_dataset.py 训练对齐）：
      0-123:   extract_static_features (124)
      124-187: extract_dynamic_features (64)
      188-195: extract_state_belief (8)  — GUA-050
      196-219: MemoryTracker.state_vector (24) — GUA-052
    """

    def __init__(self, player_id: int = 0):
        self.player_id = player_id
        self.logger = logging.getLogger(f"UltimateWinRateEngineV7.{player_id}")

        # 模型路径（使用M3胜局训练的新模型）
        self.model_path = Path(__file__).parent.parent.parent / "models" / "v-nn" / "bc_model_v2.pth"

        # 初始化模型
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 加载模型
        self._load_model()

        # 决策统计
        self.decision_count = 0
        self.model_decisions = 0
        self.fallback_decisions = 0

        # GUA-052: MemoryTracker 实例（跨决策状态）
        self._tracker = None
        self._tracker_initialized = False
        
    def _load_model(self):
        """加载终极胜率导向模型"""
        try:
            if not self.model_path.exists():
                self.logger.warning(f"[警告] 终极胜率导向模型未找到！模型路径: {self.model_path}")
                self.logger.warning("将使用规则引擎作为回退")
                return False
            
            # 加载模型
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 创建模型架构（与训练时一致的UltimateWinRateNet）
            from src.train.ultimate_win_rate_training import UltimateWinRateNet
            self.model = UltimateWinRateNet().to(self.device)
            
            # 加载权重
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            
            self.model.eval()
            
            self.logger.info(f"✓ 终极胜率导向模型加载成功: {self.model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ 模型加载失败: {e}")
            self.model = None
            return False
    
    def decide(self, game_state: Dict[str, Any]) -> int:
        """
        做出决策
        
        Args:
            game_state: 游戏状态
            
        Returns:
            选择的动作索引
        """
        self.decision_count += 1
        
        action_list = game_state.get("actionList", [])
        if not action_list:
            return 0
        
        try:
            # 如果模型可用，使用模型决策
            if self.model is not None:
                action_index = self._model_decision(game_state, action_list)
                if action_index is not None:
                    self.model_decisions += 1
                    return action_index
            
            # 回退到规则引擎
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)
            
        except Exception as e:
            self.logger.error(f"✗ 决策失败: {e}")
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)
    
    def _replay_history_to_tracker(self, game_state: Dict[str, Any]) -> None:
        """从 game_state 回放历史到 MemoryTracker。"""
        if not FEATURE_IMPORT_OK:
            return
        my_pos = game_state.get("myPos", self.player_id)
        hand_cards = game_state.get("handCards", [])
        cur_rank = str(game_state.get("curRank", "2"))

        if not self._tracker_initialized:
            self._tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0)
            if hand_cards:
                self._tracker.init_from_hand(hand_cards)
            self._tracker.set_level_rank(cur_rank)
            self._tracker_initialized = True

        # 回放 history
        history = game_state.get("history", [])
        for h in history:
            seat = h.get("pos", h.get("seat", -1))
            if seat < 0:
                continue
            action = h.get("action") or h.get("curAction") or []
            if action:
                self._tracker.record_play(seat, action)

        # 回放 recentPlays
        recent = game_state.get("recentPlays", [])
        for rp in recent:
            seat = rp.get("pos", -1)
            if seat < 0:
                continue
            cards = rp.get("cards", [])
            if cards:
                action_type = rp.get("type", "Unknown")
                self._tracker.record_play(seat, [action_type, "", cards])

    def _get_tracker_state(self) -> List[float]:
        """获取 MemoryTracker 状态向量。"""
        if not FEATURE_IMPORT_OK or self._tracker is None:
            return [0.0] * MEMORY_TRACKER_DIM
        try:
            return self._tracker.get_state_vector()
        except Exception:
            return [0.0] * MEMORY_TRACKER_DIM

    def _model_decision(self, game_state: Dict[str, Any], action_list: List) -> Optional[int]:
        """
        使用模型进行决策

        Args:
            game_state: 游戏状态
            action_list: 可选动作列表

        Returns:
            动作索引，如果失败返回None
        """
        try:
            # 提取特征（与 bc_dataset.py 训练对齐）
            features = self._extract_features(game_state, action_list)
            if features is None:
                return None

            # 转换为张量
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)

            # 模型预测
            with torch.no_grad():
                predictions = self.model(features_tensor)
                action_logits = predictions['action_logits']
                probabilities = torch.softmax(action_logits, dim=-1)

            # 选择最佳动作
            action_probs = probabilities[0][:len(action_list)]
            best_action_idx = torch.argmax(action_probs).item()

            # 验证动作索引
            if 0 <= best_action_idx < len(action_list):
                confidence = action_probs[best_action_idx].item()
                self.logger.debug(f"模型决策: 动作{best_action_idx}, 置信度: {confidence:.3f}")
                return best_action_idx
            else:
                self.logger.warning(f"模型返回无效动作索引: {best_action_idx}")
                return None

        except Exception as e:
            self.logger.error(f"模型决策失败: {e}")
            return None

    def _extract_features(self, game_state: Dict[str, Any], action_list: List) -> Optional[np.ndarray]:
        """
        从游戏状态中提取 512 维特征向量（与 bc_dataset.py 训练管线对齐）。

        维度分段（512 维）：
          0-123:   extract_static_features (124)
          124-187: extract_dynamic_features (64)
          188-195: extract_state_belief (8)  — GUA-050
          196-219: MemoryTracker.state_vector (24) — GUA-052
        """
        try:
            if not FEATURE_IMPORT_OK:
                return self._fallback_extract(game_state)

            self._replay_history_to_tracker(game_state)

            static_features = extract_static_features(game_state)
            features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
            features[:STATIC_STATE_DIM] = static_features

            try:
                dynamic = extract_dynamic_features(game_state, static_features)
                features[STATIC_STATE_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM] = dynamic
            except Exception:
                pass

            try:
                belief = extract_state_belief(game_state)
                features[STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM] = belief
            except Exception:
                pass

            try:
                mt_state = self._get_tracker_state()
                mt_start = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM
                features[mt_start:mt_start + MEMORY_TRACKER_DIM] = mt_state
            except Exception:
                pass

            return features

        except Exception as e:
            self.logger.error(f"特征提取失败: {e}")
            return None

    def _fallback_extract(self, game_state: Dict[str, Any]) -> Optional[np.ndarray]:
        """Fallback 简化特征提取（特征工程导入失败时使用）。"""
        try:
            features = []
            my_pos = game_state.get("myPos", self.player_id)
            cur_pos = game_state.get("curPos", -1)
            greater_pos = game_state.get("greaterPos", -1)
            for pos, feat_list in [(my_pos, 4), (cur_pos, 4), (greater_pos, 4)]:
                feat = [0] * 4
                if 0 <= pos < 4:
                    feat[pos] = 1
                features.extend(feat)
            features.append(len(game_state.get("handCards", [])))
            public_info = game_state.get("publicInfo", [])
            for i in range(4):
                rest = DEFAULT_REST_CARDS
                if i < len(public_info) and isinstance(public_info[i], dict):
                    rest = public_info[i].get("rest", DEFAULT_REST_CARDS)
                features.append(rest)
            rank_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
                       "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
            for rk in ["curRank", "selfRank", "oppoRank"]:
                features.append(rank_map.get(game_state.get(rk, "2"), 2))
            features.append(len(game_state.get("actionList", [])))
            for fk in ["curAction", "greaterAction"]:
                features.append(len(game_state.get(fk, [])))
            if len(features) < TARGET_FEATURE_DIM:
                features.extend([0] * (TARGET_FEATURE_DIM - len(features)))
            else:
                features = features[:TARGET_FEATURE_DIM]
            return np.array(features, dtype=np.float32)
        except Exception as e:
            self.logger.error(f"Fallback 特征提取失败: {e}")
            return None

    def _rule_based_decision(self, game_state: Dict[str, Any], action_list: List) -> int:
        """
        基于规则的回退决策
        
        Args:
            game_state: 游戏状态
            action_list: 可选动作列表
            
        Returns:
            动作索引
        """
        try:
            # 简单的规则：优先选择非PASS动作
            for i, action in enumerate(action_list):
                if action and len(action) > 0:
                    if isinstance(action, list) and action[0] != "PASS":
                        return i
                    elif isinstance(action, str) and action.upper() != "PASS":
                        return i
            
            # 如果都是PASS，返回第一个
            return 0
            
        except Exception as e:
            self.logger.error(f"规则决策失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        return {
            "total_decisions": self.decision_count,
            "model_decisions": self.model_decisions,
            "fallback_decisions": self.fallback_decisions,
            "model_usage_rate": self.model_decisions / max(1, self.decision_count),
            "model_available": self.model is not None
        }