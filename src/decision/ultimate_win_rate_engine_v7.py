# -*- coding: utf-8 -*-
"""
Ultimate Win Rate Decision Engine V7
终极胜率导向决策引擎 V7版本
基于终极胜率导向训练模型的决策引擎
"""

import os
import torch
import torch.nn as nn
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import sys

from src.contracts.decision_provider import ActMessage, assert_v_integration_gate

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27

from src.v.nn.features.static_features import extract_static_features, STATIC_STATE_DIM, extract_state_belief, BELIEF_DIM
from src.v.nn.features.dynamic_features import extract_dynamic_features, DYNAMIC_HIDDEN_DIM
from src.v.nn.features.belief_state import extract_situation_vector, SITUATION_DIM
from src.v.nn.guards import filter_action_list, validate_decision

class UltimateWinRateEngineV7:
    """
    终极胜率导向决策引擎 V7
    使用训练好的终极胜率导向模型进行决策
    """
    
    def __init__(self, player_id: int = 0):
        self.player_id = player_id
        self.logger = logging.getLogger(f"UltimateWinRateEngineV7.{player_id}")

        # 批跑四进程并行时避免每进程占满 CPU（可用 V7_TORCH_THREADS 覆盖）
        thread_count = int(os.environ.get("V7_TORCH_THREADS", "1"))
        torch.set_num_threads(max(1, thread_count))
        
        # 模型路径（config/v7_paths.yaml + 环境变量）
        from src.utils.v7_paths import get_model_file
        self.model_path = Path(get_model_file())
        
        # 初始化模型
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 决策统计（必须在 _load_model 前初始化，因其引用这些属性）
        self.decision_count = 0
        self.model_decisions = 0
        self.fallback_decisions = 0
        self.model_load_failures = 0  # GUA-037a: 模型加载失败计数器
        
        # 加载模型
        self._load_model()

        assert_v_integration_gate(self, label="UltimateWinRateEngineV7")
        
    def _load_model(self):
        """加载终极胜率导向模型"""
        try:
            if not self.model_path.exists():
                self.model_load_failures += 1
                self.logger.error(f"[GUA-037a] 终极胜率导向模型未找到！模型路径: {self.model_path} — 将使用规则引擎回退（model_load_failures={self.model_load_failures}）")
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
            self.model_load_failures += 1
            self.logger.error(f"[GUA-037a] 模型加载失败: {e} — model_load_failures={self.model_load_failures}")
            self.model = None
            return False
    
    def decide(self, message: ActMessage) -> int:
        """
        做出决策（IDecisionProvider v1.0）
        
        Args:
            message: 平台 act 消息（含 actionList 等）
            
        Returns:
            选择的 actionList 下标
        """
        game_state = message
        self.decision_count += 1

        action_list = game_state.get("actionList", [])
        if not action_list:
            return 0

        try:
            # ── GUA-045: 应用 P0 Guard 过滤 ──
            filtered_actions, action_map = filter_action_list(game_state)
            if not filtered_actions:
                filtered_actions = action_list
                action_map = list(range(len(action_list)))

            # 如果模型可用，使用模型决策
            if self.model is not None:
                # 在 filtered_actions 上做模型推理
                filtered_index = self._model_decision(game_state, filtered_actions)
                if filtered_index is not None:
                    # GUA-045: 校验决策（覆盖不合理选择）
                    safe_idx = validate_decision(
                        filtered_index, filtered_actions, game_state,
                        original_action_list=action_list,
                    )
                    # 映射回原始 actionList 下标
                    if safe_idx < len(action_map):
                        original_index = action_map[safe_idx]
                    else:
                        original_index = safe_idx
                    self.model_decisions += 1
                    return original_index

            # 回退到规则引擎
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)

        except Exception as e:
            self.logger.error(f"✗ 决策失败: {e}", exc_info=True)
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)
    
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
            # 提取特征
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
        从游戏状态中提取特征（GUA-037a 静态 + GUA-037b 动态 LSTM）。

        GUA-037b 改造后（GUA-050 追加信念）：
          - 前 124 维 = state_牌态（extract_static_features）
          - 124-187 维 = LSTM 动态编码（extract_dynamic_features, 64 维）
          - 188-195 维 = 局面信念向量（extract_state_belief, 8 维；GUA-050）
          - 196-511 维 = 零填充（待 GUA-038 模型重训后替换）
          - 总输出仍为 512 维（保持与现有 UltimateWinRateNet 架构兼容）
          - 有效特征: 196 维（利用率 196/512 = 38.3%；GUA-050 增 8 维信念）

        Args:
            game_state: 游戏状态
            action_list: 可选动作列表

        Returns:
            512 维 float32 数组，失败返回 None
        """
        try:
            # GUA-037a: 124 维静态特征（牌态）
            static_features = extract_static_features(game_state)
            assert static_features.shape == (STATIC_STATE_DIM,), \
                f"静态特征维度异常: {static_features.shape}"

            # 填充至 512 维
            target_size = 512
            features = np.zeros(target_size, dtype=np.float32)
            features[:STATIC_STATE_DIM] = static_features

            # GUA-037b: 64 维动态特征（LSTM 历史编码）
            try:
                dynamic_features = extract_dynamic_features(game_state, static_features)
                assert dynamic_features.shape == (DYNAMIC_HIDDEN_DIM,), \
                    f"动态特征维度异常: {dynamic_features.shape}"
                features[STATIC_STATE_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM] = dynamic_features
            except Exception as dyn_e:
                self.logger.debug(f"[GUA-037b] 动态特征提取失败(回退零填充): {dyn_e}")

            # GUA-050: 8 维局面信念向量（放置在 dynamic 之后，188-195）
            try:
                belief = extract_state_belief(game_state)
                assert len(belief) == BELIEF_DIM, \
                    f"信念向量维度异常: {len(belief)}"
                belief_start = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM  # 124 + 64 = 188
                features[belief_start:belief_start + BELIEF_DIM] = belief
            except Exception as bel_e:
                self.logger.debug(f"[GUA-050] 信念提取失败(回退零填充): {bel_e}")

            return features

        except Exception as e:
            self.logger.error(f"特征提取失败: {e}", exc_info=True)
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
                if isinstance(action, list) and len(action) > 0 and action[0] != "PASS":
                    return i
                elif isinstance(action, str) and action.upper() != "PASS":
                    return i
            
            # 如果都是PASS，返回第一个
            return 0
            
        except Exception as e:
            self.logger.error(f"规则决策失败: {e}", exc_info=True)
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